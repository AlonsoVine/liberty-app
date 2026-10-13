# -*- coding: utf-8 -*-
"""
Endpoint /api/descargar-version: descarga el .exe de la última versión y lo deja JUNTO al
actual, con la versión en el nombre, sin ejecutar ni sobrescribir nada. Todo con
mocks (sys.frozen, sys.executable y urlopen): no se sale a la red ni hace falta un .exe.
"""
import io
import json
import sys


def test_actualizar_en_dev_no_hace_nada(monkeypatch):
    from app import servidor
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    r = servidor.app.test_client().post("/api/descargar-version")
    j = r.get_json()
    assert j["ok"] is False and j["motivo"] == "dev"


def test_actualizar_descarga_junto_al_exe(tmp_path, monkeypatch):
    from app import servidor
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    exe = tmp_path / "Liberty.exe"
    exe.write_bytes(b"ejecutable-viejo")
    monkeypatch.setattr(sys, "executable", str(exe))
    monkeypatch.setattr(servidor, "version_actual", lambda: "1.0.0")
    monkeypatch.setenv("PATRIMONIO_NO_ABRIR", "1")   # no abrir la carpeta en el test

    data_exe = b"MZ" + b"\x00" * 2_000_000          # un .exe de pega, >1 MB

    def fake_urlopen(req, timeout=0):
        url = getattr(req, "full_url", str(req))
        if "api.github.com" in url:                 # consulta de la última versión
            return io.BytesIO(json.dumps({"tag_name": "v9.9.9"}).encode())
        return io.BytesIO(data_exe)                 # descarga del ejecutable

    monkeypatch.setattr(servidor.urllib.request, "urlopen", fake_urlopen)

    j = servidor.app.test_client().post("/api/descargar-version").get_json()
    assert j["ok"] is True
    assert j["archivo"] == "Liberty 9.9.9.exe"
    destino = tmp_path / "Liberty 9.9.9.exe"
    assert destino.exists() and destino.read_bytes() == data_exe
    assert not (tmp_path / "Liberty 9.9.9.exe.parcial").exists()   # el temporal se renombra
    assert exe.read_bytes() == b"ejecutable-viejo"                 # el viejo NO se toca


def test_actualizar_cuando_ya_esta_al_dia(tmp_path, monkeypatch):
    from app import servidor
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Liberty.exe"))
    monkeypatch.setattr(servidor, "version_actual", lambda: "9.9.9")
    monkeypatch.setattr(servidor.urllib.request, "urlopen",
                        lambda req, timeout=0: io.BytesIO(json.dumps({"tag_name": "v1.0.0"}).encode()))
    j = servidor.app.test_client().post("/api/descargar-version").get_json()
    assert j["ok"] is False and j["motivo"] == "al-dia"
