# -*- coding: utf-8 -*-
"""
Colores (oct-2026): paleta ampliada, color propio para los apartados (reservados) y
repartir colores entre apartados igual que entre los productos.
"""
import copy

from app import almacen, motor


def cfg():
    return copy.deepcopy(almacen.CARTERA_VACIA)


def test_paleta_ampliada():
    assert len(motor.PALETA) >= 24
    # cada entrada es (color_claro, color_oscuro)
    assert all(len(v) == 2 for v in motor.PALETA.values())


def test_apartado_guarda_su_color():
    c = cfg()
    a = almacen.guarda_apartado(c, {"nombre": "Impuestos", "importe": "500", "slot": "7"})
    assert a["slot"] == 7


def test_apartado_sin_color_no_guarda_slot():
    c = cfg()
    a = almacen.guarda_apartado(c, {"nombre": "Obras", "importe": "1000"})
    assert "slot" not in a


def test_reparte_colores_apartados_da_distintos():
    c = cfg()
    for i in range(3):
        almacen.guarda_apartado(c, {"nombre": f"A{i}", "importe": "100"})
    almacen.reparte_colores_apartados(c)
    slots = [a["slot"] for a in c["apartados"]]
    assert slots == [1, 2, 3]


def test_reparte_colores_productos_usa_toda_la_paleta():
    c = cfg()
    # 20 productos manuales -> 20 colores distintos (hay 24 en la paleta)
    for i in range(20):
        almacen.guarda_producto(c, {"nombre": f"P{i}", "tipo": "otro", "fuente": "manual"})
    almacen.reparte_colores(c)
    slots = [p["slot"] for p in c["productos"]]
    assert len(set(slots)) == 20
    assert max(slots) <= len(motor.PALETA)


def test_apartados_out_lleva_color(tmp_path):
    c = cfg()
    almacen.guarda_apartado(c, {"nombre": "Impuestos", "importe": "500", "slot": "3"})
    almacen.guarda_producto(c, {"nombre": "Piso", "tipo": "inmueble", "fuente": "manual"})
    almacen.guarda_valoracion(c, {"producto": c["productos"][0]["id"],
                                  "fecha": "2025-01-01", "valor": "100000"})
    d = motor.construir(c, str(tmp_path), descargar=False)
    ap = d["apartados"][0]
    assert ap["slot"] == 3
    assert isinstance(ap["color"], (list, tuple)) and len(ap["color"]) == 2


def test_endpoint_repartir_apartados(tmp_path, monkeypatch):
    from app import servidor as srv
    monkeypatch.setattr(srv, "DATOS", str(tmp_path))
    c = cfg()
    c["apartados"] = [{"id": "a1", "nombre": "Uno", "importe": 100},
                      {"id": "a2", "nombre": "Dos", "importe": 200}]
    import os
    os.makedirs(str(tmp_path / "carteras" / "mia"), exist_ok=True)
    import json
    with open(tmp_path / "carteras" / "mia" / "cartera.json", "w", encoding="utf-8") as f:
        json.dump(c, f)
    srv.guarda_registro({"activa": "mia"})
    cli = srv.app.test_client()
    r = cli.post("/api/repartir-colores", json={"que": "apartados"})
    assert r.get_json()["ok"] is True
    aps = r.get_json()["cartera"]["apartados"]
    assert [a["slot"] for a in aps] == [1, 2]
