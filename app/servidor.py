# -*- coding: utf-8 -*-
"""
servidor.py  ·  La app local
============================
Arranca un pequeño servidor web en tu propio ordenador (solo accesible desde él,
en 127.0.0.1) y abre el navegador. Tus datos nunca salen de la carpeta mis_datos;
a internet solo se sale para descargar precios.
"""

import copy
import datetime as dt
import io
import json
import logging
import os
import re
import secrets
import shutil
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
import zipfile

from flask import Flask, Response, jsonify, request, send_from_directory
from werkzeug.serving import make_server

from . import almacen, buscar, exportar, importar, motor, plantilla


def _base_recursos():
    """Dónde viven los recursos de solo lectura (web, demo, VERSION). Al empaquetar
    con PyInstaller están en sys._MEIPASS; si no, en la carpeta del proyecto."""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _base_datos():
    """Dónde van los datos del usuario (mis_datos). Empaquetado:
      - Windows: JUNTO al ejecutable (portable, como siempre).
      - macOS: un .app es de solo lectura (más aún en /Aplicaciones o en cuarentena de
        Gatekeeper), así que van a la carpeta de datos del usuario, que persiste aunque
        muevas o reinstales la app: ~/Library/Application Support/Liberty.
    Sin empaquetar: la carpeta del proyecto."""
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            d = os.path.join(os.path.expanduser("~/Library/Application Support"), "Liberty")
            os.makedirs(d, exist_ok=True)
            return d
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


RAIZ = _base_recursos()
WEB = os.path.join(RAIZ, "app", "web")
DEMO = os.path.join(RAIZ, "demo", "cartera.json")
# Otra carpeta de datos, solo para pruebas o capturas: PATRIMONIO_DATOS=ruta
DATOS = os.environ.get("PATRIMONIO_DATOS") or os.path.join(_base_datos(), "mis_datos")
PUERTO = int(os.environ.get("PATRIMONIO_PUERTO") or 8765)
HORAS_PRECIOS = 6          # al arrancar, se actualizan si tienen más de esto

app = Flask(__name__, static_folder=None)
app.json.sort_keys = False   # respeta el orden de tipos y listas al mandarlos al navegador
cerrojo = threading.RLock()  # el motor no admite dos cálculos (ni dos escrituras) a la vez


@app.errorhandler(almacen.ErrorValidacion)
def _error_validacion(e):
    # Cualquier ErrorValidacion no capturado (p. ej. cartera.json dañado al leerlo)
    # se devuelve como 400 con mensaje claro, nunca como un 500 opaco.
    return jsonify(ok=False, errores=e.errores), 400


@app.errorhandler(Exception)
def _error_inesperado(e):
    # Red de seguridad: cualquier error no previsto se registra y se devuelve como
    # un 500 controlado, sin filtrar la traza. Los errores HTTP normales (404…) pasan.
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return e
    logging.exception("Error inesperado")
    return jsonify(ok=False, error="Ha ocurrido un error inesperado."), 500


# Cabecera de seguridad (CSP): el navegador solo ejecuta el JS de la propia app
# (script-src 'self', sin inline), así que un nombre con HTML inyectado no puede
# ejecutar código aunque se colara. Se permiten los estilos inline (no ejecutan
# JS) y las conexiones del navegador a las fuentes de precio en vivo.
CSP = ("default-src 'self'; "
       "script-src 'self'; "
       "style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; "
       "connect-src 'self' https://api.binance.com https://api.coingecko.com; "
       "base-uri 'self'; object-src 'none'; frame-ancestors 'none'")


@app.before_request
def _solo_local():
    # 100% local: solo atendemos peticiones de este ordenador. Así una web externa
    # abierta en el navegador no puede provocar efectos (borrar, reiniciar…) contra
    # 127.0.0.1, ni valdría un ataque de DNS-rebinding (no se valida solo por IP).
    host = (request.host or "").rsplit(":", 1)[0].strip("[]").lower()
    if host and host not in ("127.0.0.1", "localhost", "::1"):
        return jsonify(ok=False, error="Esta aplicación solo responde en tu propio ordenador."), 403
    return None


@app.after_request
def _cabeceras_seguridad(resp):
    resp.headers.setdefault("Content-Security-Policy", CSP)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    return resp


# ---------------------------------------------------------------- archivos

def lee_json(ruta, defecto=None):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecto


def escribe_json(ruta, datos):
    """Escribe en un archivo temporal y lo renombra: si se corta, no se pierde nada."""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


# ---------------------------------------------------------------- carteras
# Estructura de mis_datos (ordenada y uniforme):
#   mis_datos/
#     carteras/<id>/   -> una carpeta por patrimonio (cartera.json, cálculo, cache, copias)
#     app/             -> datos internos de la app (registro.json: cuál está activa)
# Las versiones viejas dejaban una cartera suelta en mis_datos/cartera.json y
# registro.json en la raíz; migra_layout() lo reordena solo al arrancar (sin borrar).

def _carteras_dir():
    return os.path.join(DATOS, "carteras")


def _app_dir():
    return os.path.join(DATOS, "app")


def _demo_dir():
    # Archivos de trabajo de la DEMO (cálculo, estado, histórico, caché). Van dentro de
    # app/ para que la raíz de mis_datos tenga SOLO app/ y carteras/.
    return os.path.join(_app_dir(), "demo")


def registro():
    # Nuevo sitio (app/registro.json); si no, el de la raíz (layout antiguo).
    r = lee_json(os.path.join(_app_dir(), "registro.json"))
    if r is None:
        r = lee_json(os.path.join(DATOS, "registro.json"))
    return r or {}


def guarda_registro(reg):
    # Fusiona sobre lo que haya (no reemplaza), para no perder otras claves futuras.
    base = registro()
    base.update(reg)
    escribe_json(os.path.join(_app_dir(), "registro.json"), base)


def asegura_multi():
    """Pasa del modo antiguo (cartera.json suelto en DATOS) al multi: mueve esa
    cartera a carteras/<id>/ y la deja activa. No hace nada si ya es multi."""
    if os.path.isdir(_carteras_dir()):
        return
    suelta = os.path.join(DATOS, "cartera.json")
    if not os.path.exists(suelta):
        return
    cfg = lee_json(suelta, {}) or {}
    cid = almacen.slug(cfg.get("titular") or "cartera", set())
    destino = os.path.join(_carteras_dir(), cid)
    os.makedirs(destino, exist_ok=True)
    # Mueve los archivos de la cartera suelta a su carpeta; deja fuera lo que es
    # estructura (carteras/, app/) y el registro (ambos sitios).
    for n in os.listdir(DATOS):
        if n not in ("carteras", "app", "registro.json"):
            os.replace(os.path.join(DATOS, n), os.path.join(destino, n))
    guarda_registro({"activa": cid})


def migra_layout():
    """Reordena mis_datos al layout nuevo. Idempotente y no destructiva (solo mueve):
    se puede llamar en cada arranque sin efectos si ya está ordenado."""
    try:
        viejo_reg = os.path.join(DATOS, "registro.json")
        nuevo_reg = os.path.join(_app_dir(), "registro.json")
        if os.path.exists(viejo_reg) and not os.path.exists(nuevo_reg):
            os.makedirs(_app_dir(), exist_ok=True)
            os.replace(viejo_reg, nuevo_reg)
        asegura_multi()       # cartera suelta del modo antiguo -> carteras/<id>/
        _migra_demo_a_app()   # archivos de la demo sueltos en la raíz -> app/demo/
    except OSError:
        pass   # si algo está bloqueado, se intentará en el próximo arranque


def _migra_demo_a_app():
    """Mueve a app/demo/ los archivos de trabajo de la demo que las versiones anteriores
    dejaban sueltos en la raíz de mis_datos (cálculo, estado, histórico y caché). Solo
    mueve si existe el origen y NO existe el destino: idempotente y no destructivo."""
    destino = _demo_dir()
    for n in ("calculado_demo.json", "estado.json", "historico.json", "cache"):
        viejo, nuevo = os.path.join(DATOS, n), os.path.join(destino, n)
        if os.path.exists(viejo) and not os.path.exists(nuevo):
            os.makedirs(destino, exist_ok=True)
            os.replace(viejo, nuevo)


def carteras():
    """Carteras disponibles en DATOS/carteras/<id>/ (modo multi)."""
    out = []
    base = _carteras_dir()
    if os.path.isdir(base):
        for cid in sorted(os.listdir(base)):
            cfg = lee_json(os.path.join(base, cid, "cartera.json"))
            if cfg is not None:
                out.append({"id": cid, "nombre": cfg.get("titular") or cid})
    return out


def id_activa():
    lst = carteras()
    if not lst:
        return None
    ids = {c["id"] for c in lst}
    act = registro().get("activa")
    return act if act in ids else lst[0]["id"]


def dir_activa():
    """Carpeta de la cartera activa: carteras/<id>/ (multi), DATOS (modo antiguo con
    cartera.json suelto) o None (demo, sin ninguna cartera)."""
    cid = id_activa()
    if cid:
        return os.path.join(_carteras_dir(), cid)
    if os.path.exists(os.path.join(DATOS, "cartera.json")):
        return DATOS
    return None


def carpeta():
    """Dónde leer/escribir cartera, cálculo, estado y copias. En demo, app/demo/."""
    return dir_activa() or _demo_dir()


def modo():
    return "propio" if dir_activa() else "demo"


def cartera():
    d = dir_activa()
    return lee_json(os.path.join(d, "cartera.json"), {}) if d else lee_json(DEMO, {})


def ruta_calculado():
    return os.path.join(carpeta(), f"calculado_{modo()}.json")


def estado():
    return lee_json(os.path.join(carpeta(), "estado.json"), {})


# ---------------------------------------------------------------- cálculo

def recalcula(descargar):
    """Recalcula el panel. Con descargar=True baja antes los precios nuevos;
    con "faltan", solo los de productos que aún no tienen precios guardados."""
    with cerrojo:
        datos = motor.construir(cartera(), carpeta(), descargar=descargar)
        est = estado()
        if descargar is True:
            est["preciosActualizados"] = dt.datetime.now().replace(microsecond=0).isoformat()
            escribe_json(os.path.join(carpeta(), "estado.json"), est)
        if datos is not None:
            datos["modo"] = modo()
            datos["preciosActualizados"] = est.get("preciosActualizados")
        escribe_json(ruta_calculado(), datos)
        return datos


def precios_viejos():
    ultima = estado().get("preciosActualizados")
    if not ultima or not os.path.exists(ruta_calculado()):
        return True
    try:
        return dt.datetime.now() - dt.datetime.fromisoformat(ultima) > dt.timedelta(hours=HORAS_PRECIOS)
    except (ValueError, TypeError):
        return True   # estado.json con fecha corrupta: tratamos como "hay que actualizar"


# ---------------------------------------------------------------- rutas

@app.get("/")
def inicio():
    return send_from_directory(WEB, "index.html")


@app.get("/datos.js")
def datos_js():
    # Vista de un mes pasado: recalcula el panel como estaba a fin de ese mes, sin
    # persistir nada ni salir a la red (usa los precios de la caché).
    hasta = request.args.get("hasta")
    # Acepta un mes (AAAA-MM, fin de mes) o un día concreto (AAAA-MM-DD).
    if hasta and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])(-(0[1-9]|[12]\d|3[01]))?", hasta):
        with cerrojo:
            datos = motor.construir(cartera(), carpeta(), descargar=False, hasta=hasta)
        if datos is not None:
            datos["modo"] = modo()
    else:
        datos = lee_json(ruta_calculado())
        if datos is None and not os.path.exists(ruta_calculado()):
            datos = recalcula(descargar=False)
    cuerpo = "window.DATOS = " + json.dumps(datos, ensure_ascii=False, separators=(",", ":")) + ";\n"
    return Response(cuerpo, mimetype="application/javascript",
                    headers={"Cache-Control": "no-store"})


@app.post("/api/actualizar")
def api_actualizar():
    try:
        datos = recalcula(descargar=True)
    except Exception as e:  # que la app no se caiga nunca por un precio
        logging.exception("Fallo al actualizar")
        return jsonify(ok=False, error=f"No he podido actualizar: {e}"), 500
    return jsonify(ok=True, avisos=(datos or {}).get("avisos", []))


@app.get("/api/cartera")
def api_cartera():
    cfg = cartera()
    # tipos = los de base no ocultos + los que haya creado el usuario (para los
    # selectores); tiposBase para que el editor sepa cuáles puede ocultar/renombrar.
    return jsonify(modo=modo(), cartera=cfg, tipos=motor.tipos_visibles(cfg),
                   tiposBase=motor.TIPOS, fuentes=motor.FUENTES, avisosCatalogo=motor.AVISOS_CATALOGO,
                   marcas=almacen.marcas_de(cfg),
                   tiposMovimiento=almacen.TIPOS_MOV, tiposFlujo=almacen.TIPOS_FLUJO)


@app.get("/api/buscar")
def api_buscar():
    return jsonify(resultados=buscar.buscar(request.args.get("q", "")))


GUARDAR = {"productos": almacen.guarda_producto, "movimientos": almacen.guarda_movimiento,
           "valoraciones": almacen.guarda_valoracion, "apartados": almacen.guarda_apartado,
           "flujos": almacen.guarda_flujo}
BORRAR = {"productos": almacen.borra_producto, "movimientos": almacen.borra_movimiento,
          "valoraciones": almacen.borra_valoracion, "apartados": almacen.borra_apartado,
          "flujos": almacen.borra_flujo}
AVISO_DEMO = ("Estás viendo el patrimonio de ejemplo. Pulsa «Empezar con mis datos» "
              "para crear el tuyo y poder guardar cambios.")


def cambia(fn, recalc=True):
    """Aplica un cambio a la cartera, la guarda (con copia automática) y, si procede,
    recalcula el panel. Con recalc=False (notas, tablero…) no se recalcula: esos datos
    no afectan a las cifras del panel y así van más ágiles."""
    if modo() == "demo":
        return jsonify(ok=False, errores=[AVISO_DEMO]), 403
    with cerrojo:
        ruta = os.path.join(carpeta(), "cartera.json")
        try:
            cfg = almacen.carga(ruta)
            item = fn(cfg)
        except almacen.ErrorValidacion as e:
            return jsonify(ok=False, errores=e.errores), 400
        almacen.guarda(ruta, cfg)
        datos = recalcula(descargar="faltan") if recalc else None
    return jsonify(ok=True, item=item, cartera=cfg, avisos=(datos or {}).get("avisos", []))


@app.post("/api/<coleccion>")
def api_guardar(coleccion):
    if coleccion not in GUARDAR:
        return jsonify(ok=False, errores=["No sé guardar eso."]), 404
    datos = request.get_json(silent=True) or {}

    if coleccion == "productos":
        # La comprobación del precio online es una llamada de red lenta: se hace
        # ANTES de tomar el cerrojo para no congelar el resto de la app. Para
        # saber la fuente/código normalizados y si cambian, se normaliza en una
        # copia (guarda_producto no sale a la red; la prueba la hace el servidor).
        if modo() != "demo":
            try:
                prod, cambio = almacen.guarda_producto(copy.deepcopy(cartera()), datos)
            except almacen.ErrorValidacion as e:
                return jsonify(ok=False, errores=e.errores), 400
            if cambio and prod["fuente"] != "manual" and not buscar.probar(prod["fuente"], prod["codigo"]):
                return jsonify(ok=False, errores=[
                    f"No encuentro precio para «{prod['codigo']}» en {motor.FUENTES[prod['fuente']]}. "
                    "Revisa el código con el buscador o elige «a mano» y anota tú su valor."]), 400
        return cambia(lambda cfg: almacen.guarda_producto(cfg, datos)[0])
    return cambia(lambda cfg: GUARDAR[coleccion](cfg, datos))


@app.delete("/api/<coleccion>/<ident>")
def api_borrar(coleccion, ident):
    if coleccion not in BORRAR:
        return jsonify(ok=False, errores=["No sé borrar eso."]), 404
    # Si el apunte tenía facturas, las CONSERVAMOS (son independientes del apunte):
    # se renombran a un nombre legible y se avisa al usuario de dónde quedan.
    adjs = []
    if coleccion == "flujos" and modo() != "demo":
        fl = next((x for x in cartera().get("flujos", []) if x.get("id") == ident), None)
        adjs = (fl or {}).get("adjuntos", []) or []
    resp = cambia(lambda cfg: BORRAR[coleccion](cfg, ident))
    if adjs and not isinstance(resp, tuple):   # tuple = error (jsonify, código); Response = OK
        huerfanos = _conserva_adjuntos_huerfanos(fl, adjs)
        if huerfanos["archivos"]:
            data = resp.get_json()
            data["adjuntosHuerfanos"] = huerfanos
            return jsonify(data)
    return resp


def _conserva_adjuntos_huerfanos(fl, adjs):
    """Al borrar un apunte, sus facturas NO se borran: se renombran a su nombre
    descriptivo (fecha - importe - concepto - original) en la carpeta «adjuntos», para
    que el usuario las encuentre. Devuelve la carpeta y los nombres finales."""
    adj_dir = os.path.join(carpeta(), "adjuntos")
    finales, usados = [], {n.lower() for n in os.listdir(adj_dir)} if os.path.isdir(adj_dir) else set()
    for a in adjs:
        origen = os.path.join(adj_dir, os.path.basename(a.get("archivo") or ""))
        if not os.path.exists(origen):
            continue
        destino = os.path.join(adj_dir, _nombre_factura(fl or {}, a, usados))
        try:
            os.rename(origen, destino)
            finales.append(os.path.basename(destino))
        except OSError:
            finales.append(os.path.basename(origen))
    return {"carpeta": os.path.abspath(adj_dir), "archivos": finales}


def _responde_con_huerfanos(resp, flujos_con_adj):
    """Tras un borrado en masa de apuntes, conserva las facturas de los borrados (igual
    que el borrado individual) y las añade a la respuesta. 'resp' tuple = error: se pasa tal cual."""
    if isinstance(resp, tuple):
        return resp
    archivos, carpeta_abs = [], None
    for fl in flujos_con_adj:
        h = _conserva_adjuntos_huerfanos(fl, fl.get("adjuntos") or [])
        archivos += h["archivos"]
        carpeta_abs = h["carpeta"]
    if archivos:
        data = resp.get_json()
        data["adjuntosHuerfanos"] = {"carpeta": carpeta_abs, "archivos": archivos}
        return jsonify(data)
    return resp


@app.post("/api/flujos-borrar")
def api_flujos_borrar():
    """Borra varios apuntes de ingreso/gasto a la vez (selección múltiple)."""
    d = request.get_json(silent=True) or {}
    ids = d.get("ids") or []
    conserva = []
    if modo() != "demo":
        porid = {x.get("id"): x for x in cartera().get("flujos", [])}
        conserva = [porid[i] for i in ids if i in porid and porid[i].get("adjuntos")]
    resp = cambia(lambda cfg: almacen.borra_flujos(cfg, ids))
    return _responde_con_huerfanos(resp, conserva)


@app.post("/api/movimientos-borrar")
def api_movimientos_borrar():
    """Borra varios movimientos a la vez (selección múltiple)."""
    d = request.get_json(silent=True) or {}
    return cambia(lambda cfg: almacen.borra_movimientos(cfg, d.get("ids") or []))


@app.post("/api/flujos-masa")
def api_flujos_masa():
    """Acciones en masa sobre ingresos y gastos por fecha: archivar/desarchivar (ocultar
    de la lista, reversible) o borrar permanentemente todo lo anterior a una fecha."""
    d = request.get_json(silent=True) or {}
    accion, hasta = d.get("accion"), d.get("hasta")
    if accion in ("archivar", "desarchivar"):
        return cambia(lambda cfg: almacen.archiva_flujos(cfg, hasta, accion == "archivar"))
    if accion == "borrar":
        conserva = []
        if modo() != "demo":
            conserva = [x for x in cartera().get("flujos", [])
                        if (x.get("fecha") or "") <= (hasta or "") and x.get("adjuntos")]
        resp = cambia(lambda cfg: almacen.borra_flujos_hasta(cfg, hasta))
        return _responde_con_huerfanos(resp, conserva)
    return jsonify(ok=False, errores=["Acción no válida."]), 400


@app.post("/api/config")
def api_config():
    """Guarda los parámetros del hogar (colchón, titulares)."""
    datos = request.get_json(silent=True) or {}
    return cambia(lambda cfg: almacen.guarda_config(cfg, datos))


@app.post("/api/flujo-marca")
def api_flujo_marca():
    """Pone o quita la marca de un apunte de ingreso/gasto (sin tocar el resto)."""
    d = request.get_json(silent=True) or {}
    return cambia(lambda cfg: almacen.marca_flujo(cfg, d.get("id"), d.get("marca")))


# ---- adjuntos (facturas) de un apunte: los archivos viven en «adjuntos/» de la cartera.
ADJ_MAX_BYTES = 15 * 1024 * 1024   # 15 MB por archivo


def _borra_fichero_adjunto(archivo):
    try:
        base = os.path.basename(archivo or "")
        if base:
            p = os.path.join(carpeta(), "adjuntos", base)
            if os.path.exists(p):
                os.remove(p)
    except OSError:
        pass


@app.post("/api/flujo-adjunto")
def api_flujo_adjunto():
    """Adjunta una factura/ticket a un apunte. El archivo se guarda en disco (local);
    la cartera solo guarda la referencia. No recalcula el panel."""
    if modo() == "demo":
        return jsonify(ok=False, errores=[AVISO_DEMO]), 403
    fid = request.form.get("id")
    f = request.files.get("archivo")
    if not f or not f.filename:
        return jsonify(ok=False, errores=["Elige un archivo."]), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in almacen.ADJ_EXT:
        return jsonify(ok=False, errores=["Formato no admitido. Usa PDF o una imagen (JPG, PNG, WEBP…)."]), 400
    with cerrojo:
        ruta = os.path.join(carpeta(), "cartera.json")
        cfg = almacen.carga(ruta)
        if not any(x.get("id") == fid for x in cfg.get("flujos", [])):
            return jsonify(ok=False, errores=["Ese apunte ya no existe."]), 400
        adj_dir = os.path.join(carpeta(), "adjuntos")
        os.makedirs(adj_dir, exist_ok=True)
        adj_id = "adj_" + secrets.token_hex(6)
        archivo = adj_id + ext
        destino = os.path.join(adj_dir, archivo)
        f.save(destino)
        tam = os.path.getsize(destino)
        if tam > ADJ_MAX_BYTES:
            _borra_fichero_adjunto(archivo)
            return jsonify(ok=False, errores=["El archivo es demasiado grande (máximo 15 MB)."]), 400
        try:
            adj = almacen.anota_adjunto(cfg, fid, adj_id, archivo, f.filename, f.mimetype or "", tam)
        except almacen.ErrorValidacion as e:
            _borra_fichero_adjunto(archivo)
            return jsonify(ok=False, errores=e.errores), 400
        almacen.guarda(ruta, cfg)
    return jsonify(ok=True, cartera=cfg, item=adj)


@app.post("/api/flujo-adjunto-quitar")
def api_flujo_adjunto_quitar():
    """Quita una factura de un apunte y borra su archivo del disco."""
    if modo() == "demo":
        return jsonify(ok=False, errores=[AVISO_DEMO]), 403
    d = request.get_json(silent=True) or {}
    with cerrojo:
        ruta = os.path.join(carpeta(), "cartera.json")
        cfg = almacen.carga(ruta)
        try:
            adj = almacen.quita_adjunto(cfg, d.get("flujo"), d.get("adjunto"))
        except almacen.ErrorValidacion as e:
            return jsonify(ok=False, errores=e.errores), 400
        almacen.guarda(ruta, cfg)
        _borra_fichero_adjunto(adj.get("archivo"))
    return jsonify(ok=True, cartera=cfg)


@app.post("/api/flujo-adjunto-importante")
def api_flujo_adjunto_importante():
    """Marca/desmarca una factura como importante."""
    d = request.get_json(silent=True) or {}
    return cambia(lambda cfg: almacen.marca_adjunto(cfg, d.get("flujo"), d.get("adjunto"), bool(d.get("importante"))), recalc=False)


@app.get("/api/adjunto/<fid>/<adj_id>")
def api_adjunto(fid, adj_id):
    """Sirve el archivo de una factura (inline, para verla o descargarla)."""
    fl = next((x for x in cartera().get("flujos", []) if x.get("id") == fid), None)
    adj = next((a for a in (fl or {}).get("adjuntos", []) if a.get("id") == adj_id), None) if fl else None
    if not adj:
        return jsonify(ok=False, errores=["No encuentro esa factura."]), 404
    adj_dir = os.path.join(carpeta(), "adjuntos")
    archivo = os.path.basename(adj.get("archivo") or "")   # seguridad: solo el nombre del fichero
    if not archivo or not os.path.exists(os.path.join(adj_dir, archivo)):
        return jsonify(ok=False, errores=["El archivo ya no está en disco."]), 404
    return send_from_directory(adj_dir, archivo, as_attachment=False, download_name=adj.get("nombre") or archivo)


# ---- biblioteca: gestor de documentos (los archivos viven en «biblioteca/» de la cartera) ----
BIB_MAX_BYTES = 50 * 1024 * 1024   # 50 MB por archivo


def _borra_fichero_biblioteca(archivo):
    try:
        base = os.path.basename(archivo or "")
        if base:
            p = os.path.join(carpeta(), "biblioteca", base)
            if os.path.exists(p):
                os.remove(p)
    except OSError:
        pass


@app.post("/api/biblioteca/carpeta")
def api_bib_carpeta():
    """Crea una carpeta en la biblioteca."""
    d = request.get_json(silent=True) or {}
    car_id = "car_" + secrets.token_hex(6)
    return cambia(lambda cfg: almacen.biblioteca_crea_carpeta(cfg, car_id, d.get("nombre"), d.get("padre")), recalc=False)


@app.post("/api/biblioteca/renombra")
def api_bib_renombra():
    """Renombra una carpeta o un archivo de la biblioteca."""
    d = request.get_json(silent=True) or {}
    return cambia(lambda cfg: almacen.biblioteca_renombra(cfg, d.get("tipo"), d.get("id"), d.get("nombre")), recalc=False)


@app.post("/api/biblioteca/mover")
def api_bib_mover():
    """Mueve una carpeta o un archivo a otra carpeta."""
    d = request.get_json(silent=True) or {}
    return cambia(lambda cfg: almacen.biblioteca_mueve(cfg, d.get("tipo"), d.get("id"), d.get("destino")), recalc=False)


@app.post("/api/biblioteca/carpeta-borra")
def api_bib_carpeta_borra():
    """Borra una carpeta y todo su contenido (subcarpetas y archivos del disco)."""
    if modo() == "demo":
        return jsonify(ok=False, errores=[AVISO_DEMO]), 403
    d = request.get_json(silent=True) or {}
    with cerrojo:
        ruta = os.path.join(carpeta(), "cartera.json")
        cfg = almacen.carga(ruta)
        try:
            ficheros = almacen.biblioteca_borra_carpeta(cfg, d.get("id"))
        except almacen.ErrorValidacion as e:
            return jsonify(ok=False, errores=e.errores), 400
        almacen.guarda(ruta, cfg)
        for f in ficheros:
            _borra_fichero_biblioteca(f)
    return jsonify(ok=True, cartera=cfg)


@app.post("/api/biblioteca/borrar")
def api_bib_borrar():
    """Borra un archivo moviéndolo a la papelera. El fichero del disco se conserva
    mientras esté en la papelera; solo se elimina lo que se cae del tope configurado."""
    if modo() == "demo":
        return jsonify(ok=False, errores=[AVISO_DEMO]), 403
    d = request.get_json(silent=True) or {}
    with cerrojo:
        ruta = os.path.join(carpeta(), "cartera.json")
        cfg = almacen.carga(ruta)
        maxN = (cfg.get("config") or {}).get("papeleraMax", almacen.PAPELERA_MAX_DEF)
        try:
            _arch, purgar = almacen.biblioteca_borra_archivo(cfg, d.get("id"), maxN)
        except almacen.ErrorValidacion as e:
            return jsonify(ok=False, errores=e.errores), 400
        almacen.guarda(ruta, cfg)
        for f in purgar:
            _borra_fichero_biblioteca(f)
    return jsonify(ok=True, cartera=cfg)


@app.post("/api/biblioteca/papelera-restaura")
def api_bib_papelera_restaura():
    """Saca un archivo de la papelera y lo devuelve a su carpeta."""
    d = request.get_json(silent=True) or {}
    return cambia(lambda cfg: almacen.biblioteca_restaura(cfg, d.get("id")), recalc=False)


@app.post("/api/biblioteca/papelera-vacia")
def api_bib_papelera_vacia():
    """Vacía la papelera y borra del disco sus ficheros."""
    if modo() == "demo":
        return jsonify(ok=False, errores=[AVISO_DEMO]), 403
    with cerrojo:
        ruta = os.path.join(carpeta(), "cartera.json")
        cfg = almacen.carga(ruta)
        files = almacen.biblioteca_vacia_papelera(cfg)
        almacen.guarda(ruta, cfg)
        for f in files:
            _borra_fichero_biblioteca(f)
    return jsonify(ok=True, cartera=cfg)


@app.post("/api/biblioteca/subir")
def api_bib_subir():
    """Sube un archivo a la biblioteca. Se admite cualquier tipo (hasta 50 MB)."""
    if modo() == "demo":
        return jsonify(ok=False, errores=[AVISO_DEMO]), 403
    f = request.files.get("archivo")
    if not f or not f.filename:
        return jsonify(ok=False, errores=["Elige un archivo."]), 400
    carpeta_destino = request.form.get("carpeta") or None
    ext = os.path.splitext(f.filename)[1].lower()[:12]
    with cerrojo:
        ruta = os.path.join(carpeta(), "cartera.json")
        cfg = almacen.carga(ruta)
        if carpeta_destino and not almacen._existe_carpeta(cfg, carpeta_destino):
            return jsonify(ok=False, errores=["La carpeta donde quieres guardarlo ya no existe."]), 400
        bib_dir = os.path.join(carpeta(), "biblioteca")
        os.makedirs(bib_dir, exist_ok=True)
        arch_id = "arc_" + secrets.token_hex(6)
        archivo = arch_id + ext
        destino = os.path.join(bib_dir, archivo)
        f.save(destino)
        tam = os.path.getsize(destino)
        if tam > BIB_MAX_BYTES:
            _borra_fichero_biblioteca(archivo)
            return jsonify(ok=False, errores=["El archivo es demasiado grande (máximo 50 MB)."]), 400
        fecha = dt.datetime.now().replace(microsecond=0).isoformat()
        try:
            arch = almacen.biblioteca_anota_archivo(cfg, arch_id, archivo, f.filename,
                                                    f.mimetype or "", tam, carpeta_destino, fecha)
        except almacen.ErrorValidacion as e:
            _borra_fichero_biblioteca(archivo)
            return jsonify(ok=False, errores=e.errores), 400
        almacen.guarda(ruta, cfg)
    return jsonify(ok=True, cartera=cfg, item=arch)


BIB_MAX_ARCHIVOS_LOTE = 800   # tope de archivos por subida de carpeta


def _bib_asegura_ruta(cfg, base, partes):
    """Devuelve el id de la carpeta hoja para una ruta relativa (p. ej.
    ['Documentos','2025']), creando bajo `base` las carpetas que falten."""
    bib = cfg.setdefault("biblioteca", {})
    bib.setdefault("carpetas", [])
    bib.setdefault("archivos", [])
    actual = base or None
    for nombre in partes:
        nombre = (nombre or "").strip()
        if not nombre:
            continue
        hijo = next((c for c in bib["carpetas"]
                     if (c.get("padre") or None) == (actual or None) and c.get("nombre") == nombre), None)
        if not hijo:
            hijo = almacen.biblioteca_crea_carpeta(cfg, "car_" + secrets.token_hex(6), nombre, actual)
        actual = hijo["id"]
    return actual


@app.post("/api/biblioteca/subir-carpeta")
def api_bib_subir_carpeta():
    """Sube una carpeta entera recreando su estructura. El front manda los archivos en
    «archivos» y sus rutas relativas (con subcarpetas) en «rutas» (JSON, mismo orden)."""
    if modo() == "demo":
        return jsonify(ok=False, errores=[AVISO_DEMO]), 403
    archivos = request.files.getlist("archivos")
    if not archivos:
        return jsonify(ok=False, errores=["No he recibido ningún archivo."]), 400
    if len(archivos) > BIB_MAX_ARCHIVOS_LOTE:
        return jsonify(ok=False, errores=[f"Demasiados archivos de golpe (máximo {BIB_MAX_ARCHIVOS_LOTE}). Súbela por partes."]), 400
    try:
        rutas = json.loads(request.form.get("rutas") or "[]")
    except ValueError:
        rutas = []
    base = request.form.get("base") or None
    guardados = []
    with cerrojo:
        ruta = os.path.join(carpeta(), "cartera.json")
        cfg = almacen.carga(ruta)
        if base and not almacen._existe_carpeta(cfg, base):
            return jsonify(ok=False, errores=["La carpeta de destino ya no existe."]), 400
        bib_dir = os.path.join(carpeta(), "biblioteca")
        os.makedirs(bib_dir, exist_ok=True)
        for i, f in enumerate(archivos):
            if not f or not f.filename:
                continue
            rel = rutas[i] if i < len(rutas) else f.filename
            partes = [p for p in str(rel).replace("\\", "/").split("/") if p and p not in (".", "..")]
            nombre = partes[-1] if partes else f.filename
            ext = os.path.splitext(nombre)[1].lower()[:12]
            arch_id = "arc_" + secrets.token_hex(6)
            archivo = arch_id + ext
            try:
                # Crear las subcarpetas o anotar el archivo puede fallar (p. ej. una ruta
                # más profunda que el máximo): si pasa, se salta SOLO este archivo —no se
                # aborta toda la subida ni se dejan huérfanos los que ya se guardaron—.
                destino_id = _bib_asegura_ruta(cfg, base, partes[:-1])
                f.save(os.path.join(bib_dir, archivo))
                tam = os.path.getsize(os.path.join(bib_dir, archivo))
                if tam > BIB_MAX_BYTES:
                    _borra_fichero_biblioteca(archivo)
                    continue   # se salta el archivo demasiado grande, no corta toda la subida
                arch = almacen.biblioteca_anota_archivo(cfg, arch_id, archivo, nombre,
                                                        f.mimetype or "", tam, destino_id,
                                                        dt.datetime.now().replace(microsecond=0).isoformat())
                guardados.append(arch)
            except almacen.ErrorValidacion:
                _borra_fichero_biblioteca(archivo)
        almacen.guarda(ruta, cfg)
    return jsonify(ok=True, cartera=cfg, subidos=len(guardados))


@app.post("/api/biblioteca/copiar")
def api_bib_copiar():
    """Copia (duplica) un archivo o una carpeta entera dentro de otra carpeta."""
    if modo() == "demo":
        return jsonify(ok=False, errores=[AVISO_DEMO]), 403
    d = request.get_json(silent=True) or {}
    tipo, ident, destino = d.get("tipo"), d.get("id"), d.get("destino") or None
    with cerrojo:
        ruta = os.path.join(carpeta(), "cartera.json")
        cfg = almacen.carga(ruta)
        bib = cfg.setdefault("biblioteca", {})
        bib.setdefault("carpetas", [])
        bib.setdefault("archivos", [])
        if destino and not almacen._existe_carpeta(cfg, destino):
            return jsonify(ok=False, errores=["La carpeta de destino ya no existe."]), 400
        bib_dir = os.path.join(carpeta(), "biblioteca")
        os.makedirs(bib_dir, exist_ok=True)
        # Instantáneas para iterar sin que afecten las copias que vamos añadiendo.
        carpetas0 = list(bib["carpetas"])
        archivos0 = list(bib["archivos"])

        def copia_archivo(arch, carpeta_dst):
            base = os.path.basename(arch.get("archivo") or "")
            ext = os.path.splitext(base)[1].lower()[:12]
            new_id = "arc_" + secrets.token_hex(6)
            new_name = new_id + ext
            src = os.path.join(bib_dir, base)
            if base and os.path.exists(src):
                shutil.copyfile(src, os.path.join(bib_dir, new_name))
            almacen.biblioteca_anota_archivo(cfg, new_id, new_name, arch.get("nombre") or "documento",
                                             arch.get("tipo") or "", arch.get("tam") or 0, carpeta_dst,
                                             dt.datetime.now().replace(microsecond=0).isoformat())

        try:
            if tipo == "archivo":
                arch = next((a for a in archivos0 if a.get("id") == ident), None)
                if not arch:
                    return jsonify(ok=False, errores=["Ese archivo ya no está."]), 400
                copia_archivo(arch, destino)
            else:
                # No se puede copiar una carpeta dentro de sí misma o de un descendiente.
                hijos = {}
                for c in carpetas0:
                    hijos.setdefault(c.get("padre"), []).append(c["id"])
                desc, pila = set(), [ident]
                while pila:
                    x = pila.pop()
                    if x in desc:
                        continue
                    desc.add(x)
                    pila.extend(hijos.get(x, []))
                if destino in desc:
                    return jsonify(ok=False, errores=["No puedes copiar una carpeta dentro de sí misma."]), 400

                def copia_carpeta(cid, padre_dst):
                    orig = next((c for c in carpetas0 if c["id"] == cid), None)
                    if not orig:
                        return
                    nueva = almacen.biblioteca_crea_carpeta(cfg, "car_" + secrets.token_hex(6), orig["nombre"], padre_dst)
                    for sub in [c for c in carpetas0 if c.get("padre") == cid]:
                        copia_carpeta(sub["id"], nueva["id"])
                    for a in [x for x in archivos0 if x.get("carpeta") == cid]:
                        copia_archivo(a, nueva["id"])

                copia_carpeta(ident, destino)
        except almacen.ErrorValidacion as e:
            return jsonify(ok=False, errores=e.errores), 400
        almacen.guarda(ruta, cfg)
    return jsonify(ok=True, cartera=cfg)


@app.get("/api/biblioteca/archivo/<arch_id>")
def api_bib_archivo(arch_id):
    """Sirve un archivo de la biblioteca (inline para verlo, o descarga con ?descargar=1)."""
    bib = cartera().get("biblioteca") or {}
    arch = next((a for a in bib.get("archivos", []) if a.get("id") == arch_id), None)
    if not arch:
        return jsonify(ok=False, errores=["No encuentro ese archivo."]), 404
    bib_dir = os.path.join(carpeta(), "biblioteca")
    archivo = os.path.basename(arch.get("archivo") or "")   # seguridad: solo el nombre del fichero
    if not archivo or not os.path.exists(os.path.join(bib_dir, archivo)):
        return jsonify(ok=False, errores=["El archivo ya no está en disco."]), 404
    descarga = request.args.get("descargar") == "1"
    return send_from_directory(bib_dir, archivo, as_attachment=descarga, download_name=arch.get("nombre") or archivo)


@app.post("/api/notas")
def api_notas():
    """Guarda la lista de notas (espacio libre del usuario). No recalcula el panel."""
    d = request.get_json(silent=True) or {}
    return cambia(lambda cfg: almacen.guarda_notas(cfg, d.get("notas")), recalc=False)


@app.post("/api/tablero")
def api_tablero():
    """Guarda el tablero tipo Trello (columnas y tarjetas). No recalcula el panel."""
    d = request.get_json(silent=True) or {}
    return cambia(lambda cfg: almacen.guarda_tablero(cfg, d.get("tablero")), recalc=False)


@app.post("/api/recordatorios")
def api_recordatorios():
    """Guarda la agenda de recordatorios del usuario. No recalcula el panel."""
    d = request.get_json(silent=True) or {}
    return cambia(lambda cfg: almacen.guarda_recordatorios(cfg, d.get("recordatorios")), recalc=False)


@app.post("/api/cuadernos")
def api_cuadernos():
    """Guarda los cuadernos (agrupadores de notas). No recalcula el panel."""
    d = request.get_json(silent=True) or {}
    return cambia(lambda cfg: almacen.guarda_cuadernos(cfg, d.get("cuadernos")), recalc=False)


@app.post("/api/cuaderno-borra")
def api_cuaderno_borra():
    """Borra un cuaderno; sus notas quedan sueltas. No recalcula el panel."""
    d = request.get_json(silent=True) or {}
    return cambia(lambda cfg: almacen.borra_cuaderno(cfg, d.get("id")), recalc=False)


@app.post("/api/repartir-colores")
def api_repartir_colores():
    # Con {"que": "apartados"} reparte colores entre los reservados; por defecto,
    # entre los productos (activos, cuentas y deudas), dando los colores más fáciles
    # de distinguir a los de mayor valor.
    que = (request.get_json(silent=True) or {}).get("que")
    if que == "apartados":
        return cambia(lambda cfg: almacen.reparte_colores_apartados(cfg))
    calc = lee_json(ruta_calculado()) or {}
    grandes = [p["id"] for p in sorted(calc.get("productos", []) + calc.get("otrosActivos", []),
                                       key=lambda p: -(p.get("valor") or 0))]
    return cambia(lambda cfg: almacen.reparte_colores(cfg, grandes))


@app.post("/api/empezar")
def api_empezar():
    """Sale de la demo: crea tu cartera, vacía o como copia del ejemplo para practicar."""
    if modo() != "demo":
        return jsonify(ok=False, errores=["Ya tienes tu propia cartera."]), 400
    with cerrojo:
        if (request.get_json(silent=True) or {}).get("desde") == "ejemplo":
            cfg = dict(lee_json(DEMO, {}), titular="Mi patrimonio (copia del ejemplo)")
        else:
            cfg = json.loads(json.dumps(almacen.CARTERA_VACIA))
        # Tu primera cartera ya va a su carpeta carteras/<id>/ (layout ordenado),
        # no suelta en la raíz de mis_datos.
        cid = almacen.slug(cfg.get("titular") or "cartera", {c["id"] for c in carteras()})
        os.makedirs(os.path.join(_carteras_dir(), cid), exist_ok=True)
        almacen.guarda(os.path.join(_carteras_dir(), cid, "cartera.json"), cfg)
        guarda_registro({"activa": cid})
        recalcula(descargar="faltan")
    return jsonify(ok=True)


# ---------------------------------------------------------------- varias carteras

@app.get("/api/carteras")
def api_carteras():
    lst, activa = carteras(), id_activa()
    if not lst and modo() == "propio":   # modo antiguo: una sola cartera suelta
        lst = [{"id": "__actual__", "nombre": cartera().get("titular") or "Mi patrimonio"}]
        activa = "__actual__"
    return jsonify(carteras=lst, activa=activa, modo=modo())


@app.post("/api/cartera/nueva")
def api_cartera_nueva():
    cuerpo = request.get_json(silent=True) or {}
    desde = cuerpo.get("desde")
    nombre = (cuerpo.get("nombre") or "").strip()[:60]
    if not nombre:
        nombre = "Ejemplo" if desde == "ejemplo" else ""
    if not nombre:
        return jsonify(ok=False, errores=["Ponle un nombre a la cartera."]), 400
    with cerrojo:
        asegura_multi()   # si venías del modo antiguo, lo pasa a multi
        cid = almacen.slug(nombre, {c["id"] for c in carteras()})
        if desde == "ejemplo":
            # Copia del patrimonio de ejemplo (demo): para comparar y aprender sin tocar el tuyo.
            cfg = dict(lee_json(DEMO, {}), titular=nombre)
        else:
            cfg = json.loads(json.dumps(almacen.CARTERA_VACIA))
            cfg["titular"] = nombre
        os.makedirs(os.path.join(_carteras_dir(), cid), exist_ok=True)
        almacen.guarda(os.path.join(_carteras_dir(), cid, "cartera.json"), cfg)
        guarda_registro({"activa": cid})
        recalcula(descargar="faltan")
    return jsonify(ok=True, id=cid)


@app.post("/api/cartera/activar")
def api_cartera_activar():
    cid = (request.get_json(silent=True) or {}).get("id")
    with cerrojo:
        if cid not in {c["id"] for c in carteras()}:
            return jsonify(ok=False, errores=["Ese patrimonio ya no existe."]), 400
        guarda_registro({"activa": cid})
        recalcula(descargar="faltan")
    return jsonify(ok=True)


@app.post("/api/cartera/borrar")
def api_cartera_borrar():
    cid = (request.get_json(silent=True) or {}).get("id")
    with cerrojo:
        ids = {c["id"] for c in carteras()}
        if cid not in ids:
            return jsonify(ok=False, errores=["Ese patrimonio ya no existe."]), 400
        if len(ids) <= 1:
            return jsonify(ok=False, errores=["No puedes borrar tu único patrimonio. Crea otro antes."]), 400
        ruta = os.path.join(_carteras_dir(), cid)
        # En Windows un archivo de caché puede estar en uso un instante: reintentamos.
        borrado = False
        for _ in range(4):
            try:
                shutil.rmtree(ruta)
                borrado = True
                break
            except FileNotFoundError:
                borrado = True
                break
            except OSError:
                time.sleep(0.25)
        if not borrado and os.path.exists(ruta):
            return jsonify(ok=False, errores=[
                "No he podido borrar todos sus archivos (alguno estaba en uso). "
                "Cierra otras ventanas de la app e inténtalo de nuevo."]), 500
        if registro().get("activa") == cid:
            guarda_registro({"activa": sorted(ids - {cid})[0]})
        recalcula(descargar="faltan")
    return jsonify(ok=True)


# ---------------------------------------------------------------- importar

PLANES = {}   # vista previa pendiente de confirmar: {token: plan}


@app.post("/api/importar/previsualizar")
def api_importar_previsualizar():
    """Lee lo que se quiere importar y devuelve la vista previa, sin guardar nada."""
    if modo() == "demo":
        return jsonify(ok=False, errores=[AVISO_DEMO]), 403
    origen = request.form.get("origen")
    destino = request.form.get("destino") or "activos"   # "activos" o "banco"
    archivos = [(f.filename, f.read()) for f in request.files.getlist("archivos") if f.filename]
    texto = (request.form.get("texto") or "").strip()
    # La preparación del plan baja precios (lenta) y usa el motor, que guarda su estado
    # en variables de módulo (cache, flags de descarga): si corriera a la vez que un
    # recálculo se pisarían esas variables. Por eso todo el acceso al motor va bajo el
    # cerrojo —aunque bloquee brevemente—, igual que el resto de cálculos de la app.
    with cerrojo:
        cfg = almacen.carga(os.path.join(carpeta(), "cartera.json"))
        dir_datos = carpeta()
        if destino == "banco":
            if not archivos and not texto:
                return jsonify(ok=False, errores=["Sube el CSV del banco (o tu plantilla) o pega el texto."]), 400
            filas, error = [], None
            for nombre, contenido in archivos or [("pegado.csv", texto)]:
                leidas, error = importar.leer_tabla_banco(nombre, contenido)
                if error:
                    return jsonify(ok=False, errores=[f"{nombre}: {error}" if archivos else error]), 400
                filas += leidas
            plan = importar.preparar_banco(cfg, filas)
        elif origen == "myinvestor":
            if not archivos:
                return jsonify(ok=False, errores=["Elige los archivos CSV que has descargado de MyInvestor."]), 400
            plan = importar.preparar_myinvestor(cfg, archivos, dir_datos)
        else:
            if not archivos and not texto:
                return jsonify(ok=False, errores=["Elige un archivo o pega el texto que te ha dado la IA."]), 400
            filas, error = [], None
            for nombre, contenido in archivos or [("pegado.csv", texto)]:
                leidas, error = importar.leer_tabla(nombre, contenido)
                if error:
                    return jsonify(ok=False, errores=[f"{nombre}: {error}" if archivos else error]), 400
                filas += leidas
            plan = importar.preparar_tabla(cfg, filas, dir_datos)
        informe = importar.vista_previa(cfg, plan)
    token = secrets.token_hex(8)
    PLANES.clear()   # solo una importación pendiente a la vez
    PLANES[token] = plan
    return jsonify(ok=True, token=token, informe=informe)


@app.post("/api/importar/confirmar")
def api_importar_confirmar():
    cuerpo = request.get_json(silent=True) or {}
    plan = PLANES.pop(cuerpo.get("token"), None)
    if plan is None:
        return jsonify(ok=False, errores=["Esa vista previa ya no vale: vuelve a revisar el archivo."]), 400
    # El usuario puede haber corregido categorías en la vista previa (banco): {fila: categoria}.
    cambios_cat = cuerpo.get("categorias") or {}
    if cambios_cat and getattr(plan, "flujos", None):
        for fl in plan.flujos:
            key = str(fl.get("fila"))
            if key in cambios_cat:
                fl["categoria"] = str(cambios_cat[key] or "")[:40]
    # Entidad/banco de esta importación: se asigna a TODOS sus apuntes de una vez.
    entidad = str(cuerpo.get("entidad") or "").strip()[:40]
    if entidad and getattr(plan, "flujos", None):
        for fl in plan.flujos:
            fl["entidad"] = entidad
    aprender = bool(cuerpo.get("recordar")) and cambios_cat and getattr(plan, "flujos", None)
    informe = {}

    def fn(cfg):
        if aprender:
            informe["reglasAprendidas"] = importar.aprende_reglas(cfg, plan, cambios_cat)
        informe.update(importar.aplicar(cfg, plan))
        return None
    respuesta = cambia(fn)
    if isinstance(respuesta, tuple):
        return respuesta
    datos = respuesta.get_json()
    datos["informe"] = {k: informe.get(k, 0) for k in
                        ("añadidos", "repetidos", "saldos", "sustituidos", "flujosAñadidos",
                         "flujosRepetidos", "reglasAprendidas")}
    return jsonify(datos)


@app.get("/api/plantilla.xlsx")
def api_plantilla_xlsx():
    return Response(plantilla.excel(), headers={"Content-Disposition": 'attachment; filename="plantilla_patrimonio.xlsx"'},
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/api/plantilla.csv")
def api_plantilla_csv():
    return Response(plantilla.csv_vacio(), mimetype="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="plantilla_patrimonio.csv"'})


@app.get("/api/plantilla-banco.xlsx")
def api_plantilla_banco_xlsx():
    return Response(plantilla.excel_banco(), headers={"Content-Disposition": 'attachment; filename="plantilla_banco.xlsx"'},
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/api/plantilla-banco.csv")
def api_plantilla_banco_csv():
    return Response(plantilla.csv_vacio_banco(), mimetype="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="plantilla_banco.csv"'})


@app.get("/api/prompt")
def api_prompt():
    with open(os.path.join(RAIZ, "app", "prompt_ia.txt"), encoding="utf-8") as f:
        return jsonify(texto=f.read())


@app.get("/api/prompt-banco")
def api_prompt_banco():
    with open(os.path.join(RAIZ, "app", "prompt_ia_banco.txt"), encoding="utf-8") as f:
        return jsonify(texto=f.read())


@app.post("/api/recurrentes")
def api_recurrentes():
    """Añade o quita una plantilla de ingreso/gasto recurrente (config.recurrentes)."""
    cuerpo = request.get_json(silent=True) or {}
    accion = cuerpo.get("accion")

    def fn(cfg):
        lista = cfg.setdefault("config", {}).setdefault("recurrentes", [])
        if accion == "quitar":
            i = cuerpo.get("indice")
            if isinstance(i, int) and 0 <= i < len(lista):
                lista.pop(i)
        else:
            r = almacen.sanea_recurrente(cuerpo.get("recurrente") or cuerpo)
            if not r:
                raise almacen.ErrorValidacion(["Esa plantilla recurrente no es válida (tipo e importe)."])
            lista.append(r)
        return None
    return cambia(fn)


# ---------------------------------------------------------------- copias de seguridad

def ruta_copias():
    return os.path.join(carpeta(), "copias")


def valida_copia(cfg):
    """Comprueba que un JSON es una copia válida de esta app, SIN persistir nada.
    Además de la forma, verifica que el motor puede calcularla (en un directorio
    temporal), para no sustituir la cartera activa por datos que luego revienten."""
    if not isinstance(cfg, dict):
        raise almacen.ErrorValidacion(["Ese archivo no es una copia de seguridad de esta app."])
    for k in ("productos", "movimientos", "valoraciones"):
        if not isinstance(cfg.get(k), list) or any(not isinstance(x, dict) for x in cfg[k]):
            raise almacen.ErrorValidacion(["Ese archivo no es una copia de seguridad de esta app."])
    for k in ("flujos", "apartados", "titulares", "monedas"):
        if k in cfg and not isinstance(cfg.get(k), list):
            raise almacen.ErrorValidacion([f"La copia está dañada (campo «{k}» con formato incorrecto)."])
    if "config" in cfg and not isinstance(cfg.get("config"), dict):
        raise almacen.ErrorValidacion(["La copia está dañada (la configuración tiene un formato incorrecto)."])
    # Prueba de fuego: que el motor la calcule en un directorio desechable. Bajo el
    # cerrojo porque el motor guarda su estado en variables de módulo y no puede correr
    # a la vez que otro cálculo (el RLock lo hace reentrante si ya lo tuviéramos).
    try:
        with cerrojo, tempfile.TemporaryDirectory(prefix="liberty_chk_") as tmp:
            motor.construir(cfg, tmp, descargar=False)
    except almacen.ErrorValidacion:
        raise
    except Exception as e:
        raise almacen.ErrorValidacion([f"La copia está dañada o no es compatible con esta app ({e})."]) from e
    return cfg


def restaura(cfg):
    """Pone cfg como cartera activa. Lo que hubiera antes queda en las copias.
    Con varias carteras, conserva el NOMBRE de la cartera en la que restauras, para
    no acabar con dos carteras con el mismo nombre (la copia trae su propio titular)."""
    with cerrojo:
        if len(carteras()) > 1:
            actual = cartera().get("titular")
            if actual:
                cfg = dict(cfg, titular=actual)
        almacen.guarda(os.path.join(carpeta(), "cartera.json"), cfg)
        for viejo in ("calculado_propio.json", "historico.json"):
            if os.path.exists(os.path.join(carpeta(), viejo)):
                os.remove(os.path.join(carpeta(), viejo))
        recalcula(descargar="faltan")


def crea_desde_copia(cfg, nombre):
    """Crea un patrimonio NUEVO a partir de la copia, sin tocar el actual, y lo activa."""
    with cerrojo:
        asegura_multi()
        nombre = (nombre or cfg.get("titular") or "Patrimonio restaurado").strip()[:60] or "Patrimonio restaurado"
        cid = almacen.slug(nombre, {c["id"] for c in carteras()})
        os.makedirs(os.path.join(_carteras_dir(), cid), exist_ok=True)
        almacen.guarda(os.path.join(_carteras_dir(), cid, "cartera.json"), dict(cfg, titular=nombre))
        guarda_registro({"activa": cid})
        recalcula(descargar="faltan")
    return cid


# ---- copia en .zip (cartera.json + facturas con nombre descriptivo) ----

def _san_nombre(s, maximo=60):
    """Sanea un trozo para usarlo en un nombre de archivo (quita caracteres ilegales,
    respeta tildes y espacios) y lo acorta."""
    s = re.sub(r'[\\/:*?"<>|\x00-\x1f]', " ", str(s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:maximo].strip()


def _nombre_factura(fl, adj, usados):
    """Nombre descriptivo para una factura dentro del zip:
    «AAAA-MM-DD - IMPORTE€ - CONCEPTO/CATEGORÍA - nombre_original.ext». Dedup con (2), (3)…"""
    fecha = (fl.get("fecha") or "")[:10]
    try:
        imp_txt = format(float(fl.get("importe")), "g").replace(".", ",") + "€"
    except (TypeError, ValueError):
        imp_txt = ""
    concepto = _san_nombre(fl.get("nota") or fl.get("categoria") or "apunte", 60)
    original = _san_nombre(adj.get("nombre") or "factura", 80)
    root, ext = os.path.splitext(original)
    base = " - ".join(p for p in (fecha, imp_txt, concepto, root) if p)[:150].strip() or "factura"
    nombre, i = base + ext, 2
    while nombre.lower() in usados:
        nombre, i = f"{base} ({i}){ext}", i + 1
    usados.add(nombre.lower())
    return nombre


def _ruta_carpeta_bib(carpetas_por_id, cid):
    """Ruta (saneada, desde la raíz) de una carpeta de la biblioteca, para recrear la
    MISMA estructura dentro del zip. Protegido contra ciclos de «padre»."""
    partes, visto = [], set()
    while cid and cid in carpetas_por_id and cid not in visto:
        visto.add(cid)
        c = carpetas_por_id[cid]
        partes.append(_san_nombre(c.get("nombre") or "carpeta", 80) or "carpeta")
        cid = c.get("padre")
    return "/".join(reversed(partes))


def _zip_cartera(base="cartera"):
    """Construye en memoria un .zip con la cartera actual, perfectamente estructurado para
    poder recuperar la aplicación (o extraer los documentos a mano):
      · «<base>.json»      → todos los datos del patrimonio (referencias reescritas),
      · «facturas/…»       → las facturas de los apuntes, con nombre descriptivo,
      · «archivos/…»       → la biblioteca de documentos con su MISMA estructura de
                             carpetas y los nombres visibles (la papelera, en «.papelera/»).
    Solo lee (no toca nada en disco)."""
    cfg = copy.deepcopy(cartera())
    adj_dir = os.path.join(carpeta(), "adjuntos")
    bib_dir = os.path.join(carpeta(), "biblioteca")
    buf, usados_fact, usados_arch = io.BytesIO(), set(), set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for fl in cfg.get("flujos", []):
            for adj in fl.get("adjuntos", []):
                origen = os.path.join(adj_dir, os.path.basename(adj.get("archivo") or ""))
                if os.path.exists(origen):
                    nombre = _nombre_factura(fl, adj, usados_fact)
                    z.write(origen, "facturas/" + nombre)
                    adj["archivo"] = nombre     # referencia -> nombre descriptivo
        # Biblioteca: se recrea la estructura de carpetas con los nombres visibles. La
        # referencia de cada documento pasa a ser su ruta relativa dentro de «archivos/»,
        # para poder localizarlo al restaurar.
        bib_cfg = cfg.get("biblioteca") or {}
        carpetas_por_id = {c.get("id"): c for c in bib_cfg.get("carpetas", [])}

        def _mete(arch, prefijo):
            base_disk = os.path.basename(arch.get("archivo") or "")
            origen = os.path.join(bib_dir, base_disk)
            if not base_disk or not os.path.exists(origen):
                return
            visible = _san_nombre(arch.get("nombre") or base_disk, 120) or "documento"
            carpeta_rel = _ruta_carpeta_bib(carpetas_por_id, arch.get("carpeta"))
            destino = "/".join(p for p in (prefijo, carpeta_rel) if p)
            rel = (destino + "/" if destino else "") + visible
            raiz, ext = os.path.splitext(rel)
            i = 2
            while rel.lower() in usados_arch:
                rel = f"{raiz} ({i}){ext}"
                i += 1
            usados_arch.add(rel.lower())
            z.write(origen, "archivos/" + rel)
            arch["archivo"] = rel     # referencia -> ruta relativa dentro de «archivos/»

        for arch in bib_cfg.get("archivos", []):
            _mete(arch, "")
        for arch in bib_cfg.get("papelera", []):
            _mete(arch, ".papelera")
        z.writestr(_san_nombre(base, 80) + ".json", json.dumps(cfg, ensure_ascii=False, indent=1))
    return buf.getvalue()


def _recupera_biblioteca_zip(cfg, z, nombres):
    """Lee los documentos de la biblioteca de un .zip —estructura nueva («archivos/<ruta>»,
    por la ruta relativa que guardamos en la referencia) o antigua («biblioteca/<fichero>»)—
    y a cada uno le asigna un nombre de almacenamiento único, reescribiendo la referencia de
    la cartera. Devuelve {nombre_en_disco: bytes} para volcarlos en «biblioteca/»."""
    bib = cfg.get("biblioteca") or {}
    hay_nuevo = any(n.startswith("archivos/") for n in nombres)
    salida = {}

    def _resuelve(arch):
        ref = arch.get("archivo") or ""
        clave = ("archivos/" + ref) if hay_nuevo else ("biblioteca/" + os.path.basename(ref))
        if clave not in nombres:
            clave = next((n for n in nombres
                          if (n.startswith("archivos/") or n.startswith("biblioteca/"))
                          and not n.endswith("/")
                          and os.path.basename(n) == os.path.basename(ref)), None)
        if not clave:
            return
        ext = os.path.splitext(ref or clave)[1]
        nuevo = "bib_" + secrets.token_hex(8) + ext
        salida[nuevo] = z.read(clave)
        arch["archivo"] = nuevo

    for arch in bib.get("archivos", []):
        _resuelve(arch)
    for arch in bib.get("papelera", []):
        _resuelve(arch)
    return salida


def _escribe_adjuntos(destino, adjuntos):
    """Vuelca las facturas extraídas de un zip en la carpeta de adjuntos de una cartera."""
    if not adjuntos:
        return
    os.makedirs(destino, exist_ok=True)
    for nombre, data in adjuntos.items():
        safe = os.path.basename(nombre)     # seguridad: solo el nombre, sin rutas
        if safe:
            with open(os.path.join(destino, safe), "wb") as fh:
                fh.write(data)


def _respalda_adjuntos():
    """Antes de restaurar (sustituir), mueve las facturas actuales a una copia con sello,
    para no perder NINGUNA aunque el zip traiga otras con el mismo nombre."""
    adj = os.path.join(carpeta(), "adjuntos")
    if os.path.isdir(adj) and os.listdir(adj):
        os.makedirs(ruta_copias(), exist_ok=True)
        sello = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.rename(adj, os.path.join(ruta_copias(), f"adjuntos_antes_de_recuperar_{sello}"))


@app.get("/api/copias")
def api_copias():
    lista = []
    if os.path.isdir(ruta_copias()):
        for n in os.listdir(ruta_copias()):
            if not n.endswith(".json"):
                continue
            ruta = os.path.join(ruta_copias(), n)
            cfg = lee_json(ruta, {}) or {}
            lista.append({"archivo": n,
                          "fecha": dt.datetime.fromtimestamp(os.path.getmtime(ruta)).isoformat(timespec="minutes"),
                          "motivo": "Antes de empezar de nuevo" if n.startswith("antes_de_reiniciar")
                          else "Antes de recuperar una copia" if n.startswith("antes_de_recuperar")
                          else "Automática",
                          "productos": len(cfg.get("productos", [])),
                          "movimientos": len(cfg.get("movimientos", []))})
    lista.sort(key=lambda c: c["fecha"], reverse=True)
    return jsonify(copias=lista)


@app.get("/api/copia/descargar")
def api_copia_descargar():
    if modo() != "propio":
        return jsonify(ok=False, errores=["Todavía no tienes una cartera propia que guardar."]), 400
    slug = almacen.slug(cartera().get("titular") or "patrimonio", set())
    base = f"copia_patrimonio_{slug}_{dt.date.today().isoformat()}"
    # Con ?formato=zip: la cartera + las facturas (nombre descriptivo). Si no, solo el .json.
    if request.args.get("formato") == "zip":
        return Response(_zip_cartera(base), mimetype="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{base}.zip"'})
    with open(os.path.join(carpeta(), "cartera.json"), "rb") as f:
        contenido = f.read()
    return Response(contenido, mimetype="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{base}.json"'})


@app.post("/api/copia/subir")
def api_copia_subir():
    """Importa una copia descargada antes (al cambiar de ordenador, etc.). Acepta el
    .json de siempre y el .zip nuevo (que incluye las facturas)."""
    f = request.files.get("archivo")
    if not f:
        return jsonify(ok=False, errores=["Elige el archivo de la copia (.json o .zip)."]), 400
    raw = f.read()
    es_zip = (f.filename or "").lower().endswith(".zip") or raw[:2] == b"PK"
    adjuntos, biblioteca = {}, {}
    try:
        if es_zip:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                nombres = z.namelist()
                # El JSON de datos: «cartera.json» (copias antiguas) o el .json de la raíz.
                jn = "cartera.json" if "cartera.json" in nombres else next(
                    (n for n in nombres if n.endswith(".json") and "/" not in n), None)
                if not jn:
                    raise KeyError("cartera.json")
                cfg = valida_copia(json.loads(z.read(jn).decode("utf-8")))
                # Facturas: carpeta «facturas/» (nueva) o «adjuntos/» (copias antiguas).
                adjuntos = {os.path.basename(n): z.read(n) for n in nombres
                            if (n.startswith("facturas/") or n.startswith("adjuntos/")) and not n.endswith("/")}
                # Biblioteca: estructura «archivos/…» (nueva) o «biblioteca/…» (antigua).
                biblioteca = _recupera_biblioteca_zip(cfg, z, nombres)
        else:
            cfg = valida_copia(json.loads(importar.decodifica(raw)))
    except (ValueError, KeyError, zipfile.BadZipFile):
        return jsonify(ok=False, errores=["Ese archivo no es una copia de seguridad de esta app."]), 400
    except almacen.ErrorValidacion as e:
        return jsonify(ok=False, errores=e.errores), 400
    # «nuevo»: crea un patrimonio aparte con la copia; por defecto, sustituye el actual.
    if request.form.get("destino") == "nuevo":
        cid = crea_desde_copia(cfg, request.form.get("nombre"))
        _escribe_adjuntos(os.path.join(_carteras_dir(), cid, "adjuntos"), adjuntos)
        _escribe_adjuntos(os.path.join(_carteras_dir(), cid, "biblioteca"), biblioteca)
    else:
        if adjuntos:
            _respalda_adjuntos()   # pone a salvo las facturas actuales antes de sustituir
        restaura(cfg)
        _escribe_adjuntos(os.path.join(carpeta(), "adjuntos"), adjuntos)
        _escribe_adjuntos(os.path.join(carpeta(), "biblioteca"), biblioteca)
    return jsonify(ok=True)


@app.post("/api/copia/recuperar")
def api_copia_recuperar():
    nombre = os.path.basename((request.get_json(silent=True) or {}).get("archivo") or "")
    ruta = os.path.join(ruta_copias(), nombre)
    if not nombre.endswith(".json") or not os.path.exists(ruta):
        return jsonify(ok=False, errores=["Esa copia ya no existe."]), 400
    try:
        cfg = valida_copia(lee_json(ruta))
    except almacen.ErrorValidacion as e:
        return jsonify(ok=False, errores=e.errores), 400
    if modo() == "propio":
        # Además de la copia automática, una con nombre propio que no se borra sola.
        sello = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(os.path.join(carpeta(), "cartera.json"), "rb") as a, \
                open(os.path.join(ruta_copias(), f"antes_de_recuperar_{sello}.json"), "wb") as b:
            b.write(a.read())
    restaura(cfg)
    return jsonify(ok=True)


# ---------------------------------------------------------------- web estática y versión

@app.get("/api/exportar-web")
def api_exportar_web():
    datos = lee_json(ruta_calculado())
    if not datos:
        return jsonify(ok=False, errores=["Todavía no hay nada que exportar."]), 400
    ocultar = request.args.get("ocultar") == "1"
    html = exportar.pagina(WEB, datos, ocultar=ocultar, titulo=datos.get("titular") or "Mi patrimonio")
    nombre = "patrimonio_sin_importes.html" if ocultar else "patrimonio.html"
    return Response(html.encode("utf-8"), mimetype="text/html",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


# Liberty: web de descargas (destino principal para el usuario) y repositorio (secundario).
WEB_LIBERTY = "https://alonsovine.github.io/liberty/"
REPO = "https://github.com/AlonsoVine/liberty"
DESCARGA = WEB_LIBERTY
_API_RELEASE = "https://api.github.com/repos/AlonsoVine/liberty/releases/latest"
_VERSION = {}


def version_actual():
    with open(os.path.join(RAIZ, "app", "VERSION"), encoding="utf-8") as f:
        return f.read().strip()


@app.get("/api/version")
def api_version():
    """Compara esta versión con la última release publicada en el repositorio de Liberty
    (se consulta como mucho una vez al día). Solo sale a internet si lo activas en
    Configuración: por defecto está apagado, para que la app sea 100 % local salvo la
    descarga de precios."""
    actual = version_actual()
    activado = bool((cartera().get("config") or {}).get("buscarActualizaciones"))
    # ?manual=1 = comprobación que pide el usuario con un clic («comprobar ahora»). Como es
    # una acción explícita suya, se hace aunque la comprobación automática esté apagada (igual
    # que el botón «descargar e instalar»): no cambia el ajuste ni activa el chequeo diario.
    manual = request.args.get("manual") == "1"
    if not activado and not manual:
        return jsonify(actual=actual, ultima=None, repo=REPO, descarga=DESCARGA,
                       hayNueva=False, desactivado=True)
    # Normalmente se consulta como mucho una vez al día; con ?forzar=1 (p. ej. al pulsar
    # «Actualizar precios») o ?manual=1 se salta esa caché y se comprueba al momento.
    forzar = manual or request.args.get("forzar") == "1"
    error = False
    if forzar or not _VERSION or dt.datetime.now() - _VERSION["cuando"] > dt.timedelta(hours=24):
        try:
            req = urllib.request.Request(_API_RELEASE, headers=motor.UA)
            with urllib.request.urlopen(req, timeout=5) as r:
                tag = (json.loads(r.read().decode()).get("tag_name") or "").lstrip("vV")
                _VERSION.update(ultima=tag or None, cuando=dt.datetime.now())
        except Exception:
            _VERSION.update(ultima=None, cuando=dt.datetime.now())
            error = True
    ultima = _VERSION.get("ultima")
    def como_tupla(v):
        return tuple(int(x) for x in re.findall(r"\d+", v or "0"))
    return jsonify(actual=actual, ultima=ultima, repo=REPO, descarga=DESCARGA, manual=manual,
                   error=error,
                   hayNueva=bool(ultima) and como_tupla(ultima) > como_tupla(actual))


# Ejecutable de la última versión (el nombre del asset es siempre «Liberty.exe»).
_URL_EXE = "https://github.com/AlonsoVine/liberty/releases/latest/download/Liberty.exe"


def _vtupla(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "0"))


def _mayor(a, b):
    return _vtupla(a) > _vtupla(b)


@app.post("/api/descargar-version")
def api_descargar_version():
    """Descarga el ejecutable de la última versión y lo deja JUNTO al actual, con la
    versión en el nombre (p. ej. «Liberty 1.8.2.exe»). No ejecuta ni sobrescribe nada
    (un .exe en marcha está bloqueado por Windows): solo es una descarga —un GET a
    GitHub— y escribir un archivo nuevo. El usuario abre el nuevo y borra el viejo
    cuando quiera. La app sigue siendo 100 % local. Lo lanza el usuario con un botón."""
    if not getattr(sys, "frozen", False):
        return jsonify(ok=False, motivo="dev", descarga=DESCARGA,
                       mensaje="En modo desarrollo no hay ejecutable que actualizar. "
                               "Al compilar, este botón descargará el .exe nuevo junto al actual."), 200
    if sys.platform == "darwin":
        # En Mac la app es un .app (un paquete): reemplazarlo en marcha es delicado, así
        # que la actualización se hace desde la web (descargar el nuevo .app y arrastrarlo).
        return jsonify(ok=False, motivo="mac", descarga=DESCARGA,
                       mensaje="Descarga la versión nueva de Liberty para Mac desde la web "
                               "y arrástrala a tu carpeta de Aplicaciones (reemplaza la anterior)."), 200
    try:
        req = urllib.request.Request(_API_RELEASE, headers=motor.UA)
        with urllib.request.urlopen(req, timeout=8) as r:
            ultima = (json.loads(r.read().decode()).get("tag_name") or "").lstrip("vV") or None
    except Exception:
        return jsonify(ok=False, motivo="sin-conexion", descarga=DESCARGA,
                       mensaje="No he podido consultar la última versión. "
                               "Revisa tu conexión o descárgala desde la web."), 200
    actual = version_actual()
    if not ultima or not _mayor(ultima, actual):
        return jsonify(ok=False, motivo="al-dia", actual=actual, ultima=ultima,
                       mensaje="Ya tienes la última versión."), 200
    carpeta_exe = os.path.dirname(sys.executable)
    nombre = f"Liberty {ultima}.exe"
    destino = os.path.join(carpeta_exe, nombre)
    tmp = destino + ".parcial"
    try:
        req = urllib.request.Request(_URL_EXE, headers=motor.UA)
        with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        if os.path.getsize(tmp) < 1_000_000:     # un .exe real pesa decenas de MB
            raise OSError("descarga incompleta")
        os.replace(tmp, destino)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return jsonify(ok=False, motivo="error-descarga", descarga=DESCARGA,
                       mensaje="No he podido descargar la nueva versión. "
                               "Puedes bajarla a mano desde la web de Liberty."), 200
    try:   # abrir la carpeta para que vea el archivo nuevo (como ya abrimos el navegador al arrancar)
        if not os.environ.get("PATRIMONIO_NO_ABRIR"):
            webbrowser.open("file:///" + carpeta_exe.replace(os.sep, "/"))
    except Exception:
        pass
    return jsonify(ok=True, archivo=nombre, carpeta=carpeta_exe, actual=actual, ultima=ultima)


@app.post("/api/reiniciar")
def api_reiniciar():
    """Empieza de cero o vuelve a la demo. Lo que había se guarda antes en mis_datos/copias."""
    if modo() != "propio":
        return jsonify(ok=False, errores=["Ahora mismo no tienes ninguna cartera propia."]), 400
    a = (request.get_json(silent=True) or {}).get("a")
    with cerrojo:
        ruta = os.path.join(carpeta(), "cartera.json")
        copias = os.path.join(carpeta(), "copias")
        os.makedirs(copias, exist_ok=True)
        sello = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.replace(ruta, os.path.join(copias, f"antes_de_reiniciar_{sello}.json"))
        for viejo in ("calculado_propio.json", "historico.json"):
            if os.path.exists(os.path.join(carpeta(), viejo)):
                os.remove(os.path.join(carpeta(), viejo))
        if a == "vacia":
            almacen.guarda(ruta, json.loads(json.dumps(almacen.CARTERA_VACIA)))
        recalcula(descargar="faltan")
    return jsonify(ok=True)


@app.get("/api/ping")
def api_ping():
    return jsonify(app="patrimonio")


@app.get("/<path:archivo>")
def estaticos(archivo):
    return send_from_directory(WEB, archivo)


# ---------------------------------------------------------------- arranque

def ya_abierta(puerto):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/ping", timeout=1) as r:
            return json.load(r).get("app") == "patrimonio"
    except Exception:
        return False


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    # Si la app ya está abierta (otra ventana), basta con enseñarla.
    if ya_abierta(PUERTO):
        print("La app ya estaba abierta: te la enseño en el navegador.")
        if not os.environ.get("PATRIMONIO_NO_ABRIR"):
            webbrowser.open(f"http://127.0.0.1:{PUERTO}/")
        return

    migra_layout()   # reordena mis_datos al layout nuevo si viene de una versión vieja
    print("\n  RUMBO  ·  tu patrimonio neto")
    print("  " + "-" * 40)
    if modo() == "demo":
        print("  Modo demostración: estás viendo una cartera de ejemplo.")
    # Siempre se recalcula al arrancar (sin internet es un momento): así, tras
    # actualizar la app a una versión nueva, el panel nunca usa cálculos viejos.
    viejos = precios_viejos()
    if viejos:
        print("  Actualizando precios (tarda unos segundos)...")
    try:
        recalcula(descargar=viejos or "faltan")
    except Exception as e:
        print(f"\n  [!] No he podido actualizar los precios: {e}")
        print("      Abro la app con los últimos datos guardados.")

    srv = None
    for puerto in range(PUERTO, PUERTO + 10):
        try:
            srv = make_server("127.0.0.1", puerto, app, threaded=True)
            break
        except OSError:
            continue
    if srv is None:
        print("  [!] No encuentro ningún puerto libre para abrir la app.")
        return
    url = f"http://127.0.0.1:{srv.server_port}/"
    if not os.environ.get("PATRIMONIO_NO_ABRIR"):   # para pruebas: no abre el navegador
        threading.Timer(0.8, webbrowser.open, [url]).start()
    print(f"\n  App abierta en {url}")
    print("  Deja esta ventana abierta mientras la uses. Para salir, ciérrala.\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
