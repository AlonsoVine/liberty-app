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
