"""Renombrar (o fusionar) una categoría de ingresos y gastos en toda la cartera (ADR 0032)."""

import copy
import json
import os

import pytest

from app import almacen


def cartera():
    cfg = copy.deepcopy(almacen.CARTERA_VACIA)
    cfg["config"]["categorias"] = [
        {"nombre": "Alquiler Mayor", "tipo": "ingreso"},
        {"nombre": "Alquileres", "tipo": "ingreso"},
        {"nombre": "Comida", "tipo": "gasto", "presupuesto": 400},
        {"nombre": "Alimentación", "tipo": "gasto"},
    ]
    cfg["config"]["reglasCategoria"] = [{"palabra": "mercadona", "categoria": "Comida"},
                                        {"palabra": "mercadona", "categoria": "Alimentación"},
                                        {"palabra": "inquilino", "categoria": "Alquiler Mayor"}]
    cfg["config"]["recurrentes"] = [{"tipo": "gasto", "importe": 50, "categoria": "comida"}]
    cfg["flujos"] = [
        {"id": "f1", "tipo": "ingreso", "fecha": "2026-10-05", "importe": 750, "categoria": "Alquiler Mayor"},
        {"id": "f2", "tipo": "gasto", "fecha": "2026-10-06", "importe": 80, "categoria": "Comida"},
        {"id": "f3", "tipo": "gasto", "fecha": "2026-10-07", "importe": 20, "categoria": "Alimentación"},
    ]
    im = almacen.guarda_inmueble(cfg, {"nombre": "Piso Mayor", "categorias": ["Alquiler Mayor"]})
    q = almacen.guarda_inquilino(cfg, {"inmueble": im["id"], "nombre": "Ana"})
    almacen.guarda_contrato(cfg, {"inquilino": q["id"], "inicio": "2025-01-01", "renta": "750",
                                  "categoria": "Alquiler Mayor"})
    cfg["notas"] = [{"id": "n1", "texto": "x", "vinculo": {"tipo": "categoria", "ref": "Alquiler Mayor"},
                     "vinculos": [{"tipo": "categoria", "ref": "Alquiler Mayor"}]}]
    return cfg


def test_renombrar_cambia_el_nombre_en_todas_partes():
    cfg = cartera()
    n = almacen.renombra_categoria(cfg, "Alquiler Mayor", "Alquiler piso Mayor")
    assert n == {"apuntes": 1, "plantillas": 0, "reglas": 1, "inmuebles": 1, "contratos": 1, "notas": 1,
                 "fusion": False}
    assert cfg["config"]["categorias"][0] == {"nombre": "Alquiler piso Mayor", "tipo": "ingreso"}
    assert cfg["flujos"][0]["categoria"] == "Alquiler piso Mayor"
    assert cfg["config"]["reglasCategoria"][2]["categoria"] == "Alquiler piso Mayor"
    im = cfg["inmuebles"][0]
    assert im["categorias"] == ["Alquiler piso Mayor"]
    assert im["inquilinos"][0]["contratos"][0]["categoria"] == "Alquiler piso Mayor"
    assert cfg["notas"][0]["vinculo"]["ref"] == "Alquiler piso Mayor"
    assert cfg["notas"][0]["vinculos"] == [{"tipo": "categoria", "ref": "Alquiler piso Mayor"}]


def test_solo_mayusculas_tambien_vale():
    cfg = cartera()
    n = almacen.renombra_categoria(cfg, "Comida", "COMIDA")
    assert not n["fusion"] and n["apuntes"] == 1 and n["plantillas"] == 1
    assert cfg["config"]["categorias"][2] == {"nombre": "COMIDA", "tipo": "gasto", "presupuesto": 400}


def test_fusionar_con_una_que_ya_existe():
    cfg = cartera()
    n = almacen.renombra_categoria(cfg, "Comida", "alimentación")
    assert n["fusion"] is True and n["apuntes"] == 1
    nombres = [c["nombre"] for c in cfg["config"]["categorias"]]
    assert "Comida" not in nombres and nombres.count("Alimentación") == 1
    # La de destino hereda el presupuesto que no tenía.
    assert next(c for c in cfg["config"]["categorias"] if c["nombre"] == "Alimentación")["presupuesto"] == 400
    # Manda el nombre de la de destino, aunque se escribiera en minúsculas.
    assert {f["categoria"] for f in cfg["flujos"] if f["tipo"] == "gasto"} == {"Alimentación"}
    assert cfg["config"]["recurrentes"][0]["categoria"] == "Alimentación"
    # La regla repetida (misma palabra y categoría) queda una sola vez.
    assert [r for r in cfg["config"]["reglasCategoria"] if r["palabra"] == "mercadona"] == \
        [{"palabra": "mercadona", "categoria": "Alimentación"}]


def test_lo_que_no_se_puede():
    cfg = cartera()
    for de, a, trozo in (("Comida", "Alquileres", "no se pueden fusionar"),      # gasto con ingreso
                         ("No existe", "Otra", "ya no existe"),
                         ("Comida", "", "nombre nuevo"),
                         ("Comida", "Comida", "igual"),
                         ("Comida", "Sin categoría", "no es una categoría")):
        with pytest.raises(almacen.ErrorValidacion) as e:
            almacen.renombra_categoria(cfg, de, a)
        assert trozo in " ".join(e.value.errores)
    # Dos categorías de inmuebles distintos no se fusionan.
    otro = almacen.guarda_inmueble(cfg, {"nombre": "Local", "categorias": ["Alquileres"]})
    with pytest.raises(almacen.ErrorValidacion) as e:
        almacen.renombra_categoria(cfg, "Alquiler Mayor", "Alquileres")
    assert "inmuebles distintos" in e.value.errores[0] and otro["nombre"] in e.value.errores[0]
    # Una que solo está en los apuntes (no en la lista) también se renombra.
    cfg["flujos"].append({"id": "f9", "tipo": "gasto", "fecha": "2026-10-08", "importe": 5, "categoria": "Varios"})
    assert almacen.renombra_categoria(cfg, "varios", "Otros gastos")["apuntes"] == 1


def test_api_renombrar(tmp_path, monkeypatch):
    from app import servidor
    monkeypatch.setattr(servidor, "DATOS", str(tmp_path))
    with open(os.path.join(str(tmp_path), "cartera.json"), "w", encoding="utf-8") as f:
        json.dump(cartera(), f)
    cl = servidor.app.test_client()
    j = cl.post("/api/categorias/renombrar", json={"de": "Comida", "a": "Supermercado"}).get_json()
    assert j["ok"] is True and j["item"]["apuntes"] == 1
    assert j["cartera"]["flujos"][1]["categoria"] == "Supermercado"
    r = cl.post("/api/categorias/renombrar", json={"de": "Nada", "a": "X"})
    assert r.status_code == 400
