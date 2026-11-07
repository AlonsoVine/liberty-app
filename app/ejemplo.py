# -*- coding: utf-8 -*-
"""
ejemplo.py  ·  El patrimonio de ejemplo
=======================================
Genera el hogar de muestra que ve quien abre Liberty por primera vez y el que se copia
desde «Empezar con mis datos» o desde Ayuda («Crear un patrimonio de ejemplo»).

Va con FECHAS VIVAS (ADR 0037): se genera respecto a hoy, así que siempre está al día
(el mes en curso tiene apuntes, el alquiler está cobrado…) y nunca recibe con avisos
falsos. Es determinista: el mismo día da siempre el mismo ejemplo y un mes ya pasado
sale igual día tras día.

Cubre toda la app a propósito (lo vigila tests/test_ejemplo.py): cartera con activos que
cotizan y a mano (alguno en pérdidas), deudas, reservados, alertas, tres años de
ingresos y gastos con facturas, inmuebles con inquilinos y contratos, notas, cuadernos,
agenda, tablero y biblioteca con documentos.

Las unidades de cada compra de lo que cotiza salen del precio real de ese día (de la
caché de precios), para que la rentabilidad sea la de verdad. Sin caché (primer arranque
sin internet, tests) se usa un precio aproximado.
"""

import calendar
import datetime as dt
import math
import os
import random

from .motor import valor_en

TITULARES = ["Yo", "Mi pareja", "Común"]
MESES = 36   # meses de historia antes del actual

# Activos que cotizan: precio aproximado de hoy (en euros) y subida anual, para cuando no
# hay precios en la caché.
APROX = {"world": (14.3, 0.09), "etfworld": (128.0, 0.09), "emergentes": (8.5, 0.05),
         "monetario": (2690.0, 0.03), "bitcoin": (68000.0, 0.35), "apple": (205.0, 0.12)}


def cotizados():
    """Los productos del ejemplo que cotizan (para leer sus precios de la caché)."""
    return [p for p in _productos() if p.get("fuente", "manual") != "manual"]


# ---------------------------------------------------------------- fechas

def _suma_meses(y, m, k):
    t = y * 12 + (m - 1) + k
    return t // 12, t % 12 + 1


def _dia(y, m, d):
    return dt.date(y, m, min(d, calendar.monthrange(y, m)[1]))


def _fin_mes(y, m):
    return dt.date(y, m, calendar.monthrange(y, m)[1])


def _cuota(capital, tae, meses):
    r = tae / 12
    return capital * r / (1 - (1 + r) ** -meses)


def _pendiente(capital, tae, cuota, pagos):
    r = tae / 12
    return max(0.0, capital * (1 + r) ** pagos - cuota * ((1 + r) ** pagos - 1) / r)


def _meses_entre(a, b):
    """Meses completos de `a` a `b` (pagos hechos el día 1 de cada mes siguiente)."""
    return max(0, (b.year - a.year) * 12 + (b.month - a.month))


# ---------------------------------------------------------------- catálogo fijo

def _productos():
    def p(pid, nombre, corto, tipo, titular, entidad, clase, geo, **extra):
        x = {"id": pid, "nombre": nombre, "corto": corto, "tipo": tipo, "titular": titular,
             "entidad": entidad, "fuente": "manual", "moneda": "EUR", "largoPlazo": True,
             "disponible": False}
        if clase:
            x["categorias"] = {"clase-de-activo": clase, "geografia": geo}
        x.update(extra)
        return x
    return [
        p("world", "Fondo indexado MSCI World", "MSCI World", "fondo", "Yo", "Plataforma de fondos",
          "Renta variable", "Global", fuente="morningstar", codigo="0P0001CLDK", ter=0.0012, riesgo=4),
        p("emergentes", "Fondo indexado Mercados Emergentes", "Emergentes", "fondo", "Mi pareja",
          "Plataforma de fondos", "Renta variable", "Emergentes", fuente="morningstar",
          codigo="0P0001CJGK", ter=0.0028, riesgo=5),
        p("etfworld", "ETF iShares Core MSCI World (IWDA)", "ETF World", "etf", "Yo", "Bróker online",
          "Renta variable", "Global", fuente="yahoo", codigo="IWDA.AS", ter=0.002, riesgo=4),
        p("monetario", "Fondo monetario del euro", "Monetario", "fondo", "Común", "Banco online",
          "Liquidez", "Europa", fuente="morningstar", codigo="0P00000F24", riesgo=1,
          largoPlazo=False, disponible=True),
        p("bitcoin", "Bitcoin", "Bitcoin", "cripto", "Yo", "Exchange de ejemplo", "Alternativos",
          "Global", fuente="coingecko", codigo="bitcoin", riesgo=7),
        p("apple", "Acciones de Apple (AAPL)", "Apple", "accion", "Mi pareja", "Bróker online",
          "Renta variable", "EEUU", fuente="yahoo", codigo="AAPL", moneda="USD", riesgo=6),
        p("pension", "Plan de pensiones indexado", "Plan de pensiones", "pension", "Yo",
          "Gestora de ejemplo", "Renta variable", "Global", riesgo=4),
        p("seguro", "Seguro de ahorro (PIAS)", "Seguro de ahorro", "otro", "Mi pareja",
          "Aseguradora de ejemplo", "Renta fija", "España", riesgo=2),
        p("oro", "Oro físico (monedas de una onza)", "Oro", "commodity", "Común", "Caja de seguridad",
          "Alternativos", "Global"),
        p("letras", "Letras del Tesoro a 12 meses", "Letras del Tesoro", "bono", "Mi pareja",
          "Tesoro Público", "Renta fija", "España", largoPlazo=False, riesgo=1),
        p("solar", "Acciones de Energía Solar Ibérica", "Solar Ibérica", "accion", "Mi pareja",
          "Bróker online", "Renta variable", "España", riesgo=6),
        p("crowdfunding", "Crowdfunding inmobiliario", "Crowdfunding", "crowdfunding", "Yo",
          "Plataforma de ejemplo", "Inmuebles", "España", riesgo=6),
        p("cuenta", "Cuenta nómina", "Cuenta nómina", "efectivo", "Común", "Banco principal",
          "Liquidez", "España", largoPlazo=False, disponible=True),
        p("remunerada", "Cuenta remunerada", "Cuenta remunerada", "efectivo", "Común", "Banco online",
          "Liquidez", "España", largoPlazo=False, disponible=True),
        p("dolares", "Cuenta en dólares", "Cuenta USD", "efectivo", "Yo", "Neobanco", "Liquidez",
          "EEUU", moneda="USD", largoPlazo=False, disponible=True),
        p("personal", "Cuenta personal", "Cuenta personal", "efectivo", "Mi pareja", "Banco online",
          "Liquidez", "España", largoPlazo=False, disponible=True),
        p("hipoteca_valencia", "Hipoteca del piso de Valencia", "Hipoteca Valencia", "deuda", "Común",
          "Banco principal", None, None),
        p("prestamo_coche", "Préstamo del coche", "Préstamo coche", "deuda", "Común",
          "Financiera de ejemplo", None, None),
        p("tarjeta", "Tarjeta de crédito", "Tarjeta", "deuda", "Yo", "Banco principal", None, None),
    ]


# ---------------------------------------------------------------- PDF de muestra

def pdf(lineas):
    """Un PDF mínimo y válido de una página con unas líneas de texto (Helvetica). Los
    documentos del ejemplo son de muestra: se abren y se ven, pero no son reales."""
    def esc(t):
        return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    cuerpo = ["BT", "/F1 18 Tf", "56 770 Td", "24 TL", f"({esc(lineas[0])}) Tj", "/F1 11 Tf", "16 TL", "T*"]
    for ln in lineas[1:]:
        cuerpo += ["T*", f"({esc(ln)}) Tj"]
    cuerpo.append("ET")
    flujo = "\n".join(cuerpo).encode("cp1252", "replace")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Length " + str(len(flujo)).encode() + b" >>\nstream\n" + flujo + b"\nendstream"]
    out = bytearray(b"%PDF-1.4\n")
    pos = []
    for i, o in enumerate(objs, 1):
        pos.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for p in pos:
        out += f"{p:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


_PIE = ["", "Documento de muestra del patrimonio de ejemplo de Liberty.",
         "No es un documento real: sirve para ver cómo se guardan y enlazan tus papeles."]


def _documentos(cfg):
    """(subcarpeta, nombre en disco, contenido PDF, registro) de cada documento de muestra."""
    for fl in cfg.get("flujos") or []:
        for a in fl.get("adjuntos") or []:
            lineas = [a["nombre"].rsplit(".", 1)[0],
                      f"Fecha: {fl['fecha'][8:10]}/{fl['fecha'][5:7]}/{fl['fecha'][:4]}",
                      f"Concepto: {fl.get('nota') or fl.get('categoria')}",
                      f"Importe: {fl['importe']:.2f} €".replace(".", ",")]
            yield "adjuntos", a["archivo"], pdf(lineas + _PIE), a
    bib = cfg.get("biblioteca") or {}
    for a in (bib.get("archivos") or []) + (bib.get("papelera") or []):
        yield "biblioteca", a["archivo"], pdf([a["nombre"].rsplit(".", 1)[0]] + _PIE), a


def escribe_archivos(cfg, carpeta):
    """Escribe en disco (adjuntos/ y biblioteca/ de `carpeta`) los documentos de muestra que
    señala el ejemplo `cfg`. Solo los que falten: no pisa nada."""
    for sub, archivo, datos, _a in _documentos(cfg):
        d = os.path.join(carpeta, sub)
        os.makedirs(d, exist_ok=True)
        ruta = os.path.join(d, os.path.basename(archivo))
        if not os.path.exists(ruta):
            with open(ruta, "wb") as f:
                f.write(datos)


# ---------------------------------------------------------------- generador

class _Gen:
    def __init__(self, hoy, precios):
        self.hoy = hoy
        self.precios = precios or {}
        self.aprox = False          # True si algún precio salió de la aproximación
        self.movs, self.vals, self.flujos = [], [], []

    # -- utilidades
    def mes(self, k):
        return _suma_meses(self.hoy.year, self.hoy.month, k)

    def fecha(self, k, d):
        y, m = self.mes(k)
        return _dia(y, m, d)

    def cierre(self, k):
        """Fecha de la foto mensual: fin de mes, o hoy en el mes en curso."""
        y, m = self.mes(k)
        return min(_fin_mes(y, m), self.hoy)

    def rng(self, k, etiqueta):
        y, m = self.mes(k)
        return random.Random(f"{y}-{m}-{etiqueta}")

    def anios(self, f):
        return (self.hoy - f).days / 365.25

    def precio(self, pid, f):
        serie = self.precios.get(pid)
        if serie:
            v = valor_en(serie, f, margen=120)
            if v:
                return v
        self.aprox = True
        base, g = APROX[pid]
        return base * (1 + g) ** (-self.anios(f)) * (1 + 0.04 * math.sin(f.toordinal() / 45))

    # -- altas
    def mov(self, f, pid, tipo, importe, unidades=0.0, **extra):
        if f <= self.hoy:
            self.movs.append({"fecha": f.isoformat(), "producto": pid, "tipo": tipo,
                              "unidades": round(unidades, 8), "importe": round(importe, 2), **extra})

    def compra(self, f, pid, importe, comision=0.0, nota=None):
        u = (importe - comision) / self.precio(pid, f)
        extra = {}
        if comision:
            extra["comision"] = round(comision, 2)
        if nota:
            extra["nota"] = nota
        self.mov(f, pid, "compra", importe, u, **extra)
        return u

    def val(self, f, pid, valor):
        if f <= self.hoy:
            self.vals.append({"fecha": f.isoformat(), "producto": pid, "valor": round(valor, 2)})

    def fl(self, f, tipo, importe, categoria, titular, entidad, nota, naturaleza, **extra):
        if f <= self.hoy and importe > 0:
            self.flujos.append({"fecha": f.isoformat(), "tipo": tipo, "importe": round(importe, 2),
                                "categoria": categoria, "titular": titular, "entidad": entidad,
                                "nota": nota, "categorias": {"naturaleza": naturaleza}, **extra})
            return self.flujos[-1]
        return None


def genera(hoy=None, precios=None):
    """El patrimonio de ejemplo a fecha `hoy` (por defecto, hoy). `precios` = {id del
    producto: {fecha ISO: precio en euros}} de los que cotizan (de la caché); sin ellos se
    usa un precio aproximado. Devuelve (cartera, con_precios_reales)."""
    hoy = hoy or dt.date.today()
    g = _Gen(hoy, precios)
    k0 = -MESES
    Y = hoy.year
    FY = Y - 1                                    # último año fiscal cerrado
    RENTA = Y - 1 if hoy.month >= 7 else Y - 2   # última declaración presentada
    productos = _productos()

    # ---- inversiones que cotizan: un capital inicial y aportaciones mensuales ----
    for pid, inicial, mensual, desde, com in (("world", 16000, 300, k0, 0), ("emergentes", 4000, 100, k0, 0),
                                              ("etfworld", 7000, 150, k0, 2), ("bitcoin", 800, 50, -11, 0)):
        for k in range(desde, 1):
            f = g.fecha(k, 3)
            nota = "Traspaso inicial" if k == desde else "Aportación periódica"
            g.compra(f, pid, inicial if k == desde else mensual, comision=com, nota=nota)
    # Monetario: el colchón que rinde. Un rescate con ganancia (Fiscal) y una recompra.
    g.compra(g.fecha(k0, 3), "monetario", 15000, nota="Traspaso inicial")
    g.compra(_dia(FY - 1, 11, 4), "monetario", 2000)
    pv = g.precio("monetario", _dia(FY, 5, 12))
    g.mov(_dia(FY, 5, 12), "monetario", "venta", round(6000 / pv, 6) * pv, round(6000 / pv, 6),
          nota="Rescate para la reforma del piso")
    g.compra(g.fecha(-4, 6), "monetario", 2500)
    # Apple (en dólares): tres compras, dividendos trimestrales con retención y la custodia.
    for k, imp in ((-30, 1500), (-18, 1000), (-8, 800)):
        g.compra(g.fecha(k, 12), "apple", imp, comision=3)
    for k in range(k0, 1):
        y, m = g.mes(k)
        if m in (2, 5, 8, 11):
            tenia = sum(x["unidades"] for x in g.movs if x["producto"] == "apple" and x["tipo"] == "compra"
                        and x["fecha"] <= g.fecha(k, 15).isoformat())
            if tenia:
                bruto = tenia * 0.25 * 0.92
                g.mov(g.fecha(k, 15), "apple", "dividendo", bruto * 0.85, retencion=round(bruto * 0.15, 2))
    g.mov(_dia(FY, 12, 20), "apple", "comision", 12, nota="Comisión de custodia anual")

    # ---- inversiones a mano: compras como movimientos y su valor, mes a mes ----
    for k in range(k0, 1):
        f, c = g.fecha(k, 5), g.cierre(k)
        g.mov(f, "pension", "compra", 12000 if k == k0 else 100,
              nota="Traspaso desde el plan anterior" if k == k0 else None)
        g.mov(f, "seguro", "compra", 5000 if k == k0 else 50)
        n = k - k0 + 1
        ap_p = 12000 + 100 * (n - 1)
        ap_s = 5000 + 50 * (n - 1)
        # Valor: lo aportado más una rentabilidad suave con altibajos (el plan, del 6 % anual).
        vaiv = 1 + 0.035 * math.sin(n / 2.7)
        g.val(c, "pension", ap_p * (1 + 0.06 * n / 12) * vaiv)
        g.val(c, "seguro", ap_s * (1 + 0.025 * n / 12))
    for x in g.movs:   # sin nota vacía
        if x.get("nota") is None:
            x.pop("nota", None)
    # Oro: 4 onzas al principio; se vende una (con ganancia) en el año fiscal cerrado.
    g.mov(g.fecha(k0, 20), "oro", "compra", 7000, 4)
    g.mov(_dia(FY, 9, 20), "oro", "venta", 2450, 1, nota="Venta de una onza")
    for k in range(k0, 1, 3):
        onza = 1750 * (1 + 0.20) ** ((k - k0) / 12)
        onzas = 4 if g.fecha(k, 28) < _dia(FY, 9, 20) else 3
        g.val(g.cierre(k), "oro", onzas * onza)
    # Letras del Tesoro: vencen en unas semanas (aviso de vencimiento cercano).
    vence_letras = hoy + dt.timedelta(days=45)
    compra_letras = vence_letras - dt.timedelta(days=364)
    g.mov(compra_letras, "letras", "compra", 4865, 5)
    for k in range(k0, 1):
        c = g.cierre(k)
        if c >= compra_letras:
            g.val(c, "letras", 4865 + 135 * (c - compra_letras).days / 364)
    # Energía Solar Ibérica: va en pérdidas. Una venta con pérdida y dos dividendos.
    g.mov(g.fecha(k0 + 2, 14), "solar", "compra", 3400, 400)
    g.mov(_dia(FY, 3, 15), "solar", "venta", 960, 150, nota="Venta con pérdida para compensar ganancias")
    for f in (_dia(FY, 6, 10), _dia(FY, 12, 10)):
        bruto = 250 * 0.18
        g.mov(f, "solar", "dividendo", bruto * 0.81, retencion=round(bruto * 0.19, 2))
    for k in range(k0 + 2, 1):
        acc = 400 if g.fecha(k, 28) < _dia(FY, 3, 15) else 250
        precio = 8.5 - 2.4 * (k - k0 - 2) / (MESES - 2) + 0.35 * math.sin(k / 1.7)
        g.val(g.cierre(k), "solar", acc * precio)
    # Crowdfunding: dos proyectos; el valor cae por un retraso (va en negativo).
    g.mov(g.fecha(-28, 9), "crowdfunding", "compra", 2000, nota="Proyecto de viviendas en Málaga")
    g.mov(g.fecha(-20, 9), "crowdfunding", "compra", 1000, nota="Proyecto de oficinas en Sevilla")
    for k in range(-28, 1):
        ap = 2000 if k < -20 else 3000
        caida = 1.0 if k < -10 else 1 - 0.35 * (k + 10) / 10
        g.val(g.cierre(k), "crowdfunding", ap * (1.04 if k < -10 else caida))

    # ---- cuentas y deudas: un saldo por mes ----
    q_val = _cuota(92000, 0.024, 300)
    ini_val = _dia(*_suma_meses(Y, hoy.month, -90), 10)
    q_coche = _cuota(18000, 0.065, 60)
    ini_coche = g.fecha(-30, 1)
    for k in range(k0, 1):
        c = g.cierre(k)
        r = g.rng(k, "saldos")
        n = k - k0
        g.val(c, "cuenta", 4200 + 1800 * math.sin(n / 1.9) + r.uniform(-400, 400))
        g.val(c, "remunerada", 11000 + 260 * n + r.uniform(-150, 150))
        g.val(c, "dolares", 2400 + 9 * n + r.uniform(-60, 60))
        g.val(c, "personal", 1900 + 25 * n + r.uniform(-250, 250))
        g.val(c, "hipoteca_valencia", _pendiente(92000, 0.024, q_val, _meses_entre(ini_val, c)))
        if c >= ini_coche:
            g.val(c, "prestamo_coche", _pendiente(18000, 0.065, q_coche, _meses_entre(ini_coche, c)))
        g.val(c, "tarjeta", r.uniform(250, 950))

    # ---- ingresos y gastos ----
    q_casa = _cuota(195000, 0.019, 360)
    fin_javier = _fin_mes(*g.mes(-13))
    ini_ana = g.fecha(-11, 1)
    ini_garaje = g.fecha(-30, 1)
    B, O, T = "Banco principal", "Banco online", "Tarjeta de crédito"
    for k in range(k0, 1):
        y, m = g.mes(k)
        r = g.rng(k, "flujos")
        anyos = (y - (Y - 3))
        sube = 1.03 ** max(0, anyos)
        # Ingresos
        g.fl(_dia(y, m, 28), "ingreso", 2350 * sube, "Nómina", "Yo", B, "NOMINA EMPRESA DE EJEMPLO SA", "Fijo")
        g.fl(_dia(y, m, 30), "ingreso", 2050 * sube, "Nómina", "Mi pareja", B, "NOMINA COLEGIO DE EJEMPLO", "Fijo")
        if m in (6, 12):
            g.fl(_dia(y, m, 20), "ingreso", 2350 * sube, "Nómina", "Yo", B, "PAGA EXTRA", "Extraordinario")
            g.fl(_dia(y, m, 21), "ingreso", 2050 * sube, "Nómina", "Mi pareja", B, "PAGA EXTRA", "Extraordinario")
        f5 = _dia(y, m, 5)
        if f5 <= fin_javier:
            renta = 700 if k < -26 else 721
            g.fl(f5, "ingreso", renta, "Alquiler piso Valencia", "Común", B, "TRANSF. JAVIER ORTEGA ALQUILER", "Fijo")
        elif f5 >= ini_ana:
            g.fl(f5, "ingreso", 780, "Alquiler piso Valencia", "Común", B, "TRANSF. ANA MARTIN ALQUILER", "Fijo")
        if _dia(y, m, 1) >= ini_garaje:
            g.fl(_dia(y, m, 1), "ingreso", 85, "Alquiler garaje", "Común", B, "BIZUM PEDRO SANZ GARAJE", "Fijo")
        g.fl(_fin_mes(y, m), "ingreso", 22 + 0.6 * (k - k0) + r.uniform(-3, 3), "Intereses y dividendos",
             "Común", O, "INTERESES CUENTA REMUNERADA", "Variable")
        # Vivienda habitual
        g.fl(_dia(y, m, 1), "gasto", q_casa, "Vivienda", "Común", B, "RECIBO PRESTAMO HIPOTECARIO", "Fijo")
        g.fl(_dia(y, m, 2), "gasto", 70, "Vivienda", "Común", B, "RECIBO COMUNIDAD DE PROPIETARIOS", "Fijo")
        if m == 10:
            g.fl(_dia(y, m, 20), "gasto", 515, "Vivienda", "Común", B, "RECIBO IBI AYUNTAMIENTO", "Extraordinario")
        # Suministros
        invierno = m in (12, 1, 2)
        g.fl(_dia(y, m, 12), "gasto", (88 if invierno else 58) + r.uniform(-8, 12), "Suministros", "Común", B,
             "RECIBO LUZ COMERCIALIZADORA", "Variable")
        if m in (11, 12, 1, 2, 3):
            g.fl(_dia(y, m, 18), "gasto", 62 + r.uniform(0, 45), "Suministros", "Común", B, "RECIBO GAS NATURAL", "Variable")
        if m % 2 == 0:
            g.fl(_dia(y, m, 22), "gasto", 41 + r.uniform(-3, 6), "Suministros", "Común", B, "RECIBO AGUA", "Variable")
        g.fl(_dia(y, m, 8), "gasto", 58, "Suministros", "Común", B, "FIBRA Y MOVIL", "Fijo")
        # Comida, transporte y día a día
        for d in (3, 10, 17, 24):
            extra = 1.25 if m == 12 and d == 24 else 1
            g.fl(_dia(y, m, d), "gasto", (128 + r.uniform(-25, 40)) * extra, "Alimentación", "Común", T,
                 "COMPRA SUPERMERCADO", "Variable")
        for d in (6, 21):
            g.fl(_dia(y, m, d), "gasto", 52 + r.uniform(0, 22), "Transporte", "Yo", T, "GASOLINERA", "Variable")
        if _dia(y, m, 10) >= ini_coche:
            g.fl(_dia(y, m, 10), "gasto", q_coche, "Préstamos", "Común", B, "CUOTA PRESTAMO COCHE", "Fijo")
        for i, d in enumerate(sorted(r.sample(range(4, 28), 3))):
            g.fl(_dia(y, m, d), "gasto", 24 + r.uniform(0, 70), "Ocio y restaurantes",
                 "Común" if i else r.choice(["Yo", "Mi pareja"]), T,
                 r.choice(["RESTAURANTE", "CINE", "CAFETERIA", "ENTRADAS CONCIERTO"]), "Variable")
        g.fl(_dia(y, m, 15), "gasto", 13.99, "Suscripciones", "Común", T, "PLATAFORMA DE STREAMING", "Fijo")
        g.fl(_dia(y, m, 15), "gasto", 10.99, "Suscripciones", "Yo", T, "SERVICIO DE MUSICA", "Fijo")
        g.fl(_dia(y, m, 1), "gasto", 39.9, "Suscripciones", "Mi pareja", B, "CUOTA GIMNASIO", "Fijo")
        g.fl(_dia(y, m, 19), "gasto", (180 if m == 1 else 45) + r.uniform(0, 90), "Compras y ropa",
             r.choice(["Yo", "Mi pareja"]), T, "TIENDA DE ROPA" if r.random() < 0.6 else "LIBRERIA", "Variable")
        if m % 3 == 0:
            g.fl(_dia(y, m, 14), "gasto", 14 + r.uniform(0, 18), "Salud", "Común", T, "FARMACIA", "Variable")
        if m == 5:
            g.fl(_dia(y, m, 16), "gasto", 120, "Salud", "Mi pareja", T, "CLINICA DENTAL", "Extraordinario")
        if m == 8:
            g.fl(_dia(y, m, 10), "gasto", 1350 + r.uniform(0, 300), "Vacaciones y viajes", "Común", T,
                 "AGENCIA DE VIAJES", "Extraordinario")
        if m == 4:
            g.fl(_dia(y, m, 2), "gasto", 420 + r.uniform(0, 120), "Vacaciones y viajes", "Común", T,
                 "HOTEL SEMANA SANTA", "Extraordinario")
        if m == 12:
            g.fl(_dia(y, m, 18), "gasto", 380, "Regalos", "Común", T, "REGALOS DE NAVIDAD", "Extraordinario")
        if m == 2:
            g.fl(_dia(y, m, 15), "gasto", 285, "Seguros", "Común", B, "SEGURO DE HOGAR", "Extraordinario")
        if m == 3:
            g.fl(_dia(y, m, 10), "gasto", 420, "Seguros", "Común", B, "SEGURO DEL COCHE", "Extraordinario")
        # Piso de Valencia, garaje y trastero (forman el libro de cada inmueble)
        g.fl(_dia(y, m, 1), "gasto", q_val, "Gastos piso Valencia", "Común", B, "RECIBO HIPOTECA PISO VALENCIA", "Fijo")
        g.fl(_dia(y, m, 2), "gasto", 45, "Gastos piso Valencia", "Común", B, "COMUNIDAD PISO VALENCIA", "Fijo")
        if m == 6:
            g.fl(_dia(y, m, 12), "gasto", 260, "Gastos piso Valencia", "Común", B, "IBI PISO VALENCIA", "Extraordinario")
            g.fl(_dia(y, m, 12), "gasto", 48, "Gastos garaje", "Común", B, "IBI PLAZA DE GARAJE", "Extraordinario")
            g.fl(_dia(y, m, 12), "gasto", 22, "Gastos trastero", "Común", B, "IBI TRASTERO", "Extraordinario")
        if m == 5:
            g.fl(_dia(y, m, 7), "gasto", 190, "Gastos piso Valencia", "Común", B, "SEGURO HOGAR PISO VALENCIA", "Extraordinario")
        if m % 3 == 1:
            g.fl(_dia(y, m, 4), "gasto", 30, "Gastos garaje", "Común", B, "COMUNIDAD GARAJE", "Fijo")
            g.fl(_dia(y, m, 4), "gasto", 12, "Gastos trastero", "Común", B, "COMUNIDAD TRASTERO", "Fijo")

    # Apuntes sueltos con historia: la reforma entre inquilinos, la caldera, la ITV, la renta.
    pintura = g.fl(g.fecha(-12, 16), "gasto", 1450, "Gastos piso Valencia", "Común", B, "PINTURA Y REPARACIONES",
                   "Extraordinario", observaciones="Pintar el piso entero y arreglar la persiana del salón "
                   "entre un inquilino y otro. Pagado con el rescate del monetario.", marca="justificante")
    caldera = g.fl(g.fecha(-7, 22), "gasto", 340, "Gastos piso Valencia", "Común", B, "REPARACION CALDERA",
                   "Extraordinario", observaciones="Cambio de la placa electrónica. Garantía de 2 años: "
                   "guardar la factura.", marca="importante")
    g.fl(g.fecha(-14, 9), "gasto", 45, "Transporte", "Yo", T, "ITV", "Extraordinario")
    g.fl(_dia(Y - 2 if hoy.month < 7 else Y - 1, 6, 25), "gasto", 640, "Impuestos", "Común", B,
         "DECLARACION IRPF", "Extraordinario", observaciones="Nos salió a pagar: este año reservamos "
         "dinero para la renta (ver el reservado).", marca="verificado")
    g.fl(_dia(Y - 3 if hoy.month < 7 else Y - 2, 7, 28), "ingreso", 310, "Otros ingresos", "Común", B,
         "DEVOLUCION IRPF", "Extraordinario")
    g.fl(g.fecha(-5, 11), "ingreso", 150, "Otros ingresos", "Mi pareja", B, "VENTA MUEBLE DE SEGUNDA MANO",
         "Extraordinario")

    # Marcas y facturas en algunos apuntes recientes.
    def ultimo(nota, antes=0):
        cand = [x for x in g.flujos if x["nota"] == nota]
        return cand[-1 - antes] if len(cand) > antes else None

    for x, marca in ((ultimo("RECIBO LUZ COMERCIALIZADORA", 2), "revisar"),
                     (ultimo("RESTAURANTE"), "duda"),
                     (ultimo("RECIBO IBI AYUNTAMIENTO"), "importante")):
        if x:
            x["marca"] = marca
    luz_alta = ultimo("RECIBO LUZ COMERCIALIZADORA", 2)
    if luz_alta:
        luz_alta["observaciones"] = "Más alta de lo normal: comprobar la lectura del contador."
    facturas = [(ultimo("RECIBO LUZ COMERCIALIZADORA", i), f"Factura de la luz {i + 1}") for i in range(3)]
    facturas += [(pintura, "Factura pintura piso Valencia"), (caldera, "Factura reparación caldera"),
                 (ultimo("RECIBO IBI AYUNTAMIENTO"), "Recibo IBI casa"), (ultimo("SEGURO DEL COCHE"), "Recibo seguro del coche"),
                 (ultimo("CLINICA DENTAL"), "Factura clínica dental"), (ultimo("ITV"), "Justificante ITV"),
                 (ultimo("SEGURO HOGAR PISO VALENCIA"), "Recibo seguro piso Valencia")]
    n_adj = 0
    for x, nombre in facturas:
        if not x:
            continue
        n_adj += 1
        adj = {"id": f"adj_demo{n_adj:02d}", "archivo": f"adj_demo{n_adj:02d}.pdf",
               "nombre": f"{nombre}.pdf", "tipo": "application/pdf", "tam": 0}
        if nombre.startswith("Recibo IBI"):
            adj["importante"] = True
        x.setdefault("adjuntos", []).append(adj)
    for x in g.flujos:   # los luz llevan número de mes en el nombre, no «1, 2, 3»
        for a in x.get("adjuntos") or []:
            if a["nombre"].startswith("Factura de la luz"):
                a["nombre"] = f"Factura de la luz {x['fecha'][5:7]}-{x['fecha'][:4]}.pdf"

    # El año más antiguo, archivado (oculto de la lista; sigue contando en el Panel).
    corte = g.fecha(-24, 1).isoformat()
    for x in g.flujos:
        if x["fecha"] < corte:
            x["archivado"] = True

    # ---- ids y orden ----
    g.movs.sort(key=lambda x: x["fecha"])
    for i, x in enumerate(g.movs, 1):
        x["id"] = f"m{i}"
    g.vals.sort(key=lambda x: (x["producto"], x["fecha"]))
    for i, x in enumerate(g.vals, 1):
        x["id"] = f"v{i}"
    g.flujos.sort(key=lambda x: x["fecha"])
    for i, x in enumerate(g.flujos, 1):
        x["id"] = f"f{i}"
    g.movs = [{"id": x.pop("id"), **x} for x in g.movs]
    g.vals = [{"id": x.pop("id"), **x} for x in g.vals]
    g.flujos = [{"id": x.pop("id"), **x} for x in g.flujos]

    # ---- fechas de los productos ----
    por_id = {p["id"]: p for p in productos}
    por_id["letras"]["fechaVencimiento"] = vence_letras.isoformat()
    por_id["hipoteca_valencia"].update(capitalInicial=92000, tae=0.024, cuota=round(q_val, 2),
                                       fechaInicio=ini_val.isoformat(),
                                       fechaVencimiento=_dia(ini_val.year + 25, ini_val.month, 10).isoformat())
    por_id["prestamo_coche"].update(capitalInicial=18000, tae=0.065, cuota=round(q_coche, 2),
                                    fechaInicio=ini_coche.isoformat(),
                                    fechaVencimiento=_dia(ini_coche.year + 5, ini_coche.month, 1).isoformat())
    for n, p in enumerate(productos):
        p["slot"] = n % 16 + 1

    # ---- inmuebles ----
    hip_val = _pendiente(92000, 0.024, q_val, _meses_entre(ini_val, hoy))
    compra_casa = _dia(*_suma_meses(Y, hoy.month, -66), 15)
    hip_casa = _pendiente(195000, 0.019, q_casa, _meses_entre(compra_casa, hoy))
    fin_ana = _dia(ini_ana.year + 5, ini_ana.month, 1) - dt.timedelta(days=1)
    fin_garaje = _dia(ini_garaje.year + 3, ini_garaje.month, 1) - dt.timedelta(days=1)
    inmuebles = [
        {"id": "i1", "nombre": "Nuestra casa", "tipo": "piso", "uso": "habitual", "titular": "Común",
         "direccion": "C/ de Ejemplo 21, 3.º B, Madrid", "m2": 88, "habitaciones": 3, "valorCatastral": 98000,
         "compra": {"fecha": compra_casa.isoformat(), "precio": 225000, "gastos": 22500},
         "valor": {"importe": 235000, "fecha": g.fecha(-2, 15).isoformat()},
         "historico": [{"fecha": g.fecha(k, 15).isoformat(), "importe": v}
                       for k, v in ((-34, 222000), (-22, 226000), (-14, 230000))],
         "hipoteca": {"capitalPendiente": round(hip_casa, 2), "cuota": round(q_casa, 2), "tipoInteres": 0.019,
                      "fechaFin": _dia(compra_casa.year + 30, compra_casa.month, 15).isoformat()},
         "nota": "Hipoteca a tipo fijo. La estimación de valor es la de un portal inmobiliario.",
         "categorias": ["Vivienda"]},
        {"id": "i2", "nombre": "Piso en alquiler (Valencia)", "tipo": "piso", "uso": "inversion", "estado": "alquilado",
         "titular": "Común", "direccion": "C/ de Muestra 12, 4.º, Valencia", "refCatastral": "EJEMPLO0000000000001",
         "m2": 72, "habitaciones": 3, "valorCatastral": 61000,
         "compra": {"fecha": ini_val.isoformat(), "precio": 115000, "gastos": 11500},
         "valor": {"importe": 138000, "fecha": g.fecha(-3, 10).isoformat()},
         "historico": [{"fecha": g.fecha(k, 10).isoformat(), "importe": v}
                       for k, v in ((-33, 127000), (-21, 131000), (-9, 135000))],
         "hipoteca": {"capitalPendiente": round(hip_val, 2), "cuota": round(q_val, 2), "tipoInteres": 0.024,
                      "fechaFin": por_id["hipoteca_valencia"]["fechaVencimiento"], "deudaRef": "hipoteca_valencia"},
         "nota": "Alquilado como vivienda habitual del inquilino (contrato de la LAU).",
         "categorias": ["Alquiler piso Valencia", "Gastos piso Valencia"],
         "inquilinos": [
             {"id": "q1", "nombre": "Javier Ortega", "telefono": "600 000 111", "email": "javier@ejemplo.com",
              "nota": "Se fue a otra ciudad por trabajo. Devolvimos la fianza entera.",
              "contratos": [{"id": "c1", "inicio": g.fecha(-50, 1).isoformat(), "fin": fin_javier.isoformat(),
                             "renta": 700, "diaCobro": 5, "fianza": 700, "actualizacion": "ipc",
                             "categoria": "Alquiler piso Valencia", "archivos": [{"tipo": "archivo", "id": "arc_demo14"}]}]},
             {"id": "q2", "nombre": "Ana Martín", "telefono": "600 123 456", "email": "ana@ejemplo.com",
              "campos": [{"nombre": "Avalista", "valores": ["Luis Martín"]},
                         {"nombre": "Contacto de emergencia", "valores": ["Marta (hermana) · 600 987 654"]}],
              "contratos": [{"id": "c2", "inicio": ini_ana.isoformat(), "fin": fin_ana.isoformat(), "renta": 780,
                             "diaCobro": 5, "fianza": 1560, "actualizacion": "irav",
                             "categoria": "Alquiler piso Valencia",
                             "nota": "Dos meses de fianza. La renta se actualiza cada año con el IRAV.",
                             "campos": [{"nombre": "Gastos incluidos", "valores": ["Comunidad", "Agua"]},
                                        {"nombre": "Duración mínima", "valores": ["1 año"]}],
                             "archivos": [{"tipo": "archivo", "id": "arc_demo03"}, {"tipo": "archivo", "id": "arc_demo04"},
                                          {"tipo": "archivo", "id": "arc_demo05"}]}]}]},
        {"id": "i3", "nombre": "Plaza de garaje", "tipo": "garaje", "uso": "inversion", "estado": "alquilado",
         "titular": "Común", "direccion": "C/ de Ejemplo 21, sótano 1, plaza 14, Madrid", "m2": 12,
         "compra": {"fecha": g.fecha(-40, 20).isoformat(), "precio": 14000, "gastos": 1200},
         "valor": {"importe": 15500, "fecha": g.fecha(-8, 1).isoformat()},
         "categorias": ["Alquiler garaje", "Gastos garaje"],
         "inquilinos": [{"id": "q3", "nombre": "Pedro Sanz", "telefono": "600 222 333",
                         "contratos": [{"id": "c3", "inicio": ini_garaje.isoformat(), "fin": fin_garaje.isoformat(),
                                        "renta": 85, "diaCobro": 1, "fianza": 85, "actualizacion": "pactada",
                                        "categoria": "Alquiler garaje",
                                        "archivos": [{"tipo": "archivo", "id": "arc_demo06"}]}]}]},
        {"id": "i4", "nombre": "Trastero", "tipo": "trastero", "uso": "inversion", "estado": "venta",
         "titular": "Común", "direccion": "C/ de Ejemplo 21, trastero 6, Madrid", "m2": 6,
         "compra": {"fecha": g.fecha(-60, 12).isoformat(), "precio": 6500, "gastos": 600},
         "valor": {"importe": 8000, "fecha": g.fecha(-4, 1).isoformat()},
         "nota": "Anunciado en portales por 8.500 €. Ya no lo usamos.",
         "categorias": ["Gastos trastero"]},
    ]

    # ---- biblioteca ----
    def carpeta(cid, nombre, padre=None):
        return {"id": f"car_demo_{cid}", "nombre": nombre, "padre": f"car_demo_{padre}" if padre else None}
    carpetas = [carpeta("casa", "Casa"), carpeta("escrituras", "Escrituras", "casa"),
                carpeta("inmuebles", "Inmuebles"), carpeta("valencia", "Piso Valencia", "inmuebles"),
                carpeta("garaje", "Garaje", "inmuebles"), carpeta("inversiones", "Inversiones"),
                carpeta("impuestos", "Impuestos"), carpeta("renta", f"Renta {RENTA}", "impuestos"),
                carpeta("seguros", "Seguros")]
    mes_ext = g.fecha(-1, 1)
    docs = [("01", "Escritura de compraventa de casa", "escrituras", compra_casa),
            ("02", f"Recibo IBI casa {Y - 1}", "casa", _dia(Y - 1, 10, 20)),
            ("03", "Contrato de alquiler - Ana Martín", "valencia", ini_ana),
            ("04", "Inventario del piso", "valencia", ini_ana),
            ("05", "Depósito de la fianza", "valencia", ini_ana + dt.timedelta(days=12)),
            ("06", "Contrato de la plaza de garaje", "garaje", ini_garaje),
            ("07", f"Extracto del bróker {mes_ext.month:02d}-{mes_ext.year}", "inversiones", _fin_mes(mes_ext.year, mes_ext.month)),
            ("08", f"Certificado del plan de pensiones {Y - 1}", "inversiones", _dia(Y, 1, 20) if hoy >= _dia(Y, 1, 20) else _dia(Y - 1, 1, 20)),
            ("09", f"Declaración de la renta {RENTA}", "renta", _dia(RENTA + 1, 6, 25)),
            ("10", f"Certificado de retenciones {RENTA}", "renta", _dia(RENTA + 1, 3, 10)),
            ("11", "Póliza del seguro de hogar", "seguros", _dia(Y - 1, 2, 15)),
            ("12", "Póliza del seguro del coche", "seguros", _dia(Y - 1, 3, 10)),
            ("13", "Nota simple del trastero", "inmuebles", g.fecha(-4, 2)),
            ("14", "Contrato anterior - Javier Ortega", "valencia", g.fecha(-50, 1))]
    archivos = [{"id": f"arc_demo{n}", "archivo": f"arc_demo{n}.pdf", "nombre": f"{nombre}.pdf",
                 "tipo": "application/pdf", "tam": 0, "carpeta": f"car_demo_{car}",
                 "fecha": f"{min(f, hoy).isoformat()}T10:00:00"} for n, nombre, car, f in docs]
    papelera = [{"id": "arc_demo15", "archivo": "arc_demo15.pdf", "nombre": "Recibo duplicado.pdf",
                 "tipo": "application/pdf", "tam": 0, "carpeta": "car_demo_casa", "carpetaNombre": "Casa",
                 "fecha": f"{(hoy - dt.timedelta(days=30)).isoformat()}T10:00:00",
                 "borrado": f"{(hoy - dt.timedelta(days=3)).isoformat()}T18:30:00"}]

    # ---- notas, cuadernos, agenda y tablero ----
    def hace(dias):
        return (hoy - dt.timedelta(days=dias)).isoformat()

    def act(ref):
        return {"tipo": "activo", "ref": ref}
    cuadernos = [{"id": "inversiones", "nombre": "Inversiones", "color": "s2"},
                 {"id": "casa", "nombre": "Casa e inmuebles", "color": "s6"},
                 {"id": "impuestos", "nombre": "Impuestos y papeles", "color": "s8"}]
    notas = [
        {"id": "n1", "titulo": "Cómo usar este ejemplo", "fijada": True, "fecha": hace(1), "etiquetas": ["empezar"],
         "texto": "Este es un hogar de muestra: una pareja con su casa, un piso alquilado, una plaza de garaje, "
                  "un trastero en venta y sus inversiones.\n\nPrueba a:\n- [ ] Abrir la ficha de un activo desde "
                  "Cartera\n- [ ] Ver el libro del piso de Valencia en Inmuebles\n- [ ] Buscar las facturas en "
                  "Ingresos y gastos (📎)\n- [ ] Abrir los cuadernos de Documentos\n\nCuando quieras, pulsa "
                  "«Empezar con mis datos»."},
        {"id": "n2", "titulo": "Nuestra estrategia de inversión", "cuaderno": "inversiones", "fijada": True,
         "color": "s2", "fecha": hace(200), "editada": hace(40), "etiquetas": ["estrategia"],
         "vinculos": [act("world"), act("etfworld"), act("emergentes")],
         "texto": "Fondos y ETF indexados, aportación automática cada mes y no tocar nada cuando el mercado "
                  "cae. Reparto: 80 % mundo desarrollado y 20 % emergentes. Lo que sobra del colchón, al "
                  "monetario."},
        {"id": "n3", "titulo": "Rebalanceo de fin de año", "cuaderno": "inversiones", "fecha": hace(25),
         "etiquetas": ["estrategia"], "vinculos": [act("world"), act("bitcoin")],
         "texto": "- [x] Revisar los pesos en Distribución\n- [ ] Compararlos con los objetivos\n"
                  "- [ ] Ajustar la aportación de enero\n- [ ] Decidir si seguimos con el bitcoin (máx. 2 %)"},
        {"id": "n4", "titulo": "Crowdfunding: por qué va en negativo", "cuaderno": "inversiones", "color": "s14",
         "fecha": hace(60), "etiquetas": ["riesgo"], "vinculos": [act("crowdfunding")],
         "texto": "El proyecto de Málaga lleva retraso y la plataforma ha rebajado su valor. Hay una alerta "
                  "puesta por si baja de 2.000 €. No volver a meter más dinero aquí."},
        {"id": "n5", "titulo": "Solar Ibérica: vender o aguantar", "cuaderno": "inversiones", "fecha": hace(150),
         "etiquetas": ["fiscalidad"], "vinculos": [act("solar")],
         "texto": f"En marzo de {FY} vendimos 150 acciones con pérdida para compensar la ganancia del oro y del "
                  "monetario en la declaración. El resto lo aguantamos por el dividendo."},
        {"id": "n6", "titulo": "Papeles para la renta", "cuaderno": "impuestos", "fijada": True, "color": "s8",
         "fecha": hace(15), "etiquetas": ["renta"],
         "vinculos": [{"tipo": "reservado", "ref": "a1"}],
         "archivos": [{"tipo": "carpeta", "id": "car_demo_renta"}, {"tipo": "archivo", "id": "arc_demo08"}],
         "texto": "- [x] Certificado de retenciones de las nóminas\n- [x] Certificado del plan de pensiones\n"
                  "- [ ] Informe fiscal del bróker (Panel → Fiscal)\n- [ ] Ingresos y gastos del piso de Valencia\n"
                  "- [ ] Recibos del IBI"},
        {"id": "n7", "titulo": "Plan de pensiones: cuánto aportar", "cuaderno": "impuestos", "fecha": hace(90),
         "vinculos": [act("pension")], "archivos": [{"tipo": "archivo", "id": "arc_demo08"}],
         "texto": "Aportamos 100 € al mes. Si en diciembre sobra, una aportación extra: reduce la base del IRPF."},
        {"id": "n8", "titulo": "Contrato de Ana", "cuaderno": "casa", "fecha": hace(330), "editada": hace(10),
         "etiquetas": ["alquiler"],
         "vinculos": [{"tipo": "inmueble", "ref": "i2"}, {"tipo": "reservado", "ref": "a3"}],
         "archivos": [{"tipo": "archivo", "id": "arc_demo03"}, {"tipo": "archivo", "id": "arc_demo05"}],
         "texto": "Cinco años, renta de 780 € que se revisa cada año con el IRAV. La fianza (dos meses) está "
                  "depositada y reservada aparte, porque hay que devolverla."},
        {"id": "n9", "titulo": "Caldera del piso de Valencia", "cuaderno": "casa", "fecha": g.fecha(-7, 22).isoformat(),
         "vinculos": [{"tipo": "inmueble", "ref": "i2"}],
         "texto": "Se cambió la placa electrónica. Dos años de garantía: la factura está en el apunte de la "
                  "reparación (Ingresos y gastos)."},
        {"id": "n10", "titulo": "¿Amortizar hipoteca o invertir?", "cuaderno": "casa", "color": "s6", "fecha": hace(120),
         "vinculos": [{"tipo": "inmueble", "ref": "i1"}, {"tipo": "deuda", "ref": "hipoteca_valencia"}],
         "texto": "Las dos hipotecas están por debajo del 2,5 %. De momento compensa más seguir invirtiendo "
                  "que amortizar. Revisarlo si suben los tipos."},
        {"id": "n11", "titulo": "Vender el trastero", "cuaderno": "casa", "fecha": hace(50),
         "vinculos": [{"tipo": "inmueble", "ref": "i4"}], "archivos": [{"tipo": "archivo", "id": "arc_demo13"}],
         "texto": "- [x] Pedir la nota simple\n- [x] Anunciarlo en dos portales\n- [ ] Enseñarlo a los interesados"},
        {"id": "n12", "titulo": "Seguro del coche", "fecha": hace(240), "etiquetas": ["seguros"],
         "vinculos": [{"tipo": "deuda", "ref": "prestamo_coche"}],
         "archivos": [{"tipo": "archivo", "id": "arc_demo12"}],
         "texto": "Renueva en marzo. Antes, pedir precio en otras dos aseguradoras."},
        {"id": "n13", "titulo": "Ideas para las vacaciones", "color": "s14", "fecha": hace(35),
         "vinculos": [{"tipo": "reservado", "ref": "a2"}],
         "texto": "Asturias en coche o una semana en Lisboa. Presupuesto: lo reservado."},
    ]
    proximo_irav = _dia(ini_ana.year + 1, ini_ana.month, 1)
    while proximo_irav < hoy:
        proximo_irav = _dia(proximo_irav.year + 1, proximo_irav.month, 1)
    recordatorios = [
        {"id": "r1", "texto": "Revisar el recibo de la luz", "fecha": g.fecha(-6, 12).isoformat(), "repetir": "mensual"},
        {"id": "r2", "texto": "Pagar el IBI de casa", "fecha": _dia(Y - 1, 10, 20).isoformat(), "repetir": "anual",
         "vinculo": {"tipo": "inmueble", "ref": "i1"}},
        {"id": "r3", "texto": "Presentar la declaración de la renta", "fecha": _dia(Y - 1, 6, 15).isoformat(),
         "repetir": "anual", "vinculo": {"tipo": "reservado", "ref": "a1"}},
        {"id": "r4", "texto": "Aportación extra al plan de pensiones", "fecha": _dia(Y - 1, 12, 15).isoformat(),
         "repetir": "anual", "vinculo": act("pension")},
        {"id": "r5", "texto": "Pasar la ITV del coche", "fecha": (hoy + dt.timedelta(days=5)).isoformat(),
         "vinculo": {"tipo": "deuda", "ref": "prestamo_coche"}},
        {"id": "r6", "texto": "Actualizar la renta de Ana con el IRAV", "fecha": proximo_irav.isoformat(),
         "vinculo": {"tipo": "inmueble", "ref": "i2"}},
        {"id": "r7", "texto": "Decidir qué hacer con las Letras cuando venzan", "fecha": vence_letras.isoformat(),
         "vinculo": act("letras")},
        {"id": "r8", "texto": "Renovar el DNI", "fecha": hace(40), "hecho": True},
    ]
    for r in recordatorios:
        r.setdefault("hecho", False)
        r.setdefault("repetir", "no")
    tablero = {"columnas": [{"id": "pendiente", "nombre": "Por hacer"}, {"id": "en-marcha", "nombre": "En marcha"},
                            {"id": "hecho", "nombre": "Hecho"}],
               "tarjetas": [
                   {"id": "t1", "col": "pendiente", "texto": "Comparar seguros de hogar antes de renovar", "color": "s6",
                    "vence": _dia(*_suma_meses(Y, hoy.month, 2), 1).isoformat()},
                   {"id": "t2", "col": "pendiente", "texto": "Pedir presupuesto para cambiar las ventanas"},
                   {"id": "t3", "col": "pendiente", "texto": "Rebalancear la cartera (ver la nota)", "color": "s2",
                    "vence": _dia(Y, 12, 31).isoformat()},
                   {"id": "t4", "col": "en-marcha", "texto": "Vender el trastero", "color": "s14"},
                   {"id": "t5", "col": "en-marcha", "texto": "Reunir los papeles de la renta", "color": "s8"},
                   {"id": "t6", "col": "hecho", "texto": "Cambiar la tarifa de la luz"},
                   {"id": "t7", "col": "hecho", "texto": "Abrir la cuenta remunerada", "color": "s2"}]}

    # ---- configuración ----
    gasto = "gasto"
    categorias = [{"nombre": n, "tipo": "ingreso"} for n in
                  ("Nómina", "Alquiler piso Valencia", "Alquiler garaje", "Intereses y dividendos", "Otros ingresos")]
    for n, pres in (("Vivienda", 820), ("Alimentación", 600), ("Suministros", 230), ("Transporte", 140),
                    ("Préstamos", None), ("Ocio y restaurantes", 220), ("Suscripciones", 70),
                    ("Compras y ropa", 120), ("Salud", 40), ("Vacaciones y viajes", None), ("Regalos", None),
                    ("Seguros", None), ("Impuestos", None), ("Gastos piso Valencia", None),
                    ("Gastos garaje", None), ("Gastos trastero", None)):
        c = {"nombre": n, "tipo": gasto}
        if pres:
            c["presupuesto"] = pres
        categorias.append(c)
    def q(tipo, imp, cat, tit, nota):   # plantilla de apunte recurrente
        return {"tipo": tipo, "importe": round(imp, 2), "categoria": cat, "titular": tit, "nota": nota}
    config = {
        "colchon": 6000, "titularDefecto": "Común",
        "objetivos": {"fondo": 0.42, "etf": 0.11, "accion": 0.04, "cripto": 0.01, "commodity": 0.05,
                      "bono": 0.03, "pension": 0.11, "otro": 0.04, "crowdfunding": 0.01, "efectivo": 0.18},
        "umbralConcentracion": 0.5, "desviacionMax": 0.05, "diasAviso": 90, "diasSinAnotar": 30,
        "diasSinActualizar": 90, "papeleraMax": 5, "avisoAgendaDias": 7, "inflacion": 0.025,
        "tasaRetirada": 0.04, "archivadosEnPanel": True,
        "monedas": [{"codigo": "USD", "tipo": 0.92}],
        "tipos": [{"id": "crowdfunding", "nombre": "Crowdfunding"}],
        "categorias": categorias,
        "dimensiones": [{"id": "clase-de-activo", "nombre": "Clase de activo",
                         "valores": ["Renta variable", "Renta fija", "Liquidez", "Alternativos", "Inmuebles"]},
                        {"id": "geografia", "nombre": "Geografía",
                         "valores": ["Global", "Europa", "EEUU", "Emergentes", "España"]}],
        "dimensionesFlujos": [{"id": "naturaleza", "nombre": "Naturaleza",
                               "valores": ["Fijo", "Variable", "Extraordinario"]}],
        "entidades": ["Banco principal", "Banco online", "Tarjeta de crédito"],
        "reglasCategoria": [{"palabra": "supermercado", "categoria": "Alimentación"},
                            {"palabra": "gasolinera", "categoria": "Transporte"},
                            {"palabra": "luz", "categoria": "Suministros"},
                            {"palabra": "farmacia", "categoria": "Salud"},
                            {"palabra": "ana martin", "categoria": "Alquiler piso Valencia"}],
        "recurrentes": [q("ingreso", 2350 * 1.03 ** 3, "Nómina", "Yo", "Nómina"),
                        q("ingreso", 2050 * 1.03 ** 3, "Nómina", "Mi pareja", "Nómina"),
                        q("gasto", q_casa, "Vivienda", "Común", "Hipoteca de casa"),
                        q("gasto", 70, "Vivienda", "Común", "Comunidad"),
                        q("gasto", 58, "Suministros", "Común", "Fibra y móvil"),
                        q("gasto", q_coche, "Préstamos", "Común", "Cuota del coche")],
    }
    apartados = [
        {"id": "a1", "nombre": "Reserva para la renta", "importe": 1800, "finalidad": "Pagar el IRPF de este año",
         "titular": "Común", "fechaPrevista": _dia(Y + (1 if hoy.month > 6 else 0), 6, 30).isoformat()},
        {"id": "a2", "nombre": "Vacaciones de verano", "importe": 1500, "finalidad": "Viaje de agosto",
         "titular": "Común", "fechaPrevista": _dia(Y + (1 if hoy.month > 7 else 0), 8, 1).isoformat()},
        {"id": "a3", "nombre": "Fianza de Ana (a devolver)", "importe": 1560,
         "finalidad": "Devolverla cuando termine el contrato", "titular": "Común",
         "fechaPrevista": fin_ana.isoformat(), "nota": "Dinero de la inquilina: no es nuestro."},
        {"id": "a4", "nombre": "Derrama de la comunidad", "importe": 650, "finalidad": "Arreglo de la fachada",
         "titular": "Común", "fechaPrevista": (hoy + dt.timedelta(days=120)).isoformat()},
    ]
    for n, a in enumerate(apartados, 1):
        a["slot"] = n
    # Alertas de precio: una cumplida (el crowdfunding bajó de 2.000 €) y otra vigilando.
    ref_f = g.fecha(-1, 3)
    alertas = [{"id": "al1", "producto": "crowdfunding", "condicion": "menor", "valor": 2000,
                "nota": "Si baja de 2.000 €, plantear la salida"},
               {"id": "al2", "producto": "world", "condicion": "cae", "valor": 0.15,
                "ref": round(g.precio("world", ref_f), 4), "refFecha": ref_f.isoformat(),
                "nota": "Si cae un 15 %, aportación extra"}]

    cfg = {
        "version": 1, "titular": "Patrimonio de ejemplo", "titulares": list(TITULARES),
        "productos": productos, "movimientos": g.movs, "valoraciones": g.vals,
        "comparador": [{"id": "real", "nombre": "Mi cartera real", "real": True},
                       {"id": "world100", "nombre": "100 % MSCI World", "pesos": {"world": 100}},
                       {"id": "mix8020", "nombre": "80/20 Mundo-Emergentes", "pesos": {"world": 80, "emergentes": 20}},
                       {"id": "conbtc", "nombre": "70/20/10 con bitcoin",
                        "pesos": {"world": 70, "emergentes": 20, "bitcoin": 10}}],
        "hitos": [10000, 25000, 50000, 100000, 150000, 250000, 500000],
        "objetivo": {"activo": True, "importe": 100000, "etiqueta": "Próximo objetivo"},
        "apartados": apartados, "alertasPrecio": alertas, "flujos": g.flujos, "inmuebles": inmuebles,
        "notas": notas, "cuadernos": cuadernos, "recordatorios": recordatorios, "tablero": tablero,
        "biblioteca": {"carpetas": carpetas, "archivos": archivos, "papelera": papelera},
        "config": config,
    }
    for _sub, _archivo, datos, a in _documentos(cfg):   # el tamaño real de cada PDF
        a["tam"] = len(datos)
    for n in cfg["notas"]:   # forma que guarda almacen.guarda_notas
        n.setdefault("editada", "")
        n.setdefault("fijada", False)
        n.setdefault("etiquetas", [])
        if n.get("vinculos"):
            n["vinculo"] = n["vinculos"][0]
    return cfg, not g.aprox
