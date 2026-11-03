"""Evolución del patrimonio del hogar: cartera neta + inmuebles netos, mes a mes (ADR 0034)."""

import copy
import datetime as dt

from app import almacen, motor


def eje(desde, hasta):
    return motor.rango_fechas(dt.date.fromisoformat(desde), dt.date.fromisoformat(hasta))


def piso(**kw):
    x = {"id": "i1", "compraFecha": "2026-01-15", "precio": 100000, "coste": 110000,
         "valoraciones": [{"fecha": "2026-04-10", "importe": 120000}], "hipoteca": None}
    x.update(kw)
    return x


def test_eje_mensual_desde_la_compra_aunque_la_cartera_empiece_despues():
    e = eje("2026-03-01", "2026-06-20")          # la cartera empieza en marzo
    cartera = [1000.0] * len(e)
    s = motor.serie_hogar([piso()], e, cartera, [], total_hoy=121000, inmuebles_hoy=120000)
    assert s["fechas"] == ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30", "2026-05-31", "2026-06-20"]
    # Enero y febrero: sin cartera aún (0) y el piso a su precio de compra.
    assert s["total"][:2] == [100000, 100000] and s["cartera"][:2] == [0, 0]
    # Marzo: ya hay cartera; abril: manda la estimación de 120.000.
    assert s["total"][2] == 101000 and s["inmuebles"][3] == 120000
    # El último punto es la foto de hoy, igual que la card.
    assert (s["total"][-1], s["inmuebles"][-1], s["cartera"][-1]) == (121000, 120000, 1000)
    assert s["hipotecaEstimada"] is False


def test_antes_de_la_compra_el_inmueble_no_esta():
    e = eje("2025-11-01", "2026-02-10")
    s = motor.serie_hogar([piso()], e, [500.0] * len(e), [], total_hoy=100500, inmuebles_hoy=100000)
    assert s["fechas"][0] == "2025-11-30"
    assert s["inmuebles"][:2] == [0, 0] and s["total"][:2] == [500, 500]


def test_hipoteca_sin_enlace_se_reconstruye_hacia_atras():
    e = eje("2026-01-01", "2026-04-30")
    hip = {"capitalPendiente": 80000, "cuota": 600, "tipoInteres": 0.03, "deudaRef": None}
    s = motor.serie_hogar([piso(hipoteca=hip, valoraciones=[])], e, [0.0] * len(e), [],
                          total_hoy=20000, inmuebles_hoy=20000)
    assert s["hipotecaEstimada"] is True
    # Un mes antes se debía más: (80.000 + 600) / 1,0025.
    marzo = 100000 - (80000 + 600) / 1.0025
    assert abs(s["inmuebles"][-2] - marzo) < 0.01
    # Cada mes hacia atrás, más deuda y menos neto inmobiliario.
    assert s["inmuebles"][0] < s["inmuebles"][1] < s["inmuebles"][2] < s["inmuebles"][3]
    # Nunca más deuda de lo que costó el piso.
    cap = motor._capital_hacia_atras(80000, 600, 0.03, 600)
    assert cap[-1] > 110000
    s2 = motor.serie_hogar([piso(compraFecha="1980-01-15", hipoteca=hip, valoraciones=[])],
                           eje("2026-01-01", "2026-01-31"), [0.0] * 31, [], total_hoy=20000, inmuebles_hoy=20000)
    assert min(s2["inmuebles"]) >= 100000 - 110000


def test_hipoteca_enlazada_usa_la_deuda_y_no_resta_dos_veces():
    e = eje("2026-01-01", "2026-03-31")
    n = len(e)
    deuda = [-90000.0] * 31 + [-89500.0] * (n - 31)     # la deuda en la cartera (negativa)
    cartera = [10000.0 - 90000.0] * 31 + [10000.0 - 89500.0] * (n - 31)
    hip = {"capitalPendiente": 89500, "cuota": 500, "tipoInteres": 0.02, "deudaRef": "d1"}
    s = motor.serie_hogar([piso(hipoteca=hip, valoraciones=[])], e, cartera, [{"id": "d1", "serie": deuda}],
                          total_hoy=110000, inmuebles_hoy=10500)
    # Total = cartera (que ya resta la deuda) + valor: la hipoteca no se resta otra vez.
    assert s["total"][0] == 10000 - 90000 + 100000
    # Con la hipoteca en su inmueble, la deuda se le devuelve a la cartera.
    assert s["inmuebles"][0] == 100000 - 90000 and s["cartera"][0] == 10000
    assert s["hipotecaEstimada"] is False


def test_construir_publica_la_serie_del_hogar(tmp_path):
    cfg = copy.deepcopy(almacen.CARTERA_VACIA)
    cfg["productos"] = [{"id": "c1", "nombre": "Cuenta", "tipo": "efectivo"}]
    cfg["valoraciones"] = [{"id": "v1", "producto": "c1", "fecha": "2026-06-01", "valor": 5000}]
    almacen.guarda_inmueble(cfg, {"nombre": "Piso", "compraFecha": "2025-06-10", "compraPrecio": "150000",
                                  "valorImporte": "160000", "valorFecha": "2026-05-01"})
    datos = motor.construir(cfg, str(tmp_path), descargar=False)
    sh = datos["inmuebles"]["total"]["serieHogar"]
    assert sh["fechas"][0] == "2025-06-30"
    assert sh["total"][-1] == datos["inmuebles"]["total"]["patrimonioHogar"]
    assert sh["inmuebles"][0] == 150000
