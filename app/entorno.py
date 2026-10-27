# -*- coding: utf-8 -*-
"""
entorno.py  ·  Dónde y cómo se ejecuta Liberty
==============================================
Punto ÚNICO que decide, a partir del entorno, lo que cambia entre las formas de ejecutar
Liberty (escritorio empaquetado, desarrollo y Docker): dónde están los recursos y los datos,
en qué dirección y puerto escucha, qué nombres de Host se aceptan y si corre en un contenedor.
Así el resto del código no anda mirando variables de entorno sueltas.

Es deliberadamente sencillo (solo lee variables al importarse) y NO importa nada de la app,
para poder reutilizarlo desde cualquier módulo sin ciclos. La Fase 3 (elegir carpeta de datos
en el escritorio) reutilizará este mismo punto como única fuente de la ruta.
"""
import os
import sys


def _primera(*nombres, defecto=None):
    """Primera variable de entorno no vacía de la lista (permite alias retrocompatibles)."""
    for n in nombres:
        v = os.environ.get(n)
        if v:
            return v
    return defecto


def _base_recursos():
    """Dónde viven los recursos de solo lectura (web, demo, VERSION). Empaquetado con
    PyInstaller: en sys._MEIPASS; si no, en la carpeta del proyecto."""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _base_datos():
    """Carpeta base de los datos del usuario (dentro irá «mis_datos»). Empaquetado:
      - Windows: JUNTO al ejecutable (portable, como siempre).
      - macOS: un .app es de solo lectura, así que van a ~/Library/Application Support/Liberty.
    Sin empaquetar: la carpeta del proyecto. (En Docker se ignora: LIBERTY_DATOS fija /data.)"""
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            d = os.path.join(os.path.expanduser("~/Library/Application Support"), "Liberty")
            os.makedirs(d, exist_ok=True)
            return d
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _lista_hosts(valor):
    """Nombres de Host extra aceptados además de localhost, por coincidencia EXACTA (sin
    comodines). Sirve para funcionar tras «tailscale serve» (un nombre *.ts.net) o un proxy
    inverso. Nada de comodín de TLD: eso reabriría el DNS-rebinding."""
    out = set()
    for parte in (valor or "").replace(";", ",").split(","):
        h = parte.strip().strip("[]").lower()
        if h:
            out.add(h)
    return out


def es_docker():
    """¿Estamos dentro de un contenedor? Por marca explícita (LIBERTY_MODO=docker) o por el
    fichero que Docker crea en la raíz. La marca explícita manda."""
    modo = (os.environ.get("LIBERTY_MODO") or "").strip().lower()
    if modo:
        return modo == "docker"
    return os.path.exists("/.dockerenv")


RAIZ = _base_recursos()

# Carpeta de datos del usuario. En Docker el Dockerfile fija LIBERTY_DATOS=/data; en escritorio
# y desarrollo se respeta el comportamiento de siempre. PATRIMONIO_DATOS se mantiene como alias
# para no romper scripts y pruebas anteriores.
DATOS = _primera("LIBERTY_DATOS", "PATRIMONIO_DATOS") or os.path.join(_base_datos(), "mis_datos")

# Dirección en la que escucha el servidor. Escritorio: solo este ordenador (127.0.0.1).
# Docker: 0.0.0.0 dentro del contenedor (el puerto se publica solo en 127.0.0.1 del anfitrión).
HOST = _primera("LIBERTY_HOST", defecto="127.0.0.1")

PUERTO = int(_primera("LIBERTY_PUERTO", "PATRIMONIO_PUERTO", defecto="8765"))

# Host siempre permitidos (este ordenador) + los que se configuren para VPN/proxy.
HOSTS_LOCALES = {"127.0.0.1", "localhost", "::1"}
HOSTS_PERMITIDOS = HOSTS_LOCALES | _lista_hosts(os.environ.get("LIBERTY_HOSTS_PERMITIDOS"))

ES_DOCKER = es_docker()

# No abrir el navegador al arrancar (pruebas, capturas y, siempre, Docker).
NO_ABRIR = bool(os.environ.get("PATRIMONIO_NO_ABRIR")) or ES_DOCKER
