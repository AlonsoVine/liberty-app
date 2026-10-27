# -*- coding: utf-8 -*-
"""
Entorno de ejecución (app/entorno.py) y endurecimiento del servidor para Docker:
resolución de datos/host/puerto/hosts, allowlist de Host configurable, defensa CSRF por
Origin/Referer y la señal de vida /api/ping con versión y modo. No sale a la red.
"""
import importlib
import json
import os

from app import entorno

_VARS = ("LIBERTY_DATOS", "PATRIMONIO_DATOS", "LIBERTY_HOST", "LIBERTY_PUERTO",
         "PATRIMONIO_PUERTO", "LIBERTY_HOSTS_PERMITIDOS", "LIBERTY_MODO", "PATRIMONIO_NO_ABRIR")


def _recarga(monkeypatch, **variables):
    """Fija (y limpia el resto de) las variables de entorno relevantes y recarga el módulo."""
    for v in _VARS:
        monkeypatch.delenv(v, raising=False)
    for k, val in variables.items():
        monkeypatch.setenv(k, val)
    return importlib.reload(entorno)


def teardown_module(module):
    # Deja entorno como estaba, para no afectar a otras pruebas.
    for v in _VARS:
        os.environ.pop(v, None)
    importlib.reload(entorno)


# ----------------------------------------------------------------- entorno (datos/host/puerto)

def test_datos_prioriza_liberty_sobre_patrimonio(monkeypatch):
    assert _recarga(monkeypatch, LIBERTY_DATOS="/data", PATRIMONIO_DATOS="/otro").DATOS == "/data"


def test_datos_alias_patrimonio(monkeypatch):
    assert _recarga(monkeypatch, PATRIMONIO_DATOS="/solo-alias").DATOS == "/solo-alias"


def test_datos_por_defecto_mis_datos(monkeypatch):
    assert os.path.basename(_recarga(monkeypatch).DATOS) == "mis_datos"


def test_host_y_puerto(monkeypatch):
    e = _recarga(monkeypatch, LIBERTY_HOST="0.0.0.0", LIBERTY_PUERTO="9000")
    assert e.HOST == "0.0.0.0" and e.PUERTO == 9000
    e2 = _recarga(monkeypatch)
    assert e2.HOST == "127.0.0.1" and e2.PUERTO == 8765


def test_puerto_alias_patrimonio(monkeypatch):
    assert _recarga(monkeypatch, PATRIMONIO_PUERTO="8799").PUERTO == 8799


def test_hosts_permitidos_exactos_sin_comodines(monkeypatch):
    e = _recarga(monkeypatch, LIBERTY_HOSTS_PERMITIDOS="Mi-Pi.tailnet.TS.net, otra.ts.net")
    assert "mi-pi.tailnet.ts.net" in e.HOSTS_PERMITIDOS   # normaliza a minúsculas
    assert "otra.ts.net" in e.HOSTS_PERMITIDOS
    assert {"127.0.0.1", "localhost", "::1"} <= e.HOSTS_PERMITIDOS   # localhost siempre
    assert not any("*" in h for h in e.HOSTS_PERMITIDOS)             # nada de comodines


def test_es_docker_por_marca(monkeypatch):
    assert _recarga(monkeypatch, LIBERTY_MODO="docker").ES_DOCKER is True
    assert _recarga(monkeypatch, LIBERTY_MODO="escritorio").ES_DOCKER is False


def test_no_abrir_en_docker(monkeypatch):
    assert _recarga(monkeypatch, LIBERTY_MODO="docker").NO_ABRIR is True


# ----------------------------------------------------------------- servidor (allowlist/CSRF/ping)

def _servidor_tmp(tmp_path, monkeypatch):
    from app import almacen, servidor
    monkeypatch.setattr(servidor, "DATOS", str(tmp_path))
    os.makedirs(str(tmp_path), exist_ok=True)
    cfg = json.loads(json.dumps(almacen.CARTERA_VACIA))
    with open(os.path.join(str(tmp_path), "cartera.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    return servidor


def test_host_permitido_configurado(tmp_path, monkeypatch):
    servidor = _servidor_tmp(tmp_path, monkeypatch)
    monkeypatch.setattr(servidor, "HOSTS_PERMITIDOS",
                        {"127.0.0.1", "localhost", "::1", "mi-pi.ts.net"})
    client = servidor.app.test_client()
    assert client.get("/", headers={"Host": "mi-pi.ts.net"}).status_code == 200
    assert client.get("/", headers={"Host": "otra.ts.net"}).status_code == 403


def test_csrf_origin_de_otro_sitio_bloqueado(tmp_path, monkeypatch):
    servidor = _servidor_tmp(tmp_path, monkeypatch)
    client = servidor.app.test_client()
    # POST con Origin externo -> 403 aunque el Host sea local.
    r = client.post("/api/config", json={"colchon": "1000"},
                    headers={"Host": "127.0.0.1:8765", "Origin": "http://evil.example.com"})
    assert r.status_code == 403
    # POST con Origin del propio sitio -> pasa y guarda.
    r2 = client.post("/api/config", json={"colchon": "1000"},
                     headers={"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"})
    assert r2.get_json()["ok"] is True
    # POST sin Origin (p. ej. cliente de pruebas) -> pasa, como hasta ahora.
    assert client.post("/api/config", json={"colchon": "2000"}).get_json()["ok"] is True


def test_ping_incluye_version_y_modo(tmp_path, monkeypatch):
    servidor = _servidor_tmp(tmp_path, monkeypatch)
    j = servidor.app.test_client().get("/api/ping").get_json()
    assert j["app"] == "patrimonio"
    assert j["version"] == servidor.version_actual()
    assert j["modo"] in ("propio", "demo")
    assert "docker" in j


def test_descargar_version_en_docker_avisa_de_imagen(tmp_path, monkeypatch):
    servidor = _servidor_tmp(tmp_path, monkeypatch)
    monkeypatch.setattr(servidor.entorno, "ES_DOCKER", True)
    j = servidor.app.test_client().post("/api/descargar-version").get_json()
    assert j["ok"] is False and j["motivo"] == "docker"
    assert "docker compose pull" in j["mensaje"]


def test_api_entorno(tmp_path, monkeypatch):
    servidor = _servidor_tmp(tmp_path, monkeypatch)
    monkeypatch.setattr(servidor.entorno, "ES_DOCKER", True)
    j = servidor.app.test_client().get("/api/entorno").get_json()
    assert j["docker"] is True
    assert j["puedeCambiarRuta"] is False
    assert os.path.basename(j["rutaDatos"]) == os.path.basename(str(tmp_path))
