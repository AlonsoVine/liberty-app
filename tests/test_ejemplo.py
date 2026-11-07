# -*- coding: utf-8 -*-
"""
El PATRIMONIO DE EJEMPLO (app/ejemplo.py, ADR 0037): lo ve quien abre la app por primera
vez y se copia desde «Empezar con mis datos» o desde Ayuda. Estos tests evitan que vuelva a
quedarse atrás:
- que cubra TODA la app (cada colección, tipo, fuente y función tiene su ejemplo);
- que todo lo que enlaza exista y tenga la forma que guarda la propia app;
- que vaya con fechas vivas: cualquier día del año sale al día y sin avisos falsos;
- que esté equilibrado (cartera e inmuebles parecidos, ningún activo domina) y que Fiscal
  tenga ventas con ganancia y con pérdida en el último año cerrado.
"""
import copy
import datetime as dt
import os

import pytest

from app import almacen, ejemplo, motor
from app import servidor as srv

HOY = dt.date(2026, 11, 3)
# Días con trampa: fin e inicio de mes y de año, febrero, el día de cobro del alquiler…
DIAS = [dt.date(2026, 11, 3), dt.date(2027, 1, 1), dt.date(2027, 2, 28), dt.date(2027, 3, 31),
        dt.date(2027, 6, 5), dt.date(2027, 8, 20), dt.date(2027, 12, 31)]
# Avisos que el ejemplo NO debe dar nunca: delatarían un ejemplo viejo o mal hecho.
AVISOS_FALSOS = {"sin-anotar", "sin-actualizar", "inm-cobro-pendiente", "inm-valor-antiguo",
                 "inm-fin-contrato", "dinero-libre", "objetivos-suma", "monedas-sin-cambio", "vencidos",
                 "concentracion-tipo", "concentracion-entidad"}


def _ej(hoy=HOY):
    return ejemplo.genera(hoy)[0]


def _construye(cfg, carpeta, hoy, monkeypatch):
    monkeypatch.setattr(motor, "hoy", lambda: hoy)
    return motor.construir(copy.deepcopy(cfg), str(carpeta), descargar=False)


# ---------------------------------------------------------------- cobertura

def test_cubre_todas_las_colecciones_y_tipos():
    e = _ej()
    for clave in ("productos", "movimientos", "valoraciones", "apartados", "flujos", "inmuebles", "alertasPrecio",
                  "notas", "cuadernos", "recordatorios", "comparador"):
        assert e.get(clave), f"el ejemplo no trae «{clave}»"
    assert e["titulares"] == ["Yo", "Mi pareja", "Común"]
    tipos = {p["tipo"] for p in e["productos"]}
    assert set(motor.TIPOS) - {"inmueble"} <= tipos, "falta algún tipo de activo (los inmuebles van en su zona)"
    assert tipos & {t["id"] for t in e["config"]["tipos"]}, "debería usar un tipo de activo propio"
    assert {p["fuente"] for p in e["productos"]} == set(motor.FUENTES)
    assert any(p["moneda"] != "EUR" and p["fuente"] != "manual" for p in e["productos"])
    assert any(p["moneda"] != "EUR" and p["fuente"] == "manual" for p in e["productos"])
    assert {m["tipo"] for m in e["movimientos"]} == set(almacen.TIPOS_MOV)
    assert any(m.get("retencion") for m in e["movimientos"]) and any(m.get("comision") for m in e["movimientos"])
    assert any(p.get("fechaVencimiento") for p in e["productos"] if p["tipo"] == "bono")
    assert any(p.get("tae") and p.get("cuota") for p in e["productos"] if p["tipo"] == "deuda")


def test_ingresos_y_gastos_completos():
    e, conf = _ej(), _ej()["config"]
    f = e["flujos"]
    assert {x["tipo"] for x in f} == {"ingreso", "gasto"}
    meses = {x["fecha"][:7] for x in f}
    assert len(meses) == ejemplo.MESES + 1, "tres años de apuntes, mes a mes, hasta el actual"
    assert any(x.get("adjuntos") for x in f) and any(a.get("importante") for x in f for a in x.get("adjuntos", []))
    assert {x.get("marca") for x in f if x.get("marca")} <= {m["id"] for m in motor.MARCAS_DEFECTO}
    assert len({x.get("marca") for x in f if x.get("marca")}) >= 4
    assert any(x.get("observaciones") for x in f) and any(x.get("archivado") for x in f)
    assert all(x.get("categorias", {}).get("naturaleza") for x in f)
    nombres = {c["nombre"] for c in conf["categorias"]}
    assert {x["categoria"] for x in f} <= nombres, "toda categoría usada está en Configuración"
    assert any(c.get("presupuesto") for c in conf["categorias"])
    for k in ("recurrentes", "reglasCategoria", "entidades", "dimensiones", "dimensionesFlujos", "monedas"):
        assert conf.get(k), f"la configuración no trae «{k}»"
    assert round(sum(conf["objetivos"].values()), 6) == 1


def test_inmuebles_completos():
    e = _ej()
    ims = e["inmuebles"]
    assert {x["uso"] for x in ims} == set(motor.USOS_INMUEBLE)
    assert {"alquilado", "venta"} <= {x.get("estado") for x in ims}
    assert len({x["tipo"] for x in ims}) >= 3
    assert any(x.get("historico") for x in ims)
    enlazado = [x for x in ims if (x.get("hipoteca") or {}).get("deudaRef")]
    assert enlazado and any(not (x.get("hipoteca") or {}).get("deudaRef") and x.get("hipoteca") for x in ims)
    deuda = almacen.producto(e, enlazado[0]["hipoteca"]["deudaRef"])
    assert deuda and deuda["tipo"] == "deuda"
    contratos = [c for x in ims for q in x.get("inquilinos", []) for c in q.get("contratos", [])]
    estados = {motor.estado_contrato(c, HOY.isoformat()) for c in contratos}
    assert {"vigente", "terminado"} <= estados, "un contrato vigente y uno anterior ya terminado"
    assert {c["actualizacion"] for c in contratos} >= {"ipc", "irav", "pactada"}
    for x in ims:
        for c in [c for q in x.get("inquilinos", []) for c in q.get("contratos", [])]:
            assert c["categoria"] in x["categorias"]
    # Una categoría va con un solo inmueble.
    todas = [c for x in ims for c in x.get("categorias", [])]
    assert len(todas) == len(set(todas))


def test_documentos_enlazados_y_con_la_forma_de_la_app():
    e = _ej()
    bib = e["biblioteca"]
    arch_ids = {a["id"] for a in bib["archivos"]}
    car_ids = {c["id"] for c in bib["carpetas"]}
    assert any(c["padre"] for c in bib["carpetas"]) and bib["papelera"]
    assert all(a["carpeta"] in car_ids for a in bib["archivos"])
    refs = {"activo": {p["id"] for p in e["productos"] if p["tipo"] != "deuda"},
            "deuda": {p["id"] for p in e["productos"] if p["tipo"] == "deuda"},
            "reservado": {a["id"] for a in e["apartados"]},
            "inmueble": {x["id"] for x in e["inmuebles"]}}
    usados = set()
    for n in e["notas"]:
        for v in n.get("vinculos", []):
            assert v["ref"] in refs[v["tipo"]], v
            usados.add(v["tipo"])
        for a in n.get("archivos", []):
            assert a["id"] in (arch_ids if a["tipo"] == "archivo" else car_ids), a
        assert not n.get("cuaderno") or n["cuaderno"] in {c["id"] for c in e["cuadernos"]}
    assert usados == set(refs), "notas enlazadas a activos, deudas, reservados e inmuebles"
    assert any(n.get("cuaderno") for n in e["notas"]) and any(not n.get("cuaderno") for n in e["notas"])
    assert any(a["tipo"] == "carpeta" for n in e["notas"] for a in n.get("archivos", []))
    assert any("- [ ]" in n["texto"] for n in e["notas"]) and any(n.get("color") for n in e["notas"])
    for r in e["recordatorios"]:
        v = r.get("vinculo")
        assert not v or v["ref"] in refs[v["tipo"]]
    assert {r["repetir"] for r in e["recordatorios"]} == set(almacen.REC_REPETIR)
    assert any(r["hecho"] for r in e["recordatorios"])
    for x in e["inmuebles"]:
        for q in x.get("inquilinos", []):
            for c in q.get("contratos", []):
                assert all(a["id"] in arch_ids for a in c.get("archivos", []))
    for al in e["alertasPrecio"]:
        assert almacen.producto(e, al["producto"])
    for c in e["comparador"]:
        assert all(almacen.producto(e, pid) for pid in (c.get("pesos") or {}))
    # La misma forma que guarda la app (si no, al editar algo cambiaría solo).
    assert almacen.guarda_notas(copy.deepcopy(e), e["notas"]) == e["notas"]
    assert almacen.guarda_cuadernos(copy.deepcopy(e), e["cuadernos"]) == e["cuadernos"]
    assert almacen.guarda_recordatorios(copy.deepcopy(e), e["recordatorios"]) == e["recordatorios"]
    assert almacen.guarda_tablero(copy.deepcopy(e), e["tablero"]) == e["tablero"]


def test_los_documentos_de_muestra_son_pdf_que_se_abren(tmp_path):
    e = _ej()
    ejemplo.escribe_archivos(e, str(tmp_path))
    adj = [a for x in e["flujos"] for a in x.get("adjuntos", [])]
    for a in adj:
        with open(tmp_path / "adjuntos" / a["archivo"], "rb") as f:
            datos = f.read()
        assert datos.startswith(b"%PDF-1.4") and datos.rstrip().endswith(b"%%EOF")
    n_bib = len(e["biblioteca"]["archivos"]) + len(e["biblioteca"]["papelera"])
    assert len(os.listdir(tmp_path / "biblioteca")) == n_bib
    # No pisa lo que ya hay.
    (tmp_path / "adjuntos" / adj[0]["archivo"]).write_bytes(b"mio")
    ejemplo.escribe_archivos(e, str(tmp_path))
    assert (tmp_path / "adjuntos" / adj[0]["archivo"]).read_bytes() == b"mio"


# ---------------------------------------------------------------- fechas vivas

@pytest.mark.parametrize("hoy", DIAS, ids=[d.isoformat() for d in DIAS])
def test_cualquier_dia_esta_al_dia_y_sin_avisos_falsos(hoy, tmp_path, monkeypatch):
    e = _ej(hoy)
    for clave in ("flujos", "movimientos", "valoraciones"):
        assert max(x["fecha"] for x in e[clave]) <= hoy.isoformat(), f"{clave} con fechas futuras"
    assert any(x["fecha"][:7] == hoy.isoformat()[:7] for x in e["flujos"]), "el mes en curso tiene apuntes"
    d = _construye(e, tmp_path, hoy, monkeypatch)
    claves = {a.get("clave") for a in d["alertas"]}
    assert not (claves & AVISOS_FALSOS), [a["texto"] for a in d["alertas"] if a.get("clave") in AVISOS_FALSOS]
    # Avisos que el ejemplo enseña a propósito.
    assert {"proximos", "alerta-precio", "agenda-proxima"} <= claves
    assert d["libertad"] and d["libertad"]["mesesMedia"] == 12


def test_el_mismo_dia_da_el_mismo_ejemplo_y_un_mes_pasado_no_cambia():
    assert _ej(HOY) == _ej(HOY)
    a = [x for x in _ej(dt.date(2026, 11, 3))["flujos"] if x["fecha"][:7] == "2026-09"]
    b = [x for x in _ej(dt.date(2026, 11, 20))["flujos"] if x["fecha"][:7] == "2026-09"]
    assert [(x["fecha"], x["importe"], x["categoria"]) for x in a] == [(x["fecha"], x["importe"], x["categoria"]) for x in b]


def test_con_precios_reales_las_compras_salen_a_ese_precio():
    serie = {(HOY - dt.timedelta(days=i)).isoformat(): 100.0 + i for i in range(0, 1200)}
    cfg, reales = ejemplo.genera(HOY, {p["id"]: serie for p in ejemplo.cotizados()})
    assert reales
    m = next(x for x in cfg["movimientos"] if x["producto"] == "world" and x["tipo"] == "compra")
    precio = serie[m["fecha"]]
    assert m["unidades"] == pytest.approx(m["importe"] / precio)
    assert ejemplo.genera(HOY)[1] is False   # sin caché: aproximado


# ---------------------------------------------------------------- equilibrio y fiscal

def test_fiscal_del_ultimo_anio_cerrado(tmp_path, monkeypatch):
    d = _construye(_ej(), tmp_path, HOY, monkeypatch)
    y = d["fiscal"][str(HOY.year - 1)]
    assert len(y["ventas"]) >= 3 and len(y["rendimientos"]) >= 2
    t = y["totales"]
    assert t["ganancias"] > 0 and t["perdidas"] < 0
    assert t["rendimientoIntegro"] > 0 and t["retenciones"] > 0


def test_equilibrado_entre_cartera_e_inmuebles(tmp_path, monkeypatch):
    # Sin caché, lo que cotiza se valora con el precio aproximado del propio generador.
    e = _ej()
    valor = 0.0
    for p in e["productos"]:
        if p["fuente"] != "manual":
            uds = sum(m["unidades"] * (1 if m["tipo"] == "compra" else -1) for m in e["movimientos"]
                      if m["producto"] == p["id"] and m["tipo"] in ("compra", "venta"))
            valor += uds * ejemplo.APROX[p["id"]][0]
        else:
            vs = [v for v in e["valoraciones"] if v["producto"] == p["id"]]
            ultimo = vs[-1]["valor"] * (0.92 if p["moneda"] == "USD" else 1)
            enlazada = any((x.get("hipoteca") or {}).get("deudaRef") == p["id"] for x in e["inmuebles"])
            valor += 0 if enlazada else (-ultimo if p["tipo"] == "deuda" else ultimo)
    inm = sum(x["valor"]["importe"] - (x.get("hipoteca") or {}).get("capitalPendiente", 0) for x in e["inmuebles"])
    assert 120000 < valor < 190000 and 120000 < inm < 190000, (valor, inm)
    assert 0.7 < valor / inm < 1.4
    d = _construye(e, tmp_path, HOY, monkeypatch)
    assert max(p.get("peso") or 0 for p in d["productos"]) < 0.5
    negativos = [p for p in d["productos"] if (p.get("rentabilidad") or 0) < 0]
    assert 1 <= len(negativos) <= 3, "casi todo en positivo y alguno en negativo"


# ---------------------------------------------------------------- servidor

def test_la_demo_y_las_copias_usan_el_ejemplo_de_hoy(tmp_path, monkeypatch):
    monkeypatch.setattr(srv, "DATOS", str(tmp_path))
    monkeypatch.setattr(srv, "ejemplo_con_precios", srv.cartera_ejemplo)   # sin red en los tests
    srv._EJEMPLO.clear()
    client = srv.app.test_client()
    assert client.get("/api/carteras").get_json()["modo"] == "demo"
    demo = client.get("/api/cartera").get_json()["cartera"]
    assert demo["titular"] == "Patrimonio de ejemplo" and demo["notas"]
    # La demo sirve sus facturas y documentos de muestra.
    fl = next(x for x in demo["flujos"] if x.get("adjuntos"))
    r = client.get(f"/api/adjunto/{fl['id']}/{fl['adjuntos'][0]['id']}")
    assert r.status_code == 200 and r.data.startswith(b"%PDF")
    arc = demo["biblioteca"]["archivos"][0]
    assert client.get(f"/api/biblioteca/archivo/{arc['id']}").status_code == 200

    r = client.post("/api/cartera/nueva", json={"desde": "ejemplo"})
    assert r.get_json()["ok"] is True, r.get_json()
    carteras = client.get("/api/carteras").get_json()
    assert carteras["modo"] == "propio" and any(c["nombre"] == "Ejemplo" for c in carteras["carteras"])
    copia = client.get("/api/cartera").get_json()["cartera"]
    assert copia["titular"] == "Ejemplo"
    assert len(copia["productos"]) == len(demo["productos"]) and copia["flujos"] and copia["biblioteca"]
    # La copia se lleva sus documentos: se abren desde la cartera nueva.
    r = client.get(f"/api/biblioteca/archivo/{arc['id']}")
    assert r.status_code == 200 and r.data.startswith(b"%PDF")
