# -*- coding: utf-8 -*-
"""
Estructura de mis_datos ordenada (oct-2026): las carteras siempre en carteras/<id>/
y los datos internos de la app en app/. migra_layout() reordena, sin borrar, lo que
venga de versiones viejas (cartera suelta en la raíz y registro.json en la raíz).
"""
import json
import os


def _datos(tmp_path, monkeypatch):
    from app import servidor
    monkeypatch.setattr(servidor, "DATOS", str(tmp_path))
    os.makedirs(str(tmp_path), exist_ok=True)
    return servidor


def _escribe(ruta, obj):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(obj, f)


# ---------------------------------------------------------------- migración

def test_migra_cartera_suelta_a_carpeta(tmp_path, monkeypatch):
    from app import almacen
    srv = _datos(tmp_path, monkeypatch)
    cfg = json.loads(json.dumps(almacen.CARTERA_VACIA))
    cfg["titular"] = "Mi dinero"
    _escribe(os.path.join(str(tmp_path), "cartera.json"), cfg)
    # ruido típico del layout antiguo (cálculo, estado, cache)
    _escribe(os.path.join(str(tmp_path), "estado.json"), {"x": 1})
    os.makedirs(os.path.join(str(tmp_path), "cache"), exist_ok=True)

    srv.migra_layout()

    assert not os.path.exists(os.path.join(str(tmp_path), "cartera.json"))
    assert os.path.isdir(os.path.join(str(tmp_path), "carteras"))
    cid = os.listdir(os.path.join(str(tmp_path), "carteras"))[0]
    base = os.path.join(str(tmp_path), "carteras", cid)
    assert os.path.exists(os.path.join(base, "cartera.json"))
    assert os.path.exists(os.path.join(base, "estado.json"))   # el ruido se movió también
    assert os.path.isdir(os.path.join(base, "cache"))
    # el registro interno queda en app/ y apunta a la cartera migrada
    assert os.path.exists(os.path.join(str(tmp_path), "app", "registro.json"))
    assert srv.id_activa() == cid


def test_migra_registro_de_la_raiz_a_app(tmp_path, monkeypatch):
    srv = _datos(tmp_path, monkeypatch)
    # Layout antiguo ya multi, pero con registro.json en la raíz.
    os.makedirs(os.path.join(str(tmp_path), "carteras", "uno"), exist_ok=True)
    _escribe(os.path.join(str(tmp_path), "carteras", "uno", "cartera.json"),
             {"version": 1, "titular": "Uno", "productos": [], "movimientos": [], "valoraciones": []})
    _escribe(os.path.join(str(tmp_path), "registro.json"), {"activa": "uno"})

    srv.migra_layout()

    assert not os.path.exists(os.path.join(str(tmp_path), "registro.json"))
    nuevo = os.path.join(str(tmp_path), "app", "registro.json")
    assert os.path.exists(nuevo)
    assert json.load(open(nuevo, encoding="utf-8"))["activa"] == "uno"
    assert srv.id_activa() == "uno"


def test_migra_es_idempotente(tmp_path, monkeypatch):
    from app import almacen
    srv = _datos(tmp_path, monkeypatch)
    _escribe(os.path.join(str(tmp_path), "cartera.json"),
             json.loads(json.dumps(almacen.CARTERA_VACIA)))
    srv.migra_layout()
    antes = sorted(os.listdir(str(tmp_path)))
    srv.migra_layout()   # segunda pasada: no cambia nada
    assert sorted(os.listdir(str(tmp_path))) == antes


# ---------------------------------------------------------------- empezar limpio

def test_empezar_crea_cartera_en_su_carpeta(tmp_path, monkeypatch):
    srv = _datos(tmp_path, monkeypatch)
    cli = srv.app.test_client()
    assert srv.modo() == "demo"

    r = cli.post("/api/empezar", json={"desde": "vacia"})
    assert r.get_json()["ok"] is True

    # No deja una cartera suelta en la raíz: va directa a carteras/<id>/.
    assert not os.path.exists(os.path.join(str(tmp_path), "cartera.json"))
    assert os.path.isdir(os.path.join(str(tmp_path), "carteras"))
    assert os.path.exists(os.path.join(str(tmp_path), "app", "registro.json"))
    assert srv.modo() == "propio"
