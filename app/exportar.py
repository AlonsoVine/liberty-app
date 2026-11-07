# -*- coding: utf-8 -*-
"""
exportar.py  ·  El panel como una sola página web estática
==========================================================
Mete en un único .html el panel, sus gráficos y los datos ya calculados, para
subirlo a internet (Netlify Drop, GitHub Pages...) o mandarlo por correo. Es de
solo lectura: sin la pestaña «Mis datos» ni botones que necesiten la app.

Con «ocultar importes», las cantidades en euros se multiplican por un factor al
azar ANTES de meterlas en la página, y además no se muestran. Así, aunque alguien
mire el código fuente, solo puede sacar proporciones (que ya se ven en los
porcentajes), nunca tu patrimonio real.

Se escala TODO número salvo los que se sabe que no son euros (porcentajes, días,
recuentos…). Al revés —escalar solo una lista de campos «de dinero»— cualquier campo
nuevo que nadie añadiera a la lista se colaba con su cifra real (pasó con el patrimonio
neto, las deudas y el bloque fiscal).
"""

import base64
import datetime as dt
import json
import os
import random
import re
from html import escape as _escape  # alias: dentro de pagina() «html» es la página

# Números que NO son euros: porcentajes, tipos, días, recuentos, superficies… Se dejan
# tal cual (no revelan el patrimonio y escalarlos rompería los porcentajes que sí se ven).
# Cualquier otro número se escala.
NO_DINERO = {
    "activos", "alquilados", "anios", "apuntes", "cagr", "caidaMaxima", "cuotaSobreIngresos",
    "desviacion", "desviacionMax", "dias", "diasAviso", "diasInvertido", "diasRestantes",
    "documentos", "facturas", "habitaciones", "inflacion", "m2", "maxDD", "movimientos", "n",
    "nApuntes", "nHabitual", "nInversion", "numAportaciones", "ocupacion", "pct", "peso",
    "contratos", "inquilinos", "ocupados", "vigentes",
    "mesesCartera", "mesesDisponible", "mesesMedia", "progreso", "tasaRetirada",
    "plusvaliaPct", "racha", "ratioDeudaActivos", "rentTotal", "rentabilidad",
    "rentabilidadBruta", "rentabilidadNeta", "riesgo", "sharpe", "slot", "sumaObjetivos", "tae", "tasaAhorro",
    "ter", "terPonderado", "tipo", "tipoInteres", "tir", "tuTir", "twr", "umbral", "vol", "ytd",
}
# Bloques enteros de proporciones o índices (base 100): se copian sin tocar.
BLOQUES_RATIO = {"rentabilidadAnual", "comparador", "indiceCartera", "control", "conteos"}
# Cifras absolutas que ni escaladas tienen sentido: fuera.
FUERA = {"alertasPrecio", "hitos", "objetivo", "precioMedio"}
# Un importe escrito dentro de un texto (p. ej. en un aviso): «1.234,56 €».
_EUROS_EN_TEXTO = re.compile(r"[-+−]?\d[\d.,]*\s?€")


def _anonimiza(nodo, k, clave=None):
    if isinstance(nodo, bool) or nodo is None:
        return nodo
    if isinstance(nodo, (int, float)):
        if clave in NO_DINERO:
            return nodo
        return round(nodo * k, 2 if abs(nodo) >= 1 else 6)   # 6: títulos de cripto (0,0123 BTC)
    if isinstance(nodo, str):
        return _EUROS_EN_TEXTO.sub("••• €", nodo)
    if isinstance(nodo, list):   # una lista hereda la clave que la contiene
        return [_anonimiza(v, k, clave) for v in nodo]
    if isinstance(nodo, dict):
        out = {}
        for c, v in nodo.items():
            if c in FUERA:
                continue
            out[c] = v if c in BLOQUES_RATIO else _anonimiza(v, k, c)
        return out
    return nodo


def sin_importes(datos):
    """Copia de los datos con los euros escalados por un factor secreto."""
    k = random.uniform(0.37, 2.9)
    out = _anonimiza(datos, k)
    if isinstance(out.get("total"), dict):
        out["total"]["hitos"] = []
    out["objetivo"] = None
    return out


def pagina(web, datos, ocultar=False, titulo="Mi patrimonio"):
    """HTML autónomo del panel. 'web' es la carpeta app/web."""
    def lee(nombre):
        with open(os.path.join(web, nombre), encoding="utf-8") as f:
            return f.read()

    if ocultar:
        datos = sin_importes(datos)
    datos = dict(datos, modo="estatico", avisos=[])
    html = lee("index.html")

    # Fuera lo que solo tiene sentido dentro de la app.
    html = re.sub(r'\s*<button class="btn" id="btnPrecios".*?</button>', "", html, flags=re.S)
    html = re.sub(r'\s*<button data-tab="datos".*?</button>', "", html, flags=re.S)
    html = re.sub(r'\s*<button data-tab="ayuda".*?</button>', "", html, flags=re.S)
    html = re.sub(r'\s*<button data-tab="ajustes".*?</button>', "", html, flags=re.S)
    html = re.sub(r'<div class="banner" id="bannerDemo".*?</div>', "", html, flags=re.S)
    html = re.sub(r'<div class="panel" id="tab-datos".*?</div></div>', "", html, flags=re.S)
    html = re.sub(r'<div class="panel" id="tab-ayuda".*?<!-- /ayuda -->', "", html, flags=re.S)
    html = re.sub(r'<div class="panel" id="tab-ajustes".*?</section>\s*</div>', "", html, flags=re.S)
    html = re.sub(r'<div class="banner" id="bannerVersion".*?</div>', "", html, flags=re.S)

    previo = "window.ESTATICO = true;\n"
    if ocultar:
        previo += "window.OCULTAR_IMPORTES = true;\n"
    trozos = [previo + "window.DATOS = " + json.dumps(datos, ensure_ascii=False, separators=(",", ":")) + ";"]
    trozos += [lee(n) for n in ("canal.js", "graficos.js", "app.js")]
    scripts = "\n".join("<script>\n" + t.replace("</script>", "<\\/script>") + "\n</script>" for t in trozos)
    html, n = re.subn(r'<script src="cargador\.js[^"]*">\s*</script>', lambda m: scripts, html, flags=re.S)
    if not n:
        raise RuntimeError("No encuentro el cargador de scripts en index.html.")

    # El icono va dentro del archivo (la web es un solo .html); noindex para que no salga en Google.
    with open(os.path.join(web, "icono-64.png"), "rb") as f:
        icono = "data:image/png;base64," + base64.b64encode(f.read()).decode()
    html = html.replace('src="icono-64.png"', f'src="{icono}"')
    # Las tipografías también van dentro (la web exportada es un solo archivo, sin carpeta
    # «fuentes/» al lado): se incrustan como data: y se quitan los <link rel="preload">.
    html = re.sub(r'\s*<link rel="preload" href="fuentes/[^"]+"[^>]*>', "", html)

    def _fuente(m):
        ruta = os.path.join(web, "fuentes", m.group(1))
        if not os.path.exists(ruta):
            return m.group(0)
        with open(ruta, "rb") as f:
            return 'url("data:font/woff2;base64,' + base64.b64encode(f.read()).decode() + '")'
    html = re.sub(r'url\("fuentes/([\w.-]+\.woff2)"\)', _fuente, html)
    html = re.sub(r'\s*<link rel="(icon|apple-touch-icon)"[^>]*>', "", html)
    desc = "Panel de patrimonio neto e inversiones hecho con Liberty." + (" Importes ocultos." if ocultar else "")
    # Escapar antes de interpolar: «titulo» es el nombre que pone el usuario y
    # podría llevar comillas o «<» que romperían el atributo e inyectarían markup
    # en la página que se comparte.
    titulo_s = _escape(titulo, quote=True)
    desc_s = _escape(desc, quote=True)
    cabeceras = ('<meta name="robots" content="noindex, nofollow">\n'
                 f'<link rel="icon" type="image/png" href="{icono}">\n'
                 f'<meta property="og:title" content="{titulo_s} · Liberty">\n'
                 f'<meta property="og:description" content="{desc_s}">\n'
                 f'<meta name="description" content="{desc_s}">\n'
                 f'<!-- Exportado el {dt.datetime.now():%d/%m/%Y %H:%M} -->')
    html = html.replace("</head>", cabeceras + "\n</head>", 1)
    return html
