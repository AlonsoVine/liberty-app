# -*- coding: utf-8 -*-
"""
Biblioteca de documentos: carpetas anidadas y archivos (gestor de archivos integrado).
Los ficheros viven en disco (carpeta «biblioteca») y la cartera solo guarda la
referencia. Carpeta temporal, sin red. Modo «propio» (cartera.json suelto en DATOS).
"""
import io
import json
import os
import zipfile

import pytest

from app import almacen


def _prepara(tmp_path, monkeypatch):
    from app import servidor
    monkeypatch.setattr(servidor, "DATOS", str(tmp_path))
    os.makedirs(str(tmp_path), exist_ok=True)
    cfg = json.loads(json.dumps(almacen.CARTERA_VACIA))
    with open(os.path.join(str(tmp_path), "cartera.json"), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh)
    return servidor


def _carga(servidor):
    with open(os.path.join(servidor.DATOS, "cartera.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _bib(servidor):
    return _carga(servidor).get("biblioteca", {})


# ----------------------------------------------------------- almacen (unidad)

def cfg_vacia():
    return json.loads(json.dumps(almacen.CARTERA_VACIA))


def test_crea_carpetas_y_limita_anidamiento():
    cfg = cfg_vacia()
    raiz = almacen.biblioteca_crea_carpeta(cfg, "car_1", "Hacienda", None)
    sub = almacen.biblioteca_crea_carpeta(cfg, "car_2", "2025", raiz["id"])
    assert sub["padre"] == "car_1"
    assert len(cfg["biblioteca"]["carpetas"]) == 2
    # nombre vacío -> error
    with pytest.raises(almacen.ErrorValidacion):
        almacen.biblioteca_crea_carpeta(cfg, "car_x", "   ", None)
    # padre inexistente -> error
    with pytest.raises(almacen.ErrorValidacion):
        almacen.biblioteca_crea_carpeta(cfg, "car_y", "X", "no_existe")


def test_mover_carpeta_dentro_de_si_misma_falla():
    cfg = cfg_vacia()
    a = almacen.biblioteca_crea_carpeta(cfg, "car_a", "A", None)
    b = almacen.biblioteca_crea_carpeta(cfg, "car_b", "B", a["id"])
    with pytest.raises(almacen.ErrorValidacion):
        almacen.biblioteca_mueve(cfg, "carpeta", a["id"], b["id"])  # a dentro de su hija


def test_borra_carpeta_arrastra_subcarpetas_y_archivos():
    cfg = cfg_vacia()
    a = almacen.biblioteca_crea_carpeta(cfg, "car_a", "A", None)
    b = almacen.biblioteca_crea_carpeta(cfg, "car_b", "B", a["id"])
    almacen.biblioteca_anota_archivo(cfg, "arc_1", "arc_1.pdf", "doc.pdf", "application/pdf", 10, b["id"], "2026-01-01T00:00:00")
    ficheros = almacen.biblioteca_borra_carpeta(cfg, a["id"])
    assert ficheros == ["arc_1.pdf"]
    assert cfg["biblioteca"]["carpetas"] == []
    assert cfg["biblioteca"]["archivos"] == []


# ----------------------------------------------------------- servidor (e2e)

def test_biblioteca_ciclo_completo(tmp_path, monkeypatch):
    servidor = _prepara(tmp_path, monkeypatch)
    client = servidor.app.test_client()

    # Crear carpeta.
    r = client.post("/api/biblioteca/carpeta", json={"nombre": "Hacienda", "padre": None})
    j = r.get_json()
    assert j["ok"] is True
    cid = j["item"]["id"]

    # Subir un archivo a esa carpeta (cualquier tipo: aquí un .txt).
    data = {"archivo": (io.BytesIO(b"declaracion 2025"), "renta.txt"), "carpeta": cid}
    j = client.post("/api/biblioteca/subir", data=data, content_type="multipart/form-data").get_json()
    assert j["ok"] is True
    arch = j["item"]
    assert arch["nombre"] == "renta.txt" and arch["carpeta"] == cid
    assert os.path.exists(os.path.join(str(tmp_path), "biblioteca", arch["archivo"]))

    # Servir el archivo (inline).
    r = client.get("/api/biblioteca/archivo/" + arch["id"])
    assert r.status_code == 200 and r.data == b"declaracion 2025"
    # Descargar (as_attachment).
    r = client.get("/api/biblioteca/archivo/" + arch["id"] + "?descargar=1")
    assert r.status_code == 200 and "attachment" in r.headers.get("Content-Disposition", "")

    # Renombrar el archivo.
    r = client.post("/api/biblioteca/renombra", json={"tipo": "archivo", "id": arch["id"], "nombre": "Renta 2025.txt"})
    assert r.get_json()["ok"] is True
    assert _bib(servidor)["archivos"][0]["nombre"] == "Renta 2025.txt"

    # Mover el archivo a la raíz.
    r = client.post("/api/biblioteca/mover", json={"tipo": "archivo", "id": arch["id"], "destino": None})
    assert r.get_json()["ok"] is True
    assert _bib(servidor)["archivos"][0]["carpeta"] is None

    # Borrar el archivo: sale de «archivos» pero va a la papelera (el fichero se conserva).
    r = client.post("/api/biblioteca/borrar", json={"id": arch["id"]})
    assert r.get_json()["ok"] is True
    assert _bib(servidor)["archivos"] == []
    assert [e["id"] for e in _bib(servidor)["papelera"]] == [arch["id"]]
    assert os.path.exists(os.path.join(str(tmp_path), "biblioteca", arch["archivo"]))


def test_subir_carpeta_recrea_estructura(tmp_path, monkeypatch):
    servidor = _prepara(tmp_path, monkeypatch)
    client = servidor.app.test_client()
    # Dos archivos dentro de una estructura de carpetas (como webkitdirectory).
    data = {
        "archivos": [
            (io.BytesIO(b"doc A"), "renta.pdf"),
            (io.BytesIO(b"doc B"), "nomina.pdf"),
        ],
        "rutas": json.dumps(["Documentos/Hacienda/renta.pdf", "Documentos/Nominas/nomina.pdf"]),
    }
    r = client.post("/api/biblioteca/subir-carpeta", data=data, content_type="multipart/form-data")
    j = r.get_json()
    assert j["ok"] is True and j["subidos"] == 2
    bib = _bib(servidor)
    nombres = {c["nombre"] for c in bib["carpetas"]}
    assert {"Documentos", "Hacienda", "Nominas"} <= nombres
    # Estructura: Documentos padre de Hacienda y Nominas.
    docs = next(c for c in bib["carpetas"] if c["nombre"] == "Documentos")
    hac = next(c for c in bib["carpetas"] if c["nombre"] == "Hacienda")
    assert docs["padre"] is None and hac["padre"] == docs["id"]
    # El archivo renta.pdf cuelga de Hacienda y existe en disco.
    renta = next(a for a in bib["archivos"] if a["nombre"] == "renta.pdf")
    assert renta["carpeta"] == hac["id"]
    assert os.path.exists(os.path.join(str(tmp_path), "biblioteca", renta["archivo"]))


def test_copiar_archivo_y_carpeta(tmp_path, monkeypatch):
    servidor = _prepara(tmp_path, monkeypatch)
    client = servidor.app.test_client()
    # Estructura: Origen/sub con un archivo.
    orig = client.post("/api/biblioteca/carpeta", json={"nombre": "Origen"}).get_json()["item"]["id"]
    sub = client.post("/api/biblioteca/carpeta", json={"nombre": "Sub", "padre": orig}).get_json()["item"]["id"]
    data = {"archivo": (io.BytesIO(b"contenido"), "doc.txt"), "carpeta": sub}
    arch = client.post("/api/biblioteca/subir", data=data, content_type="multipart/form-data").get_json()["item"]

    # Copiar el ARCHIVO a la raíz: ahora hay 2 archivos, mismo nombre, en disco ambos.
    r = client.post("/api/biblioteca/copiar", json={"tipo": "archivo", "id": arch["id"], "destino": None})
    assert r.get_json()["ok"] is True
    archivos = _bib(servidor)["archivos"]
    assert len(archivos) == 2
    for a in archivos:
        assert os.path.exists(os.path.join(str(tmp_path), "biblioteca", a["archivo"]))

    # Copiar la CARPETA Origen (con su subcarpeta y archivo) a la raíz: duplica el árbol.
    carpetas_antes = len(_bib(servidor)["carpetas"])
    r = client.post("/api/biblioteca/copiar", json={"tipo": "carpeta", "id": orig, "destino": None})
    assert r.get_json()["ok"] is True
    bib = _bib(servidor)
    assert len(bib["carpetas"]) == carpetas_antes + 2        # Origen + Sub duplicadas
    assert sum(1 for c in bib["carpetas"] if c["nombre"] == "Origen") == 2

    # No se puede copiar una carpeta dentro de sí misma.
    r = client.post("/api/biblioteca/copiar", json={"tipo": "carpeta", "id": orig, "destino": sub})
    assert r.status_code == 400 and r.get_json()["ok"] is False


def test_papelera_guarda_restaura_y_limita(tmp_path, monkeypatch):
    servidor = _prepara(tmp_path, monkeypatch)
    client = servidor.app.test_client()
    # Tope de papelera = 2.
    client.post("/api/config", json={"papeleraMax": 2})
    ids, discos = [], []
    for i in range(3):
        data = {"archivo": (io.BytesIO(b"x" * (i + 1)), f"f{i}.txt")}
        a = client.post("/api/biblioteca/subir", data=data, content_type="multipart/form-data").get_json()["item"]
        ids.append(a["id"])
        discos.append(a["archivo"])
    # Borra los tres (en orden f0, f1, f2). La papelera guarda solo los 2 últimos (f2, f1).
    for i in range(3):
        r = client.post("/api/biblioteca/borrar", json={"id": ids[i]})
        assert r.get_json()["ok"] is True
    pap = _bib(servidor)["papelera"]
    assert [e["nombre"] for e in pap] == ["f2.txt", "f1.txt"]
    # f0 se cayó de la papelera -> su fichero ya no está en disco.
    assert not os.path.exists(os.path.join(str(tmp_path), "biblioteca", discos[0]))
    # f1 y f2 siguen en disco (están en la papelera).
    assert os.path.exists(os.path.join(str(tmp_path), "biblioteca", discos[1]))
    # Restaurar f1: vuelve a archivos.
    r = client.post("/api/biblioteca/papelera-restaura", json={"id": ids[1]})
    assert r.get_json()["ok"] is True
    assert any(a["id"] == ids[1] for a in _bib(servidor)["archivos"])
    # Vaciar papelera: borra lo que quede (f2) del disco.
    r = client.post("/api/biblioteca/papelera-vacia")
    assert r.get_json()["ok"] is True
    assert _bib(servidor)["papelera"] == []
    assert not os.path.exists(os.path.join(str(tmp_path), "biblioteca", discos[2]))


def test_biblioteca_zip_export_import(tmp_path, monkeypatch):
    servidor = _prepara(tmp_path, monkeypatch)
    client = servidor.app.test_client()
    cid = client.post("/api/biblioteca/carpeta", json={"nombre": "Escrituras"}).get_json()["item"]["id"]
    data = {"archivo": (io.BytesIO(b"PDF escritura"), "piso.pdf"), "carpeta": cid}
    arch = client.post("/api/biblioteca/subir", data=data, content_type="multipart/form-data").get_json()["item"]

    # Exportar el .zip: el documento va en «archivos/» recreando su carpeta, con el nombre
    # visible, y los datos en un .json reconocible en la raíz.
    r = client.get("/api/copia/descargar?formato=zip")
    assert r.status_code == 200
    zip_bytes = r.data
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        nombres = z.namelist()
        assert "archivos/Escrituras/piso.pdf" in nombres
        assert z.read("archivos/Escrituras/piso.pdf") == b"PDF escritura"
        assert any(n.endswith(".json") and "/" not in n for n in nombres)

    # Simular pérdida: borrar el archivo.
    client.post("/api/biblioteca/borrar", json={"id": arch["id"]})
    assert _bib(servidor)["archivos"] == []

    # Restaurar el .zip: el documento vuelve a la cartera y al disco.
    r = client.post("/api/copia/subir",
                    data={"archivo": (io.BytesIO(zip_bytes), "copia.zip")},
                    content_type="multipart/form-data")
    assert r.get_json()["ok"] is True
    archivos = _bib(servidor)["archivos"]
    assert len(archivos) == 1 and archivos[0]["nombre"] == "piso.pdf"
    assert os.path.exists(os.path.join(str(tmp_path), "biblioteca", archivos[0]["archivo"]))
