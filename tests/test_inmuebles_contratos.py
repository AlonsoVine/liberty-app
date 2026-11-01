# -*- coding: utf-8 -*-
"""
Zona de Inmuebles, iteración 2: inquilinos y sus contratos (con datos propios de uno o
varios valores), renta, rentabilidad bruta y ocupación; la batería de avisos de los
inmuebles (configurable); el filtro de sus apuntes en Ingresos y gastos y el Panel con
una cartera sin activos.
"""
import copy
import datetime as dt
import json
import os

import pytest

from app import almacen, exportar, motor


def cfg_vacia():
    return copy.deepcopy(almacen.CARTERA_VACIA)


def con_piso(cfg, **extra):
    datos = {"nombre": "Piso Mayor", "compraFecha": "2019-05-10", "compraPrecio": "150.000",
             "compraGastos": "15000", "valorImporte": "185.000", "valorFecha": "2026-10-01",
             "categorias": ["Alquiler Mayor", "IBI Mayor"]}
    datos.update(extra)
    return almacen.guarda_inmueble(cfg, datos)


def con_contrato(cfg, iid, **extra):
    q = almacen.guarda_inquilino(cfg, {"inmueble": iid, "nombre": "Ana"})
    c = {"inquilino": q["id"], "inicio": "2025-08-01", "fin": "2030-07-31", "renta": "750",
         "diaCobro": "5", "fianza": "750", "actualizacion": "irav"}
    c.update(extra)
    return q, almacen.guarda_contrato(cfg, c)


# ---------------------------------------------------------------- almacén

def test_inquilino_con_datos_propios_de_varios_valores():
    cfg = cfg_vacia()
    im = con_piso(cfg)
    q = almacen.guarda_inquilino(cfg, {
        "inmueble": im["id"], "nombre": " Ana Martín ", "documento": "12345678z",
        "telefono": "600 123 456", "email": "ana@ejemplo.com",
        "campos": [{"nombre": "Avalista", "valores": ["Luis", " ", "Marta"]},
                   {"nombre": "", "valores": []},                      # fila vacía: se ignora
                   {"nombre": "Mascota", "valores": "Gato"}]})        # un valor suelto vale
    assert q["id"] == "q1" and q["nombre"] == "Ana Martín" and q["documento"] == "12345678Z"
    assert q["campos"] == [{"nombre": "Avalista", "valores": ["Luis", "Marta"]},
                           {"nombre": "Mascota", "valores": ["Gato"]}]
    assert cfg["inmuebles"][0]["inquilinos"] == [q]


def test_inquilino_validaciones():
    cfg = cfg_vacia()
    im = con_piso(cfg)
    with pytest.raises(almacen.ErrorValidacion) as e:
        almacen.guarda_inquilino(cfg, {"inmueble": im["id"], "nombre": "", "email": "no-es-correo",
                                       "campos": [{"nombre": "", "valores": ["x"]},
                                                  {"nombre": "A", "valores": ["1"]}, {"nombre": "a", "valores": ["2"]}]})
    txt = " ".join(e.value.errores)
    assert "nombre al inquilino" in txt and "no parece válido" in txt
    assert "Ponle nombre a cada dato" in txt and "repetido" in txt
    with pytest.raises(almacen.ErrorValidacion):
        almacen.guarda_inquilino(cfg, {"inmueble": "i99", "nombre": "Ana"})


def test_contrato_y_sus_validaciones():
    cfg = cfg_vacia()
    im = con_piso(cfg)
    q, c = con_contrato(cfg, im["id"], categoria="alquiler mayor",
                        campos=[{"nombre": "Gastos incluidos", "valores": ["Comunidad", "Agua"]}])
    assert c == {"id": "c1", "inicio": "2025-08-01", "fin": "2030-07-31", "renta": 750.0, "diaCobro": 5,
                 "fianza": 750.0, "actualizacion": "irav", "categoria": "alquiler mayor",
                 "campos": [{"nombre": "Gastos incluidos", "valores": ["Comunidad", "Agua"]}]}
    with pytest.raises(almacen.ErrorValidacion) as e:
        almacen.guarda_contrato(cfg, {"inquilino": q["id"], "inicio": "2026-01-01", "fin": "2025-01-01",
                                      "renta": "0", "diaCobro": "32", "actualizacion": "rara",
                                      "categoria": "Otra cosa"})
    txt = " ".join(e.value.errores)
    for trozo in ("terminar después de empezar", "mayor que 0", "del 1 al 31", "cómo se actualiza",
                  "no va con este inmueble"):
        assert trozo in txt
    with pytest.raises(almacen.ErrorValidacion) as e:
        almacen.guarda_contrato(cfg, {"inquilino": q["id"], "renta": "700"})
    assert "inicio" in e.value.errores[0]


def test_editar_inquilino_conserva_sus_contratos_y_la_ficha_conserva_los_inquilinos():
    cfg = cfg_vacia()
    im = con_piso(cfg)
    q, c = con_contrato(cfg, im["id"])
    almacen.guarda_inquilino(cfg, {"inmueble": im["id"], "id": q["id"], "nombre": "Ana M."})
    assert cfg["inmuebles"][0]["inquilinos"][0]["contratos"] == [c]
    almacen.guarda_inmueble(cfg, {"id": im["id"], "nombre": "Piso Mayor (reformado)"})
    assert cfg["inmuebles"][0]["inquilinos"][0]["nombre"] == "Ana M."
    # Editar el contrato lo reemplaza; los ids son únicos en toda la cartera.
    almacen.guarda_contrato(cfg, {"inquilino": q["id"], "id": c["id"], "inicio": "2025-08-01", "renta": "800"})
    assert cfg["inmuebles"][0]["inquilinos"][0]["contratos"][0]["renta"] == 800.0
    otro = almacen.guarda_inmueble(cfg, {"nombre": "Local"})
    q2, c2 = con_contrato(cfg, otro["id"])
    assert (q2["id"], c2["id"]) == ("q2", "c2")


def test_borrar_contrato_e_inquilino():
    cfg = cfg_vacia()
    im = con_piso(cfg)
    q, c = con_contrato(cfg, im["id"])
    almacen.borra_contrato(cfg, c["id"])
    assert "contratos" not in cfg["inmuebles"][0]["inquilinos"][0]
    almacen.borra_inquilino(cfg, q["id"])
    assert "inquilinos" not in cfg["inmuebles"][0]
    with pytest.raises(almacen.ErrorValidacion):
        almacen.borra_inquilino(cfg, q["id"])
    with pytest.raises(almacen.ErrorValidacion):
        almacen.borra_contrato(cfg, "c9")


def test_config_guarda_los_plazos_de_los_avisos_de_inmuebles():
    cfg = cfg_vacia()
    almacen.guarda_config(cfg, {"inmDiasFinContrato": "90", "inmDiasCobro": "", "avisosOff": ["inm-cobro-proximo"]})
    conf = cfg["config"]
    assert conf["inmDiasFinContrato"] == 90 and "inmDiasCobro" not in conf
    assert conf["avisosOff"] == ["inm-cobro-proximo"]
    with pytest.raises(almacen.ErrorValidacion):
        almacen.guarda_config(cfg, {"inmMesesValor": "-1"})


# ---------------------------------------------------------------- motor

def _resumen(cfg, monkeypatch, hoy="2026-11-01"):
    monkeypatch.setattr(motor, "hoy", lambda: dt.date.fromisoformat(hoy))
    return motor.inmuebles_de(cfg, [], flujos=cfg.get("flujos"), fecha_ref=dt.date.fromisoformat(hoy))


def test_renta_rentabilidad_bruta_y_ocupacion(monkeypatch):
    cfg = cfg_vacia()
    im = con_piso(cfg)
    con_contrato(cfg, im["id"])
    almacen.guarda_inmueble(cfg, {"nombre": "Local vacío", "estado": "vacio", "compraPrecio": "50000"})
    r = _resumen(cfg, monkeypatch)
    x = r["lista"][0]
    assert x["alquiler"] == {"inquilinos": 1, "contratos": 1, "vigentes": 1, "rentaMensual": 750.0,
                             "proximoFin": "2030-07-31"}
    assert x["rentabilidadBruta"] == round(750 * 12 / 165000, 4)
    assert x["ocupado"] is True and r["lista"][1]["ocupado"] is False
    t = r["total"]
    assert t["rentaMensual"] == 750.0 and t["ocupacion"] == 0.5 and t["alquilados"] == 1
    assert t["rentabilidadBruta"] == round(9000 / 165000, 4)
    # Los datos del inquilino no viajan en el resumen (ni, por tanto, en la web exportada).
    assert "Ana" not in json.dumps(r)


def test_contrato_terminado_o_futuro_no_cuenta(monkeypatch):
    cfg = cfg_vacia()
    im = con_piso(cfg)
    con_contrato(cfg, im["id"], inicio="2020-01-01", fin="2025-12-31")
    x = _resumen(cfg, monkeypatch)["lista"][0]
    assert x["alquiler"]["vigentes"] == 0 and x["alquiler"]["rentaMensual"] is None
    assert x["rentabilidadBruta"] is None and x["ocupado"] is False   # con contratos manda el contrato
    x = _resumen(cfg, monkeypatch, hoy="2021-06-01")["lista"][0]
    assert x["alquiler"]["vigentes"] == 1


def _avisos(cfg, hoy, conf=None):
    return motor.avisos_inmuebles(cfg, cfg.get("flujos"), conf or {}, dt.date.fromisoformat(hoy))


def test_aviso_fin_de_contrato_y_terminado_sin_otro():
    cfg = cfg_vacia()
    im = con_piso(cfg)
    con_contrato(cfg, im["id"], fin="2026-12-15")
    av = [a for a in _avisos(cfg, "2026-11-01") if a[3] == "inm-fin-contrato"]
    assert len(av) == 1 and "termina el 15/12/2026" in av[0][0] and av[0][1] == "44 días" and av[0][4] == im["id"]
    assert not [a for a in _avisos(cfg, "2026-11-01", {"inmDiasFinContrato": 30}) if a[3] == "inm-fin-contrato"]
    av = [a for a in _avisos(cfg, "2026-12-20") if a[3] == "inm-fin-contrato"]
    assert av and "terminó" in av[0][0] and av[0][2] == "aviso"
    # Con un contrato nuevo firmado para después, el terminado ya no avisa.
    q = cfg["inmuebles"][0]["inquilinos"][0]
    almacen.guarda_contrato(cfg, {"inquilino": q["id"], "inicio": "2027-01-01", "renta": "800"})
    assert not [a for a in _avisos(cfg, "2026-12-20") if a[3] == "inm-fin-contrato" and "terminó" in a[0]]


def test_aviso_revision_de_la_renta_solo_si_se_actualiza():
    cfg = cfg_vacia()
    im = con_piso(cfg)
    con_contrato(cfg, im["id"], inicio="2025-11-20")
    av = [a for a in _avisos(cfg, "2026-11-01") if a[3] == "inm-revision-renta"]
    assert len(av) == 1 and "20/11/2026" in av[0][0] and "IRAV" in av[0][0]
    cfg2 = cfg_vacia()
    im2 = con_piso(cfg2)
    con_contrato(cfg2, im2["id"], inicio="2025-11-20", actualizacion="ninguna")
    assert not [a for a in _avisos(cfg2, "2026-11-01") if a[3] == "inm-revision-renta"]
    # El primer «aniversario» no es el propio día de inicio.
    cfg3 = cfg_vacia()
    im3 = con_piso(cfg3)
    con_contrato(cfg3, im3["id"], inicio="2026-11-10")
    assert not [a for a in _avisos(cfg3, "2026-11-01") if a[3] == "inm-revision-renta"]


def test_aviso_cobro_proximo_y_sin_cobrar():
    cfg = cfg_vacia()
    im = con_piso(cfg)
    con_contrato(cfg, im["id"], categoria="Alquiler Mayor")
    # Día de cobro 5: el 3 avisa de que se acerca.
    av = [a for a in _avisos(cfg, "2026-11-03") if a[3] == "inm-cobro-proximo"]
    assert av and av[0][1] == "2 días" and "5/11/2026" in av[0][0]
    # El 11 (5 + 5 de margen) sin ningún ingreso desde unos días antes del 5: sin cobrar.
    av = [a for a in _avisos(cfg, "2026-11-11") if a[3] == "inm-cobro-pendiente"]
    assert av and av[0][2] == "aviso" and "5/11/2026" in av[0][0]
    # El día 9 aún está en el margen: mira el cobro de octubre.
    cfg["flujos"] = [{"id": "f1", "tipo": "ingreso", "fecha": "2026-10-04", "importe": 750, "categoria": "Alquiler Mayor"}]
    assert not [a for a in _avisos(cfg, "2026-11-09") if a[3] == "inm-cobro-pendiente"]
    # Un ingreso en otra categoría no cuenta; uno en la suya, sí.
    cfg["flujos"].append({"id": "f2", "tipo": "ingreso", "fecha": "2026-11-05", "importe": 750, "categoria": "IBI Mayor"})
    assert [a for a in _avisos(cfg, "2026-11-11") if a[3] == "inm-cobro-pendiente"]
    cfg["flujos"].append({"id": "f3", "tipo": "ingreso", "fecha": "2026-11-06", "importe": 750, "categoria": "alquiler mayor"})
    assert not [a for a in _avisos(cfg, "2026-11-11") if a[3] == "inm-cobro-pendiente"]


def test_sin_categorias_no_vigila_el_cobro_ni_avisa_antes_del_inicio():
    cfg = cfg_vacia()
    im = con_piso(cfg, categorias=[])
    con_contrato(cfg, im["id"])
    assert not [a for a in _avisos(cfg, "2026-11-11") if a[3] == "inm-cobro-pendiente"]
    cfg2 = cfg_vacia()
    im2 = con_piso(cfg2)
    con_contrato(cfg2, im2["id"], inicio="2026-11-08")
    assert not [a for a in _avisos(cfg2, "2026-11-11") if a[3] == "inm-cobro-pendiente"]


def test_vivienda_habitual_sin_ingresos_ni_alquiler_ni_avisos_de_contrato(monkeypatch):
    cfg = cfg_vacia()
    cfg["config"]["categorias"] = [{"nombre": "Alquiler Mayor", "tipo": "ingreso"},
                                   {"nombre": "IBI Mayor", "tipo": "gasto"}]
    im = con_piso(cfg)
    con_contrato(cfg, im["id"], fin="2026-12-15", categoria="Alquiler Mayor")
    assert [a for a in _avisos(cfg, "2026-11-01") if a[3] == "inm-fin-contrato"]
    # Pasa a vivienda habitual: la categoría de ingresos se cae, la de gastos se queda,
    # los inquilinos se conservan pero ni cuentan ni avisan.
    almacen.guarda_inmueble(cfg, {"id": im["id"], "nombre": "Piso Mayor", "uso": "habitual",
                                  "estado": "alquilado", "categorias": ["Alquiler Mayor", "IBI Mayor"],
                                  "valorImporte": "185000", "valorFecha": "2026-10-01"})
    x = cfg["inmuebles"][0]
    assert x["categorias"] == ["IBI Mayor"] and "estado" not in x and x["inquilinos"]
    assert not [a for a in _avisos(cfg, "2026-11-01") if a[3].startswith("inm-") and a[3] != "inm-valor-antiguo"]
    r = _resumen(cfg, monkeypatch)
    assert r["lista"][0]["alquiler"] is None and r["total"]["rentaMensual"] is None
    # Un gasto sin tipo en Configuración se reconoce por sus apuntes.
    assert almacen._tipo_categoria({"flujos": [{"tipo": "gasto", "categoria": "Luz"}]}, "luz") == "gasto"


def test_aviso_valor_estimado_antiguo():
    cfg = cfg_vacia()
    con_piso(cfg, valorFecha="2025-06-01")
    assert [a for a in _avisos(cfg, "2026-11-01") if a[3] == "inm-valor-antiguo"]
    assert not [a for a in _avisos(cfg, "2026-11-01", {"inmMesesValor": 24}) if a[3] == "inm-valor-antiguo"]


def test_los_avisos_de_inmuebles_llegan_al_panel_y_se_pueden_apagar(cartera_manual, tmp_path, monkeypatch):
    monkeypatch.setattr(motor, "hoy", lambda: dt.date(2026, 11, 11))
    cfg = copy.deepcopy(cartera_manual)
    im = con_piso(cfg)
    con_contrato(cfg, im["id"], categoria="Alquiler Mayor")
    d = motor.construir(cfg, str(tmp_path), descargar=False)
    al = [a for a in d["alertas"] if a["clave"] == "inm-cobro-pendiente"]
    assert al and al[0]["destino"] == {"tab": "inmuebles", "inmueble": im["id"]} and al[0]["pv"] == "inmuebles"
    assert "Ana" not in json.dumps(d["alertas"])
    cfg.setdefault("config", {})["avisosOff"] = ["inm-cobro-pendiente"]
    d = motor.construir(cfg, str(tmp_path), descargar=False)
    assert not [a for a in d["alertas"] if a["clave"] == "inm-cobro-pendiente"]


def test_flujos_lista_lleva_el_inmueble_de_cada_apunte(cartera_manual, tmp_path):
    cfg = copy.deepcopy(cartera_manual)
    im = con_piso(cfg)
    cfg["flujos"] = [{"id": "f1", "tipo": "ingreso", "fecha": "2026-10-05", "importe": 750, "categoria": "alquiler mayor"},
                     {"id": "f2", "tipo": "gasto", "fecha": "2026-10-06", "importe": 50, "categoria": "Comida"}]
    d = motor.construir(cfg, str(tmp_path), descargar=False)
    assert [f["inmueble"] for f in d["flujosLista"]] == [im["id"], ""]


@pytest.mark.parametrize("que", ["inmuebles", "flujos"])
def test_panel_sin_activos_pero_con_inmuebles_o_apuntes(tmp_path, que):
    cfg = cfg_vacia()
    if que == "inmuebles":
        con_piso(cfg)
    else:
        cfg["flujos"] = [{"id": "f1", "tipo": "ingreso", "fecha": "2026-10-05", "importe": 900, "categoria": "Nómina"}]
    d = motor.construir(cfg, str(tmp_path), descargar=False)
    assert d is not None and d["total"]["patrimonioNeto"] == 0
    if que == "inmuebles":
        assert d["inmuebles"]["total"]["patrimonioHogar"] == 185000
    else:
        assert d["flujos"] and len(d["flujosLista"]) == 1
    json.dumps(d)
    # Sin nada de nada, sigue sin haber Panel (la invitación a empezar).
    assert motor.construir(cfg_vacia(), str(tmp_path), descargar=False) is None


def test_la_web_exportada_no_escala_porcentajes_ni_recuentos_del_alquiler(monkeypatch):
    cfg = cfg_vacia()
    im = con_piso(cfg)
    con_contrato(cfg, im["id"])
    r = _resumen(cfg, monkeypatch)
    oculto = exportar.sin_importes({"inmuebles": r})
    x, t = oculto["inmuebles"]["lista"][0], oculto["inmuebles"]["total"]
    assert x["rentabilidadBruta"] == r["lista"][0]["rentabilidadBruta"]
    assert x["alquiler"]["vigentes"] == 1 and x["alquiler"]["contratos"] == 1
    assert t["ocupacion"] == r["total"]["ocupacion"] == 1.0
    assert x["alquiler"]["rentaMensual"] != 750.0   # el dinero sí se escala


def test_contrato_e_inquilino_llevan_sus_documentos_de_la_biblioteca():
    cfg = cfg_vacia()
    im = con_piso(cfg)
    q = almacen.guarda_inquilino(cfg, {"inmueble": im["id"], "nombre": "Ana",
                                       "archivos": [{"tipo": "archivo", "id": "arc_dni"}, {"tipo": "raro", "id": "x"}]})
    assert q["archivos"] == [{"tipo": "archivo", "id": "arc_dni"}]
    c = almacen.guarda_contrato(cfg, {"inquilino": q["id"], "inicio": "2025-08-01", "renta": "750",
                                      "archivos": [{"tipo": "archivo", "id": "arc_contrato"},
                                                   {"tipo": "archivo", "id": "arc_contrato"},
                                                   {"tipo": "carpeta", "id": "car_anexos"}]})
    assert c["archivos"] == [{"tipo": "archivo", "id": "arc_contrato"}, {"tipo": "carpeta", "id": "car_anexos"}]
    # Editar el inquilino sin mandar documentos los quita (el formulario siempre los manda).
    almacen.guarda_inquilino(cfg, {"inmueble": im["id"], "id": q["id"], "nombre": "Ana"})
    assert "archivos" not in cfg["inmuebles"][0]["inquilinos"][0]


# ---------------------------------------------------------------- servidor

def test_subir_a_la_biblioteca_con_ruta_crea_las_carpetas(tmp_path, monkeypatch):
    import io

    from app import servidor
    monkeypatch.setattr(servidor, "DATOS", str(tmp_path))
    with open(os.path.join(str(tmp_path), "cartera.json"), "w", encoding="utf-8") as f:
        json.dump(cfg_vacia(), f)
    cl = servidor.app.test_client()
    ruta = json.dumps(["Inmuebles", "Piso Mayor", "Contratos"])
    j = cl.post("/api/biblioteca/subir", data={"archivo": (io.BytesIO(b"%PDF-1.4"), "contrato.pdf"), "ruta": ruta},
                content_type="multipart/form-data").get_json()
    assert j["ok"] is True
    bib = j["cartera"]["biblioteca"]
    nombres = {c["id"]: c for c in bib["carpetas"]}
    hoja = nombres[j["item"]["carpeta"]]
    assert hoja["nombre"] == "Contratos" and nombres[hoja["padre"]]["nombre"] == "Piso Mayor"
    # La segunda vez reutiliza las mismas carpetas.
    j2 = cl.post("/api/biblioteca/subir", data={"archivo": (io.BytesIO(b"x"), "anexo.pdf"), "ruta": ruta},
                 content_type="multipart/form-data").get_json()
    assert j2["item"]["carpeta"] == j["item"]["carpeta"] and len(j2["cartera"]["biblioteca"]["carpetas"]) == 3

def test_una_estimacion_nueva_pasa_la_anterior_al_historial(monkeypatch):
    cfg = cfg_vacia()
    im = con_piso(cfg)                                    # 185.000 a 2026-10-01
    base = {"id": im["id"], "nombre": "Piso Mayor", "compraPrecio": "150000", "compraFecha": "2019-05-10"}
    almacen.guarda_inmueble(cfg, {**base, "valorImporte": "190000", "valorFecha": "2026-10-20"})
    x = cfg["inmuebles"][0]
    assert x["historico"] == [{"fecha": "2026-10-01", "importe": 185000.0}]
    # Corregir la del mismo día no añade historial; editar otra cosa lo conserva.
    almacen.guarda_inmueble(cfg, {**base, "valorImporte": "191000", "valorFecha": "2026-10-20"})
    assert len(cfg["inmuebles"][0]["historico"]) == 1
    r = _resumen(cfg, monkeypatch)["lista"][0]
    assert [v["importe"] for v in r["valoraciones"]] == [185000.0, 191000.0] and r["valor"] == 191000.0
    # La foto de un mes pasado usa la estimación de entonces.
    pasado = motor.inmuebles_de(cfg, [], "2026-10-10", flujos=[], fecha_ref=dt.date(2026, 10, 10))["lista"][0]
    assert pasado["valor"] == 185000.0 and len(pasado["valoraciones"]) == 1


def _con_producto_inmueble(cfg):
    cfg["productos"].append({"id": "trastero", "tipo": "inmueble", "fuente": "manual", "nombre": "Trastero",
                             "titular": "Común", "slot": 3})
    cfg["valoraciones"] += [{"id": "v1", "producto": "trastero", "fecha": "2025-06-01", "valor": 10500},
                            {"id": "v2", "producto": "trastero", "fecha": "2026-09-30", "valor": 11300}]
    cfg["movimientos"].append({"id": "m1", "producto": "trastero", "tipo": "compra", "fecha": "2020-03-01",
                               "importe": 9000, "unidades": 1})
    cfg.setdefault("notas", []).append({"id": "n1", "texto": "Escritura", "vinculo": {"tipo": "activo", "ref": "trastero"},
                                        "vinculos": [{"tipo": "activo", "ref": "trastero"}, {"tipo": "categoria", "ref": "IBI"}]})
    cfg.setdefault("recordatorios", []).append({"id": "r1", "vinculo": {"tipo": "activo", "ref": "trastero"}})


def test_traspaso_completo_de_un_inmueble_de_la_cartera():
    cfg = cfg_vacia()
    _con_producto_inmueble(cfg)
    im = almacen.traspasa_a_inmueble(cfg, {"producto": "trastero", "nombre": "Trastero", "tipo": "trastero",
                                           "estado": "alquilado", "compraFecha": "2020-03-01", "compraPrecio": "9000"})
    assert im["valor"] == {"importe": 11300, "fecha": "2026-09-30"}      # su último valor
    assert im["historico"] == [{"fecha": "2025-06-01", "importe": 10500.0}]
    assert im["compra"] == {"fecha": "2020-03-01", "precio": 9000.0}
    # Sale de la cartera también hacia atrás: ni producto, ni valores, ni movimientos.
    assert not cfg["productos"] and not cfg["valoraciones"] and not cfg["movimientos"]
    n = cfg["notas"][0]
    assert n["vinculo"] == {"tipo": "inmueble", "ref": im["id"]}
    assert n["vinculos"] == [{"tipo": "inmueble", "ref": im["id"]}, {"tipo": "categoria", "ref": "IBI"}]
    assert cfg["recordatorios"][0]["vinculo"] == {"tipo": "inmueble", "ref": im["id"]}
    with pytest.raises(almacen.ErrorValidacion):                          # ya no está
        almacen.traspasa_a_inmueble(cfg, {"producto": "trastero", "nombre": "Otra vez"})


def test_traspaso_que_no_valida_deja_el_producto_donde_estaba():
    cfg = cfg_vacia()
    _con_producto_inmueble(cfg)
    with pytest.raises(almacen.ErrorValidacion):
        almacen.traspasa_a_inmueble(cfg, {"producto": "trastero", "nombre": ""})
    assert cfg["productos"][0]["id"] == "trastero" and len(cfg["valoraciones"]) == 2
    assert not cfg.get("inmuebles")
    cfg["productos"][0]["tipo"] = "fondo"                                # solo los de tipo inmueble
    with pytest.raises(almacen.ErrorValidacion):
        almacen.traspasa_a_inmueble(cfg, {"producto": "trastero", "nombre": "Trastero"})


def test_api_traspaso(tmp_path, monkeypatch):
    from app import servidor
    monkeypatch.setattr(servidor, "DATOS", str(tmp_path))
    cfg = cfg_vacia()
    _con_producto_inmueble(cfg)
    with open(os.path.join(str(tmp_path), "cartera.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    cl = servidor.app.test_client()
    j = cl.post("/api/traspasos", json={"producto": "trastero", "nombre": "Trastero", "tipo": "trastero"}).get_json()
    assert j["ok"] is True and j["item"]["historico"]
    c = cl.get("/api/cartera").get_json()["cartera"]
    assert not c["productos"] and c["inmuebles"][0]["nombre"] == "Trastero"


def test_api_inquilinos_y_contratos(tmp_path, monkeypatch):
    from app import servidor
    monkeypatch.setattr(servidor, "DATOS", str(tmp_path))
    cfg = cfg_vacia()
    im = con_piso(cfg)
    with open(os.path.join(str(tmp_path), "cartera.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    cl = servidor.app.test_client()
    j = cl.post("/api/inquilinos", json={"inmueble": im["id"], "nombre": "Ana"}).get_json()
    assert j["ok"] is True
    qid = j["item"]["id"]
    j = cl.post("/api/contratos", json={"inquilino": qid, "inicio": "2025-08-01", "renta": "750"}).get_json()
    assert j["ok"] is True
    cid = j["item"]["id"]
    assert cl.post("/api/contratos", json={"inquilino": qid, "renta": "750"}).status_code == 400
    assert cl.get("/api/cartera").get_json()["inmueble"]["actualizaciones"]["irav"]
    assert cl.delete(f"/api/contratos/{cid}").get_json()["ok"] is True
    assert cl.delete(f"/api/inquilinos/{qid}").get_json()["ok"] is True
    assert "inquilinos" not in cl.get("/api/cartera").get_json()["cartera"]["inmuebles"][0]
