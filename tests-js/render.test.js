// Tests de frontend con jsdom: cargan graficos.js y app.js en un DOM real (el de
// index.html) con un DATOS realista y comprueban que el panel y cada vista se
// dibujan SIN errores. Cazan fallos de render como los de fV o `cambio`.
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");

const RAIZ = path.join(__dirname, "..");
const leer = p => fs.readFileSync(path.join(RAIZ, p), "utf8");
// Quitamos los <script> propios del HTML: en el test inyectamos nosotros
// graficos.js y app.js, y así el cargador del HTML no interfiere.
const HTML = leer("app/web/index.html").replace(/<script[\s\S]*?<\/script>/gi, "");
const GRAFICOS = leer("app/web/graficos.js");
const APP = leer("app/web/app.js");
const DATOS = fs.readFileSync(path.join(__dirname, "fixtures", "datos.json"), "utf8");

function montaPanel(datos) {
  const errores = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", e => errores.push(e.detail || e));
  const dom = new JSDOM(HTML, {
    runScripts: "dangerously", virtualConsole: vc, pretendToBeVisual: true, url: "http://localhost/",
  });
  const { window } = dom;
  window.fetch = () => Promise.resolve({ ok: false, json: () => Promise.resolve({}) });
  window.scrollTo = () => {};
  if (!window.matchMedia) window.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
  const inyecta = code => {
    const s = window.document.createElement("script");
    s.textContent = code;           // inline: se ejecuta en el contexto del window
    window.document.body.appendChild(s);
  };
  inyecta(GRAFICOS);                 // define window.G
  inyecta("window.DATOS = " + (datos || DATOS) + ";");
  inyecta(APP);                      // ejecuta el panel (registra jsdomError si peta)
  return { window, errores };
}

test("el panel se dibuja sin errores y con cifras", () => {
  const { window, errores } = montaPanel();
  assert.strictEqual(errores.length, 0, "errores al cargar: " + errores.join(" | "));
  const hero = window.document.getElementById("heroCifra").textContent.trim();
  assert.ok(hero && hero !== "—", "el patrimonio del hero debería tener valor, es: " + hero);
});

test("el control de periodo aparece con los selectores de fecha", () => {
  const { window, errores } = montaPanel();
  const desde = window.document.getElementById("inpDesde");
  const hasta = window.document.getElementById("inpHasta");
  const ver = window.document.getElementById("btnVerPeriodo");
  assert.ok(desde && hasta && ver, "deberían existir los selectores desde/hasta y el botón Ver");
  // Hay presets de rango (1M, 3M, …).
  assert.ok(window.document.querySelectorAll(".periodoPresets button").length >= 4);
  assert.strictEqual(errores.length, 0, "sin errores: " + errores.join(" | "));
});

test("el informe fiscal se dibuja con ventas y rendimientos", () => {
  const { window, errores } = montaPanel();
  window.document.querySelector('#subtabs button[data-pv="fiscal"]').click();
  const cont = window.document.getElementById("fiscalContenido");
  assert.ok(/patrimoniales/i.test(cont.innerHTML), "debería listar ganancias/pérdidas");
  assert.ok(/capital mobiliario/i.test(cont.innerHTML), "debería listar rendimientos");
  assert.ok(window.document.getElementById("selAnioFisc"), "debería haber selector de año");
  assert.strictEqual(errores.length, 0, "sin errores: " + errores.join(" | "));
});

test("un nombre con HTML malicioso se escapa y no se ejecuta (XSS)", () => {
  // Metemos un payload en el nombre de un producto y en el titular. El panel
  // debe mostrarlo como TEXTO, nunca crear un <img onerror> que ejecute código.
  const d = JSON.parse(DATOS);
  const payload = '<img src=x onerror="window.__xss=1">';
  if (d.productos && d.productos[0]) {
    d.productos[0].nombre = payload; d.productos[0].corto = payload; d.productos[0].papel = payload;
    d.productos[0].entidad = payload; d.productos[0].gestora = payload;   // campos de la ficha
  }
  if (d.total) d.total.titular = payload;
  d.titular = payload;
  d.avisos = [payload];            // también los avisos del motor
  const { window, errores } = montaPanel(JSON.stringify(d));
  // Pasa por las vistas que pintan nombre de producto (rentabilidad) y la ficha.
  window.document.querySelector('#subtabs button[data-pv="rentabilidad"]').click();
  // Abre la ficha de un producto (entidad/gestora van en ella).
  const chip = window.document.querySelector("#chips button");
  if (chip) chip.click();
  assert.strictEqual(window.__xss, undefined, "el onerror NO debería ejecutarse");
  // No debe existir una imagen real inyectada desde ningún nombre/campo.
  const imgs = [...window.document.querySelectorAll("img")].filter(i => i.getAttribute("src") === "x");
  assert.strictEqual(imgs.length, 0, "no debería crearse el <img> del payload");
  // Y el texto escapado sí aparece en el HTML.
  assert.ok(/&lt;img/.test(window.document.body.innerHTML), "el texto debería aparecer escapado");
  assert.strictEqual(errores.length, 0, "sin errores: " + errores.join(" | "));
});

test("la tabla de variación (ahora / 1 mes / 12 meses) se dibuja", () => {
  const { window, errores } = montaPanel();
  const cont = window.document.getElementById("hogarVariacion");
  assert.ok(cont, "debería existir el contenedor de variación");
  assert.ok(/Cómo ha cambiado/.test(cont.innerHTML), "debería mostrar el título de variación");
  assert.ok(cont.querySelector("table"), "debería dibujar la tabla de variación");
  assert.strictEqual(errores.length, 0, "sin errores: " + errores.join(" | "));
});

test("la card de bienvenida aparece la primera vez y se cierra al aceptar", () => {
  const { window, errores } = montaPanel();
  const dlg = window.document.getElementById("bienvenida");
  assert.ok(dlg, "debería existir la card de bienvenida");
  assert.ok(dlg.hasAttribute("open") || dlg.open, "debería mostrarse la primera vez");
  window.document.getElementById("bvCerrar").click();
  let flag = null;
  try { flag = window.localStorage.getItem("patrimonio.bienvenida"); } catch (e) { /* jsdom */ }
  assert.strictEqual(flag, "vista", "al aceptar debería marcarse como vista");
  assert.strictEqual(errores.length, 0, "sin errores: " + errores.join(" | "));
});

test("el borrado de cartera pide confirmación (botón bloqueado hasta marcar)", () => {
  const { window, errores } = montaPanel();
  const dlg = window.document.getElementById("dlgBorrarCartera");
  const cb = window.document.getElementById("borrarConfirmo");
  const ok = window.document.getElementById("borrarOk");
  assert.ok(dlg && cb && ok, "debería existir el diálogo de borrado y sus controles");
  assert.strictEqual(ok.disabled, true, "el botón de eliminar empieza bloqueado");
  cb.checked = true; cb.dispatchEvent(new window.Event("change"));
  assert.strictEqual(ok.disabled, false, "al marcar «entiendo», se habilita eliminar");
  assert.strictEqual(errores.length, 0, "sin errores: " + errores.join(" | "));
});

test("la pestaña Ajustes muestra los controles y se aplican", () => {
  const { window, errores } = montaPanel();
  window.document.querySelector('[data-tab="ajustes"]').click();
  const cont = window.document.getElementById("ajustesCont");
  assert.ok(cont.querySelectorAll(".ajusteSeg").length >= 5, "debería haber varios ajustes");
  cont.querySelector('.ajusteSeg[data-pref="ocultar"] button[data-val="1"]').click();
  assert.strictEqual(window.OCULTAR_IMPORTES, true, "ocultar importes debería activarse");
  cont.querySelector('.ajusteSeg[data-pref="texto"] button[data-val="muyGrande"]').click();
  assert.ok(window.document.body.classList.contains("textoMuyGrande"), "debería aplicar texto muy grande");
  assert.strictEqual(errores.length, 0, "sin errores: " + errores.join(" | "));
});

test("imprimir ofrece resumen/detallado y genera el informe", () => {
  const { window, errores } = montaPanel();
  let llamado = 0;
  window.print = () => { llamado++; };
  const b = window.document.getElementById("btnImprimir");
  assert.ok(b, "debería existir el botón de imprimir");
  b.click();   // abre el menú
  const dlg = window.document.getElementById("dlgImpr");
  assert.ok(dlg, "debería abrirse el menú de impresión");
  const resumen = dlg.querySelector('[data-m="resumen"]');
  assert.ok(resumen, "debería haber opción de resumen");
  resumen.click();   // elige resumen -> imprime
  assert.strictEqual(llamado, 1, "al elegir un modo debería llamar a window.print");
  const hoja = window.document.getElementById("hojaInforme");
  assert.ok(/Cartera neta/.test(hoja.innerHTML), "el informe debería tener la cartera neta");
  assert.ok(/Distribución por tipo/.test(hoja.innerHTML), "el informe debería tener la distribución");
  // El detallado añade el informe fiscal.
  window.document.getElementById("btnImprimir").click();
  window.document.querySelector('#dlgImpr [data-m="detalle"]').click();
  assert.ok(/Informe fiscal/.test(hoja.innerHTML), "el detallado debería incluir el informe fiscal");
  assert.strictEqual(errores.length, 0, "no debería haber errores: " + errores.join(" | "));
});

test("cada sub-pestaña del Panel se dibuja sin errores", () => {
  const { window, errores } = montaPanel();
  const botones = [...window.document.querySelectorAll("#subtabs button")];
  assert.ok(botones.length >= 6, "deberían estar las sub-pestañas del Panel");
  for (const b of botones) {
    b.click();
    assert.strictEqual(errores.length, 0, `error al abrir «${b.textContent}»: ` + errores.join(" | "));
  }
});

test("Ingresos y gastos: las 4 sub-vistas y sus segmentos se dibujan sin errores", () => {
  const { window, errores } = montaPanel();
  window.document.querySelector('#subtabs button[data-pv="ingresos"]').click();
  const subs = [...window.document.querySelectorAll("#igNav button")];
  assert.ok(subs.length === 4, "deberían estar Resumen/Categorías/Tendencias/Presupuesto");
  for (const b of subs) {
    b.click();
    assert.strictEqual(errores.length, 0, `error en sub-vista «${b.textContent}»: ` + errores.join(" | "));
  }
  // Segmentos de Categorías (tipo y periodo) y de Tendencias.
  window.document.querySelector('#igNav button[data-ig="categorias"]').click();
  for (const sel of ["#segCatTipo", "#segCatPeriodo"]) {
    for (const b of window.document.querySelectorAll(sel + " button")) b.click();
  }
  window.document.querySelector('#igNav button[data-ig="tendencias"]').click();
  for (const b of window.document.querySelectorAll("#segTendTipo button")) b.click();
  assert.strictEqual(errores.length, 0, "errores en segmentos de ingresos: " + errores.join(" | "));
  // El mapa de calor y la cascada deben haber pintado un SVG.
  assert.ok(window.document.querySelector("#grafHeatmap svg"), "el mapa de calor debería dibujarse");
});

test("Distribución: el toggle Anillo/Mapa no rompe", () => {
  const { window, errores } = montaPanel();
  window.document.querySelector('#subtabs button[data-pv="distribucion"]').click();
  for (const b of window.document.querySelectorAll("#segDistModo button")) b.click();
  assert.ok(window.document.querySelector("#grafTreemap svg") || window.document.querySelector("#grafDonut svg"),
    "debería dibujarse el treemap o el donut");
  assert.strictEqual(errores.length, 0, "errores en el toggle de distribución: " + errores.join(" | "));
});

test("Inmuebles: sin inmuebles se ve el estado vacío", () => {
  const { window, errores } = montaPanel();
  window.document.querySelector('#subtabs button[data-pv="inmuebles"]').click();
  assert.strictEqual(window.document.getElementById("inmVacio").hidden, false, "debería verse el estado vacío");
  assert.strictEqual(window.document.getElementById("tarjetaInmuebles").hidden, true);
  assert.strictEqual(errores.length, 0, "errores: " + errores.join(" | "));
});

test("Inmuebles: KPIs y una tarjeta por inmueble, con su estado y el enlace a la deuda", () => {
  const datos = JSON.parse(DATOS);
  datos.inmuebles = {
    lista: [
      { id: "i1", nombre: "Piso <img src=x onerror=alert(1)>", tipo: "piso", tipoNombre: "Piso", uso: "inversion",
        estado: "alquilado", estadoNombre: "Alquilado", direccion: "C/ Mayor 1", m2: 80, habitaciones: 3,
        compraFecha: "2019-05-10", coste: 165000, valor: 185000, valorFecha: "2026-10-01", valorDeCompra: false,
        plusvalia: 20000, plusvaliaPct: 0.1212, anios: 7.5, neto: 95000,
        hipoteca: { capitalPendiente: 90000, cuota: 650, deudaRef: "hipoteca", deudaNombre: "Hipoteca" } },
      { id: "i2", nombre: "Nuestra casa", tipo: "casa", tipoNombre: "Casa", uso: "habitual", estado: null,
        coste: null, valor: 250000, valorFecha: "2026-09-30", valorDeCompra: false, plusvalia: null,
        hipoteca: null, neto: 250000 },
    ],
    total: { n: 2, nInversion: 1, nHabitual: 1, alquilados: 1, valor: 435000, coste: 165000,
             plusvalia: 20000, plusvaliaPct: 0.1212, hipotecas: 90000, cuotaHipotecas: 650, neto: 345000 },
  };
  const { window, errores } = montaPanel(JSON.stringify(datos));
  const doc = window.document;
  doc.querySelector('#subtabs button[data-pv="inmuebles"]').click();
  assert.strictEqual(errores.length, 0, "errores: " + errores.join(" | "));
  assert.strictEqual(doc.getElementById("tarjetaInmuebles").hidden, false);
  assert.strictEqual(doc.getElementById("inmVacio").hidden, true);
  assert.strictEqual(doc.querySelectorAll("#inmKpis .kpi").length, 5, "los 4 KPIs y el de alquileres");
  const tarjetas = doc.querySelectorAll("#inmTarjetas .inmCard");
  assert.strictEqual(tarjetas.length, 2, "una tarjeta por inmueble");
  assert.match(tarjetas[0].textContent, /Alquilado/);
  assert.match(tarjetas[1].textContent, /Vivienda habitual/);
  assert.ok(tarjetas[0].querySelector('[data-deuda="hipoteca"]'), "la hipoteca enlazada lleva a su deuda");
  assert.ok(!tarjetas[1].querySelector("[data-deuda]"), "sin hipoteca no hay enlace");
  // El nombre se escapa: no se inyecta ninguna imagen.
  assert.strictEqual(doc.querySelector("#inmTarjetas img"), null, "el nombre debería ir escapado");
  // Es una foto fija: el periodo del panel no se muestra.
  assert.ok(doc.getElementById("mesReferencia").classList.contains("ocultoInicio"));
});

// Datos de inmuebles con libro (para la ficha ampliada e Inicio).
function datosConLibro() {
  const datos = JSON.parse(DATOS);
  const meses = ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"];
  const cero = meses.map(() => 0);
  datos.inmuebles = {
    lista: [
      { id: "i1", nombre: "Piso <b>Mayor</b>", tipo: "piso", tipoNombre: "Piso", uso: "inversion", usoNombre: "Inversión",
        estado: "alquilado", estadoNombre: "Alquilado", titular: "Yo", direccion: "C/ Mayor 1", refCatastral: "123ABC",
        valorCatastral: 60000, m2: 80, habitaciones: 3, nota: "Contrato LAU", compraFecha: "2019-05-10", precio: 150000,
        gastosCompra: 15000, coste: 165000, valor: 185000, valorFecha: "2026-10-01", valorDeCompra: false,
        plusvalia: 20000, plusvaliaPct: 0.1212, anios: 7.5, neto: 95000, categorias: ["Alquiler Mayor", "Gastos Mayor"],
        hipoteca: { capitalPendiente: 90000, cuota: 650, tipoInteres: 0.025, fechaFin: "2044-05-10", deudaRef: null },
        rentabilidadNeta: 0.05,
        libro: { categorias: ["Alquiler Mayor", "Gastos Mayor"], n: 2, ingresos12: 900, gastos12: 100, neto12: 800,
          ingresosTotal: 900, gastosTotal: 100, netoTotal: 800, meses,
          serieIngresos: cero.slice(0, 11).concat([900]), serieGastos: cero.slice(0, 11).concat([100]),
          porCategoria: [{ categoria: "Alquiler Mayor", tipo: "ingreso", total: 900, ultimos12: 900, n: 1 },
                         { categoria: "Gastos Mayor", tipo: "gasto", total: 100, ultimos12: 100, n: 1 }],
          apuntes: [{ id: "f2", fecha: "2026-10-05", tipo: "ingreso", importe: 900, categoria: "Alquiler Mayor" },
                    { id: "f3", fecha: "2026-10-02", tipo: "gasto", importe: 100, categoria: "Gastos Mayor" }] } },
    ],
    total: { n: 1, nInversion: 1, nHabitual: 0, alquilados: 1, valor: 185000, coste: 165000, plusvalia: 20000,
             plusvaliaPct: 0.1212, hipotecas: 90000, hipotecasSinEnlace: 90000, cuotaHipotecas: 650, neto: 95000,
             conLibro: 1, ingresos12: 900, gastos12: 100, neto12: 800, costeHabitual12: null,
             patrimonioCartera: 50000, patrimonioHogar: 145000 },
  };
  return datos;
}

test("Inmuebles: la ficha ampliada muestra datos, hipoteca y libro, y vuelve a la lista", () => {
  const { window, errores } = montaPanel(JSON.stringify(datosConLibro()));
  const doc = window.document;
  doc.querySelector('#subtabs button[data-pv="inmuebles"]').click();
  assert.strictEqual(doc.querySelectorAll("#inmKpis .kpi").length, 6, "con libro se añade el cash-flow");
  doc.querySelector("#inmTarjetas .inmCard").click();
  assert.strictEqual(errores.length, 0, "errores: " + errores.join(" | "));
  const ficha = doc.getElementById("inmFicha");
  assert.strictEqual(ficha.hidden, false);
  assert.strictEqual(doc.getElementById("inmLista").hidden, true);
  assert.strictEqual(ficha.querySelector("h2").textContent, "Piso <b>Mayor</b>", "el nombre va escapado");
  assert.strictEqual(ficha.querySelector("h2 b"), null);
  for (const txt of ["123ABC", "Contrato LAU", "Gastos de compra", "Capital pendiente", "Alquiler Mayor", "Rentabilidad neta"])
    assert.ok(ficha.textContent.includes(txt), "la ficha debería mostrar " + txt);
  assert.ok(ficha.querySelector("#inmFichaBarras svg"), "gráfica del libro");
  assert.strictEqual(ficha.querySelectorAll("table")[1].tBodies[0].rows.length, 2, "últimos apuntes");
  // Sin «Mis datos» detrás (como en la web exportada) no hay botón de editar ni documentos.
  assert.strictEqual(ficha.querySelector('[data-f="editar"]'), null);
  assert.strictEqual(doc.getElementById("inmDocs"), null);
  ficha.querySelector('[data-f="volver"]').click();
  assert.strictEqual(doc.getElementById("inmLista").hidden, false);
  assert.strictEqual(ficha.hidden, true);
});

test("Inmuebles: el libro de la ficha se filtra por periodo, también de una fecha a otra", async () => {
  const datos = datosConLibro();
  const lb = datos.inmuebles.lista[0].libro;
  lb.apuntes.push({ id: "f1", fecha: "2024-03-10", tipo: "gasto", importe: 300, categoria: "Gastos Mayor" });
  lb.n = 3;
  const { window, errores } = montaPanel(JSON.stringify(datos));
  const doc = window.document;
  doc.querySelector('#subtabs button[data-pv="inmuebles"]').click();
  doc.querySelector("#inmTarjetas .inmCard").click();
  const kpi = i => doc.querySelectorAll("#inmLibroCuerpo .kpi .v")[i].textContent;
  const boton = et => [...doc.querySelectorAll("#segInmPeriodo button")].find(b => b.textContent === et);
  assert.ok(kpi(1).includes("100"), "12 meses: el gasto viejo no cuenta (" + kpi(1) + ")");
  assert.strictEqual(kpi(3), "2");
  boton("Todo").click();
  assert.ok(kpi(1).includes("400"), "todo: " + kpi(1));
  assert.strictEqual(kpi(3), "3");
  boton("Rango…").click();
  const de = doc.getElementById("inmDesde"), ha = doc.getElementById("inmHasta");
  assert.ok(de && ha, "rango con dos fechas");
  de.value = "2024-01-01"; ha.value = "2024-12-31";
  de.dispatchEvent(new window.Event("change"));
  await new Promise(r => setTimeout(r, 450));
  assert.strictEqual(kpi(3), "1");
  assert.ok(kpi(1).includes("300"), "rango: " + kpi(1));
  assert.strictEqual(doc.getElementById("inmDesde"), de, "los campos de fecha no se rehacen (no se pierde el foco)");
  assert.strictEqual(errores.length, 0, "errores: " + errores.join(" | "));
});

test("Inmuebles: la ficha dibuja la evolución del valor con dos o más fechas", () => {
  const datos = datosConLibro();
  const x = datos.inmuebles.lista[0];
  x.compraFecha = "2020-03-01"; x.precio = 150000;
  x.valoraciones = [{ fecha: "2025-06-01", importe: 180000 }, { fecha: "2026-09-30", importe: 185000 }];
  const { window, errores } = montaPanel(JSON.stringify(datos));
  const doc = window.document;
  doc.querySelector('#subtabs button[data-pv="inmuebles"]').click();
  doc.querySelector("#inmTarjetas .inmCard").click();
  assert.ok(doc.querySelector("#inmEvol svg"), "gráfica de la evolución del valor");
  assert.ok(doc.querySelectorAll("#inmEvol circle.marcador").length >= 3, "marcas de la compra y de cada estimación");
  assert.strictEqual(errores.length, 0, "errores: " + errores.join(" | "));
  // Con una sola fecha (ni compra ni historial) no hay gráfica.
  x.compraFecha = null; x.valoraciones = [{ fecha: "2026-09-30", importe: 185000 }];
  const b = montaPanel(JSON.stringify(datos));
  b.window.document.querySelector('#subtabs button[data-pv="inmuebles"]').click();
  b.window.document.querySelector("#inmTarjetas .inmCard").click();
  assert.strictEqual(b.window.document.getElementById("inmEvol"), null);
});

test("Inmuebles: los chips de categorías filtran el libro de la ficha", () => {
  const datos = datosConLibro();
  const x = datos.inmuebles.lista[0], lb = x.libro;
  const { window, errores } = montaPanel(JSON.stringify(datos));
  const doc = window.document;
  doc.querySelector('#subtabs button[data-pv="inmuebles"]').click();
  doc.querySelector("#inmTarjetas .inmCard").click();
  [...doc.querySelectorAll("#segInmPeriodo button")].find(b => b.textContent === "Todo").click();
  const apuntes = () => doc.querySelectorAll("#inmLibroCuerpo .kpi .v")[3].textContent;
  const chips = [...doc.querySelectorAll("#inmFicha [data-chip]")];
  assert.strictEqual(chips.length, x.categorias.length, "un chip pulsable por categoría");
  assert.strictEqual(apuntes(), String(lb.apuntes.length));
  const cat = chips[0].dataset.chip;
  chips[0].click();
  const n = lb.apuntes.filter(a => a.categoria.toLowerCase() === cat).length;
  assert.strictEqual(apuntes(), String(n), "solo los de " + cat);
  assert.strictEqual(chips[0].getAttribute("aria-pressed"), "true");
  assert.ok(chips[1].classList.contains("apagado"), "los demás se atenúan");
  doc.querySelector("#inmFicha [data-chip-todas]").click();
  assert.strictEqual(apuntes(), String(lb.apuntes.length), "«Todas» vuelve a todo");
  assert.strictEqual(errores.length, 0, "errores: " + errores.join(" | "));
});

test("Ingresos y gastos: el filtro «Inmuebles» oculta (o deja solos) sus apuntes", () => {
  const datos = datosConLibro();
  const mes = datos.flujos.meses[datos.flujos.meses.length - 1];
  const ap = (tipo, importe, categoria, inmueble) => ({ fecha: mes + "-05", tipo, importe, categoria, titular: "", entidad: "Sin entidad", marca: "", inmueble, categorias: {} });
  datos.flujosLista = [ap("ingreso", 900, "Alquiler Mayor", "i1"), ap("ingreso", 2000, "Nómina", ""), ap("gasto", 300, "Comida", "")];
  const { window, errores } = montaPanel(JSON.stringify(datos));
  const doc = window.document;
  doc.querySelector('#subtabs button[data-pv="ingresos"]').click();
  const sel = doc.querySelector('#igFiltros [data-igf="inm"]');
  assert.ok(sel, "hay filtro de inmuebles");
  assert.deepStrictEqual([...sel.options].map(o => o.value), ["", "__sin__", "__con__", "i1"]);
  const kpis = () => doc.getElementById("flujosKpis").textContent;
  assert.ok(/2.?900/.test(kpis()), "sin filtro cuentan todos: " + kpis());
  sel.value = "__sin__"; sel.dispatchEvent(new window.Event("change"));
  assert.ok(/2.?000/.test(kpis()) && !/2.?900/.test(kpis()), "sin los del inmueble: " + kpis());
  const sel2 = doc.querySelector('#igFiltros [data-igf="inm"]');
  sel2.value = "i1"; sel2.dispatchEvent(new window.Event("change"));
  assert.ok(/900/.test(kpis()) && !/2.?000/.test(kpis()), "solo el piso: " + kpis());
  assert.strictEqual(window.localStorage.getItem("patrimonio.igInm"), "i1", "se recuerda");
  doc.getElementById("igQuitar").click();
  assert.ok(/2.?900/.test(kpis()));
  assert.strictEqual(errores.length, 0, "errores: " + errores.join(" | "));
});

test("Inmuebles: renta y rentabilidad bruta; sin «Mis datos» solo cifras del alquiler; aviso que abre la ficha", () => {
  const datos = datosConLibro();
  const x = datos.inmuebles.lista[0];
  x.alquiler = { inquilinos: 1, contratos: 2, vigentes: 1, rentaMensual: 750, proximoFin: "2030-07-31" };
  x.rentabilidadBruta = 0.0545; x.ocupado = true;
  Object.assign(datos.inmuebles.total, { rentaMensual: 750, ocupacion: 1, rentabilidadBruta: 0.0545 });
  datos.alertas = [{ texto: "No hay ningún cobro del alquiler de «Piso Mayor».", n: "Sin cobrar", nivel: "aviso", pv: "inmuebles",
    clave: "inm-cobro-pendiente", destino: { tab: "inmuebles", inmueble: "i1" } }];
  const { window, errores } = montaPanel(JSON.stringify(datos));
  const doc = window.document;
  const linea = doc.querySelector("#bannerAlertas [data-dest-inm]");
  assert.ok(linea, "el aviso del inmueble es clicable");
  linea.click();
  const ficha = doc.getElementById("inmFicha");
  assert.strictEqual(ficha.hidden, false, "el aviso abre la ficha");
  const t = ficha.textContent;
  for (const s of ["Renta mensual", "750", "Rentabilidad bruta", "5,45", "Inquilinos y contratos", "Contratos vigentes", "31"])
    assert.ok(t.includes(s), "la ficha debería mostrar " + s);
  assert.strictEqual(doc.getElementById("inmInq"), null, "sin editor no hay lista de inquilinos (ni sus datos)");
  ficha.querySelector('[data-f="volver"]').click();
  assert.ok(doc.getElementById("inmKpis").textContent.includes("ocupación 100"), doc.getElementById("inmKpis").textContent);
  assert.strictEqual(errores.length, 0, "errores: " + errores.join(" | "));
});

test("Inicio: bloque de inmuebles (sin el total, que va arriba); sin inmuebles, una invitación", () => {
  let { window, errores } = montaPanel(JSON.stringify(datosConLibro()));
  window.document.querySelector('#subtabs button[data-pv="inicio"]').click();
  assert.strictEqual(errores.length, 0, "errores: " + errores.join(" | "));
  const bloque = window.document.querySelector(".megaInm");
  assert.ok(bloque && /Neto inmobiliario/.test(bloque.textContent) && bloque.textContent.includes("95.000"));
  assert.ok(!/Patrimonio del hogar/.test(bloque.textContent), "el total ya no se repite aquí");
  assert.strictEqual(bloque.querySelectorAll(".iiFila").length, 1);
  ({ window, errores } = montaPanel());
  window.document.querySelector('#subtabs button[data-pv="inicio"]').click();
  assert.ok(window.document.querySelector(".megaInm.vacia"), "sin inmuebles: invitación a la zona");
});

test("Inicio: la card «Tu patrimonio» suma cartera + inmuebles netos, arriba del todo (ADR 0033)", () => {
  const ver = datos => {
    const { window, errores } = montaPanel(datos && JSON.stringify(datos));
    window.document.querySelector('#subtabs button[data-pv="inicio"]').click();
    assert.strictEqual(errores.length, 0, "errores: " + errores.join(" | "));
    const card = window.document.querySelector("#inicioCuerpo > .inicioTotal");
    assert.ok(card, "debería haber card de patrimonio total");
    assert.strictEqual(window.document.querySelector("#inicioCuerpo").firstElementChild, card, "va la primera");
    return { window, card };
  };
  // Con inmuebles: 50.000 de cartera + 95.000 de inmuebles netos = 145.000.
  let { window, card } = ver(datosConLibro());
  assert.ok(card.querySelector(".ptCifra").textContent.includes("145.000"), card.textContent);
  const filas = [...card.querySelectorAll(".ptFila")];
  assert.strictEqual(filas.length, 2);
  assert.ok(/Cartera neta/.test(filas[0].textContent) && filas[0].textContent.includes("50.000"));
  assert.ok(/Inmuebles netos/.test(filas[1].textContent) && filas[1].textContent.includes("95.000"));
  assert.ok(card.querySelector(".ptBarra"), "barra del reparto");
  filas[1].click();
  assert.strictEqual(window.document.querySelector('#subtabs button[data-pv="inmuebles"]').getAttribute("aria-selected"), "true");
  // Hipoteca enlazada a una deuda de la cartera: va con su inmueble y se le devuelve a la
  // cartera; el total es el del motor, sin restarla dos veces.
  const enl = datosConLibro();
  Object.assign(enl.inmuebles.total, { hipotecasSinEnlace: 0, patrimonioHogar: 235000 });
  ({ card } = ver(enl));
  assert.ok(card.querySelector(".ptCifra").textContent.includes("235.000"));
  assert.ok(card.querySelectorAll(".ptFila")[0].textContent.includes("140.000"), card.textContent);
  assert.ok(/la hipoteca va con su inmueble/.test(card.textContent));
  // Sin inmuebles: el patrimonio es la cartera, con una invitación a añadirlos.
  ({ window, card } = ver());
  assert.ok(!card.querySelector(".ptBarra"));
  assert.ok(/Añade tus inmuebles/.test(card.textContent));
  // La pestaña ahora se llama «Cartera» (su id interno sigue siendo «patrimonio»).
  assert.strictEqual(window.document.querySelector('#subtabs button[data-pv="patrimonio"]').textContent, "Cartera");
});

test("web exportada con «ocultar importes»: ninguna preferencia vuelve a mostrar cantidades", () => {
  const datos = JSON.parse(DATOS);
  const errores = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", e => errores.push(e.detail || e));
  const dom = new JSDOM(HTML, { runScripts: "dangerously", virtualConsole: vc, pretendToBeVisual: true, url: "http://localhost/" });
  const { window } = dom;
  window.fetch = () => Promise.resolve({ ok: false, json: () => Promise.resolve({}) });
  window.scrollTo = () => {};
  if (!window.matchMedia) window.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
  window.localStorage.setItem("patrimonio.ocultar", "0");   // quien la abre tenía «mostrar importes»
  const s = c => { const e = window.document.createElement("script"); e.textContent = c; window.document.body.appendChild(e); };
  s("window.ESTATICO = true; window.OCULTAR_IMPORTES = true;");
  s(GRAFICOS);
  s("window.DATOS = " + JSON.stringify(datos) + ";");
  s(APP);
  assert.strictEqual(window.OCULTAR_IMPORTES, true);
  assert.strictEqual(window.document.getElementById("heroCifra").textContent.trim(), "•••");
});

test("los modos de los gráficos (segmentos) no rompen", () => {
  const { window, errores } = montaPanel();
  // Evolución: modos del gráfico principal (incluye «Reparto %») y mes/año.
  window.document.querySelector('#subtabs button[data-pv="evolucion"]').click();
  for (const sel of ["#segVista", "#segPeriodo"]) {
    for (const b of window.document.querySelectorAll(sel + " button")) b.click();
  }
  // Distribución: por clase/producto/entidad/tipo.
  window.document.querySelector('#subtabs button[data-pv="distribucion"]').click();
  for (const b of window.document.querySelectorAll("#segDist button")) b.click();
  assert.strictEqual(errores.length, 0, "errores en segmentos: " + errores.join(" | "));
});

test("las funciones de gráfico dibujan un SVG sin lanzar", () => {
  const { window } = montaPanel();
  const G = window.G;
  const div = () => { const d = window.document.createElement("div"); window.document.body.appendChild(d); return d; };
  const fechas = ["2024-01-31", "2024-02-29", "2024-03-31"];
  const serie = [{ nombre: "A", color: "#2a78d6", valores: [1, 2, 3] },
                 { nombre: "B", color: "#eb6834", valores: [2, 1, 0] }];
  let d;
  d = div(); G.barrasApiladas(d, { categorias: fechas, series: serie, alto: 200 });
  assert.ok(d.querySelector("svg"), "barrasApiladas debería dibujar un SVG");
  d = div(); G.multiLinea(d, { fechas, series: serie, alto: 200 });
  assert.ok(d.querySelector("svg"), "multiLinea debería dibujar un SVG");
  d = div(); G.areaApilada(d, { fechas, series: serie, alto: 200 });
  assert.ok(d.querySelector("svg"), "areaApilada debería dibujar un SVG");
  d = div(); G.donut(d, { datos: [{ nombre: "A", valor: 3, color: "#2a78d6" }, { nombre: "B", valor: 1, color: "#eb6834" }], alto: 200 });
  assert.ok(d.querySelector("svg"), "donut debería dibujar un SVG");

  // Área apilada CON una serie negativa (deuda): no debe romperse y debe pintar la
  // línea del cero, con la banda negativa por debajo del eje.
  const conDeuda = [{ nombre: "Activo", color: "#2a78d6", valores: [100, 120, 140] },
                    { nombre: "Deuda", color: "#e34948", valores: [-40, -35, -30] }];
  d = div(); G.areaApilada(d, { fechas, series: conDeuda, alto: 200, overlay: { nombre: "Aportado", valores: [80, 90, 100] } });
  assert.ok(d.querySelector("svg"), "areaApilada con negativos debería dibujar un SVG");
  assert.ok(d.querySelector(".ejeCero"), "con negativos debería pintar la línea del cero");

  // multiLinea con «desdeCero» pero una serie negativa (ahorro del mes cuando se gasta
  // más de lo que se ingresa): el eje debe BAJAR por debajo de 0, no recortarse en 0
  // dejando la línea fuera de la gráfica por abajo.
  const conAhorroNeg = [{ nombre: "Ingresos", color: "#2a78d6", valores: [1000, 900, 800] },
                        { nombre: "Gastos", color: "#eb6834", valores: [700, 950, 1100] },
                        { nombre: "Ahorro", color: "#2a78d6", valores: [300, -50, -300], destacado: true }];
  d = div(); G.multiLinea(d, { fechas, series: conAhorroNeg, alto: 200, desdeCero: true });
  assert.ok(d.querySelector("svg"), "multiLinea con negativos debería dibujar un SVG");
  assert.ok(d.querySelector(".ejeCero"), "con ahorro negativo y desdeCero debería pintar la línea del cero");
  const etiqY = [...d.querySelectorAll(".ejeY")].map(t => t.textContent);
  assert.ok(etiqY.some(s => /^-/.test(s.trim())), "el eje Y debería mostrar algún valor negativo: " + etiqY.join(", "));
});
