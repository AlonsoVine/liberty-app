"""Inicio a tu gusto: la disposición se guarda en la cartera (ADR 0036)."""

import copy

import pytest

from app import almacen, motor


def test_se_guarda_saneada_y_se_puede_restablecer():
    cfg = copy.deepcopy(almacen.CARTERA_VACIA)
    almacen.guarda_config(cfg, {"inicio": {
        "orden": ["cartera", "patrimonio", "cartera", "<script>", 3],
        "ocultas": ["banda", "nada"], "medias": "cartera", "compacto": 1}})
    assert cfg["config"]["inicio"] == {"orden": ["cartera", "patrimonio"], "ocultas": ["banda"],
                                       "medias": [], "compacto": True}
    # Guardar otra cosa de Configuración no la toca.
    almacen.guarda_config(cfg, {"colchon": "100"})
    assert cfg["config"]["inicio"]["orden"] == ["cartera", "patrimonio"]
    almacen.guarda_config(cfg, {"inicio": None})
    assert "inicio" not in cfg["config"]
    with pytest.raises(almacen.ErrorValidacion):
        almacen.guarda_config(cfg, {"inicio": "todo"})


def test_construir_la_publica(tmp_path):
    cfg = copy.deepcopy(almacen.CARTERA_VACIA)
    cfg["productos"] = [{"id": "c1", "nombre": "Cuenta", "tipo": "efectivo"}]
    cfg["valoraciones"] = [{"id": "v1", "producto": "c1", "fecha": "2026-10-01", "valor": 100}]
    assert motor.construir(copy.deepcopy(cfg), str(tmp_path), descargar=False)["inicio"] is None
    almacen.guarda_config(cfg, {"inicio": {"orden": ["archivo"], "compacto": True}})
    assert motor.construir(cfg, str(tmp_path), descargar=False)["inicio"]["compacto"] is True
