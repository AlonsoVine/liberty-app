# -*- coding: utf-8 -*-
"""
Facturas adjuntas a un apunte de ingreso/gasto: subir, servir, marcar importante y
quitar; el archivo vive en disco (carpeta «adjuntos») y la cartera solo guarda la
referencia. Carpeta temporal, sin red. Modo «propio» (cartera.json suelto en DATOS).
"""
import io
import json
import os


def _prepara(tmp_path, monkeypatch):
    from app import almacen, servidor
    monkeypatch.setattr(servidor, "DATOS", str(tmp_path))
    os.makedirs(str(tmp_path), exist_ok=True)
    cfg = json.loads(json.dumps(almacen.CARTERA_VACIA))
    cfg["flujos"] = [{"id": "f1", "fecha": "2026-01-10", "tipo": "gasto",
                      "importe": 50.0, "categoria": "Alimentación"}]
    with open(os.path.join(str(tmp_path), "cartera.json"), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh)
    return servidor


def _carga(servidor):
    with open(os.path.join(servidor.DATOS, "cartera.json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_adjunto_ciclo_completo(tmp_path, monkeypatch):
    servidor = _prepara(tmp_path, monkeypatch)
    client = servidor.app.test_client()
    # Subir una factura (PDF de pega).
    data = {"id": "f1", "archivo": (io.BytesIO(b"%PDF-1.4 factura"), "factura mayo.pdf")}
    adj = client.post("/api/flujo-adjunto", data=data, content_type="multipart/form-data").get_json()
    assert adj["ok"] is True
    a = adj["item"]
    assert a["nombre"] == "factura mayo.pdf" and a["id"] and a["archivo"].endswith(".pdf")
    assert os.path.exists(os.path.join(str(tmp_path), "adjuntos", a["archivo"]))
    assert _carga(servidor)["flujos"][0]["adjuntos"][0]["id"] == a["id"]
    # Servir el archivo (inline).
    r = client.get("/api/adjunto/f1/" + a["id"])
    assert r.status_code == 200 and r.data == b"%PDF-1.4 factura"
    # Marcar como importante.
    r = client.post("/api/flujo-adjunto-importante", json={"flujo": "f1", "adjunto": a["id"], "importante": True})
    assert r.get_json()["ok"] is True
    assert _carga(servidor)["flujos"][0]["adjuntos"][0]["importante"] is True
    # Quitar: borra referencia y archivo.
    r = client.post("/api/flujo-adjunto-quitar", json={"flujo": "f1", "adjunto": a["id"]})
    assert r.get_json()["ok"] is True
    assert not os.path.exists(os.path.join(str(tmp_path), "adjuntos", a["archivo"]))
    assert "adjuntos" not in _carga(servidor)["flujos"][0]


def test_adjunto_formato_no_admitido(tmp_path, monkeypatch):
    servidor = _prepara(tmp_path, monkeypatch)
    client = servidor.app.test_client()
    data = {"id": "f1", "archivo": (io.BytesIO(b"MZ"), "programa.exe")}
    r = client.post("/api/flujo-adjunto", data=data, content_type="multipart/form-data")
    assert r.status_code == 400 and r.get_json()["ok"] is False
    assert not os.path.isdir(os.path.join(str(tmp_path), "adjuntos")) or not os.listdir(os.path.join(str(tmp_path), "adjuntos"))


def test_borrar_apunte_borra_sus_facturas(tmp_path, monkeypatch):
    servidor = _prepara(tmp_path, monkeypatch)
    client = servidor.app.test_client()
    data = {"id": "f1", "archivo": (io.BytesIO(b"%PDF"), "f.pdf")}
    a = client.post("/api/flujo-adjunto", data=data, content_type="multipart/form-data").get_json()["item"]
    ruta = os.path.join(str(tmp_path), "adjuntos", a["archivo"])
    assert os.path.exists(ruta)
    r = client.delete("/api/flujos/f1")
    assert r.get_json()["ok"] is True
    assert not os.path.exists(ruta)   # al borrar el apunte, su factura también
