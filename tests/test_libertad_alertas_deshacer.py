"""Libertad financiera, alertas de precio y «Deshacer» tras borrar (ADR 0035)."""

import copy
import json
import os

import pytest

from app import almacen, motor


def ig(**meses):
    return {k.replace("_", "-"): {"ingreso": v[0], "gasto": v[1]} for k, v in meses.items()}


# ---------------------------------------------------------------- libertad financiera

def test_gasto_medio_de_los_meses_completos_sin_el_mes_en_curso():
    meses = ig(m2026_08=(3000, 2000), m2026_09=(3000, 1000), m2026_10=(3000, 1500), m2026_11=(3000, 9000))
    meses = {k[1:]: v for k, v in meses.items()}
    L = motor.libertad_financiera(meses, "2026-11", disponible=9000, cartera=300000, renta_inmuebles=0)
    assert L["gastoMedio"] == 1500 and L["mesesMedia"] == 3          # noviembre (en curso) no cuenta
    assert L["mesesDisponible"] == 6.0 and L["mesesCartera"] == 200.0
    # 4 % de 300.000 = 12.000 al año = 1.000 al mes: cubre 2/3 de 1.500.
    assert L["rentaCartera"] == 1000 and abs(L["progreso"] - 0.6667) < 1e-4
    assert L["carteraObjetivo"] == 450000 and L["falta"] == 150000


def test_los_alquileres_cuentan_y_la_tasa_se_puede_cambiar():
    meses = {"2026-10": {"ingreso": 0, "gasto": 2000}}
    L = motor.libertad_financiera(meses, "2026-11", 0, 240000, renta_inmuebles=1000, tasa=0.03)
    assert L["rentaCartera"] == 600 and L["rentaPasiva"] == 1600 and L["progreso"] == 0.8
    # Falta cubrir 1.000 €/mes con la cartera: 12.000 / 3 % = 400.000.
    assert L["carteraObjetivo"] == 400000 and L["tasaRetirada"] == 0.03


def test_sin_un_mes_completo_de_gastos_no_hay_calculo():
    assert motor.libertad_financiera({}, "2026-11", 1000, 1000, 0) is None
    solo_este_mes = {"2026-11": {"ingreso": 100, "gasto": 50}}
    assert motor.libertad_financiera(solo_este_mes, "2026-11", 1000, 1000, 0) is None


def test_construir_publica_la_libertad(tmp_path):
    cfg = copy.deepcopy(almacen.CARTERA_VACIA)
    cfg["productos"] = [{"id": "c1", "nombre": "Cuenta", "tipo": "efectivo"}]
    hoy = motor.hoy()
    mes_pasado = (hoy.replace(day=1) - motor.dt.timedelta(days=1)).replace(day=10).isoformat()
    cfg["valoraciones"] = [{"id": "v1", "producto": "c1", "fecha": mes_pasado, "valor": 12000}]
    cfg["flujos"] = [{"id": "f1", "fecha": mes_pasado, "tipo": "gasto", "importe": 2000, "categoria": "Casa"}]
    cfg["config"]["tasaRetirada"] = 0.05
    L = motor.construir(cfg, str(tmp_path), descargar=False)["libertad"]
    assert L["gastoMedio"] == 2000 and L["mesesDisponible"] == 6.0 and L["tasaRetirada"] == 0.05


def test_la_tasa_de_retirada_se_valida_en_configuracion():
    cfg = copy.deepcopy(almacen.CARTERA_VACIA)
    almacen.guarda_config(cfg, {"tasaRetirada": "3,5"})
    assert cfg["config"]["tasaRetirada"] == 0.035
    almacen.guarda_config(cfg, {"tasaRetirada": ""})
    assert cfg["config"]["tasaRetirada"] is None
    with pytest.raises(almacen.ErrorValidacion):
        almacen.guarda_config(cfg, {"tasaRetirada": "30"})


# ---------------------------------------------------------------- alertas de precio

FONDO = {"id": "p1", "corto": "Fondo", "origen": "csv", "nav": 90.0, "valor": 900.0}
CUENTA = {"id": "p2", "corto": "Cuenta", "origen": "manual", "valor": 4000.0}


def test_alerta_de_caida_y_de_subida_por_porcentaje():
    cae = {"producto": "p1", "condicion": "cae", "valor": 0.1, "ref": 100}
    sube = {"producto": "p1", "condicion": "sube", "valor": 0.1, "ref": 100}
    out = motor.alertas_precio([cae, sube], [FONDO])
    assert len(out) == 1 and out[0][1] == "p1"
    assert "ha caído un 10,0 % desde 100,00 €" in out[0][0]
    assert motor.alertas_precio([dict(cae, valor=0.15)], [FONDO]) == []


def test_alerta_por_importe_y_valor_de_los_que_van_a_mano():
    out = motor.alertas_precio([{"producto": "p2", "condicion": "menor", "valor": 5000, "nota": "¡Revisa!"},
                                {"producto": "p1", "condicion": "mayor", "valor": 95}], [FONDO, CUENTA])
    assert len(out) == 1
    assert "su valor (4.000,00 €) ha bajado de 5.000,00 €" in out[0][0] and out[0][0].endswith("¡Revisa!")


def test_guardar_alertas_valida_y_se_van_con_su_producto():
    cfg = copy.deepcopy(almacen.CARTERA_VACIA)
    cfg["productos"] = [{"id": "p1", "nombre": "Fondo", "tipo": "fondo"}]
    a = almacen.guarda_alerta(cfg, {"producto": "p1", "condicion": "cae", "valor": "10", "ref": "25,5",
                                    "refFecha": "2026-11-03"})
    assert a == {"id": "al1", "producto": "p1", "condicion": "cae", "valor": 0.1, "ref": 25.5,
                 "refFecha": "2026-11-03"}
    b = almacen.guarda_alerta(cfg, {"producto": "p1", "condicion": "mayor", "valor": "30", "ref": "99"})
    assert b["id"] == "al2" and "ref" not in b and b["valor"] == 30
    for malo in ({"producto": "zz", "condicion": "cae", "valor": "10", "ref": "1"},
                 {"producto": "p1", "condicion": "rara", "valor": "10"},
                 {"producto": "p1", "condicion": "cae", "valor": "100", "ref": "1"},
                 {"producto": "p1", "condicion": "cae", "valor": "10"}):
        with pytest.raises(almacen.ErrorValidacion):
            almacen.guarda_alerta(cfg, malo)
    almacen.borra_alerta(cfg, "al2")
    assert [x["id"] for x in cfg["alertasPrecio"]] == ["al1"]
    almacen.borra_producto(cfg, "p1")
    assert cfg["alertasPrecio"] == []


def test_construir_convierte_la_alerta_en_aviso_y_se_puede_apagar(tmp_path):
    cfg = copy.deepcopy(almacen.CARTERA_VACIA)
    cfg["productos"] = [{"id": "c1", "nombre": "Cuenta", "tipo": "efectivo"}]
    cfg["valoraciones"] = [{"id": "v1", "producto": "c1", "fecha": motor.hoy().isoformat(), "valor": 800}]
    cfg["alertasPrecio"] = [{"id": "al1", "producto": "c1", "condicion": "menor", "valor": 1000}]
    d = motor.construir(copy.deepcopy(cfg), str(tmp_path), descargar=False)
    al = [a for a in d["alertas"] if a["clave"] == "alerta-precio"]
    assert len(al) == 1 and al[0]["destino"] == {"tab": "producto", "producto": "c1"}
    assert d["alertasPrecio"] == cfg["alertasPrecio"]
    cfg["config"]["avisosOff"] = ["alerta-precio"]
    d = motor.construir(cfg, str(tmp_path), descargar=False)
    assert not [a for a in d["alertas"] if a["clave"] == "alerta-precio"]


# ---------------------------------------------------------------- deshacer tras borrar

@pytest.fixture
def srv(tmp_path, monkeypatch):
    from app import servidor
    monkeypatch.setattr(servidor, "DATOS", str(tmp_path))
    cfg = copy.deepcopy(almacen.CARTERA_VACIA)
    cfg["productos"] = [{"id": "c1", "nombre": "Cuenta", "tipo": "efectivo"}]
    cfg["valoraciones"] = [{"id": "v1", "producto": "c1", "fecha": "2026-10-01", "valor": 1000}]
    cfg["flujos"] = [{"id": "f1", "fecha": "2026-10-02", "tipo": "gasto", "importe": 50, "categoria": "Casa",
                      "concepto": "Luz", "adjuntos": [{"archivo": "f1_luz.pdf", "nombre": "luz.pdf"}]},
                     {"id": "f2", "fecha": "2026-10-03", "tipo": "gasto", "importe": 20, "categoria": "Casa"}]
    car = tmp_path / "carteras" / "mia"
    os.makedirs(car / "adjuntos")
    (car / "adjuntos" / "f1_luz.pdf").write_bytes(b"%PDF")
    (car / "cartera.json").write_text(json.dumps(cfg), encoding="utf-8")
    servidor.guarda_registro({"activa": "mia"})
    servidor._DESHACER.clear()
    return servidor, car


def _lee(car):
    return json.loads((car / "cartera.json").read_text(encoding="utf-8"))


def test_deshacer_devuelve_lo_borrado_con_sus_facturas(srv):
    servidor, car = srv
    cli = servidor.app.test_client()
    j = cli.delete("/api/flujos/f1").get_json()
    assert j["ok"] and j["deshacer"]
    assert [f["id"] for f in _lee(car)["flujos"]] == ["f2"]
    assert not (car / "adjuntos" / "f1_luz.pdf").exists()         # renombrada para encontrarla
    r = cli.post("/api/deshacer", json={"token": j["deshacer"]})
    assert r.status_code == 200 and [f["id"] for f in r.get_json()["cartera"]["flujos"]] == ["f1", "f2"]
    assert [f["id"] for f in _lee(car)["flujos"]] == ["f1", "f2"]
    assert (car / "adjuntos" / "f1_luz.pdf").exists()             # y vuelve a su nombre
    # Solo una vez.
    assert cli.post("/api/deshacer", json={"token": j["deshacer"]}).status_code == 409


def test_no_deshace_si_despues_hubo_otro_cambio_o_el_token_no_vale(srv):
    servidor, car = srv
    cli = servidor.app.test_client()
    j = cli.post("/api/flujos-borrar", json={"ids": ["f1"]}).get_json()
    assert j["deshacer"]
    assert cli.post("/api/deshacer", json={"token": "otro"}).status_code == 409
    assert cli.post("/api/deshacer", json={"token": j["deshacer"]}).status_code == 200
    j = cli.delete("/api/flujos/f2").get_json()
    cli.post("/api/flujos", json={"fecha": "2026-10-05", "tipo": "gasto", "importe": "9", "categoria": "Casa"})
    r = cli.post("/api/deshacer", json={"token": j["deshacer"]})
    assert r.status_code == 409 and "Copias" in r.get_json()["errores"][0]
    assert sorted(f["importe"] for f in _lee(car)["flujos"]) == [9, 50]   # no pisa el cambio nuevo


def test_no_deshace_si_alguien_escribio_por_fuera(srv):
    servidor, car = srv
    cli = servidor.app.test_client()
    j = cli.delete("/api/flujos/f2").get_json()
    cfg = _lee(car)
    cfg["titular"] = "Cambiado en otro sitio"
    (car / "cartera.json").write_text(json.dumps(cfg), encoding="utf-8")
    assert cli.post("/api/deshacer", json={"token": j["deshacer"]}).status_code == 409
    assert _lee(car)["titular"] == "Cambiado en otro sitio"


def test_guardar_no_ofrece_deshacer(srv):
    servidor, _ = srv
    j = servidor.app.test_client().post(
        "/api/flujos", json={"fecha": "2026-10-05", "tipo": "gasto", "importe": "9", "categoria": "Casa"}).get_json()
    assert j["ok"] and "deshacer" not in j


def test_siguiente_id_con_prefijo_largo():
    assert almacen.siguiente_id([{"id": "al9"}, {"id": "a3"}], "al") == "al10"
    assert almacen.siguiente_id([{"id": "al9"}, {"id": "a3"}], "a") == "a4"
