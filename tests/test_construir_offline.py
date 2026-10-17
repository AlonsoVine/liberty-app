# -*- coding: utf-8 -*-
"""
Prueba de extremo a extremo del motor SIN RED: `motor.construir` sobre una
cartera 100 % «a mano». Es la caracterización global que protege el cálculo
del patrimonio antes de ampliarlo en las siguientes fases.
"""
import os

from app import motor


def test_construir_cartera_manual(cartera_manual, tmp_path):
    datos = motor.construir(cartera_manual, str(tmp_path), descargar=False)

    assert datos is not None
    total = datos["total"]

    # Patrimonio = último valor de la cuenta (1500) + del piso (102000).
    assert total["patrimonio"] == 103500.0
    # Solo el piso lleva «aportado» (80000); la cuenta de efectivo no.
    assert total["aportado"] == 80000.0
    assert total["plusvalia"] == 22000.0

    # Eje diario del 2024-01-31 al 2024-02-29 (mes bisiesto) = 30 días.
    assert datos["fechas"][0] == "2024-01-31"
    assert datos["fechas"][-1] == "2024-02-29"
    assert len(datos["fechas"]) == 30

    # El piso es «producto»; la cuenta de efectivo va como «otro activo».
    ids_prod = {p["id"] for p in datos["productos"]}
    ids_otros = {p["id"] for p in datos["otrosActivos"]}
    assert "piso" in ids_prod
    assert "cuenta" in ids_otros

    # La serie total termina en el patrimonio y tiene la longitud del eje.
    assert len(datos["total"]["serie"]) == len(datos["fechas"])
    assert datos["total"]["serie"][-1] == 103500.0

    # Deja rastro en el histórico.
    assert os.path.exists(os.path.join(str(tmp_path), "historico.json"))


def test_construir_cartera_vacia_devuelve_none(tmp_path):
    vacia = {"version": 1, "productos": [], "movimientos": [], "valoraciones": []}
    assert motor.construir(vacia, str(tmp_path), descargar=False) is None


def test_conteos_y_aportaciones_llevan_mov_id(cartera_manual, tmp_path):
    """El panel expone contadores (inicio) y cada aportación lleva el id de su
    movimiento de origen, para poder saltar a él desde la ficha del componente."""
    cfg = dict(cartera_manual)
    # Una compra del piso (movimiento con id) -> genera una aportación con movId.
    cfg["movimientos"] = [{"id": "m1", "producto": "piso", "fecha": "2024-01-31",
                           "tipo": "compra", "importe": 80000.0}]
    cfg["flujos"] = [
        {"id": "f1", "fecha": "2024-02-10", "tipo": "gasto", "importe": 50.0,
         "categoria": "Casa", "adjuntos": [{"id": "a1", "archivo": "a1.pdf", "nombre": "x.pdf"}]},
        {"id": "f2", "fecha": "2024-02-11", "tipo": "ingreso", "importe": 1000.0, "categoria": "Nómina"},
    ]
    cfg["biblioteca"] = {"carpetas": [{"id": "c1", "nombre": "Casa", "padre": None}],
                         "archivos": [{"id": "d1", "archivo": "d1.pdf", "nombre": "escritura.pdf",
                                       "carpeta": "c1", "tipo": "application/pdf", "tam": 10}]}

    datos = motor.construir(cfg, str(tmp_path), descargar=False)
    assert datos is not None

    c = datos["conteos"]
    assert c["facturas"] == 1
    assert c["documentos"] == 1
    assert c["apuntes"] == 2
    assert c["activos"] == 2
    assert c["movimientos"] == 1

    piso = next(p for p in datos["productos"] if p["id"] == "piso")
    aps = [a for a in piso["aportaciones"] if a.get("importe")]
    assert aps and aps[0]["movId"] == "m1"
