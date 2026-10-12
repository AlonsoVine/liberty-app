# -*- coding: utf-8 -*-
"""
Mejoras de configuración (oct-2026): titular «Yo» por defecto y renombrado que se
propaga, tipos de activo propios (añadir y ocultar los de base) y alta automática
de categorías al anotar un ingreso o gasto con una categoría nueva.
"""
import copy

from app import almacen, motor


def cfg():
    return copy.deepcopy(almacen.CARTERA_VACIA)


# ---------------------------------------------------------------- titular por defecto

def test_cartera_nueva_trae_un_titular_yo():
    assert cfg()["titulares"] == ["Yo"]


# ---------------------------------------------------------------- renombrar titular

def test_renombrar_titular_se_propaga_a_todo():
    c = cfg()
    c["productos"] = [{"id": "p1", "nombre": "Fondo", "titular": "Yo"},
                      {"id": "p2", "nombre": "Casa", "titular": "Común"}]
    c["flujos"] = [{"id": "f1", "fecha": "2025-01-01", "tipo": "ingreso",
                    "importe": 100, "titular": "Yo"}]
    c["apartados"] = [{"id": "a1", "nombre": "Impuestos", "importe": 10, "titular": "Yo"}]
    c.setdefault("config", {})["recurrentes"] = [
        {"tipo": "ingreso", "importe": 100, "categoria": "", "titular": "Yo", "nota": ""}]

    almacen.guarda_config(c, {"titulares": ["Alonso", "Común"],
                              "renombresTitular": [{"de": "Yo", "a": "Alonso"}]})

    assert c["titulares"] == ["Alonso", "Común"]
    assert c["productos"][0]["titular"] == "Alonso"
    assert c["productos"][1]["titular"] == "Común"   # intacto
    assert c["flujos"][0]["titular"] == "Alonso"
    assert c["apartados"][0]["titular"] == "Alonso"
    assert c["config"]["recurrentes"][0]["titular"] == "Alonso"


def test_renombrar_ignora_cambios_vacios_o_iguales():
    c = cfg()
    c["productos"] = [{"id": "p1", "nombre": "X", "titular": "Yo"}]
    almacen.guarda_config(c, {"renombresTitular": [{"de": "Yo", "a": "Yo"},
                                                   {"de": "", "a": "Nadie"}]})
    assert c["productos"][0]["titular"] == "Yo"


# ---------------------------------------------------------------- tipos propios

def test_tipos_propios_se_guardan_con_id_estable():
    c = cfg()
    almacen.guarda_config(c, {"tipos": [{"nombre": "Crowdlending"}, {"nombre": "Arte"}]})
    propios = c["config"]["tipos"]
    assert [t["nombre"] for t in propios] == ["Crowdlending", "Arte"]
    ids = [t["id"] for t in propios]
    assert ids == ["crowdlending", "arte"]
    # Reeditar conserva el id aunque cambie el orden.
    almacen.guarda_config(c, {"tipos": [{"nombre": "Arte"}, {"nombre": "Crowdlending"}]})
    por_nombre = {t["nombre"]: t["id"] for t in c["config"]["tipos"]}
    assert por_nombre["Crowdlending"] == "crowdlending"


def test_tipo_propio_no_pisa_una_clave_de_base():
    c = cfg()
    # «Fondo» colisionaría con la clave de base «fondo» -> se le da otro id.
    almacen.guarda_config(c, {"tipos": [{"nombre": "fondo"}]})
    assert c["config"]["tipos"][0]["id"] not in motor.TIPOS


def test_guarda_producto_acepta_un_tipo_propio():
    c = cfg()
    almacen.guarda_config(c, {"tipos": [{"nombre": "Crowdlending"}]})
    tid = c["config"]["tipos"][0]["id"]
    p, _ = almacen.guarda_producto(c, {"nombre": "Mintos", "tipo": tid})
    assert p["tipo"] == tid
    assert len(c["productos"]) == 1


def test_tipo_invalido_sigue_fallando():
    c = cfg()
    import pytest
    with pytest.raises(almacen.ErrorValidacion):
        almacen.guarda_producto(c, {"nombre": "Algo", "tipo": "noexiste"})


# ---------------------------------------------------------------- ocultar tipos de base

def test_ocultar_tipos_solo_admite_claves_de_base():
    c = cfg()
    almacen.guarda_config(c, {"tiposOcultos": ["cripto", "inventado", "bono"]})
    assert c["config"]["tiposOcultos"] == ["cripto", "bono"]


def test_tipos_visibles_quita_ocultos_y_suma_propios():
    c = cfg()
    almacen.guarda_config(c, {"tipos": [{"nombre": "Arte"}], "tiposOcultos": ["cripto"]})
    vis = motor.tipos_visibles(c)
    assert "cripto" not in vis
    assert "fondo" in vis
    assert vis.get("arte") == "Arte"
    # tipos_todos NO oculta nada (sirve para validar productos existentes).
    todos = motor.tipos_todos(c)
    assert "cripto" in todos and "arte" in todos


# ---------------------------------------------------------------- categoría nueva al anotar

def test_anotar_categoria_nueva_la_da_de_alta():
    c = cfg()
    almacen.guarda_flujo(c, {"fecha": "2025-03-01", "tipo": "gasto",
                             "importe": "40", "categoria": "Mascotas"})
    cats = c["config"]["categorias"]
    assert {"nombre": "Mascotas", "tipo": "gasto"} in cats


def test_anotar_no_duplica_categoria_existente():
    c = cfg()
    c["config"]["categorias"] = [{"nombre": "Nómina", "tipo": "ingreso"}]
    almacen.guarda_flujo(c, {"fecha": "2025-03-01", "tipo": "ingreso",
                             "importe": "2000", "categoria": "nómina"})
    nombres = [x["nombre"] for x in c["config"]["categorias"]]
    assert nombres.count("Nómina") == 1


def test_anotar_sin_categoria_no_crea_nada():
    c = cfg()
    almacen.guarda_flujo(c, {"fecha": "2025-03-01", "tipo": "gasto", "importe": "10"})
    assert c["config"]["categorias"] == []


# ---------------------------------------------------------------- avisos activables

def _cartera_dinero_libre_negativo():
    c = cfg()
    almacen.guarda_producto(c, {"nombre": "Cuenta", "tipo": "efectivo", "fuente": "manual"})
    almacen.guarda_valoracion(c, {"producto": c["productos"][0]["id"],
                                  "fecha": "2025-01-01", "valor": "1000"})
    almacen.guarda_config(c, {"colchon": "5000"})   # colchón > disponible -> dinero libre < 0
    return c


def test_aviso_salta_por_defecto(tmp_path):
    c = _cartera_dinero_libre_negativo()
    d = motor.construir(c, str(tmp_path), descargar=False)
    assert "dinero-libre" in {a.get("clave") for a in d["alertas"]}


def test_aviso_desactivado_no_salta(tmp_path):
    c = _cartera_dinero_libre_negativo()
    almacen.guarda_config(c, {"avisosOff": ["dinero-libre"]})
    d = motor.construir(c, str(tmp_path), descargar=False)
    assert "dinero-libre" not in {a.get("clave") for a in d["alertas"]}
    # el catálogo completo se expone igualmente
    assert len(d["avisosCatalogo"]) == len(motor.AVISOS_CATALOGO)
    assert d["avisosOff"] == ["dinero-libre"]


def test_avisos_off_valida_claves():
    c = cfg()
    almacen.guarda_config(c, {"avisosOff": ["dinero-libre", "inventado", "dinero-libre"]})
    assert c["config"]["avisosOff"] == ["dinero-libre"]


# ---------------------------------------------------------------- marcas de apuntes

def test_marca_flujo_pone_y_quita():
    c = cfg()
    fl = almacen.guarda_flujo(c, {"fecha": "2025-03-01", "tipo": "gasto", "importe": "40"})
    almacen.marca_flujo(c, fl["id"], "revisar")
    assert c["flujos"][0]["marca"] == "revisar"
    almacen.marca_flujo(c, fl["id"], "")   # quitar
    assert "marca" not in c["flujos"][0]


def test_marca_desconocida_no_se_aplica():
    c = cfg()
    fl = almacen.guarda_flujo(c, {"fecha": "2025-03-01", "tipo": "gasto", "importe": "40"})
    almacen.marca_flujo(c, fl["id"], "inventada")
    assert "marca" not in c["flujos"][0]


def test_editar_flujo_conserva_la_marca():
    c = cfg()
    fl = almacen.guarda_flujo(c, {"fecha": "2025-03-01", "tipo": "gasto", "importe": "40"})
    almacen.marca_flujo(c, fl["id"], "revisar")
    # Editar el importe (el formulario no manda marca) no debe borrarla.
    almacen.guarda_flujo(c, {"id": fl["id"], "fecha": "2025-03-01", "tipo": "gasto", "importe": "50"})
    assert c["flujos"][0]["marca"] == "revisar"


def test_config_marcas_se_guardan_con_id_y_color():
    c = cfg()
    almacen.guarda_config(c, {"marcas": [{"nombre": "A revisar", "color": "#e34948"},
                                         {"nombre": "Duda", "color": "malo"}]})
    ms = c["config"]["marcas"]
    assert ms[0] == {"id": "a-revisar", "nombre": "A revisar", "color": "#e34948"}
    assert ms[1]["color"] == "#e34948"   # color inválido -> por defecto


def test_marcas_de_usa_defecto_si_vacio():
    c = cfg()
    assert almacen.marcas_de(c) == almacen.MARCAS_DEFECTO


# ---------------------------------------------------------------- entidad y dimensiones de flujos

def test_entidades_y_dimensiones_flujos_se_guardan():
    c = cfg()
    almacen.guarda_config(c, {"entidades": ["BBVA", "ING", "bbva"],   # dedup sin mayúsculas
                              "dimensionesFlujos": [{"nombre": "Necesidad", "valores": ["Fijo", "Variable"]}]})
    assert c["config"]["entidades"] == ["BBVA", "ING"]
    df = c["config"]["dimensionesFlujos"]
    assert df[0]["id"] == "necesidad" and df[0]["valores"] == ["Fijo", "Variable"]


def test_flujo_guarda_entidad_y_dimension():
    c = cfg()
    almacen.guarda_config(c, {"entidades": ["BBVA"], "dimensionesFlujos": [{"nombre": "Necesidad", "valores": ["Fijo"]}]})
    did = c["config"]["dimensionesFlujos"][0]["id"]
    fl = almacen.guarda_flujo(c, {"fecha": "2025-03-01", "tipo": "gasto", "importe": "40",
                                  "entidad": "BBVA", f"cat_{did}": "Fijo"})
    assert fl["entidad"] == "BBVA"
    assert fl["categorias"] == {did: "Fijo"}


# ---------------------------------------------------------------- notas y tablero

def test_guarda_notas():
    c = cfg()
    almacen.guarda_notas(c, [{"titulo": "Idea", "texto": "Comprar X"}, {"titulo": "", "texto": ""}])
    assert len(c["notas"]) == 1   # la vacía se descarta
    assert c["notas"][0]["titulo"] == "Idea" and c["notas"][0]["fecha"]


def test_guarda_tablero_sanea_columnas_y_tarjetas():
    c = cfg()
    almacen.guarda_tablero(c, {"columnas": [{"id": "a", "nombre": "Por hacer"}, {"id": "b", "nombre": "Hecho"}],
                               "tarjetas": [{"id": "t1", "col": "a", "texto": "Tarea"},
                                            {"id": "t2", "col": "zzz", "texto": "Huérfana"},
                                            {"col": "a", "texto": ""}]})
    tb = c["tablero"]
    assert [col["id"] for col in tb["columnas"]] == ["a", "b"]
    assert len(tb["tarjetas"]) == 2            # la vacía se descarta
    assert tb["tarjetas"][1]["col"] == "a"     # la de columna inexistente va a la primera


# ---------------------------------------------------------------- motor con tipo propio

def test_motor_construye_con_un_tipo_propio(tmp_path):
    c = cfg()
    almacen.guarda_config(c, {"tipos": [{"nombre": "Crowdlending"}]})
    tid = c["config"]["tipos"][0]["id"]
    almacen.guarda_producto(c, {"nombre": "Mintos", "tipo": tid})
    almacen.guarda_valoracion(c, {"producto": c["productos"][0]["id"],
                                  "fecha": "2025-01-10", "valor": "5000"})
    d = motor.construir(c, str(tmp_path), descargar=False)
    assert d["total"]["patrimonioNeto"] > 0
    # El tipo propio aparece en la asignación con su nombre, no como «Otro».
    assert any(a["tipo"] == "Crowdlending" for a in d["asignacion"])
