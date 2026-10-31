# -*- coding: utf-8 -*-
"""
Zona de Inmuebles (rama `inmuebles`, iteración 1 · núcleo): la ficha de cada inmueble
(datos, compra, valor estimado, uso e hipoteca con enlace opcional a una deuda), su
resumen en el motor y la regla de oro de la zona: va APARTE de la cartera, así que no
altera el patrimonio ni los gráficos de tus inversiones.
"""
import copy
import datetime as dt
import json
import os

import pytest

from app import almacen, motor


def cfg_vacia():
    return copy.deepcopy(almacen.CARTERA_VACIA)


def con_deuda(cfg, pid="hipoteca"):
    cfg["productos"].append({"id": pid, "nombre": "Hipoteca del piso", "corto": "Hipoteca",
                             "tipo": "deuda", "fuente": "manual", "slot": 3})
    return cfg


PISO = {"nombre": "Piso Calle Mayor", "tipo": "piso", "uso": "inversion", "estado": "alquilado",
        "titular": "Yo", "direccion": "C/ Mayor 1, Madrid", "refCatastral": "9872023 vh5797s",
        "m2": "80", "habitaciones": "3", "valorCatastral": "60.000",
        "compraFecha": "2019-05-10", "compraPrecio": "150.000", "compraGastos": "15000",
        "valorImporte": "185.000", "valorFecha": "2026-10-01",
        "hipCapital": "90.000", "hipCuota": "650", "hipInteres": "2,125", "hipFin": "2044-05-10"}


# ---------------------------------------------------------------- almacén

def test_crea_inmueble_agrupa_los_campos_planos():
    cfg = cfg_vacia()
    im = almacen.guarda_inmueble(cfg, dict(PISO))
    assert im["id"] == "i1"
    assert im["compra"] == {"fecha": "2019-05-10", "precio": 150000.0, "gastos": 15000.0}
    assert im["valor"] == {"importe": 185000.0, "fecha": "2026-10-01"}
    # El interés se escribe en % (con coma) y se guarda como fracción, como la TAE.
    assert im["hipoteca"] == {"capitalPendiente": 90000.0, "cuota": 650.0,
                              "tipoInteres": 0.02125, "fechaFin": "2044-05-10"}
    assert im["refCatastral"] == "9872023VH5797S"
    assert im["m2"] == 80.0 and im["habitaciones"] == 3 and im["valorCatastral"] == 60000.0
    assert cfg["inmuebles"] == [im]


def test_minimo_solo_nombre_y_por_defecto_inversion():
    cfg = cfg_vacia()
    im = almacen.guarda_inmueble(cfg, {"nombre": "Garaje"})
    assert im["tipo"] == "piso" and im["uso"] == "inversion" and im["estado"] == "vacio"
    assert "compra" not in im and "valor" not in im and "hipoteca" not in im


def test_sin_nombre_falla():
    with pytest.raises(almacen.ErrorValidacion) as e:
        almacen.guarda_inmueble(cfg_vacia(), {"nombre": "  "})
    assert "nombre" in str(e.value)


@pytest.mark.parametrize("campo,valor", [("tipo", "castillo"), ("uso", "vacaciones"),
                                         ("estado", "okupado")])
def test_catalogos_invalidos_fallan(campo, valor):
    with pytest.raises(almacen.ErrorValidacion):
        almacen.guarda_inmueble(cfg_vacia(), {"nombre": "X", campo: valor})


def test_compra_futura_y_numero_raro_fallan():
    futura = (dt.date.today() + dt.timedelta(days=30)).isoformat()
    with pytest.raises(almacen.ErrorValidacion) as e:
        almacen.guarda_inmueble(cfg_vacia(), {"nombre": "X", "compraFecha": futura,
                                              "compraPrecio": "mucho"})
    assert "futura" in str(e.value) and "no es un número" in str(e.value)


def test_valor_sin_fecha_es_de_hoy():
    im = almacen.guarda_inmueble(cfg_vacia(), {"nombre": "X", "valorImporte": "100000"})
    assert im["valor"]["fecha"] == dt.date.today().isoformat()


def test_vivienda_habitual_no_lleva_estado_y_solo_puede_haber_una():
    cfg = cfg_vacia()
    casa = almacen.guarda_inmueble(cfg, {"nombre": "Mi casa", "uso": "habitual", "estado": "alquilado"})
    assert casa["uso"] == "habitual" and "estado" not in casa
    with pytest.raises(almacen.ErrorValidacion) as e:
        almacen.guarda_inmueble(cfg, {"nombre": "Otra", "uso": "habitual"})
    assert "Mi casa" in str(e.value)
    # Editar la propia habitual sí se puede (no choca consigo misma).
    almacen.guarda_inmueble(cfg, {"id": casa["id"], "nombre": "Mi casa (renovada)", "uso": "habitual"})
    assert cfg["inmuebles"][0]["nombre"] == "Mi casa (renovada)"


def test_editar_reemplaza_la_ficha_pero_conserva_contratos_y_categorias():
    cfg = cfg_vacia()
    im = almacen.guarda_inmueble(cfg, dict(PISO))
    im["contratos"] = [{"id": "c1", "renta": 900}]
    im["categorias"] = ["Alquiler · Piso Mayor"]
    editado = almacen.guarda_inmueble(cfg, {"id": im["id"], "nombre": "Piso Mayor", "uso": "inversion",
                                            "estado": "vacio"})
    assert editado["nombre"] == "Piso Mayor" and editado["estado"] == "vacio"
    assert "hipoteca" not in editado            # los campos que no se mandan se quitan
    assert editado["contratos"] == [{"id": "c1", "renta": 900}]
    assert editado["categorias"] == ["Alquiler · Piso Mayor"]
    assert len(cfg["inmuebles"]) == 1


def test_hipoteca_enlazada_a_una_deuda_valida():
    cfg = con_deuda(cfg_vacia())
    im = almacen.guarda_inmueble(cfg, {"nombre": "Piso", "hipCuota": "650", "hipDeuda": "hipoteca"})
    assert im["hipoteca"]["deudaRef"] == "hipoteca"


def test_enlace_a_algo_que_no_es_deuda_o_no_existe_falla():
    cfg = con_deuda(cfg_vacia())
    cfg["productos"].append({"id": "cuenta", "nombre": "Cuenta", "tipo": "efectivo", "fuente": "manual"})
    for ref in ("cuenta", "fantasma"):
        with pytest.raises(almacen.ErrorValidacion) as e:
            almacen.guarda_inmueble(cfg, {"nombre": "Piso", "hipDeuda": ref})
        assert "ya no existe" in str(e.value)


def test_una_deuda_solo_se_enlaza_a_un_inmueble():
    cfg = con_deuda(cfg_vacia())
    almacen.guarda_inmueble(cfg, {"nombre": "Piso A", "hipDeuda": "hipoteca"})
    with pytest.raises(almacen.ErrorValidacion) as e:
        almacen.guarda_inmueble(cfg, {"nombre": "Piso B", "hipDeuda": "hipoteca"})
    assert "Piso A" in str(e.value)


def test_borrar_la_deuda_suelta_el_enlace_pero_no_la_hipoteca():
    cfg = con_deuda(cfg_vacia())
    almacen.guarda_inmueble(cfg, {"nombre": "Piso", "hipCuota": "650", "hipDeuda": "hipoteca"})
    almacen.borra_producto(cfg, "hipoteca")
    assert cfg["inmuebles"][0]["hipoteca"] == {"cuota": 650.0}


def test_borrar_inmueble():
    cfg = cfg_vacia()
    im = almacen.guarda_inmueble(cfg, {"nombre": "Trastero"})
    almacen.borra_inmueble(cfg, im["id"])
    assert cfg["inmuebles"] == []
    with pytest.raises(almacen.ErrorValidacion):
        almacen.borra_inmueble(cfg, im["id"])


def test_renombrar_titular_llega_a_los_inmuebles():
    cfg = cfg_vacia()
    cfg["titulares"] = ["Yo", "Común"]
    almacen.guarda_inmueble(cfg, {"nombre": "Piso", "titular": "Común"})
    almacen.guarda_config(cfg, {"titulares": ["Yo", "Familia"],
                                "renombresTitular": [{"de": "Común", "a": "Familia"}]})
    assert cfg["inmuebles"][0]["titular"] == "Familia"


# ---------------------------------------------------------------- motor

def _resumen(cfg, deudas=None, hasta=None):
    return motor.inmuebles_de(cfg, deudas or [], hasta)


def test_motor_coste_valor_revalorizacion_y_neto():
    cfg = cfg_vacia()
    almacen.guarda_inmueble(cfg, dict(PISO))
    r = _resumen(cfg)
    x = r["lista"][0]
    assert x["coste"] == 165000.0                 # precio + gastos de compra
    assert x["valor"] == 185000.0 and x["valorDeCompra"] is False
    assert x["plusvalia"] == 20000.0 and x["plusvaliaPct"] == round(20000 / 165000, 4)
    assert x["neto"] == 95000.0                   # valor − hipoteca pendiente
    assert x["tipoNombre"] == "Piso" and x["estadoNombre"] == "Alquilado"
    t = r["total"]
    assert (t["n"], t["nInversion"], t["nHabitual"], t["alquilados"]) == (1, 1, 0, 1)
    assert t["valor"] == 185000.0 and t["hipotecas"] == 90000.0 and t["neto"] == 95000.0
    assert t["cuotaHipotecas"] == 650.0 and t["plusvalia"] == 20000.0


def test_motor_sin_estimacion_vale_lo_que_costo_y_no_inventa_revalorizacion():
    cfg = cfg_vacia()
    almacen.guarda_inmueble(cfg, {"nombre": "Garaje", "compraFecha": "2020-01-01",
                                  "compraPrecio": "20000", "compraGastos": "2000"})
    x = _resumen(cfg)["lista"][0]
    assert x["valor"] == 20000.0 and x["valorDeCompra"] is True
    assert x["plusvalia"] is None
    assert _resumen(cfg)["total"]["plusvalia"] is None


def test_motor_capital_de_la_deuda_enlazada_si_no_hay_uno_propio():
    cfg = con_deuda(cfg_vacia())
    almacen.guarda_inmueble(cfg, {"nombre": "Piso", "valorImporte": "200000", "hipDeuda": "hipoteca"})
    deudas = [{"id": "hipoteca", "nombre": "Hipoteca", "capitalPendiente": 120000.0}]
    x = _resumen(cfg, deudas)["lista"][0]
    assert x["hipoteca"]["capitalPendiente"] == 120000.0
    assert x["hipoteca"]["deudaRef"] == "hipoteca" and x["hipoteca"]["deudaNombre"] == "Hipoteca"
    assert x["neto"] == 80000.0


def test_motor_foto_de_un_mes_pasado():
    cfg = cfg_vacia()
    almacen.guarda_inmueble(cfg, dict(PISO))                       # comprado en 2019
    almacen.guarda_inmueble(cfg, {"nombre": "Local", "compraFecha": "2025-03-01",
                                  "compraPrecio": "90000"})
    r = _resumen(cfg, hasta="2024-12-31")
    assert [x["nombre"] for x in r["lista"]] == ["Piso Calle Mayor"]   # el local aún no era tuyo
    x = r["lista"][0]
    assert x["valorDeCompra"] is True and x["valor"] == 150000.0      # la estimación es de 2026


def test_inmuebles_no_tocan_el_patrimonio_de_la_cartera(cartera_manual, tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    sin = motor.construir(copy.deepcopy(cartera_manual), str(tmp_path / "a"), descargar=False)
    con_cfg = copy.deepcopy(cartera_manual)
    almacen.guarda_inmueble(con_cfg, dict(PISO))
    con = motor.construir(con_cfg, str(tmp_path / "b"), descargar=False)
    assert con["total"]["patrimonio"] == sin["total"]["patrimonio"]
    assert con["total"]["porClase"] == sin["total"]["porClase"]       # ni en los gráficos
    assert sin["inmuebles"]["lista"] == []
    assert con["inmuebles"]["total"]["valor"] == 185000.0


def test_vista_de_un_mes_pasado_lleva_su_foto_de_inmuebles(cartera_manual, tmp_path):
    cfg = copy.deepcopy(cartera_manual)                 # la cartera tiene datos hasta 2024-02
    almacen.guarda_inmueble(cfg, dict(PISO))
    almacen.guarda_inmueble(cfg, {"nombre": "Local", "compraFecha": "2025-03-01", "compraPrecio": "90000"})
    d = motor.construir(cfg, str(tmp_path), descargar=False, hasta="2024-02")
    assert [x["nombre"] for x in d["inmuebles"]["lista"]] == ["Piso Calle Mayor"]


def test_la_demo_trae_inmuebles_de_inversion_y_vivienda_habitual(tmp_path):
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(raiz, "demo", "cartera.json"), encoding="utf-8") as f:
        demo = json.load(f)
    (tmp_path / "con").mkdir()
    (tmp_path / "sin").mkdir()
    d = motor.construir(copy.deepcopy(demo), str(tmp_path / "con"), descargar=False)
    t = d["inmuebles"]["total"]
    assert t["nInversion"] >= 1 and t["nHabitual"] == 1
    assert t["valor"] > 0 and t["plusvalia"] is not None
    # Y la cartera no se entera: su patrimonio es el mismo con o sin la zona de inmuebles.
    demo.pop("inmuebles")
    sin = motor.construir(demo, str(tmp_path / "sin"), descargar=False)
    assert d["total"]["patrimonio"] == sin["total"]["patrimonio"]


# ---------------------------------------------------------------- servidor

def _prepara(tmp_path, monkeypatch, cfg=None):
    from app import servidor
    monkeypatch.setattr(servidor, "DATOS", str(tmp_path))
    with open(os.path.join(str(tmp_path), "cartera.json"), "w", encoding="utf-8") as f:
        json.dump(cfg or cfg_vacia(), f)
    return servidor


def test_api_inmuebles_crea_edita_y_borra(tmp_path, monkeypatch):
    servidor = _prepara(tmp_path, monkeypatch)
    client = servidor.app.test_client()
    j = client.post("/api/inmuebles", json=dict(PISO)).get_json()
    assert j["ok"] is True
    iid = j["item"]["id"]
    j = client.post("/api/inmuebles", json={"id": iid, "nombre": "Piso Mayor"}).get_json()
    assert j["ok"] is True and j["cartera"]["inmuebles"][0]["nombre"] == "Piso Mayor"
    assert client.post("/api/inmuebles", json={"nombre": ""}).status_code == 400
    assert client.delete(f"/api/inmuebles/{iid}").get_json()["ok"] is True
    assert client.get("/api/cartera").get_json()["cartera"]["inmuebles"] == []


def test_copia_con_inmuebles_mal_formados_se_rechaza():
    from app import servidor
    cfg = cfg_vacia()
    cfg["inmuebles"] = {"no": "es una lista"}
    with pytest.raises(almacen.ErrorValidacion):
        servidor.valida_copia(cfg)


# ---------------------------------------------------------------- iteración 3+: libro, hogar y documentos
# El libro del inmueble son los apuntes de Ingresos y gastos de sus categorías asociadas
# (Configuración → Inmuebles o su ficha); Inicio suma el patrimonio de todo el hogar; las
# notas de Documentos se pueden enlazar a un inmueble y salen en su ficha.

def _flujo(fid, tipo, fecha, importe, categoria):
    return {"id": fid, "tipo": tipo, "fecha": fecha, "importe": importe, "categoria": categoria}


def test_categorias_desde_la_ficha_y_unicas_entre_inmuebles():
    cfg = cfg_vacia()
    a = almacen.guarda_inmueble(cfg, dict(PISO, categorias=["Alquiler Mayor", "alquiler mayor", "IBI Mayor"]))
    assert a["categorias"] == ["Alquiler Mayor", "IBI Mayor"]          # sin repetir (ni por mayúsculas)
    with pytest.raises(almacen.ErrorValidacion) as e:
        almacen.guarda_inmueble(cfg, {"nombre": "Local", "categorias": ["ibi mayor"]})
    assert "ya va con «Piso Calle Mayor»" in e.value.errores[0]
    # Editar sin mandar categorías las conserva; mandarlas vacías las quita.
    almacen.guarda_inmueble(cfg, {"id": a["id"], "nombre": "Piso Mayor"})
    assert cfg["inmuebles"][0]["categorias"] == ["Alquiler Mayor", "IBI Mayor"]
    almacen.guarda_inmueble(cfg, {"id": a["id"], "nombre": "Piso Mayor", "categorias": []})
    assert "categorias" not in cfg["inmuebles"][0]


def test_reparto_de_categorias_desde_configuracion():
    cfg = cfg_vacia()
    almacen.guarda_inmueble(cfg, dict(PISO, categorias=["Viejo"]))
    almacen.guarda_inmueble(cfg, {"nombre": "Casa", "uso": "habitual"})
    almacen.guarda_config(cfg, {"inmueblesCategorias": {"i1": ["Alquiler"], "i2": ["Comunidad casa"]}})
    assert [x.get("categorias") for x in cfg["inmuebles"]] == [["Alquiler"], ["Comunidad casa"]]
    with pytest.raises(almacen.ErrorValidacion):        # la misma categoría en dos inmuebles
        almacen.guarda_config(cfg, {"inmueblesCategorias": {"i1": ["Alquiler"], "i2": ["alquiler"]}})
    with pytest.raises(almacen.ErrorValidacion):        # un inmueble que ya no existe
        almacen.guarda_config(cfg, {"inmueblesCategorias": {"i9": ["X"]}})
    almacen.guarda_config(cfg, {"inmueblesCategorias": {"i1": [], "i2": []}})
    assert all("categorias" not in x for x in cfg["inmuebles"])


def test_libro_del_inmueble_con_sus_apuntes():
    cfg = cfg_vacia()
    almacen.guarda_inmueble(cfg, dict(PISO, categorias=["Alquiler Mayor", "Gastos Mayor"]))
    flujos = [_flujo("f1", "ingreso", "2026-09-05", 750, "Alquiler Mayor"),
              _flujo("f2", "gasto", "2026-09-15", 385, "gastos mayor"),       # sin distinguir mayúsculas
              _flujo("f3", "ingreso", "2024-01-05", 700, "Alquiler Mayor"),   # fuera de los 12 meses
              _flujo("f4", "gasto", "2026-09-20", 60, "Alimentación")]        # no es suyo
    r = motor.inmuebles_de(cfg, [], flujos=flujos, fecha_ref=dt.date(2026, 9, 30))
    lb = r["lista"][0]["libro"]
    assert (lb["ingresos12"], lb["gastos12"], lb["neto12"]) == (750.0, 385.0, 365.0)
    assert (lb["ingresosTotal"], lb["netoTotal"], lb["n"]) == (1450.0, 1065.0, 3)
    assert lb["meses"][-1] == "2026-09" and len(lb["meses"]) == 12
    assert lb["serieIngresos"][-1] == 750.0 and lb["serieGastos"][-1] == 385.0
    assert [a["id"] for a in lb["apuntes"]] == ["f2", "f1", "f3"]          # recientes primero
    assert "nota" not in lb["apuntes"][0]   # el concepto no va en DATOS (ni en la web exportada)
    assert r["lista"][0]["rentabilidadNeta"] == round(365 / 165000, 4)
    assert r["total"]["neto12"] == 365.0 and r["total"]["conLibro"] == 1


def test_el_cash_flow_no_mezcla_la_vivienda_habitual():
    cfg = cfg_vacia()
    almacen.guarda_inmueble(cfg, dict(PISO, categorias=["Alquiler"]))
    almacen.guarda_inmueble(cfg, {"nombre": "Casa", "uso": "habitual", "categorias": ["Comunidad casa"]})
    flujos = [_flujo("f1", "ingreso", "2026-09-05", 750, "Alquiler"),
              _flujo("f2", "gasto", "2026-09-05", 90, "Comunidad casa")]
    r = motor.inmuebles_de(cfg, [], flujos=flujos, fecha_ref=dt.date(2026, 9, 30))
    assert r["total"]["neto12"] == 750.0 and r["total"]["costeHabitual12"] == 90.0
    casa = r["lista"][1]
    assert casa["libro"]["gastos12"] == 90.0 and casa["rentabilidadNeta"] is None


def test_sin_categorias_no_hay_libro():
    cfg = cfg_vacia()
    almacen.guarda_inmueble(cfg, dict(PISO))
    r = motor.inmuebles_de(cfg, [], flujos=[_flujo("f1", "ingreso", "2026-09-05", 750, "Alquiler")])
    assert r["lista"][0]["libro"] is None and r["total"]["conLibro"] == 0


def test_patrimonio_del_hogar_no_resta_dos_veces_la_hipoteca_enlazada():
    cfg = con_deuda(cfg_vacia())
    almacen.guarda_inmueble(cfg, dict(PISO))                                     # 185.000 − 90.000 propia
    almacen.guarda_inmueble(cfg, {"nombre": "Casa", "valorImporte": "200000",
                                  "hipCapital": "120000", "hipDeuda": "hipoteca"})  # ya resta en la cartera
    deudas = [{"id": "hipoteca", "nombre": "Hipoteca", "capitalPendiente": 120000.0}]
    inm = motor.inmuebles_hogar(motor.inmuebles_de(cfg, deudas), 50000.0)
    t = inm["total"]
    assert t["hipotecas"] == 210000.0 and t["hipotecasSinEnlace"] == 90000.0
    assert t["patrimonioHogar"] == 50000.0 + 385000.0 - 90000.0
    vacio = motor.inmuebles_hogar(motor.inmuebles_de(cfg_vacia(), []), 50000.0)
    assert vacio["total"]["patrimonioHogar"] is None


def test_la_demo_trae_libro_y_patrimonio_del_hogar(tmp_path):
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(raiz, "demo", "cartera.json"), encoding="utf-8") as f:
        demo = json.load(f)
    d = motor.construir(demo, str(tmp_path), descargar=False)
    piso = next(x for x in d["inmuebles"]["lista"] if x["uso"] == "inversion")
    assert piso["libro"] and piso["libro"]["ingresos12"] > 0
    t = d["inmuebles"]["total"]
    assert t["patrimonioHogar"] == round(d["total"]["patrimonioNeto"] + t["valor"] - t["hipotecasSinEnlace"], 2)


def test_una_nota_se_enlaza_a_un_inmueble_y_se_suelta_al_borrarlo():
    cfg = cfg_vacia()
    almacen.guarda_inmueble(cfg, dict(PISO))
    almacen.guarda_inmueble(cfg, {"nombre": "Local"})
    notas = almacen.guarda_notas(cfg, [
        {"titulo": "Escrituras", "vinculos": [{"tipo": "inmueble", "ref": "i1"}]},
        {"titulo": "Seguro", "vinculos": [{"tipo": "inmueble", "ref": "i1"}, {"tipo": "inmueble", "ref": "i2"}]},
    ])
    assert notas[0]["vinculos"] == [{"tipo": "inmueble", "ref": "i1"}]
    cfg["recordatorios"] = [{"id": "r1", "texto": "IBI", "fecha": "2026-11-01", "vinculo": {"tipo": "inmueble", "ref": "i1"}}]
    almacen.borra_inmueble(cfg, "i1")
    n1, n2 = cfg["notas"]
    assert "vinculos" not in n1 and "vinculo" not in n1                 # la nota sigue, sin enlace
    assert n2["vinculos"] == [{"tipo": "inmueble", "ref": "i2"}] and n2["vinculo"]["ref"] == "i2"
    assert "vinculo" not in cfg["recordatorios"][0]


def test_api_config_reparte_categorias(tmp_path, monkeypatch):
    cfg = cfg_vacia()
    almacen.guarda_inmueble(cfg, dict(PISO))
    servidor = _prepara(tmp_path, monkeypatch, cfg)
    client = servidor.app.test_client()
    j = client.post("/api/config", json={"inmueblesCategorias": {"i1": ["Alquiler"]}}).get_json()
    assert j["ok"] is True and j["cartera"]["inmuebles"][0]["categorias"] == ["Alquiler"]
    r = client.post("/api/config", json={"inmueblesCategorias": {"i1": ["A", "a"], "i7": ["B"]}})
    assert r.status_code == 400
