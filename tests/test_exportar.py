# -*- coding: utf-8 -*-
"""
Exportar el panel a un .html autónomo: el nombre que pone el usuario (titular)
va dentro de atributos <meta> y debe quedar escapado para no inyectar markup
en la página que luego se comparte.
"""
import os

from app import exportar

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "web")


def test_pagina_se_genera():
    html = exportar.pagina(WEB, {}, ocultar=False, titulo="Mi patrimonio")
    assert "<html" in html and "window.DATOS" in html
    # La web compartida no lleva los botones ni paneles de «Mis datos», «Ayuda» ni «Ajustes».
    assert '<button data-tab="ajustes"' not in html and 'id="tab-ajustes"' not in html
    assert '<button data-tab="ayuda"' not in html and 'id="tab-datos"' not in html


def test_titulo_malicioso_se_escapa():
    titulo = '"><script>alert(1)</script>'
    html = exportar.pagina(WEB, {}, ocultar=False, titulo=titulo)
    # El payload crudo no aparece y el atributo <meta> no queda roto.
    assert '"><script>alert(1)</script>' not in html
    # Sí aparece ya escapado dentro del meta og:title.
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_ocultar_importes_no_escala_la_tasa_de_ahorro(monkeypatch):
    """Con «ocultar importes» los euros se multiplican por un factor secreto, pero la
    tasa de ahorro es una PROPORCIÓN: escalarla la dejaría sin sentido. Debe quedar
    intacta (un ratio no revela el patrimonio real)."""
    monkeypatch.setattr(exportar.random, "uniform", lambda a, b: 2.0)
    datos = {
        "total": {"patrimonio": 1000.0, "tasaAhorro": 0.25, "hitos": [1, 2]},
        "flujos": {
            "ingresos": [1000.0, 2000.0],
            "tasaAhorro": [0.2, 0.3],
            "esteMes": {"ingresos": 2000.0, "ahorro": 600.0, "tasaAhorro": 0.3},
            "anio": {"ingresos": 10.0, "tasaAhorro": 0.1},
            "media12": {"ingresos": 5.0, "tasaAhorro": 0.15},
        },
    }
    out = exportar.sin_importes(datos)
    # Las proporciones no se tocan (ni en «flujos» ni en «total»).
    assert out["flujos"]["tasaAhorro"] == [0.2, 0.3]
    assert out["flujos"]["esteMes"]["tasaAhorro"] == 0.3
    assert out["flujos"]["anio"]["tasaAhorro"] == 0.1
    assert out["flujos"]["media12"]["tasaAhorro"] == 0.15
    assert out["total"]["tasaAhorro"] == 0.25
    # Los euros del mismo bloque SÍ se escalan por el factor (aquí, ×2).
    assert out["flujos"]["ingresos"] == [2000.0, 4000.0]
    assert out["flujos"]["esteMes"]["ingresos"] == 4000.0
    assert out["flujos"]["esteMes"]["ahorro"] == 1200.0


def _numeros(nodo, ruta="D", clave=None):
    """(ruta, clave, número) de cada número de un árbol de datos."""
    if isinstance(nodo, bool) or nodo is None:
        return
    if isinstance(nodo, (int, float)):
        yield ruta, clave, nodo
    elif isinstance(nodo, list):
        for i, v in enumerate(nodo):
            yield from _numeros(v, f"{ruta}[{i}]", clave)
    elif isinstance(nodo, dict):
        for c, v in nodo.items():
            yield from _numeros(v, f"{ruta}.{c}", c)


def test_ocultar_importes_no_deja_ninguna_cifra_real_de_la_demo(tmp_path, monkeypatch):
    """Ninguna cifra en euros de la demo (patrimonio, deudas, fiscal, inmuebles…) puede
    llegar intacta a la web con «ocultar importes». Antes se escalaba solo una lista de
    campos y se colaban el patrimonio neto, las deudas o el bloque fiscal."""
    import copy
    import json

    from app import motor
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(raiz, "demo", "cartera.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    datos = motor.construir(cfg, str(tmp_path), descargar=False)
    monkeypatch.setattr(exportar.random, "uniform", lambda a, b: 1.7)
    out = exportar.sin_importes(copy.deepcopy(datos))
    orig = {r: v for r, _, v in _numeros(datos)}
    fugas = [r for r, c, v in _numeros(out)
             if c not in exportar.NO_DINERO and abs(v) >= 50 and orig.get(r) == v
             and not any(r.startswith(f"D.{b}") for b in exportar.BLOQUES_RATIO)]
    assert fugas == []
    # Las de inmuebles en concreto (zona nueva): escaladas.
    assert out["inmuebles"]["total"]["neto"] == round(datos["inmuebles"]["total"]["neto"] * 1.7, 2)
    assert out["total"]["patrimonioNeto"] != datos["total"]["patrimonioNeto"]
    # Y las proporciones siguen intactas.
    assert out["total"]["ratioDeudaActivos"] == datos["total"]["ratioDeudaActivos"]


def test_ocultar_importes_tapa_los_euros_escritos_en_textos():
    out = exportar.sin_importes({"total": {}, "alertas": [{"texto": "Te faltan 1.250,50 € para el colchón"}]})
    assert out["alertas"][0]["texto"] == "Te faltan ••• € para el colchón"
