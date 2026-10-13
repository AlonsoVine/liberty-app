/* ============================================================
   editor.js  ·  Pestaña «Mis datos»: productos, movimientos y
   saldos. Todo se guarda en mis_datos a través del servidor.
   ============================================================ */
(function () {
  "use strict";

  const $ = s => document.querySelector(s);
  const D = window.DATOS;
  const SOLO_SALDO = ["efectivo", "deuda"];
  const NCOLORES = 24;   // tantos como colores hay en la paleta (var --s1…--s24)
  const E = { cfg: null, modo: "demo", tipos: {}, fuentes: {}, tiposMov: {}, vista: "activos", filtro: "todos", tablas: {} };

  /* ---------------------------------------------- utilidades */
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const eur = v => v == null ? "—" : Number(v).toLocaleString("es-ES", { style: "currency", currency: "EUR" });
  const num = (v, d = 4) => v == null ? "—" : Number(v).toLocaleString("es-ES", { maximumFractionDigits: d });
  const fecha = iso => iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}` : "—";
  const hoy = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 10); };
  const leeNum = t => {
    t = String(t || "").replace(/[€\s]/g, "");
    // "1.234,56" y "1.000" (mil) en castellano; "1234.5" también vale.
    if (t.includes(",") || /^-?\d{1,3}(\.\d{3})+$/.test(t)) t = t.replace(/\./g, "").replace(",", ".");
    return parseFloat(t);
  };
  const nombre = p => p ? (p.corto || p.nombre) : "¿?";
  const prod = id => E.cfg.productos.find(p => p.id === id);
  const soloSaldo = p => SOLO_SALDO.includes(p.tipo);
  const manual = p => p.fuente === "manual" || soloSaldo(p);
  const opciones = (obj, sel) => Object.entries(obj)
    .map(([k, v]) => `<option value="${esc(k)}"${k === sel ? " selected" : ""}>${esc(v)}</option>`).join("");
  const recuerda = {
    lee(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    guarda(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* da igual */ } },
  };
  E.vista = new URLSearchParams(location.search).get("vista") || recuerda.lee("patrimonio.editor") || "activos";
  if (!["activos", "deudas", "apartados", "flujos", "saldos", "config", "importar", "copias"].includes(E.vista)) E.vista = "activos";

  async function api(metodo, url, cuerpo) {
    const r = await fetch(url, {
      method: metodo, headers: { "Content-Type": "application/json" },
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
    });
    let j = {};
    try { j = await r.json(); } catch (e) { /* respuesta vacía */ }
    if (!r.ok || j.ok === false) throw new Error((j.errores || [j.error || "Algo ha fallado. ¿Sigue abierta la ventana negra de la app?"]).join("\n"));
    return j;
  }
  async function carga() {
    const j = await api("GET", "api/cartera");
    Object.assign(E, { cfg: j.cartera, modo: j.modo, tipos: j.tipos, tiposBase: j.tiposBase || {}, avisosCatalogo: j.avisosCatalogo || [], marcas: j.marcas || [], fuentes: j.fuentes, tiposMov: j.tiposMovimiento, tiposFlujo: j.tiposFlujo });
  }
  async function guarda(coleccion, datos) {
    const j = await api("POST", "api/" + coleccion, datos);
    E.cfg = j.cartera;
    COP.lista = null;   // hay una copia automática nueva
    window.EDITOR_SUCIO = true;
    avisa(j.avisos);
    if (window.toast) window.toast("Guardado ✓");
    return j.item;
  }
  async function borra(coleccion, id) {
    const j = await api("DELETE", `api/${coleccion}/${encodeURIComponent(id)}`);
    E.cfg = j.cartera;
    COP.lista = null;
    window.EDITOR_SUCIO = true;
    if (window.toast) window.toast("Borrado ✓");
  }
  function avisa(avisos) {
    const el = $("#edAvisos");
    if (el) el.innerHTML = (avisos || []).map(a => `<div class="av"><span>⚠</span><span>${esc(a)}</span></div>`).join("");
  }

  /* ---------------------------------------------- ventana modal */
  function abreModal(titulo, cuerpo, alGuardar, textoBoton = "Guardar") {
    const dlg = $("#modal");
    dlg.innerHTML = `<form class="mForm" novalidate>
      <header><h2>${titulo}</h2><button type="button" class="x" data-cerrar aria-label="Cerrar">×</button></header>
      <div class="mCuerpo">${cuerpo}</div>
      <div class="mErr" hidden></div>
      <footer><button type="button" class="btn" data-cerrar>Cancelar</button>
        <button type="submit" class="btn prim">${textoBoton}</button></footer></form>`;
    const f = dlg.querySelector("form");
    dlg.querySelectorAll("[data-cerrar]").forEach(b => { b.onclick = () => dlg.close(); });
    f.onsubmit = async e => {
      e.preventDefault();
      const btn = f.querySelector("[type=submit]"), err = f.querySelector(".mErr");
      btn.disabled = true;
      err.hidden = true;
      try {
        const siguiente = await alGuardar(f);
        dlg.close();
        pinta();
        if (typeof siguiente === "function") siguiente();
      } catch (x) {
        err.textContent = x.message;
        err.hidden = false;
      } finally { btn.disabled = false; }
    };
    dlg.showModal();
    return f;
  }
  const campos = f => Object.fromEntries(new FormData(f).entries());
  function rellena(f, obj) {
    Object.entries(obj).forEach(([k, v]) => {
      const el = f.elements[k];
      if (!el || v == null) return;
      if (el.type === "checkbox") el.checked = !!v;
      else if (el instanceof RadioNodeList) el.value = String(v);
      else el.value = v;
    });
  }

  // Editor de lista en filas (para titulares y tipos propios): cada fila es un input
  // con botón de quitar, más un botón de añadir. Guarda en data-de el valor original
  // de cada fila, para poder detectar renombrados al guardar. Se lee luego recorriendo
  // las .inEdit del contenedor (no usan name, así no entran en el FormData del modal).
  function montaFilasEdit(cont, valores, ph, etiquetaNuevo, opts) {
    opts = opts || {};
    const conDef = "defecto" in opts;   // muestra un radio «por defecto» por fila
    const fila = (v, def) => `<div class="filaEdit">
      ${conDef ? `<label class="defRadio" title="Marcar como por defecto"><input type="radio" name="${esc(cont.id)}_def" class="inDef"${def ? " checked" : ""}><span>por defecto</span></label>` : ""}
      <input class="inEdit" value="${esc(v)}" data-de="${esc(v)}" placeholder="${esc(ph)}" autocomplete="off">
      <button type="button" class="btn mini filaX" data-quita aria-label="Quitar">✕</button></div>`;
    cont.innerHTML = `<div class="filasEdit">${valores.map(v => fila(v, conDef && v === opts.defecto)).join("")}</div>
      <button type="button" class="btn mini" data-add>+ ${esc(etiquetaNuevo)}</button>`;
    const lista = cont.querySelector(".filasEdit");
    cont.querySelector("[data-add]").onclick = () => {
      lista.insertAdjacentHTML("beforeend", fila("", false));
      const ins = lista.querySelectorAll(".inEdit");
      ins[ins.length - 1].focus();
    };
    lista.onclick = e => { const q = e.target.closest("[data-quita]"); if (q) q.closest(".filaEdit").remove(); };
  }
  const leeFilasEdit = cont => [...cont.querySelectorAll(".inEdit")]
    .map(i => ({ de: i.dataset.de || "", a: i.value.trim() }));
  const leeFilaDefecto = cont => {
    const r = [...cont.querySelectorAll(".filaEdit")].find(x => { const d = x.querySelector(".inDef"); return d && d.checked; });
    return r ? r.querySelector(".inEdit").value.trim() : "";
  };

  /* ---------------------------------------------- empezar con mis datos */
  function empezar() {
    const f = abreModal("Empezar con mis datos", `
      <p>Ahora estás viendo un patrimonio de ejemplo. ¿Cómo quieres empezar el tuyo?</p>
      <label class="opcion"><input type="radio" name="desde" value="vacia" checked>
        <span><b>Empezar de cero</b><br>Un patrimonio vacío para meter lo tuyo.</span></label>
      <label class="opcion"><input type="radio" name="desde" value="ejemplo">
        <span><b>Copiar el ejemplo para practicar</b><br>Puedes tocar, añadir y borrar sin miedo.
        Cuando quieras empezar de verdad, borra sus productos.</span></label>
      <p class="ayuda">Tus datos se guardan solo en tu ordenador, en la carpeta <code>mis_datos</code>.</p>`,
    async f => {
      await api("POST", "api/empezar", { desde: campos(f).desde });
      recuerda.guarda("patrimonio.tab", "datos");
      location.reload();
    }, "Empezar");
    return f;
  }
  function reiniciar() {
    abreModal("Empezar de nuevo", `
      <p>¿Qué quieres hacer con el patrimonio que tienes ahora?</p>
      <label class="opcion"><input type="radio" name="a" value="vacia" checked>
        <span><b>Empezar de cero</b><br>Un patrimonio vacío para meter lo tuyo.</span></label>
      <label class="opcion"><input type="radio" name="a" value="demo">
        <span><b>Volver a ver el patrimonio de ejemplo</b><br>Luego podrás empezar otra vez con «Empezar con mis datos».</span></label>
      <p class="ayuda">No se pierde nada: tu patrimonio actual se guarda en <code>mis_datos/copias</code> por si quieres recuperarla.</p>`,
    async f => {
      await api("POST", "api/reiniciar", { a: campos(f).a });
      recuerda.guarda("patrimonio.tab", "datos");
      location.reload();
    }, "Continuar");
  }
  function soloPropio(fn) {
    return (...a) => (E.modo === "demo" ? empezar() : fn(...a));
  }

  /* ---------------------------------------------- buscar y ordenar en tablas */
  // Estas utilidades trabajan sobre las filas ya pintadas (no vuelven a pedir datos):
  // filtran u ordenan el DOM en el sitio. El estado (búsqueda y orden) se guarda por
  // tabla en E.tablas para que sobreviva a los re-render de pinta().
  const _norm = s => String(s == null ? "" : s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  function _clave(txt) {
    const t = String(txt || "").trim();
    const m = t.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);          // fecha dd/mm/aaaa
    if (m) return { n: true, v: +(m[3] + m[2] + m[1]) };
    const limpio = t.replace(/[€%\s]/g, "").replace(/−/g, "-").replace(/\./g, "").replace(",", ".");
    if (limpio !== "" && /\d/.test(limpio) && !isNaN(Number(limpio))) return { n: true, v: Number(limpio) };
    return { n: false, v: _norm(t) };
  }
  function _compara(a, b) {
    const ca = _clave(a), cb = _clave(b);
    if (ca.n && cb.n) return ca.v - cb.v;
    return String(ca.v).localeCompare(String(cb.v), "es");
  }
  function _tablaDe(bloque) { return bloque.querySelector("table"); }
  function filtraBloque(bloque, q) {
    const tabla = _tablaDe(bloque);
    if (!tabla || !tabla.tBodies[0]) return;
    const nq = _norm(q);
    [...tabla.tBodies[0].rows].forEach(r => {
      r.style.display = (!nq || _norm(r.textContent).includes(nq)) ? "" : "none";
    });
  }
  function ordenaTabla(tabla, col, dir) {
    const tb = tabla.tBodies[0];
    if (!tb) return;
    [...tb.rows]
      .sort((ra, rb) => _compara(
        ra.cells[col] ? ra.cells[col].textContent : "",
        rb.cells[col] ? rb.cells[col].textContent : "") * dir)
      .forEach(r => tb.appendChild(r));
  }
  function marcaFlechas(tabla, col, dir) {
    if (!tabla.tHead) return;
    [...tabla.tHead.rows[0].cells].forEach((th, i) => {
      const vieja = th.querySelector(".flecha");
      if (vieja) vieja.remove();
      if (i === col) {
        const s = document.createElement("span");
        s.className = "flecha";
        s.textContent = dir > 0 ? " ▲" : " ▼";
        th.appendChild(s);
      }
    });
  }
  function aplicaTablas() {
    document.querySelectorAll("[data-tabla]").forEach(bloque => {
      const st = E.tablas[bloque.dataset.tabla];
      const tabla = _tablaDe(bloque);
      const inp = bloque.querySelector("[data-buscar]");
      if (inp && st) inp.value = st.q || "";
      if (!tabla) return;
      if (st && st.q) filtraBloque(bloque, st.q);
      if (st && st.col != null && tabla.tHead) { ordenaTabla(tabla, st.col, st.dir); marcaFlechas(tabla, st.col, st.dir); }
    });
  }
  const _estTabla = key => (E.tablas[key] || (E.tablas[key] = { q: "", col: null, dir: 1 }));
  // Acciones de fila como iconos: lápiz azul = editar, copiar azul = duplicar,
  // papelera roja = borrar. El texto va en title/aria-label (tooltip + accesible).
  const _ICO_ACC = {
    editar: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>',
    duplicar: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
    borrar: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>',
  };
  const _TIT_ACC = { editar: "Editar", duplicar: "Duplicar", borrar: "Borrar" };
  function accBtn(tipo, acc, id) {
    return `<button class="accIco" data-acc="${esc(acc)}" data-id="${esc(id)}" title="${_TIT_ACC[tipo]}" aria-label="${_TIT_ACC[tipo]}">${_ICO_ACC[tipo]}</button>`;
  }
  // Celda de acciones estándar: pasa los nombres de data-acc que existan para esa tabla.
  function celdaAcc(id, { editar, duplicar, borrar } = {}) {
    let h = "";
    if (editar) h += accBtn("editar", editar, id);
    if (duplicar) h += accBtn("duplicar", duplicar, id);
    if (borrar) h += accBtn("borrar", borrar, id);
    return `<td class="acc">${h}</td>`;
  }
  // Indicador «📝» en una entidad (activo/deuda/reservado) que tiene alguna nota
  // asociada: al pulsarlo, abre la pestaña Notas con esa nota. Llama la atención.
  function indicadorNota(ref) {
    return (E.cfg.notas || []).some(n => n.vinculo && n.vinculo.ref === ref)
      ? ` <button class="notaInd" data-acc="verNotas" data-id="${esc(ref)}" title="Tiene una nota — pulsa para verla" aria-label="Ver nota">📝</button>` : "";
  }
  // Caja de búsqueda + tabla ordenable, envuelta con su clave para conservar el estado.
  function envTabla(key, thead, filas, alto, toolsExtra) {
    return `<div class="tablaBloque" data-tabla="${esc(key)}">
      <div class="tablaTools" style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <label class="buscaTabla">${LUPA}<input type="search" data-buscar
          placeholder="Buscar…" aria-label="Buscar en la tabla" autocomplete="off"></label>
        ${toolsExtra || '<span class="ordenaHint">↕ Ordena pulsando una columna</span>'}
        <span class="sp"></span>
        <button type="button" class="btn" data-csv title="Descargar esta tabla en CSV (para Excel)">⤓ CSV</button></div>
      <div class="tablaEnv${alto ? " alto" : ""}"><table class="dt orden"><thead>${thead}</thead>
        <tbody>${filas}</tbody></table></div></div>`;
  }
  // Descarga la tabla visible (respetando búsqueda y orden) como CSV para Excel.
  function descargaTablaCSV(bloque) {
    const tabla = _tablaDe(bloque);
    if (!tabla || !tabla.tHead) return;
    const ths = [...tabla.tHead.rows[0].cells];
    const cols = ths.map((th, i) => ({ i, nombre: th.textContent.replace(/[↕▲▼]/g, "").trim() }))
      .filter(c => c.nombre);                         // se saltan las columnas sin título (acciones)
    const comilla = s => '"' + String(s == null ? "" : s).replace(/"/g, '""') + '"';
    const filas = [cols.map(c => comilla(c.nombre)).join(";")];
    [...(tabla.tBodies[0] ? tabla.tBodies[0].rows : [])]
      .filter(r => r.style.display !== "none")
      .forEach(r => filas.push(cols.map(c => comilla(r.cells[c.i] ? r.cells[c.i].textContent.trim() : "")).join(";")));
    const csv = "﻿" + filas.join("\r\n");          // BOM para que Excel lea los acentos
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = (bloque.dataset.tabla || "tabla") + "_" + new Date().toISOString().slice(0, 10) + ".csv";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  document.addEventListener("click", e => {
    const b = e.target.closest("[data-csv]");
    const bloque = b && b.closest("[data-tabla]");
    if (bloque) descargaTablaCSV(bloque);
  });

  // Listeners únicos (delegados): buscar al teclear y ordenar al pulsar una cabecera.
  document.addEventListener("input", e => {
    const inp = e.target.closest("[data-buscar]");
    const bloque = inp && inp.closest("[data-tabla]");
    if (!bloque) return;
    _estTabla(bloque.dataset.tabla).q = inp.value;
    filtraBloque(bloque, inp.value);
  });
  document.addEventListener("click", e => {
    const th = e.target.closest("table.dt.orden th");
    if (!th || th.classList.contains("nosort") || !th.textContent.trim()) return;
    const tabla = th.closest("table");
    const bloque = th.closest("[data-tabla]");
    const col = th.cellIndex;
    const st = bloque ? _estTabla(bloque.dataset.tabla) : { col: null, dir: 1 };
    st.dir = st.col === col ? -st.dir : 1;
    st.col = col;
    ordenaTabla(tabla, col, st.dir);
    marcaFlechas(tabla, col, st.dir);
    if (bloque) filtraBloque(bloque, st.q);   // mantiene el filtro tras ordenar
  });
  // Estilos propios (se inyectan una vez; usan las variables de tema ya existentes).
  (function estilosTablas() {
    const css = `
      .tablaTools{margin:0 0 10px}
      .buscaTabla{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--borde);
        border-radius:9px;padding:6px 11px;background:var(--sup);max-width:280px;color:var(--tinta3)}
      .buscaTabla input{border:0;background:transparent;font:inherit;font-size:14px;color:var(--tinta);outline:none;width:100%}
      table.dt.orden thead th{cursor:pointer;user-select:none}
      table.dt.orden thead th:not(.nosort):hover{color:var(--tinta)}
      table.dt.orden thead th.nosort{cursor:default}
      table.dt.orden thead th:not(.nosort)::after{content:"↕";margin-left:5px;opacity:.35;font-size:10px}
      table.dt.orden thead th.nosort::after{content:""}
      table.dt.orden thead th:has(.flecha)::after{content:""}
      table.dt.orden thead th .flecha{color:var(--s1);font-size:11px;opacity:1}
      .ordenaHint{color:var(--tinta3);font-size:12px}`;
    const s = document.createElement("style");
    s.textContent = css;
    document.head.appendChild(s);
  })();

  /* ---------------------------------------------- pintado general */
  function pinta() {
    const cont = $("#editor");
    if (!cont) return;
    if (!E.cfg) { cont.innerHTML = '<p class="subt" style="margin-top:24px">Cargando tus datos…</p>'; return; }
    let html = "";
    // En la demo ya se ve arriba el aviso con el botón «Empezar con mis datos».
    if (E.modo !== "demo" && !E.cfg.productos.length && !(E.cfg.config || {}).asistenteOculto) {
      html += `<section class="tarjeta asistente"><header><h2>Empecemos paso a paso</h2>
          <span class="subt">Tu patrimonio está vacío. Haz esto una vez; luego es un ratito al mes.</span></header>
        <ol class="pasosAsist">
          <li><b>1 · Añade lo que tienes.</b> Cuentas del banco, fondos, acciones, cripto, un plan de pensiones, un piso…
            <div class="botones"><button class="btn prim" data-acc="nuevoProducto">+ Añadir un activo</button></div></li>
          <li><b>2 · Añade tus deudas</b> (si las tienes): hipoteca, préstamos, tarjetas.
            <div class="botones"><button class="btn" data-acc="nuevaDeuda">+ Añadir una deuda</button></div></li>
          <li><b>3 · Ajusta tu hogar.</b> Titulares, colchón, categorías de ingresos y gastos.
            <div class="botones"><button class="btn" data-acc="editarConfig">Abrir Configuración</button></div></li>
          <li><b>4 · ¿Tienes muchos datos?</b> Tráelos de golpe (MyInvestor, Excel o con ayuda de una IA).
            <div class="botones"><button class="btn" data-acc="irImportar">Ir a Importar</button></div></li>
        </ol>
        <p class="ayuda">Cuando tengas algo, vuelve a <b>Panel</b> y verás tus cifras.
          <button class="btnLink" data-acc="ocultarAsistente">No mostrar este asistente</button></p></section>`;
    }
    html += `<div class="edBarra"><div class="edVistas" id="edVistas"></div><span class="sp"></span>
      ${!D && E.cfg.productos.length ? '<button class="btn" data-acc="verPanel">Ver mi panel →</button>' : ""}</div>
      <div id="edAvisos" class="avisos"></div><div id="edCuerpo"></div>`;
    cont.innerHTML = html;

    // Tres áreas al mismo nivel pero visualmente distintas: lo que tienes,
    // el día a día (flujos y saldos) y las herramientas.
    const grupos = [
      [["activos", "Activos"], ["deudas", "Deudas"], ["apartados", "Reservados"]],
      [["saldos", "Saldos y movimientos"], ["flujos", "Ingresos y gastos"]],
      [["config", "Configuración"], ["importar", "Importar"], ["copias", "Copias y seguridad"]],
    ];
    const seg = $("#edVistas");
    seg.innerHTML = "";
    grupos.forEach(grupo => {
      const g = document.createElement("div");
      g.className = "segm edGrupo";
      grupo.forEach(([id, et]) => {
        const b = document.createElement("button");
        b.textContent = et;
        b.setAttribute("aria-pressed", String(id === E.vista));
        b.onclick = () => { E.vista = id; recuerda.guarda("patrimonio.editor", id); pinta(); };
        g.appendChild(b);
      });
      seg.appendChild(g);
    });
    $("#edCuerpo").innerHTML = ({ activos: vistaActivos, deudas: vistaDeudas, apartados: vistaApartados,
      flujos: vistaFlujos, saldos: vistaSaldosMov, config: vistaConfig,
      importar: vistaImportar, copias: vistaCopias }[E.vista] || vistaActivos)();
    if (E.vista === "importar" || E.vista === "copias") conectaImportar();
    if (E.vista === "flujos") { montaAnotarRapido(); montaFiltrosFlujos(); }
    const filtro = $("#edFiltro");
    if (filtro) filtro.onchange = e => { E.filtro = e.target.value; pinta(); };
    aplicaTablas();   // restaura búsqueda y orden de cada tabla tras el re-render
  }

  /* ---------------------------------------------- productos */
  function precioDe(p) {
    if (manual(p)) {
      const v = E.cfg.valoraciones.filter(x => x.producto === p.id).sort((a, b) => a.fecha < b.fecha ? 1 : -1)[0];
      return v ? `${eur(v.valor)} <small>${fecha(v.fecha)}</small>` : '<span class="neg">sin valor anotado</span>';
    }
    const c = D && (D.productos || []).find(x => x.id === p.id);
    return c && c.nav ? `${num(c.nav)} € <small>${fecha(c.navFecha)}</small>` : '<small>tras guardar</small>';
  }
  function filaProducto(p) {
    const n = soloSaldo(p) || manual(p)
      ? E.cfg.valoraciones.filter(v => v.producto === p.id).length + " valores"
      : E.cfg.movimientos.filter(m => m.producto === p.id).length + " movs.";
    return `<tr><td><i class="pt" style="background:var(--s${p.slot || 1})"></i>${esc(nombre(p))}${indicadorNota(p.id)}
        ${p.identificador ? `<small class="idp">${esc(p.identificador)}</small>` : ""}</td>
      <td>${esc(E.tipos[p.tipo] || p.tipo)}</td><td>${precioDe(p)}</td>
      <td>${esc(E.fuentes[p.fuente] || "")}${p.codigo ? ` <small>${esc(p.codigo)}</small>` : ""}</td>
      <td>${n}</td>
      ${celdaAcc(p.id, { editar: "editarProducto", duplicar: "duplicarProducto", borrar: "borrarProducto" })}</tr>`;
  }

  function vistaActivos() {
    const lista = E.cfg.productos.filter(p => p.tipo !== "deuda");
    const filas = lista.map(filaProducto).join("");
    return `<section class="tarjeta"><header><h2>Activos</h2>
        <span class="subt">Todo lo que suma: fondos, acciones, cripto, cuentas, planes, inmuebles… Desde la ficha de cada uno anotas sus compras o su saldo.</span>
        <span class="sp"></span>${lista.length > 1 ? '<button class="btn" data-acc="repartirColores" title="Da a cada activo un color distinto">Repartir colores</button>' : ""}
        <button class="btn prim" data-acc="nuevoProducto">+ Añadir activo</button></header>
      ${filas ? envTabla("activos", `<tr><th>Activo</th><th>Tipo</th><th>Último precio</th>
        <th>Fuente del precio</th><th>Datos</th><th class="nosort"></th></tr>`, filas)
        : '<p class="subt">Todavía no has añadido ningún activo.</p>'}</section>`;
  }

  function vistaDeudas() {
    const lista = E.cfg.productos.filter(p => p.tipo === "deuda");
    const filas = lista.map(filaProducto).join("");
    return `<section class="tarjeta"><header><h2>Deudas</h2>
        <span class="subt">Préstamos, hipoteca, tarjetas… El capital pendiente lo anotas cada mes en «Saldos y movimientos».</span>
        <span class="sp"></span>${lista.length > 1 ? '<button class="btn" data-acc="repartirColores" title="Da a cada elemento un color distinto">Repartir colores</button>' : ""}
        <button class="btn prim" data-acc="nuevaDeuda">+ Añadir deuda</button></header>
      ${filas ? envTabla("deudas", `<tr><th>Deuda</th><th>Tipo</th><th>Último saldo</th>
        <th>Fuente</th><th>Datos</th><th class="nosort"></th></tr>`, filas)
        : '<p class="subt">No tienes deudas registradas.</p>'}</section>`;
  }

  function vistaSaldosMov() {
    return vistaMovimientos() + vistaSaldos();
  }

  function siguienteColor(lista) {
    const usos = Array(NCOLORES + 1).fill(0);
    (lista || E.cfg.productos).forEach(p => { usos[p.slot || 1]++; });
    let mejor = 1;
    for (let i = 1; i <= NCOLORES; i++) if (usos[i] < usos[mejor]) mejor = i;
    return mejor;
  }
  // Rejilla de radios de color reutilizable (ficha de activo y de apartado).
  const rejillaColores = () => Array.from({ length: NCOLORES }, (_, i) =>
    `<label class="color" style="--c:var(--s${i + 1})" title="Color ${i + 1}"><input type="radio" name="slot" value="${i + 1}"><i></i></label>`).join("");

  /* Piezas de formulario: todas las cajas iguales, con su etiqueta encima. */
  const campo = (et, control, pista = "", clase = "") =>
    `<label class="campo ${clase}"><span class="et">${et}${pista ? ` <em>${pista}</em>` : ""}</span>${control}</label>`;
  const seccion = t => `<div class="secc">${t}</div>`;
  // Iconito ⓘ con explicación al pasar el ratón (tooltip nativo: nunca se recorta,
  // ni dentro del modal con scroll). aria-label para lectores de pantalla.
  const info = t => ` <span class="info" tabindex="0" role="note" title="${esc(t)}" aria-label="${esc(t)}">i</span>`;
  const LUPA = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>';
  const COLOR_FUENTE = { morningstar: "var(--s3)", yahoo: "var(--s7)", coingecko: "var(--s4)" };
  const decimal = v => v == null || v === "" ? "" : String(v).replace(".", ",");

  function formProducto(p, tipoInicial) {
    const nuevo = !p || !p.id;   // sin id = producto nuevo (p. ej. al duplicar)
    p = p || { tipo: tipoInicial || "fondo", fuente: tipoInicial === "deuda" ? "manual" : "morningstar", moneda: "EUR", largoPlazo: true, slot: siguienteColor() };
    const clases = [...new Set(E.cfg.productos.map(x => x.clase).filter(Boolean))];
    const entidades = [...new Set(E.cfg.productos.map(x => x.entidad).filter(Boolean))].sort();
    const dims = ((E.cfg.config || {}).dimensiones) || [];
    const cats = p.categorias || {};
    const seccionDims = dims.length ? `
      ${seccion("Clasificación")}
      <div class="rejilla">
        ${dims.map(dm => campo(esc(dm.nombre),
          `<input name="cat_${esc(dm.id)}" list="dl_${esc(dm.id)}" value="${esc(cats[dm.id] || "")}" placeholder="…" autocomplete="off">
           <datalist id="dl_${esc(dm.id)}">${(dm.valores || []).map(v => `<option value="${esc(v)}">`).join("")}</datalist>`,
          "opcional")).join("")}
      </div>
      <p class="ayuda">Ejes para agrupar y filtrar el panel (Distribución, Reparto %, Estructura). Los defines en <b>Configuración → Dimensiones</b>.</p>` : "";
    const colores = rejillaColores();
    const esDeuda = (tipoInicial === "deuda" || p.tipo === "deuda");
    const tituloNuevo = esDeuda ? "Añadir deuda" : "Añadir activo";
    const f = abreModal(nuevo ? tituloNuevo : "Editar " + esc(nombre(p)), `
      <div class="buscador">
        <div class="tit">Busca tu producto</div>
        <div class="sub">Por ISIN, ticker o nombre. Comprobamos que tiene precio antes de proponerlo.</div>
        <div class="fila"><div class="caja">${LUPA}<input id="bq" placeholder="IE00BYX5NX33, AAPL, bitcoin, oro…" autocomplete="off"></div>
          <button type="button" class="btn prim" id="bBuscar">Buscar</button></div>
        <div id="bRes" class="bRes"></div>
        <p class="ayuda">¿No aparece o no tiene precio en internet (un piso, oro físico, un plan de pensiones)?
          Rellénalo abajo y elige <b>«Valor anotado a mano»</b> como fuente del precio.</p>
      </div>

      ${seccion("El producto")}
      <div class="rejilla">
        ${campo("Nombre", '<input name="nombre" required>', "", "ancho")}
        ${campo("Nombre corto", '<input name="corto" maxlength="24">', "para los gráficos")}
        ${campo("Tipo", `<select name="tipo">${opciones(E.tipos, p.tipo)}</select>`)}
        ${campo("Detalle del tipo" + info("Afina el tipo para la foto por categorías, como en el Excel: p. ej. Tipo «Cuenta / efectivo» con detalle «Cuenta remunerada» o «Depósito». Si lo dejas vacío se usa el tipo general. Para las cuentas que puedas usar ya, deja el Tipo en «Cuenta / efectivo» para que cuenten como disponible."), '<input name="tipoDetalle" placeholder="Cuenta remunerada, Depósito…">', "opcional")}
        ${campo("ISIN o ticker", '<input name="identificador">', "opcional")}
        ${campo("Banco o bróker", `<input name="entidad" list="edEntidades">
          <datalist id="edEntidades">${entidades.map(x => `<option value="${esc(x)}">`).join("")}</datalist>`, "opcional")}
        ${(E.cfg.titulares || []).length > 1 ? campo("Titular", `<input name="titular" list="edTitulares" value="${esc(nuevo ? (E.cfg.titulares || [])[0] || "" : "")}" placeholder="Yo, Común…">
          <datalist id="edTitulares">${(E.cfg.titulares || []).map(t => `<option value="${esc(t)}">`).join("")}</datalist>`, "de quién es") : ""}
        ${campo("Moneda", '<input name="moneda" maxlength="3" placeholder="EUR">', "EUR por defecto")}
      </div>

      <div class="siCotiza">${seccion("De dónde sale el precio")}
      <div class="rejilla tres">
        ${campo("Fuente", `<select name="fuente">${opciones(E.fuentes, p.fuente)}</select>`)}
        ${campo("Código", '<input name="codigo">', "", "siOnline")}
      </div></div>

      <div class="siDeuda" hidden>${seccion("Datos de la deuda")}
      <div class="rejilla tres">
        ${campo("Capital inicial", '<input name="capitalInicial" inputmode="decimal">', "€")}
        ${campo("TAE", '<input name="tae" inputmode="decimal" placeholder="6,5">', "%")}
        ${campo("Cuota mensual", '<input name="cuota" inputmode="decimal">', "€")}
        ${campo("Fecha de inicio", '<input name="fechaInicio" type="date">')}
        ${campo("Vencimiento", '<input name="fechaVencimiento" type="date">')}
        ${campo("Próxima revisión", '<input name="fechaRevision" type="date">')}
        ${campo("Fecha de cancelación", '<input name="fechaCancelacion" type="date">', "si ya la pagaste")}
      </div>
      <p class="ayuda">El <b>capital pendiente</b> lo anotas cada mes en «Saldos y movimientos» (es el saldo de la deuda).
        Aquí van los datos fijos del préstamo; los intereses anuales se estiman como capital × TAE.</p></div>

      ${seccion("Cómo se muestra")}
      <div class="rejilla">
        ${campo("Clase de activo", `<input name="clase" list="edClases" placeholder="Renta variable global">
          <datalist id="edClases">${clases.map(c => `<option value="${esc(c)}">`).join("")}</datalist>`, "opcional")}
        ${campo("Color en los gráficos", `<div class="colores">${colores}</div>`)}
        <label class="interruptor ancho"><input type="checkbox" name="largoPlazo"><span class="pista"></span>
          <span><b>Inversión a largo plazo</b><small>El botón «Solo largo plazo» del panel quita lo que no lo es: colchón, cuentas…</small></span></label>
        <label class="interruptor ancho"><input type="checkbox" name="disponible"><span class="pista"></span>
          <span><b>Disponible</b><small>Liquidez inmediata (cuentas, efectivo). Las inversiones e inmuebles no suelen serlo.</small></span></label>
      </div>
      ${seccionDims}
      <p class="relleno" id="bRelleno" hidden></p>

      <details class="avanzado"><summary>Ficha y opciones avanzadas</summary>
        <div class="rejilla tres">
          ${campo("Comisión anual", '<input name="ter" inputmode="decimal" placeholder="0,12">', "TER, %")}
          ${campo("Riesgo", '<input name="riesgo" inputmode="numeric" placeholder="1 a 7">', "de 1 a 7")}
          ${campo("Gestora", '<input name="gestora">')}
          ${campo("Línea de respaldo", '<input name="respaldo" placeholder="BTCW.SW">', "Yahoo")}
          ${campo("Moneda respaldo", '<input name="respaldoMoneda" maxlength="3" placeholder="CHF">')}
          ${campo("Precio en vivo", '<input name="vivo" placeholder="bitcoin">', "id CoinGecko")}
          ${campo("Descripción", '<textarea name="papel" rows="2" placeholder="Para qué tienes este producto"></textarea>', "opcional", "ancho")}
        </div>
        <p class="ayuda">El <b>respaldo</b> contrasta cada día el precio con otra línea del mismo producto y usa esa
          cuando no coinciden. El <b>precio en vivo</b> mueve el valor minuto a minuto con una criptomoneda.</p>
      </details>`,
    async f => {
      const d = campos(f);
      d.largoPlazo = f.elements.largoPlazo.checked;
      d.disponible = f.elements.disponible.checked;
      if (!nuevo) d.id = p.id;
      const item = await guarda("productos", d);
      if (!nuevo) return null;
      // Siguiente paso natural: su primer dato.
      return manual(item) ? () => formValor(null, item.id) : () => formMovimiento(null, item.id);
    }, nuevo ? (esDeuda ? "Guardar deuda" : "Guardar activo") : "Guardar cambios");

    rellena(f, {
      ...p,
      ter: p.ter != null ? decimal(+(p.ter * 100).toFixed(4)) : "",
      tae: p.tae != null ? decimal(+(p.tae * 100).toFixed(4)) : "",
    });
    const ajusta = () => {
      const tipo = f.elements.tipo.value;
      const saldo = SOLO_SALDO.includes(tipo);
      const deuda = tipo === "deuda";
      const online = !saldo && f.elements.fuente.value !== "manual";
      f.querySelector(".siCotiza").hidden = saldo;
      f.querySelector(".siDeuda").hidden = !deuda;
      f.querySelectorAll(".siOnline").forEach(el => { el.hidden = !online; });
      f.querySelector(".siCotiza .rejilla.tres").classList.toggle("una", !online);
      f.querySelector(".buscador").hidden = saldo;
    };
    f.elements.tipo.onchange = ajusta;
    f.elements.fuente.onchange = ajusta;
    ajusta();

    // El interruptor «disponible» debe reflejar lo MISMO que calcula el motor:
    // un producto sin ese campo se trata según su tipo (efectivo = disponible).
    // Si no, al editar un efectivo antiguo el interruptor salía apagado aunque
    // el panel ya lo contaba como disponible (desajuste que confundía).
    if (nuevo) {
      const defDisp = () => { f.elements.disponible.checked = f.elements.tipo.value === "efectivo"; };
      defDisp();
      f.elements.tipo.addEventListener("change", defDisp);
    } else if (p.disponible == null) {
      f.elements.disponible.checked = (f.elements.tipo.value === "efectivo");
    }

    const buscar = async () => {
      const q = $("#bq").value.trim();
      const res = $("#bRes");
      if (!q) return;
      res.innerHTML = '<p class="cargando">Buscando y comprobando precios…</p>';
      try {
        const j = await api("GET", "api/buscar?q=" + encodeURIComponent(q));
        if (!j.resultados.length) {
          res.innerHTML = `<p class="neg">No encuentro «${esc(q)}» con precio en internet. Prueba con el ISIN
            (viene en la ficha del producto en tu banco) o elige «Valor anotado a mano».</p>`;
          return;
        }
        res.innerHTML = j.resultados.map((r, i) => `<button type="button" class="bItem" data-i="${i}" style="--c:${COLOR_FUENTE[r.fuente]}">
          <span class="franja"></span>
          <span><span class="nm">${esc(r.nombre || r.codigo)}</span>
            <span class="meta"><span>${esc(r.codigo)}</span>${r.mercado && r.mercado !== E.fuentes[r.fuente] ? `<span>${esc(r.mercado)}</span>` : ""}<span>${esc(E.fuentes[r.fuente])}</span></span></span>
          <span class="pre">${num(r.precio)} ${esc(r.moneda)}<small>${fecha(r.fecha)}</small></span></button>`).join("");
        res.querySelectorAll(".bItem").forEach(b => {
          b.onclick = () => {
            const r = j.resultados[+b.dataset.i];
            const n = r.nombre || r.codigo;
            const fi = r.ficha || {};
            rellena(f, {
              nombre: n, corto: n.slice(0, 24).trim(), tipo: r.tipo, identificador: r.identificador,
              fuente: r.fuente, codigo: r.codigo, moneda: r.moneda || "EUR", vivo: r.vivo || "",
              ter: decimal(fi.ter), riesgo: fi.riesgo || "", gestora: fi.gestora || "",
            });
            if (fi.clase) f.elements.clase.value = fi.clase;
            const rell = [fi.ter != null && `comisión ${decimal(fi.ter)} %`, fi.riesgo && `riesgo ${fi.riesgo}/7`,
              fi.clase && "categoría", fi.gestora && "gestora"].filter(Boolean);
            const aviso = $("#bRelleno");
            aviso.hidden = !rell.length;
            aviso.textContent = rell.length ? `✓ Ficha rellenada desde Morningstar: ${rell.join(", ")}.` : "";
            res.querySelectorAll(".bItem").forEach(x => x.classList.toggle("sel", x === b));
            ajusta();
          };
        });
      } catch (x) { res.innerHTML = `<p class="neg">${esc(x.message)}</p>`; }
    };
    $("#bBuscar").onclick = buscar;
    $("#bq").onkeydown = e => { if (e.key === "Enter") { e.preventDefault(); buscar(); } };
    if (nuevo) $("#bq").focus();
  }

  async function borrarProducto(id) {
    const p = prod(id);
    const nm = E.cfg.movimientos.filter(m => m.producto === id).length;
    const nv = E.cfg.valoraciones.filter(v => v.producto === id).length;
    const extra = nm || nv ? `\n\nSe borrarán también sus ${nm} movimientos y ${nv} valores anotados.` : "";
    if (!confirm(`¿Borrar «${nombre(p)}»?${extra}\n\nSi te equivocas, hay copias automáticas en mis_datos/copias.`)) return;
    try { await borra("productos", id); pinta(); } catch (x) { alert(x.message); }
  }

  /* ---------------------------------------------- hogar (apartados y parámetros) */
  function vistaApartados() {
    const aps = E.cfg.apartados || [];
    const filasAp = aps.map(a => `<tr>
      <td><i class="pt" style="background:var(--s${a.slot || 8})"></i>${esc(a.nombre)}${indicadorNota(a.id)}</td><td>${esc(a.finalidad || "")}</td><td>${esc(a.titular || "")}</td>
      <td>${eur(a.importe || 0)}</td><td>${a.fechaPrevista ? fecha(a.fechaPrevista) : ""}</td>
      ${celdaAcc(a.id, { editar: "editarApartado", borrar: "borrarApartado" })}</tr>`).join("");
    return `<section class="tarjeta"><header><h2>Reservados</h2>
        <span class="subt">Dinero reservado para un fin (impuestos, obras, fianzas…): no resta del patrimonio, pero sí del dinero libre para invertir</span>
        <span class="sp"></span>${aps.length > 1 ? '<button class="btn" data-acc="repartirColoresApartados" title="Da a cada reservado un color distinto">Repartir colores</button>' : ""}
        <button class="btn prim" data-acc="nuevoApartado">+ Añadir reservado</button></header>
      ${filasAp ? envTabla("apartados", `<tr><th>Reservado</th><th>Finalidad</th><th>Titular</th>
        <th>Importe</th><th>Fecha prevista</th><th class="nosort"></th></tr>`, filasAp)
        : '<p class="subt">Todavía no has creado ningún reservado.</p>'}</section>`;
  }

  function vistaConfig() {
    const conf = E.cfg.config || {};
    const tits = E.cfg.titulares || [];
    const cats = conf.categorias || [];
    const obj = conf.objetivos || {};
    const dims = conf.dimensiones || [];
    const reglas = conf.reglasCategoria || [];
    const propios = conf.tipos || [];
    const ocultos = conf.tiposOcultos || [];
    const monedas = conf.monedas || [];
    const catal = E.avisosCatalogo || [];
    const avisosOff = conf.avisosOff || [];
    const firing = new Set(((window.DATOS || {}).alertas || []).map(a => a.clave).filter(Boolean));
    const pct = v => v != null ? (v * 100).toLocaleString("es-ES", { maximumFractionDigits: 2 }) + " %" : "—";
    const sub = t => `<span class="subt">${t}</span>`;
    const fila = (et, val) => `<tr><td>${et}</td><td>${val}</td></tr>`;
    // Nombre legible de un tipo (base o propio) a partir de su clave.
    const nomTipo = k => E.tipos[k] || (E.tiposBase && E.tiposBase[k]) || (propios.find(t => t.id === k) || {}).nombre || k;
    const objFilas = Object.entries(obj).map(([k, v]) => `${esc(nomTipo(k))}: <b>${pct(v)}</b>`).join(" · ");
    return `<section class="tarjeta"><header><h2>Configuración</h2>
        <span class="subt">Todo lo que defines del hogar: titulares, tipos, categorías, monedas y avisos (como la hoja «Configuración» del Excel). Es lo mismo que ves al pulsar «Editar».</span>
        <span class="sp"></span><button class="btn prim" data-acc="editarConfig">Editar</button></header>
      <table class="leyenda">
        ${fila("Nombre del patrimonio", esc(E.cfg.titular || "Mi patrimonio"))}
        ${fila("Objetivo de patrimonio", (E.cfg.objetivo && E.cfg.objetivo.activo) ? eur(E.cfg.objetivo.importe) : sub("sin meta"))}
        ${fila("Titulares", tits.length ? tits.map(t => esc(t) + (t === ((conf.titularDefecto && tits.includes(conf.titularDefecto)) ? conf.titularDefecto : tits[0]) ? ' <span class="subt">(por defecto)</span>' : "")).join(", ") : sub("solo tú"))}
        ${fila("Colchón deseado", eur(conf.colchon || 0))}
        ${fila("Inflación de referencia", conf.inflacion != null ? pct(conf.inflacion) : sub("sin fijar"))}
        ${fila("Tipos propios", propios.length ? propios.map(t => esc(t.nombre)).join(", ") : sub("ninguno"))}
        ${fila("Tipos de base ocultos", ocultos.length ? ocultos.map(k => esc(nomTipo(k))).join(", ") : sub("ninguno"))}
        ${fila("Objetivos de asignación", objFilas || sub("sin objetivos"))}
        ${fila("Umbral de concentración", pct(conf.umbralConcentracion))}
        ${fila("Desviación máxima", pct(conf.desviacionMax))}
        ${fila("Días de aviso de vencimientos", (conf.diasAviso != null ? conf.diasAviso : "—"))}
        ${fila("Recordatorio sin anotar", (conf.diasSinAnotar != null ? conf.diasSinAnotar + " días" : "—"))}
        ${fila("Monedas (cambio manual)", monedas.length ? monedas.map(m => `${esc(m.codigo)} = ${esc(String(m.tipo))}`).join(", ") : "EUR")}
        ${fila("Categorías de ingresos/gastos", cats.length ? cats.length + " categorías" : sub("se escriben libres"))}
        ${fila("Reglas para el banco", reglas.length ? reglas.length + " reglas" : sub("ninguna"))}
        ${fila("Marcas de apuntes", (conf.marcas || []).length ? (conf.marcas || []).map(m => esc(m.emoji || "") + (m.nombre ? " " + esc(m.nombre) : "")).join(", ") : sub("varias por defecto (🚩 ⭐ ❗ …)"))}
        ${fila("Dimensiones de clasificación de activos", dims.length ? dims.map(d => esc(d.nombre)).join(", ") : sub("ninguna"))}
        ${fila("Entidades / bancos", (conf.entidades || []).length ? (conf.entidades || []).map(esc).join(", ") : sub("ninguna"))}
        ${fila("Dimensiones de ingresos/gastos", (conf.dimensionesFlujos || []).length ? (conf.dimensionesFlujos || []).map(d => esc(d.nombre)).join(", ") : sub("ninguna"))}
        ${fila("Avisos automáticos", catal.length ? `${catal.length - avisosOff.length} de ${catal.length} activos` + (avisosOff.length ? ` · ${avisosOff.length} desactivado${avisosOff.length === 1 ? "" : "s"}` : "") : "—")}
        ${fila("Buscar actualizaciones", conf.buscarActualizaciones ? "Sí" : "No")}
      </table>
      <p class="ayuda">El <b>colchón</b> es la liquidez mínima que quieres mantener; la <b>concentración</b> avisa cuando un tipo o entidad pesa demasiado;
        las <b>categorías</b> alimentan el desplegable de ingresos y gastos; las <b>dimensiones</b> son ejes propios para agrupar tus activos.</p>
      ${cats.length ? `<div class="tablaEnv" style="margin-top:12px"><table class="dt"><thead><tr><th>Categoría</th><th>Tipo</th><th style="text-align:right">Presupuesto</th></tr></thead>
        <tbody>${cats.map(c => `<tr><td>${esc(c.nombre)}</td><td class="${c.tipo === "ingreso" ? "pos" : "neg"}">${c.tipo === "ingreso" ? "Ingreso" : "Gasto"}</td>
          <td style="text-align:right">${c.presupuesto != null ? eur(c.presupuesto) : "—"}</td></tr>`).join("")}</tbody></table></div>` : ""}
      ${dims.length ? `<div class="tablaEnv" style="margin-top:12px"><table class="dt"><thead><tr><th>Dimensión</th><th>Valores sugeridos</th></tr></thead>
        <tbody>${dims.map(d => `<tr><td>${esc(d.nombre)}</td><td>${(d.valores || []).map(esc).join(", ") || "—"}</td></tr>`).join("")}</tbody></table></div>` : ""}
      ${catal.length ? `<div class="tablaEnv" style="margin-top:12px"><table class="dt"><thead><tr><th>Aviso</th><th>Estado</th><th>Ahora mismo</th></tr></thead>
        <tbody>${catal.map(a => {
          const activo = !avisosOff.includes(a.clave);
          const ahora = !activo ? sub("—") : firing.has(a.clave) ? '<span class="neg">⚠ saltando</span>' : '<span class="pos">todo bien</span>';
          return `<tr><td>${esc(a.nombre)}</td><td class="${activo ? "pos" : ""}">${activo ? "Activo" : sub("desactivado")}</td><td>${ahora}</td></tr>`;
        }).join("")}</tbody></table></div>` : ""}
    </section>`;
  }

  function formApartado(a) {
    const nuevo = !a;
    a = a || { slot: siguienteColor(E.cfg.apartados || []) };
    const tits = E.cfg.titulares || [];
    const f = abreModal(nuevo ? "Añadir reservado" : "Editar " + esc(a.nombre || "reservado"), `
      ${seccion("El reservado")}
      <div class="rejilla">
        ${campo("Nombre", '<input name="nombre" required>', "", "ancho")}
        ${campo("Finalidad", '<input name="finalidad">', "para qué es")}
        ${tits.length > 1 ? campo("Titular", `<input name="titular" list="apTitulares" value="${esc(nuevo ? tits[0] || "" : "")}" placeholder="Común…">
          <datalist id="apTitulares">${tits.map(t => `<option value="${esc(t)}">`).join("")}</datalist>`, "opcional") : ""}
        ${campo("Importe reservado", '<input name="importe" inputmode="decimal" required>', "€")}
        ${campo("Fecha prevista de uso", '<input name="fechaPrevista" type="date">', "opcional")}
        ${campo("Nota", '<textarea name="nota" rows="2"></textarea>', "opcional", "ancho")}
        ${campo("Color", `<div class="colores">${rejillaColores()}</div>`, "", "ancho")}
      </div>`,
    async f => {
      const d = campos(f);
      if (!nuevo) d.id = a.id;
      await guarda("apartados", d);
    }, nuevo ? "Guardar reservado" : "Guardar cambios");
    rellena(f, a);
    return f;
  }

  async function borrarApartado(id) {
    const a = (E.cfg.apartados || []).find(x => x.id === id);
    if (!confirm(`¿Borrar el reservado «${a ? a.nombre : ""}»?\n\nHay copias automáticas en mis_datos/copias.`)) return;
    try { await borra("apartados", id); pinta(); } catch (x) { alert(x.message); }
  }

  async function guardaConfig(datos) {
    const j = await api("POST", "api/config", datos);
    E.cfg = j.cartera;
    COP.lista = null;
    window.EDITOR_SUCIO = true;
    avisa(j.avisos);
    if (window.toast) window.toast("Guardado ✓");
  }

  const UMBRAL_NOMBRE = { umbralConcentracion: "Umbral de concentración", desviacionMax: "Desviación máxima", diasAviso: "Días de aviso", diasSinAnotar: "Recordatorio sin anotar" };
  function formHogar() {
    const conf = E.cfg.config || {};
    const obj = conf.objetivos || {};
    const ocultos = conf.tiposOcultos || [];
    const avisosOffCfg = conf.avisosOff || [];
    const tiposPropios = (conf.tipos || []).map(t => t.nombre);
    const objInputs = Object.entries(E.tipos).map(([clave, label]) =>
      `<label class="campo"><span class="et">${esc(label)} <em>%</em></span><input name="obj_${clave}" inputmode="decimal" placeholder="0"></label>`).join("");
    const f = abreModal("Configuración", `
      ${seccion("Este patrimonio")}
      <div class="rejilla">
        ${campo("Nombre de este patrimonio", '<input name="nombreCartera" maxlength="60" required>', "aparece arriba, en el selector")}
        ${campo("Objetivo de patrimonio", '<input name="objetivoImporte" inputmode="decimal" placeholder="100000">', "€, la meta de la barra del panel; vacío = sin meta")}
      </div>
      ${seccion("Colchón de seguridad")}
      <div class="rejilla">
        ${campo("Colchón deseado", '<input name="colchon" inputmode="decimal" placeholder="3000">', "€, liquidez mínima")}
        ${campo("Inflación anual", '<input name="inflacion" inputmode="decimal" placeholder="2,5">', "%, referencia en Evolución; puedes cambiarla también en la gráfica")}
      </div>
      ${seccion("Titulares del hogar")}
      <div id="edTits" class="rejilla"></div>
      <p class="ayuda">El primero eres tú. Si le cambias el nombre, se actualiza en todos tus activos, apuntes y reservados.
        Añade más miembros con «+ Añadir titular». <b>Con un solo titular</b>, la app no te pregunta por titular en ningún sitio ni muestra los filtros por titular.</p>
      ${seccion("Tipos de activo")}
      <div class="campo ancho"><span class="et">Tipos de base <em>desmarca los que no uses</em></span>
        <div class="tiposBase">${Object.entries(E.tiposBase).map(([k, v]) =>
          `<label class="chkTipo"><input type="checkbox" class="tbChk" value="${esc(k)}"${ocultos.includes(k) ? "" : " checked"}> ${esc(v)}</label>`).join("")}</div></div>
      <div class="campo ancho"><span class="et">Tus tipos <em>se añaden a los de base</em></span>
        <div id="edTipos"></div></div>
      <p class="ayuda">Puedes crear tus propios tipos (p. ej. <code>Crowdlending</code>, <code>Arte</code>, <code>Coche</code>) además de los de base.
        Aparecen al clasificar un activo y en el objetivo de asignación de abajo. Los de base no se borran: solo se ocultan si los desmarcas.</p>
      ${seccion("Control de asignación")}
      <div class="rejilla tres">
        ${campo("Umbral de concentración", '<input name="umbralConcentracion" inputmode="decimal" placeholder="40">', "%")}
        ${campo("Desviación máxima", '<input name="desviacionMax" inputmode="decimal" placeholder="5">', "puntos %")}
        ${campo("Días de aviso", '<input name="diasAviso" inputmode="numeric" placeholder="90">', "vencimientos")}
        ${campo("Recordatorio sin anotar", '<input name="diasSinAnotar" inputmode="numeric" placeholder="30">', "días")}
      </div>
      <div class="secc">Objetivo de asignación por tipo (%)</div>
      <div class="rejilla tres">${objInputs}</div>
      <p class="ayuda">Los objetivos por tipo deberían sumar 100 %. Déjalos vacíos si no quieres objetivos.
        La concentración avisa cuando un tipo o entidad supera el umbral.</p>
      ${seccion("Monedas (tipo de cambio manual)")}
      <div class="rejilla">
        ${campo("Una moneda por línea: código y euros por unidad", '<textarea name="monedas" rows="3" placeholder="USD 0,92\nGBP 1,17"></textarea>', "EUR = 1, implícito", "ancho")}
      </div>
      <p class="ayuda">Solo para productos «a mano» en otra divisa. Es un tipo único para todo el histórico
        (aproximación). Los productos con cotización usan su cambio diario.</p>
      ${seccion("Categorías de ingresos y gastos")}
      <div class="rejilla">
        ${campo("Categorías de ingresos (una por línea)", '<textarea name="catIng" rows="3" placeholder="Nómina\nAlquileres cobrados\nIntereses y dividendos"></textarea>', "", "ancho")}
        ${campo("Categorías de gastos (una por línea; opcional «= presupuesto»)", '<textarea name="catGas" rows="5" placeholder="Vivienda = 750\nAlimentación = 600\nTransporte\nOcio = 250"></textarea>', "", "ancho")}
      </div>
      <p class="ayuda">Aparecen en el desplegable al anotar. En los gastos puedes añadir un presupuesto mensual con
        «= importe» (p. ej. <code>Alimentación = 600</code>); el Panel te dirá si te pasas. Si las dejas vacías, escribes la categoría a mano.</p>
      ${seccion("Reglas para categorizar el banco")}
      <div class="rejilla">
        ${campo("Una regla por línea: «palabra = Categoría»", '<textarea name="reglasCat" rows="4" placeholder="mercadona = Alimentación\niberdrola = Suministros\nnetflix = Ocio y restaurantes"></textarea>', "", "ancho")}
      </div>
      <p class="ayuda">Al <b>importar movimientos del banco</b>, si el concepto contiene esa palabra se asigna esa categoría
        (si existe y es del tipo correcto). Tienen prioridad sobre las que trae la app. Al importar puedes marcar
        «recordar mis correcciones» y se añaden aquí solas.</p>
      ${seccion("Marcas de apuntes")}
      <div class="rejilla">
        ${campo("Una marca por línea: «emoji» o «emoji = nombre»", '<textarea name="marcasTxt" rows="7" placeholder="👁️ = Revisar\n❗ = Importante\n❓ = Duda\n🔖 = Seguimiento\n⚠️ = Incidencia\n📎 = Justificante\n✅ = Verificado"></textarea>', "el nombre es opcional", "ancho")}
      </div>
      <p class="ayuda">Pon un <b>emoji</b> por línea (y, si quieres, un nombre tras «=»). En <b>Ingresos y gastos</b> eliges la marca de cada apunte con el desplegable de su fila (solo el icono) y puedes filtrar por marca (ahí sí sale el nombre, si lo pusiste).</p>
      ${seccion("Entidades / bancos (ingresos y gastos)")}
      <div class="rejilla">
        ${campo("Una entidad por línea", '<textarea name="entidadesTxt" rows="3" placeholder="BBVA\nING\nRevolut\nEfectivo"></textarea>', "", "ancho")}
      </div>
      <p class="ayuda">Define tus bancos o cuentas. Al <b>importar</b> del banco eliges a cuál corresponde esa importación y se asigna a todos sus apuntes. Luego puedes <b>filtrar y analizar</b> Ingresos y gastos por entidad.</p>
      ${seccion("Dimensiones de ingresos y gastos")}
      <div class="rejilla">
        ${campo("Una dimensión por línea: «Nombre: valor1, valor2, …»", '<textarea name="dimFlujos" rows="3" placeholder="Necesidad: Fijo, Variable, Caprichos\nProyecto: Casa, Viaje, Coche"></textarea>', "", "ancho")}
      </div>
      <p class="ayuda">Como las dimensiones de activos, pero para los apuntes: ejes propios para clasificar y filtrar tus ingresos y gastos.</p>
      ${seccion("Dimensiones de clasificación de activos")}
      <div class="rejilla">
        ${campo("Una dimensión por línea: «Nombre: valor1, valor2, …»", '<textarea name="dimensiones" rows="4" placeholder="Clase de activo: Renta variable, Renta fija, Liquidez, Alternativos\nGeografía: Global, EEUU, Europa, Emergentes"></textarea>', "", "ancho")}
      </div>
      <p class="ayuda">Ejes propios para clasificar tus activos (además de Tipo y Entidad). A cada activo le asignas un valor por eje en su ficha; luego puedes agrupar y filtrar <b>Distribución</b>, <b>Reparto %</b> y <b>Estructura</b> por ellos. Los valores tras los dos puntos son sugerencias; en la ficha del activo puedes escribir otro.</p>
      ${seccion("Avisos automáticos")}
      <p class="ayuda" style="margin:2px 0 8px">Activa o desactiva cada aviso. Así sabes de qué te avisa la app y de qué no: los que desactives tendrás que vigilarlos tú.</p>
      <div class="rejilla">
        ${(E.avisosCatalogo || []).map(a => `<label class="interruptor ancho"><input type="checkbox" name="aviso_${esc(a.clave)}"${avisosOffCfg.includes(a.clave) ? "" : " checked"}><span class="pista"></span>
          <span><b>${esc(a.nombre)}</b><small>${esc(a.desc)}${a.umbral ? ` · Se ajusta con «${esc(UMBRAL_NOMBRE[a.umbral] || a.umbral)}»` : ""}</small></span></label>`).join("")}
      </div>
      ${seccion("Privacidad")}
      <div class="rejilla">
        <label class="interruptor ancho"><input type="checkbox" name="buscarActualizaciones"><span class="pista"></span>
          <span><b>Buscar actualizaciones</b><small>Si lo activas, la app comprueba en GitHub (una vez al día) si hay una versión nueva. Apagado, la app no sale a internet salvo para descargar los precios. Viene apagado.</small></span></label>
      </div>`,
    async f => {
      const d = campos(f);
      const objetivos = {};
      Object.keys(E.tipos).forEach(clave => {
        const val = (d["obj_" + clave] || "").trim();
        if (val) objetivos[clave] = val;
      });
      const monedas = (d.monedas || "").split(/\n+/).map(l => l.trim()).filter(Boolean).map(l => {
        const parts = l.split(/\s+/);
        return { codigo: parts[0] || "", tipo: parts[1] || "" };
      });
      const lineas = t => (d[t] || "").split(/\n+/).map(s => s.trim()).filter(Boolean);
      const catGas = lineas("catGas").map(l => {
        const p = l.split("=");
        const o = { nombre: (p[0] || "").trim(), tipo: "gasto" };
        if ((p[1] || "").trim()) o.presupuesto = (p[1] || "").trim();
        return o;
      }).filter(o => o.nombre);
      const categorias = lineas("catIng").map(n => ({ nombre: n, tipo: "ingreso" })).concat(catGas);
      const reglasCategoria = lineas("reglasCat").map(l => {
        const i = l.indexOf("=");
        return i < 0 ? null : { palabra: l.slice(0, i).trim(), categoria: l.slice(i + 1).trim() };
      }).filter(r => r && r.palabra && r.categoria);
      const dimensiones = lineas("dimensiones").map(l => {
        const i = l.indexOf(":");
        const nombre = (i >= 0 ? l.slice(0, i) : l).trim();
        const valores = i >= 0 ? l.slice(i + 1).split(",").map(s => s.trim()).filter(Boolean) : [];
        return { nombre, valores };
      }).filter(dm => dm.nombre);
      const marcas = lineas("marcasTxt").map(l => {
        const i = l.indexOf("=");
        return { emoji: (i >= 0 ? l.slice(0, i) : l).trim(), nombre: i >= 0 ? l.slice(i + 1).trim() : "" };
      }).filter(m => m.emoji);
      const entidades = lineas("entidadesTxt");
      const dimensionesFlujos = lineas("dimFlujos").map(l => {
        const i = l.indexOf(":");
        const nombre = (i >= 0 ? l.slice(0, i) : l).trim();
        const valores = i >= 0 ? l.slice(i + 1).split(",").map(s => s.trim()).filter(Boolean) : [];
        return { nombre, valores };
      }).filter(dm => dm.nombre);
      // Titulares: filas del editor. El valor que tenía cada fila al abrir (data-de)
      // sirve para detectar renombrados y propagarlos a activos/apuntes/apartados.
      const filasTit = leeFilasEdit($("#edTits"));
      const titulares = [...new Set(filasTit.map(x => x.a).filter(Boolean))];
      const renombresTitular = filasTit.filter(x => x.de && x.a && x.de !== x.a).map(x => ({ de: x.de, a: x.a }));
      const titularDefecto = leeFilaDefecto($("#edTits"));
      // Tipos propios (filas) + tipos de base ocultos (casillas desmarcadas).
      const tipos = leeFilasEdit($("#edTipos")).map(x => ({ nombre: x.a })).filter(t => t.nombre);
      const tiposOcultos = [...f.querySelectorAll(".tbChk")].filter(c => !c.checked).map(c => c.value);
      // Avisos: los que quedan sin marcar se desactivan.
      const avisosOff = (E.avisosCatalogo || []).map(a => a.clave)
        .filter(c => { const el = f.elements["aviso_" + c]; return el && !el.checked; });
      await guardaConfig({
        titular: (d.nombreCartera || "").trim(),
        objetivoImporte: d.objetivoImporte,
        colchon: d.colchon,
        inflacion: d.inflacion,
        titulares, renombresTitular, titularDefecto, tipos, tiposOcultos, avisosOff,
        umbralConcentracion: d.umbralConcentracion,
        desviacionMax: d.desviacionMax,
        diasAviso: d.diasAviso,
        diasSinAnotar: d.diasSinAnotar,
        buscarActualizaciones: f.elements.buscarActualizaciones.checked,
        objetivos, monedas, categorias, dimensiones, reglasCategoria, marcas,
        entidades, dimensionesFlujos,
      });
      // El nombre sale en el selector de arriba: recargar para que se vea al momento.
      location.reload();
    }, "Guardar");
    f.elements.nombreCartera.value = E.cfg.titular || "";
    f.elements.objetivoImporte.value = (E.cfg.objetivo && E.cfg.objetivo.activo) ? (E.cfg.objetivo.importe || "") : "";
    f.elements.colchon.value = conf.colchon || "";
    f.elements.inflacion.value = conf.inflacion != null ? +(conf.inflacion * 100).toFixed(2) : "";
    const _tits0 = (E.cfg.titulares || []).length ? E.cfg.titulares : ["Yo"];
    const _titDef = (conf.titularDefecto && _tits0.includes(conf.titularDefecto)) ? conf.titularDefecto : _tits0[0];
    montaFilasEdit(f.querySelector("#edTits"), _tits0, "Nombre del titular", "Añadir titular", { defecto: _titDef });
    montaFilasEdit(f.querySelector("#edTipos"), tiposPropios, "Nombre del tipo", "Añadir tipo");
    f.elements.marcasTxt.value = ((conf.marcas && conf.marcas.length) ? conf.marcas : (E.marcas || []))
      .map(m => m.nombre ? `${m.emoji} = ${m.nombre}` : m.emoji).join("\n");
    const pct = v => v != null ? +(v * 100).toFixed(2) : "";
    f.elements.umbralConcentracion.value = pct(conf.umbralConcentracion);
    f.elements.desviacionMax.value = pct(conf.desviacionMax);
    f.elements.diasAviso.value = conf.diasAviso != null ? conf.diasAviso : "";
    f.elements.diasSinAnotar.value = conf.diasSinAnotar != null ? conf.diasSinAnotar : "";
    f.elements.buscarActualizaciones.checked = !!conf.buscarActualizaciones;
    Object.entries(obj).forEach(([clave, frac]) => {
      const el = f.elements["obj_" + clave];
      if (el) el.value = pct(frac);
    });
    f.elements.monedas.value = (conf.monedas || []).map(m => `${m.codigo} ${m.tipo}`).join("\n");
    const cats = conf.categorias || [];
    f.elements.catIng.value = cats.filter(c => c.tipo === "ingreso").map(c => c.nombre).join("\n");
    f.elements.catGas.value = cats.filter(c => c.tipo === "gasto")
      .map(c => c.presupuesto != null ? `${c.nombre} = ${c.presupuesto}` : c.nombre).join("\n");
    f.elements.dimensiones.value = (conf.dimensiones || [])
      .map(dm => (dm.valores || []).length ? `${dm.nombre}: ${dm.valores.join(", ")}` : dm.nombre).join("\n");
    f.elements.reglasCat.value = (conf.reglasCategoria || [])
      .map(r => `${r.palabra} = ${r.categoria}`).join("\n");
    f.elements.entidadesTxt.value = (conf.entidades || []).join("\n");
    f.elements.dimFlujos.value = (conf.dimensionesFlujos || [])
      .map(dm => (dm.valores || []).length ? `${dm.nombre}: ${dm.valores.join(", ")}` : dm.nombre).join("\n");
    return f;
  }

  /* ---------------------------------------------- ingresos y gastos (flujos) */
  // Estado del «Anotar rápido» (persiste entre re-renders para poder precargar una plantilla).
  let AR = { tipo: "gasto" };

  // Rellena el formulario rápido con una plantilla recurrente (NO guarda: el importe
  // puede variar de un mes a otro, así que el usuario lo ajusta y confirma).
  function rellenaDe(r) {
    if (!r) return;
    AR = { tipo: r.tipo, importe: r.importe, categoria: r.categoria || "", nota: r.nota || "", titular: r.titular || "" };
    montaAnotarRapido();
    const imp = $("#formAnotar") && $("#formAnotar").importe;
    if (imp) { imp.focus(); if (imp.select) imp.select(); }
  }
  async function quitaRecurrente(i) {
    try {
      const j = await api("POST", "api/recurrentes", { accion: "quitar", indice: i });
      E.cfg = j.cartera; window.EDITOR_SUCIO = true; pinta();
    } catch (x) { const m = $("#arMsg"); if (m) m.textContent = x.message; }
  }
  function montaAnotarRapido() {
    const cont = $("#anotarRapido"); if (!cont) return;
    const conf = E.cfg.config || {};
    const tipo = AR.tipo || "gasto";
    const cats = (conf.categorias || []).filter(c => c.tipo === tipo).map(c => c.nombre);
    const tits = E.cfg.titulares || [];
    const recs = conf.recurrentes || [];
    const hoy = new Date().toISOString().slice(0, 10);
    cont.innerHTML = `<form class="anotarBar" id="formAnotar" autocomplete="off">
        <div class="segm arTipo">
          <button type="button" data-ar="gasto" aria-pressed="${tipo === "gasto"}">− Gasto</button>
          <button type="button" data-ar="ingreso" aria-pressed="${tipo === "ingreso"}">+ Ingreso</button></div>
        <input name="importe" inputmode="decimal" placeholder="Importe €" class="arImp" required>
        <input name="concepto" placeholder="Concepto (nota)" class="arNota" aria-label="Concepto">
        <input name="categoria" placeholder="Categoría" list="arCats" class="arCat">
        <datalist id="arCats">${cats.map(c => `<option value="${esc(c)}">`).join("")}</datalist>
        <input name="fecha" type="date" value="${hoy}" class="arFecha" aria-label="Fecha">
        ${tits.length > 1 ? `<select name="titular" class="arTit" aria-label="Titular"><option value="">Titular…</option>${tits.map(t => `<option${t === AR.titular ? " selected" : ""}>${esc(t)}</option>`).join("")}</select>` : ""}
        <label class="arRec" title="Guardar como plantilla para repetirlo cada mes"><input type="checkbox" id="arRecurrente"> 🔁 recurrente</label>
        <button class="btn prim" type="submit">Anotar</button>
        <span class="arMsg" id="arMsg"></span></form>
      ${recs.length ? `<div class="recChips"><span class="recHint">Recurrentes · pulsa para rellenar:</span>${recs.map((r, i) => `
        <span class="recChip ${r.tipo === "ingreso" ? "pos" : "neg"}" data-rellena="${i}" role="button" tabindex="0" title="Rellenar el formulario con esta plantilla">🔁 ${esc(r.categoria || r.nota || (r.tipo === "ingreso" ? "Ingreso" : "Gasto"))} <b>${r.tipo === "gasto" ? "−" : "+"}${eur(r.importe)}</b>${r.titular ? ` · ${esc(r.titular)}` : ""}<button class="recX" data-quitar="${i}" title="Quitar plantilla" aria-label="Quitar">×</button></span>`).join("")}</div>` : ""}`;
    if (AR.importe != null) cont.querySelector('[name="importe"]').value = AR.importe;
    if (AR.categoria != null) cont.querySelector('[name="categoria"]').value = AR.categoria;
    if (AR.nota != null) cont.querySelector('[name="concepto"]').value = AR.nota;
    cont.querySelectorAll(".arTipo button").forEach(b => { b.onclick = () => { AR = { tipo: b.dataset.ar }; montaAnotarRapido(); }; });
    cont.querySelectorAll("[data-rellena]").forEach(ch => { ch.onclick = e => { if (!e.target.closest(".recX")) rellenaDe(recs[+ch.dataset.rellena]); }; });
    cont.querySelectorAll(".recX").forEach(x => { x.onclick = e => { e.stopPropagation(); quitaRecurrente(+x.dataset.quitar); }; });
    $("#formAnotar").onsubmit = async e => {
      e.preventDefault();
      const f = e.target, btn = f.querySelector('button[type="submit"]');
      const cuerpo = { tipo, importe: f.importe.value, fecha: f.fecha.value,
        categoria: (f.categoria.value || "").trim(), nota: (f.concepto.value || "").trim(),
        titular: (f.titular && f.titular.value) || "" };
      btn.disabled = true; btn.textContent = "Anotando…";
      try {
        await guarda("flujos", cuerpo);
        if ($("#arRecurrente") && $("#arRecurrente").checked) {
          try { const j = await api("POST", "api/recurrentes", { accion: "añadir", recurrente: cuerpo }); E.cfg = j.cartera; } catch (_) { /* el apunte ya se guardó */ }
        }
        AR = { tipo };
        pinta();
      } catch (x) { $("#arMsg").textContent = x.message || "No se pudo guardar."; btn.disabled = false; btn.textContent = "Anotar"; }
    };
  }

  const marcaDe = id => (E.marcas || []).find(m => m.id === id);
  // Desplegable para elegir la marca de un apunte (o quitarla), al pulsar su ☆/emoji.
  function cierraMenuMarca() { const m = document.getElementById("marcaMenu"); if (m) m.remove(); }
  function abreMenuMarca(id) {
    cierraMenuMarca();
    const fl = (E.cfg.flujos || []).find(x => x.id === id); if (!fl) return;
    const btn = document.querySelector('.marcaBtn[data-id="' + (window.CSS && CSS.escape ? CSS.escape(id) : id) + '"]'); if (!btn) return;
    const menu = document.createElement("div"); menu.id = "marcaMenu"; menu.className = "marcaMenu";
    // Solo iconos (el nombre va en el tooltip), más un ✕ para quitar la marca.
    menu.innerHTML = `<button type="button" class="marcaOpt quitar${!fl.marca ? " sel" : ""}" data-val="" title="Sin marca">✕</button>` +
      (E.marcas || []).map(m => `<button type="button" class="marcaOpt ico${fl.marca === m.id ? " sel" : ""}" data-val="${esc(m.id)}" title="${esc(m.nombre || "")}">${esc(m.emoji || "●")}</button>`).join("");
    document.body.appendChild(menu);
    const r = btn.getBoundingClientRect();
    menu.style.left = Math.max(8, Math.min(r.left, innerWidth - menu.offsetWidth - 8)) + "px";
    menu.style.top = (r.bottom + 4 + menu.offsetHeight > innerHeight ? r.top - menu.offsetHeight - 4 : r.bottom + 4) + "px";
    menu.querySelectorAll(".marcaOpt").forEach(o => o.onclick = async () => {
      cierraMenuMarca();
      try {
        const j = await api("POST", "api/flujo-marca", { id, marca: o.dataset.val });
        E.cfg = j.cartera; window.EDITOR_SUCIO = true; pinta();
      } catch (x) { alert(x.message); }
    });
    setTimeout(() => document.addEventListener("click", cierraMenuMarca, { once: true }), 0);
  }
  // Popover de «Observaciones» de un apunte: muestra la nota libre y permite editarla.
  function cierraObs() { const m = document.getElementById("obsPop"); if (m) m.remove(); }
  function abreObs(id) {
    cierraObs(); cierraMenuMarca();
    const fl = (E.cfg.flujos || []).find(x => x.id === id); if (!fl) return;
    const btn = document.querySelector('.obsBtn[data-id="' + (window.CSS && CSS.escape ? CSS.escape(id) : id) + '"]'); if (!btn) return;
    const pop = document.createElement("div"); pop.id = "obsPop"; pop.className = "obsPop";
    pop.innerHTML = (fl.observaciones
      ? `<div class="obsTxt">${esc(fl.observaciones).replace(/\n/g, "<br>")}</div>`
      : '<div class="obsVacio">Sin observaciones todavía.</div>')
      + `<div class="obsAcc"><button type="button" class="btn mini prim" data-obs-editar>${fl.observaciones ? "Editar" : "Añadir"}</button></div>`;
    pop.addEventListener("click", e => e.stopPropagation());
    document.body.appendChild(pop);
    const r = btn.getBoundingClientRect();
    pop.style.left = Math.max(8, Math.min(r.left, innerWidth - pop.offsetWidth - 8)) + "px";
    pop.style.top = (r.bottom + 4 + pop.offsetHeight > innerHeight ? r.top - pop.offsetHeight - 4 : r.bottom + 4) + "px";
    pop.querySelector("[data-obs-editar]").onclick = () => { cierraObs(); formFlujo(fl); };
    setTimeout(() => document.addEventListener("click", cierraObs, { once: true }), 0);
  }
  // Filtros potentes de la tabla de ingresos y gastos (por columna, importe y fechas).
  function filtrosFlujos() {
    try { E.flujoFiltros = E.flujoFiltros || JSON.parse(recuerda.lee("patrimonio.flujoFiltros") || "{}") || {}; } catch (e) { E.flujoFiltros = {}; }
    if (!E.flujoFiltros.dim) E.flujoFiltros.dim = {};
    return E.flujoFiltros;
  }
  function filtraFlujos(fs) {
    const F = filtrosFlujos(), cfg = E.cfg.config || {};
    const i1 = F.importe1 ? leeNum(F.importe1) : null, i2 = F.importe2 ? leeNum(F.importe2) : null;
    const titDef = (cfg.titularDefecto && (E.cfg.titulares || []).includes(cfg.titularDefecto)) ? cfg.titularDefecto : (E.cfg.titulares || [])[0] || "";
    return fs.filter(x => {
      if (F.tipo && x.tipo !== F.tipo) return false;
      if (F.categoria && (x.categoria || "") !== F.categoria) return false;
      if (F.entidad && (x.entidad || "") !== F.entidad) return false;
      if (F.titular && (((x.titular || "").trim()) || titDef) !== F.titular) return false;
      if (F.marca === "__con__" && !x.marca) return false;
      if (F.marca === "__sin__" && x.marca) return false;
      if (F.marca && F.marca[0] !== "_" && x.marca !== F.marca) return false;
      if (F.obs === "con" && !x.observaciones) return false;
      if (F.obs === "sin" && x.observaciones) return false;
      for (const d in (F.dim || {})) if (F.dim[d] && (x.categorias || {})[d] !== F.dim[d]) return false;
      const imp = +x.importe || 0;
      if (F.impOp === "mayor" && i1 != null && !isNaN(i1) && !(imp > i1)) return false;
      if (F.impOp === "menor" && i1 != null && !isNaN(i1) && !(imp < i1)) return false;
      if (F.impOp === "entre" && ((i1 != null && !isNaN(i1) && imp < i1) || (i2 != null && !isNaN(i2) && imp > i2))) return false;
      if (F.fdesde && x.fecha < F.fdesde) return false;
      if (F.fhasta && x.fecha > F.fhasta) return false;
      return true;
    });
  }
  function hayFiltroFlujos() {
    const F = filtrosFlujos();
    return !!(F.tipo || F.categoria || F.entidad || F.titular || F.marca || F.obs || F.impOp || F.fdesde || F.fhasta ||
      Object.values(F.dim || {}).some(Boolean));
  }
  function filtrosFlujosHTML() {
    const F = filtrosFlujos(), cfg = E.cfg.config || {};
    const cats = [...new Set((E.cfg.flujos || []).map(f => f.categoria).filter(Boolean))].sort();
    const ents = [...new Set([...(cfg.entidades || []), ...(E.cfg.flujos || []).map(f => f.entidad).filter(Boolean)])];
    const tits = E.cfg.titulares || [], marcas = E.marcas || [], dims = cfg.dimensionesFlujos || [];
    const campo = (key, label, opts, val, todas = "Todas") => `<span class="filtroCampo${val ? " activo" : ""}"><label>${esc(label)}</label>
      <select data-ff="${esc(key)}"><option value="">${todas}</option>${opts.map(o => `<option value="${esc(o.v)}"${o.v === val ? " selected" : ""}>${esc(o.t)}</option>`).join("")}</select></span>`;
    let h = campo("tipo", "Tipo", [{ v: "ingreso", t: "Ingresos" }, { v: "gasto", t: "Gastos" }], F.tipo || "");
    if (cats.length) h += campo("categoria", "Categoría", cats.map(c => ({ v: c, t: c })), F.categoria || "");
    if (ents.length) h += campo("entidad", "Entidad", ents.map(e => ({ v: e, t: e })), F.entidad || "");
    if (tits.length > 1) h += campo("titular", "Titular", tits.map(t => ({ v: t, t })), F.titular || "");
    if (marcas.length) h += campo("marca", "Marca", [{ v: "__con__", t: "Con marca" }, { v: "__sin__", t: "Sin marca" },
      ...marcas.map(m => ({ v: m.id, t: (m.emoji || "") + (m.nombre ? " " + m.nombre : "") }))], F.marca || "");
    h += campo("obs", "Observaciones", [{ v: "con", t: "Con nota" }, { v: "sin", t: "Sin nota" }], F.obs || "");
    dims.forEach(dm => {
      const vals = [...new Set([...(dm.valores || []), ...(E.cfg.flujos || []).map(f => (f.categorias || {})[dm.id]).filter(Boolean)])];
      if (vals.length) h += campo("dim:" + dm.id, dm.nombre, vals.map(v => ({ v, t: v })), (F.dim || {})[dm.id] || "");
    });
    h += `<span class="filtroCampo${F.impOp ? " activo" : ""}"><label>Importe €</label>
      <select data-ff="impOp"><option value="">—</option><option value="mayor"${F.impOp === "mayor" ? " selected" : ""}>mayor que</option><option value="menor"${F.impOp === "menor" ? " selected" : ""}>menor que</option><option value="entre"${F.impOp === "entre" ? " selected" : ""}>entre</option></select>
      ${F.impOp ? `<input class="fImp" data-ff="importe1" inputmode="decimal" value="${esc(F.importe1 || "")}" placeholder="€">` : ""}
      ${F.impOp === "entre" ? `<input class="fImp" data-ff="importe2" inputmode="decimal" value="${esc(F.importe2 || "")}" placeholder="€">` : ""}</span>`;
    h += `<span class="filtroCampo${(F.fdesde || F.fhasta) ? " activo" : ""}"><label>Fechas</label>
      <input type="date" class="fFecha" data-ff="fdesde" value="${esc(F.fdesde || "")}"><span class="fSep">–</span><input type="date" class="fFecha" data-ff="fhasta" value="${esc(F.fhasta || "")}"></span>`;
    if (hayFiltroFlujos()) h += `<button type="button" class="btn mini filtroQuitar" data-ff-limpiar>✕ Limpiar filtros</button>`;
    return h;
  }
  function montaFiltrosFlujos() {
    const F = filtrosFlujos();
    const guarda = () => { try { recuerda.guarda("patrimonio.flujoFiltros", JSON.stringify(F)); } catch (e) { /* da igual */ } };
    document.querySelectorAll('#tab-datos [data-ff]').forEach(el => {
      const k = el.dataset.ff;
      const aplica = pleno => {
        const v = el.value;
        if (k.indexOf("dim:") === 0) F.dim[k.slice(4)] = v; else F[k] = v;
        guarda();
        // Fechas e importes: refresco LIGERO (solo filas), sin reconstruir la barra de
        // filtros; así el campo no pierde el foco mientras tecleas (antes «saltaba»).
        if (pleno) pinta(); else refrescaFlujos();
      };
      if (el.type === "date" || el.classList.contains("fImp")) el.onchange = () => aplica(false);
      else el.onchange = () => aplica(true);   // selects: re-pinta (chips activas, importe)
    });
    const lb = document.querySelector("#tab-datos [data-ff-limpiar]");
    if (lb) lb.onclick = () => { E.flujoFiltros = { dim: {} }; try { recuerda.guarda("patrimonio.flujoFiltros", "{}"); } catch (e) { /* */ } pinta(); };
  }
  function flujosFiltrados() {
    const fs = (E.cfg.flujos || []).slice().sort((a, b) => a.fecha < b.fecha ? 1 : -1);
    return filtraFlujos(fs);
  }
  function filasFlujosHTML(fs) {
    const varios = (E.cfg.titulares || []).length > 1;   // la columna Titular solo si hay más de uno
    const conEnt = (((E.cfg.config || {}).entidades) || []).length > 0 || (E.cfg.flujos || []).some(x => x.entidad);
    const estrella = x => { const m = x.marca && marcaDe(x.marca); return `<button class="marcaBtn${m ? " on" : ""}" data-acc="menuMarca" data-id="${esc(x.id)}"
        title="${m ? "Marca" + (m.nombre ? ": " + esc(m.nombre) : "") : "Marcar"}">${m ? esc(m.emoji || "●") : "☆"}</button>`; };
    const obsInd = x => x.observaciones
      ? `<button class="obsBtn tiene" data-acc="verObs" data-id="${esc(x.id)}" title="Tiene observaciones — pulsa para verlas">📝</button>`
      : `<button class="obsBtn add" data-acc="verObs" data-id="${esc(x.id)}" title="Añadir observaciones">+</button>`;
    return fs.map(x => `<tr>
      <td class="cMarca">${estrella(x)}</td>
      <td>${fecha(x.fecha)}</td>
      <td class="${x.tipo === "ingreso" ? "pos" : "neg"}">${(E.tiposFlujo && E.tiposFlujo[x.tipo]) || x.tipo}</td>
      <td>${esc(x.categoria || "")}</td>
      ${conEnt ? `<td>${esc(x.entidad || "")}</td>` : ""}
      <td class="nota" title="${esc(x.nota)}">${esc(x.nota || "")}</td>
      <td class="cObs">${obsInd(x)}</td>
      ${varios ? `<td>${esc(x.titular || "")}</td>` : ""}
      <td style="text-align:right" class="${x.tipo === "ingreso" ? "pos" : "neg"}">${x.tipo === "gasto" ? "−" : ""}${eur(x.importe)}</td>
      ${celdaAcc(x.id, { editar: "editarFlujo", borrar: "borrarFlujo" })}</tr>`).join("");
  }
  // Refresco ligero de Ingresos y gastos: cambia solo las filas y el contador, sin
  // tocar la barra de filtros (conserva el foco de los campos de fecha/importe).
  function refrescaFlujos() {
    const bloque = document.querySelector('#tab-datos [data-tabla="flujos"]');
    if (!bloque) { pinta(); return; }
    const fs = flujosFiltrados();
    const tbody = bloque.querySelector("table.dt tbody");
    // Si cruzamos la frontera 0 ⇄ N la estructura cambia (tabla ↔ mensaje): re-pinta.
    if ((fs.length > 0) !== !!tbody) { pinta(); return; }
    if (tbody) { tbody.innerHTML = filasFlujosHTML(fs); aplicaTablas(); }
    const c = document.getElementById("flujosContador");
    if (c) c.innerHTML = hayFiltroFlujos()
      ? `<p class="subt" style="margin:10px 0 0">Mostrando <b>${fs.length}</b> de ${(E.cfg.flujos || []).length} apuntes.</p>` : "";
  }
  function vistaFlujos() {
    const fs = flujosFiltrados();
    const varios = (E.cfg.titulares || []).length > 1;
    const conEnt = (((E.cfg.config || {}).entidades) || []).length > 0 || (E.cfg.flujos || []).some(x => x.entidad);
    const filas = filasFlujosHTML(fs);
    const total = (E.cfg.flujos || []).length;
    const contador = hayFiltroFlujos() ? `<p class="subt" style="margin:10px 0 0">Mostrando <b>${fs.length}</b> de ${total} apuntes.</p>` : "";
    return `<section class="tarjeta"><header><h2>Anotar rápido</h2>
        <span class="subt">Un gasto o ingreso al vuelo, sin abrir el formulario completo. Pulsa un recurrente para rellenarlo (ajusta el importe si varía).</span></header>
      <div id="anotarRapido"></div></section>
      <section class="tarjeta"><header><h2>Ingresos y gastos</h2>
        <span class="subt">Flujo de caja del hogar: nóminas, alquileres, gastos… Busca y filtra arriba; marca apuntes con el desplegable de su fila.</span>
        <span class="sp"></span><button class="btn prim" data-acc="nuevoFlujo">+ Añadir apunte</button></header>
      ${total
        ? (filas ? envTabla("flujos", `<tr><th class="nosort"></th><th>Fecha</th><th>Tipo</th><th>Categoría</th>${conEnt ? "<th>Entidad</th>" : ""}<th>Concepto</th><th class="nosort" title="Observaciones"></th>
          ${varios ? "<th>Titular</th>" : ""}<th style="text-align:right">Importe</th><th class="nosort"></th></tr>`, filas, false, filtrosFlujosHTML())
          : `<div class="tablaBloque" data-tabla="flujos"><div class="tablaTools" style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">${filtrosFlujosHTML()}</div></div><p class="subt" style="margin-top:12px">Ningún apunte coincide con los filtros.</p>`)
        : '<p class="subt">Todavía no has anotado ingresos ni gastos.</p>'}
      <div id="flujosContador">${contador}</div>
    </section>`;
  }

  function formFlujo(x) {
    const nuevo = !x;
    x = x || { tipo: "gasto" };
    const tits = E.cfg.titulares || [];
    const ents = ((E.cfg.config || {}).entidades) || [];
    const dimsF = ((E.cfg.config || {}).dimensionesFlujos) || [];
    const xcats = x.categorias || {};
    // Categorías definidas en Configuración + las que ya hayas usado.
    const defin = ((E.cfg.config || {}).categorias || []).map(c => c.nombre);
    const usadas = (E.cfg.flujos || []).map(v => v.categoria).filter(Boolean);
    const cats = [...new Set([...defin, ...usadas])];
    const f = abreModal(nuevo ? "Añadir apunte" : "Editar apunte", `
      ${seccion("Ingreso o gasto")}
      <div class="rejilla">
        ${campo("Tipo", `<select name="tipo">${opciones(E.tiposFlujo, x.tipo)}</select>`)}
        ${campo("Fecha", '<input name="fecha" type="date" required>')}
        ${campo("Importe", '<input name="importe" inputmode="decimal" required>', "€")}
        ${campo("Categoría", `<input name="categoria" list="flCats" placeholder="Nómina, Alimentación…">
          <datalist id="flCats">${cats.map(c => `<option value="${esc(c)}">`).join("")}</datalist>`, "opcional")}
        ${campo("Entidad", `<input name="entidad" list="flEnts" value="${esc(x.entidad || "")}" placeholder="Banco / cuenta">
          <datalist id="flEnts">${[...new Set([...ents, ...(E.cfg.flujos || []).map(v => v.entidad).filter(Boolean)])].map(e => `<option value="${esc(e)}">`).join("")}</datalist>`, "banco de origen; si es nueva, se guarda sola")}
        ${tits.length > 1 ? campo("Titular", `<input name="titular" list="flTits" value="${esc(nuevo ? tits[0] || "" : "")}">
          <datalist id="flTits">${tits.map(t => `<option value="${esc(t)}">`).join("")}</datalist>`, "opcional") : ""}
        ${dimsF.map(dm => campo(esc(dm.nombre), `<input name="cat_${esc(dm.id)}" list="dlf_${esc(dm.id)}" value="${esc(xcats[dm.id] || "")}" placeholder="…" autocomplete="off">
          <datalist id="dlf_${esc(dm.id)}">${(dm.valores || []).map(v => `<option value="${esc(v)}">`).join("")}</datalist>`, "opcional")).join("")}
        ${campo("Concepto", '<textarea name="nota" rows="2"></textarea>', "de qué es; lo rellena el banco al importar", "ancho")}
        ${campo("Observaciones", '<textarea name="observaciones" rows="3"></textarea>', "tu nota libre sobre este apunte (opcional)", "ancho")}
      </div>`,
    async f => {
      const d = campos(f);
      if (!nuevo) d.id = x.id;
      await guarda("flujos", d);
    }, nuevo ? "Guardar apunte" : "Guardar cambios");
    rellena(f, x);
    return f;
  }

  async function borrarFlujo(id) {
    if (!confirm("¿Borrar este apunte de ingreso/gasto?")) return;
    try { await borra("flujos", id); pinta(); } catch (x) { alert(x.message); }
  }

  /* ---------------------------------------------- movimientos */
  function vistaMovimientos() {
    const cotizables = E.cfg.productos.filter(p => !soloSaldo(p));
    const movs = E.cfg.movimientos
      .filter(m => E.filtro === "todos" || m.producto === E.filtro)
      .sort((a, b) => a.fecha < b.fecha ? 1 : a.fecha > b.fecha ? -1 : 0);
    const filas = movs.map(m => {
      const p = prod(m.producto);
      const precio = m.unidades ? (m.importe - (m.comision || 0)) / m.unidades : null;
      return `<tr><td>${fecha(m.fecha)}</td><td style="text-align:left">${p ? `<i class="pt" style="background:var(--s${p.slot || 1})"></i>` : ""}${esc(nombre(p))}</td>
        <td style="text-align:left">${esc(E.tiposMov[m.tipo] || m.tipo)}</td>
        <td>${m.unidades ? num(m.unidades) : "—"}</td>
        <td class="${m.tipo === "compra" || m.tipo === "comision" ? "" : "pos"}">${eur(m.importe)}</td>
        <td>${precio ? num(precio) + " €" : "—"}</td>
        <td class="nota" title="${esc(m.nota)}">${esc(m.nota || "")}</td>
        ${celdaAcc(m.id, { editar: "editarMov", duplicar: "duplicarMov", borrar: "borrarMov" })}</tr>`;
    }).join("");
    return `<section class="tarjeta"><header><h2>Movimientos</h2>
        <span class="subt">Compras, ventas, dividendos y comisiones</span><span class="sp"></span>
        <select id="edFiltro" aria-label="Filtrar por producto"><option value="todos">Todos los productos</option>
          ${cotizables.map(p => `<option value="${esc(p.id)}"${p.id === E.filtro ? " selected" : ""}>${esc(nombre(p))}</option>`).join("")}</select>
        <button class="btn prim" data-acc="nuevoMov">+ Añadir movimiento</button></header>
      ${filas ? envTabla("movimientos", `<tr><th>Fecha</th><th style="text-align:left">Producto</th>
        <th style="text-align:left">Tipo</th><th>Unidades</th><th>Importe</th><th>Precio por unidad</th>
        <th style="text-align:left">Nota</th><th class="nosort"></th></tr>`, filas, true)
        + `<p class="subt" style="margin-top:10px">${movs.length} movimientos.</p>`
        : '<p class="subt">No hay movimientos todavía.</p>'}</section>`;
  }

  const AYUDA_IMPORTE = {
    compra: "Lo que salió de tu cuenta, con las comisiones incluidas.",
    venta: "Lo que te ingresaron, ya descontadas las comisiones.",
    dividendo: "Lo que te ingresaron por el dividendo o el cupón.",
    comision: "Comisiones sueltas, como la de custodia. Las de compra y venta ya van dentro de su importe.",
  };

  function formMovimiento(m, productoId) {
    const cotizables = E.cfg.productos.filter(p => !soloSaldo(p));
    if (!cotizables.length) { alert("Primero añade un activo en «Activos»."); return; }
    const nuevo = !m || !m.id;   // clon sin id = movimiento nuevo (al duplicar)
    m = m || { fecha: hoy(), tipo: "compra", producto: productoId || (E.filtro !== "todos" ? E.filtro : cotizables[0].id) };
    const pildoras = Object.entries(E.tiposMov).map(([k, v]) =>
      `<label><input type="radio" name="tipo" value="${esc(k)}"><span>${esc(k === "dividendo" ? "Dividendo" : v)}</span></label>`).join("");
    const f = abreModal(nuevo ? "Añadir movimiento" : "Editar movimiento", `
      <div class="pildoras">${pildoras}</div>
      <div class="rejilla" style="margin-top:18px">
        ${campo("Producto", `<select name="producto">${cotizables.map(p =>
          `<option value="${esc(p.id)}">${esc(nombre(p))}</option>`).join("")}</select>`, "", "ancho")}
        ${campo("Fecha", `<input type="date" name="fecha" max="${hoy()}">`)}
        ${campo("Unidades" + info("Cuántas participaciones, acciones, títulos u onzas compraste o vendiste. En productos que se valoran a mano son opcionales."), '<input name="unidades" inputmode="decimal" placeholder="0">', "participaciones, acciones…", "siUnid")}
        ${campo("Importe total" + info("El dinero total de la operación. En una COMPRA: lo que salió de tu cuenta, con las comisiones ya incluidas. En una VENTA o un DIVIDENDO: lo que te ingresaron. No se le resta nada: pon la cifra tal cual."), '<div class="conSufijo"><input name="importe" inputmode="decimal" placeholder="0,00"><span>€</span></div>')}
        ${campo("Comisión" + info("Solo informativo: la comisión que te cobraron en esta operación, que YA va dentro del importe total. No se vuelve a restar; sirve para saber cuánto pagas en comisiones."), '<div class="conSufijo"><input name="comision" inputmode="decimal" placeholder="0,00"><span>€</span></div>', "ya incluida en el importe", "siCom")}
        ${campo("Retención IRPF" + info("Opcional. Lo que te retuvieron de IRPF en este dividendo o cupón. Aparece en tu Informe fiscal. El «importe total» de arriba es lo que te ingresaron, ya con la retención descontada."), '<div class="conSufijo"><input name="retencion" inputmode="decimal" placeholder="0,00"><span>€</span></div>', "opcional", "siDiv")}
        ${campo("Nota", '<input name="nota" maxlength="200" placeholder="Por ejemplo: aportación mensual">', "opcional", "ancho")}
      </div>
      <div class="resumen"><span id="mAyuda"></span><b id="mPrecio"></b></div>`,
    async f => {
      const d = campos(f);
      if (!nuevo) d.id = m.id;
      await guarda("movimientos", d);
      E.vista = "movimientos";
      recuerda.guarda("patrimonio.editor", "movimientos");
      return null;
    }, nuevo ? "Guardar movimiento" : "Guardar cambios");
    rellena(f, { ...m, unidades: decimal(m.unidades || ""), importe: decimal(m.importe), comision: decimal(m.comision), retencion: decimal(m.retencion) });
    const ajusta = () => {
      const t = f.elements.tipo.value;
      const p = prod(f.elements.producto.value);
      const conUnid = t === "compra" || t === "venta";
      f.querySelector(".siUnid").hidden = !conUnid;
      f.querySelector(".siCom").hidden = !conUnid;
      const sd = f.querySelector(".siDiv"); if (sd) sd.hidden = t !== "dividendo";
      // Con la caja de unidades oculta, la del importe ocupa su hueco sin descuadrar la rejilla.
      $("#mAyuda").textContent = AYUDA_IMPORTE[t] + (p && manual(p) && t === "compra"
        ? " Como este producto se valora a mano, las unidades son opcionales." : "");
      const u = leeNum(f.elements.unidades.value), imp = leeNum(f.elements.importe.value);
      const com = leeNum(f.elements.comision.value) || 0;
      $("#mPrecio").textContent = conUnid && u > 0 && imp > 0 ? `${num((imp - com) / u)} € / unidad` : "";
    };
    f.oninput = ajusta;
    f.onchange = ajusta;
    ajusta();
  }

  async function borrarMov(id) {
    const m = E.cfg.movimientos.find(x => x.id === id);
    if (!confirm(`¿Borrar ${(E.tiposMov[m.tipo] || "").toLowerCase()} de ${eur(m.importe)} del ${fecha(m.fecha)} en «${nombre(prod(m.producto))}»?`)) return;
    try { await borra("movimientos", id); pinta(); } catch (x) { alert(x.message); }
  }

  /* ---------------------------------------------- saldos y valores anotados */
  const etiquetaValor = p => p.tipo === "efectivo" ? "Saldo" : p.tipo === "deuda" ? "Lo que queda por pagar" : "Valor";

  function vistaSaldos() {
    const lista = E.cfg.productos.filter(manual);
    if (!lista.length) {
      return `<section class="tarjeta"><header><h2>Saldos y valores</h2></header>
        <p class="subt">Aquí aparecen tus cuentas, deudas, planes de pensiones y todo lo que no tiene precio en
        internet. Añádelos en «Activos» (tipo «Cuenta / efectivo», o fuente del precio «Valor anotado a mano»).</p></section>`;
    }
    const tarjetas = lista.map(p => {
      const vals = E.cfg.valoraciones.filter(v => v.producto === p.id).sort((a, b) => a.fecha < b.fecha ? 1 : -1);
      const conAportado = !soloSaldo(p);
      const filas = vals.map(v => `<tr><td>${fecha(v.fecha)}</td><td>${eur(v.valor)}</td>
        ${conAportado ? `<td>${v.aportado != null ? eur(v.aportado) : "—"}</td>` : ""}
        ${celdaAcc(v.id, { editar: "editarValor", borrar: "borrarValor" })}</tr>`).join("");
      return `<section class="tarjeta saldo"><header><h2><i class="pt" style="background:var(--s${p.slot || 1})"></i>${esc(nombre(p))}</h2>
          <span class="subt">${esc(E.tipos[p.tipo] || "")}${p.entidad ? " · " + esc(p.entidad) : ""}</span><span class="sp"></span>
          <button class="btn" data-acc="nuevoValor" data-id="${esc(p.id)}">+ Anotar</button></header>
        ${filas ? `<div class="tablaEnv"><table class="dt orden"><thead><tr><th>Fecha</th><th>${etiquetaValor(p)}</th>
          ${conAportado ? "<th>Aportado</th>" : ""}<th class="nosort"></th></tr></thead><tbody>${filas}</tbody></table></div>`
          : '<p class="neg">Todavía no tiene ningún valor anotado.</p>'}</section>`;
    }).join("");
    return `<section class="tarjeta"><header><h2>Saldos y valores</h2>
        <span class="subt">Lo que no tiene precio en internet. Cuanto más a menudo lo anotes (una vez al mes basta),
        mejor sale su curva.</span><span class="sp"></span>
        <button class="btn prim" data-acc="todosValores">Cierre del mes: anotar saldos</button></header></section>
      <div class="saldos">${tarjetas}</div>`;
  }

  function formValor(v, productoId) {
    const nuevo = !v;
    const p = prod(v ? v.producto : productoId);
    const conAportado = !soloSaldo(p);
    const f = abreModal(`${nuevo ? "Anotar" : "Editar"} ${etiquetaValor(p).toLowerCase()} · ${esc(nombre(p))}`, `
      <div class="rejilla">
        ${campo("Fecha", `<input type="date" name="fecha" max="${hoy()}">`)}
        ${campo(etiquetaValor(p), '<div class="conSufijo"><input name="valor" inputmode="decimal" placeholder="0,00"><span>€</span></div>')}
        ${conAportado ? campo("Aportado hasta esa fecha", '<div class="conSufijo"><input name="aportado" inputmode="decimal" placeholder="0,00"><span>€</span></div>', "opcional", "ancho") : ""}
      </div>
      <div class="resumen"><span>${conAportado
        ? "Lo aportado es el dinero que llevas metido en total. Si lo anotas, el panel calcula su rentabilidad."
        : "Copia el saldo que ves hoy en tu banco."} Si ya había un valor ese mismo día, se sustituye.</span></div>`,
    async f => {
      const d = { ...campos(f), producto: p.id };
      if (!nuevo) d.id = v.id;
      await guarda("valoraciones", d);
      E.vista = "saldos";
      recuerda.guarda("patrimonio.editor", "saldos");
      return null;
    });
    rellena(f, v ? { ...v, valor: decimal(v.valor), aportado: decimal(v.aportado) } : { fecha: hoy() });
    f.elements.valor.focus();
  }

  function todosValores() {
    const lista = E.cfg.productos.filter(manual);
    const ultimo = id => E.cfg.valoraciones.filter(v => v.producto === id).sort((a, b) => a.fecha < b.fecha ? 1 : -1)[0];
    const h = hoy();
    const fin = new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).toISOString().slice(0, 10);
    const finMes = fin > h ? h : fin;   // fin de mes, sin pasar de hoy
    const mesRef = finMes.slice(0, 7);
    abreModal("Cierre del mes", `
      <p class="ayuda" style="margin:0 0 12px">El gesto de cada mes: abre tu banco y copia el saldo de fin de mes de cada
        cuenta, depósito, plan, inmueble o deuda. Deja en blanco los que no quieras tocar.</p>
      <div class="rejilla">${campo("Fecha (fin de mes)", `<input type="date" name="fecha" max="${h}" value="${finMes}">`)}</div>
      <div class="listaValores">${lista.map(p => {
        const u = ultimo(p.id);
        const yaEste = E.cfg.valoraciones.some(v => v.producto === p.id && (v.fecha || "").slice(0, 7) === mesRef);
        return `<label class="filaValor"><span><span class="nm"><i class="pt" style="background:var(--s${p.slot || 1})"></i>${esc(nombre(p))}${yaEste ? ' <small class="pos">✓ este mes</small>' : ""}</span>
          <small>${u ? `Último: ${eur(u.valor)} el ${fecha(u.fecha)}` : "Sin valores todavía"}</small></span>
          <span class="conSufijo"><input name="v_${esc(p.id)}" inputmode="decimal" placeholder="${u ? decimal(u.valor) : "0,00"}"><span>€</span></span></label>`;
      }).join("")}</div>
      <div class="resumen"><span>Los marcados con «✓ este mes» ya tienen saldo en el mes de la fecha elegida.</span></div>`,
    async f => {
      const d = campos(f);
      const pendientes = lista.filter(p => String(d["v_" + p.id] || "").trim());
      if (!pendientes.length) throw new Error("No has escrito ningún valor.");
      for (const p of pendientes) {
        try { await guarda("valoraciones", { producto: p.id, fecha: d.fecha, valor: d["v_" + p.id] }); }
        catch (x) { throw new Error(`${nombre(p)}: ${x.message}`); }
      }
      E.vista = "saldos";
      return null;
    }, "Guardar todos");
  }

  async function borrarValor(id) {
    const v = E.cfg.valoraciones.find(x => x.id === id);
    if (!confirm(`¿Borrar el valor de ${eur(v.valor)} del ${fecha(v.fecha)} de «${nombre(prod(v.producto))}»?`)) return;
    try { await borra("valoraciones", id); pinta(); } catch (x) { alert(x.message); }
  }

  /* ---------------------------------------------- importar */
  const IMP = { destino: "activos", origen: "myinvestor", informe: null, token: null, hecho: null, prompt: null, archivos: [], cats: {} };
  const ICONOS = {
    myinvestor: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18M5 21V10l7-5 7 5v11M9 21v-6h6v6"/></svg>',
    plantilla: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg>',
    ia: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 17l.8 2.2L22 20l-2.2.8L19 23l-.8-2.2L16 20l2.2-.8z"/></svg>',
  };

  function zona(acepta, varios, texto) {
    return `<label class="zona" id="imZona"><input type="file" id="imArchivos" accept="${acepta}"${varios ? " multiple" : ""}>
      <span class="zIc">↥</span><b>${texto}</b><small>o pulsa aquí para elegir${varios ? "los" : "lo"}</small>
      <span class="zNom" id="imNombres"></span></label>`;
  }

  function vistaImportar() {
    if (IMP.informe) return vistaPrevia();
    const banco = IMP.destino === "banco";
    const exito = IMP.hecho ? `<div class="exito"><b>✓ ${esc(IMP.hecho)}</b>
      <button class="btn" data-acc="verPanelDatos">Ver mi panel →</button></div>` : "";
    const opDest = (id, emoji, titulo, texto) => `<button class="imOp${IMP.destino === id ? " sel" : ""}" data-acc="imDestino" data-id="${id}">
      <span class="ic" style="font-size:22px;line-height:1">${emoji}</span><b>${titulo}</b><small>${texto}</small></button>`;
    const op = (id, titulo, texto) => `<button class="imOp${IMP.origen === id ? " sel" : ""}" data-acc="imOrigen" data-id="${id}">
      <span class="ic">${ICONOS[id]}</span><b>${titulo}</b><small>${texto}</small></button>`;
    const prompt = banco ? "api/prompt-banco" : "api/prompt";
    let metodos, paso;
    if (!banco) {
      metodos = op("myinvestor", "MyInvestor", "El CSV de cada fondo") +
        op("plantilla", "Plantilla", "Excel o CSV, para cualquier banco") +
        op("ia", "Con ayuda de una IA", "Convierte el extracto de tu banco o bróker");
      if (IMP.origen === "myinvestor") {
        paso = `<ol class="pasos">
            <li>Entra en MyInvestor desde el ordenador y abre <b>cada uno de tus fondos</b>.</li>
            <li>Pulsa <b>«Plusvalías y minusvalías»</b> y descarga el <b>CSV</b>. No le cambies el nombre: lleva el ISIN del fondo.</li>
            <li>Arrastra aquí todos los archivos a la vez.</li></ol>
          ${zona(".csv", true, "Arrastra aquí los CSV de MyInvestor")}
          <p class="ayuda">Cada importación sustituye lo que importaste antes de ese mismo fondo: repítela cada mes sin miedo a duplicar.
            MyInvestor no permite descargar las órdenes de ETF o acciones: haz capturas y usa la opción «Con ayuda de una IA».</p>`;
      } else if (IMP.origen === "plantilla") {
        paso = `<ol class="pasos">
            <li>Descarga la plantilla: <a class="btn" href="api/plantilla.xlsx" download>Excel</a>
              <a class="btn" href="api/plantilla.csv" download>CSV</a></li>
            <li>Rellena una fila por operación. En la hoja «Ejemplo» tienes cinco filas de muestra.</li>
            <li>Guárdala y arrástrala aquí.</li></ol>
          ${zona(".xlsx,.csv,.txt", false, "Arrastra aquí tu plantilla")}`;
      } else {
        paso = `<ol class="pasos">
            <li><b>Copia el prompt</b>: <button class="btn" data-acc="imCopiar" id="imCopiarBtn">Copiar prompt</button>
              <details class="verPrompt"><summary>Ver el prompt</summary><pre id="imPrompt">${esc(IMP.prompt || "Cargando…")}</pre></details></li>
            <li>Abre ChatGPT, Gemini o la IA que uses. Pega el prompt y, debajo, tu extracto, o adjunta el PDF o
              <b>capturas de pantalla</b> de tus órdenes (así se importan, por ejemplo, las compras de ETF o acciones de MyInvestor).
              <span class="alerta">Antes, borra (o tapa en las capturas) tu nombre, DNI, IBAN, números de cuenta y cualquier dato personal.</span></li>
            <li>Copia su respuesta y pégala aquí:</li></ol>
          <textarea id="imTexto" class="imTexto" rows="8" spellcheck="false"
            placeholder="fecha;identificador;nombre;tipo_producto;tipo_movimiento;unidades;importe;moneda;comision;nota"></textarea>`;
      }
    } else {
      metodos = op("plantilla", "Plantilla", "Excel o CSV, rellénala a mano") +
        op("ia", "Con ayuda de una IA", "Convierte el extracto de tu banco");
      if (IMP.origen === "plantilla") {
        paso = `<ol class="pasos">
            <li>Descarga la plantilla: <a class="btn" href="api/plantilla-banco.xlsx" download>Excel</a>
              <a class="btn" href="api/plantilla-banco.csv" download>CSV</a></li>
            <li>Rellena una fila por movimiento: fecha, concepto e importe (negativo = gasto). La categoría es opcional:
              si la dejas vacía, la app intenta adivinarla y podrás corregirla antes de confirmar.</li>
            <li>Guárdala y arrástrala aquí. También puedes pegar directamente el Excel/CSV que exporta tu banco.</li></ol>
          ${zona(".xlsx,.csv,.txt", false, "Arrastra aquí tu plantilla o el extracto del banco")}
          <p class="ayuda">¿Tu banco exporta los movimientos a Excel o CSV? Arrástralo tal cual: la app reconoce las columnas
            de fecha, concepto, importe (o «cargo»/«abono») más habituales.</p>`;
      } else {
        paso = `<ol class="pasos">
            <li><b>Copia el prompt</b>: <button class="btn" data-acc="imCopiar" id="imCopiarBtn">Copiar prompt</button>
              <details class="verPrompt"><summary>Ver el prompt</summary><pre id="imPrompt">${esc(IMP.prompt || "Cargando…")}</pre></details></li>
            <li>Abre ChatGPT, Gemini o la IA que uses. Pega el prompt y, debajo, los movimientos de tu cuenta, o adjunta el PDF
              o <b>capturas de pantalla</b> del extracto.
              <span class="alerta">Antes, borra (o tapa en las capturas) tu nombre, DNI, IBAN, números de cuenta y cualquier dato personal.</span></li>
            <li>Copia su respuesta y pégala aquí:</li></ol>
          <textarea id="imTexto" class="imTexto" rows="8" spellcheck="false"
            placeholder="fecha;concepto;importe;tipo;categoria;titular"></textarea>`;
      }
    }
    const intro = banco
      ? `<p class="imIntro">Son los <b>ingresos y gastos</b> de tu día a día (nómina, recibos, compras con tarjeta…).
          Alimentan tus <b>flujos</b> y el panel de ingresos/gastos. <span class="muted">No son inversiones: las compras de fondos,
          acciones o cripto van en «Activos e inversiones».</span></p>`
      : `<p class="imIntro">Son los <b>productos</b> que forman tu patrimonio: fondos, ETFs, acciones, cripto, cuentas, inmuebles, deudas…
          con sus <b>compras, ventas, dividendos y saldos</b>. <span class="muted">Los gastos e ingresos corrientes van en «Datos del banco».</span></p>`;
    return `${exito}<section class="tarjeta"><header><h2>Importar datos</h2>
        <span class="subt">Trae tus datos de golpe. Antes de guardar nada verás una vista previa.</span></header>
      <div class="imPregunta">¿Qué quieres importar?</div>
      <div class="imOps imOpsDest">
        ${opDest("activos", "📈", "Activos e inversiones", "Fondos, acciones, cripto, cuentas, inmuebles, deudas…")}
        ${opDest("banco", "🏦", "Datos del banco", "Ingresos y gastos del día a día: nómina, recibos, compras…")}
      </div>
      ${intro}
      <div class="imPregunta">¿Cómo los traes?</div>
      <div class="imOps">${metodos}</div>
      <div class="imPaso">${paso}
        <div class="imErr" id="imFallo" hidden></div>
        <div class="imAcc"><span class="sp"></span>
          <button class="btn prim" data-acc="imRevisar" id="imRevisarBtn">Revisar antes de importar</button></div>
      </div></section>`;
  }

  function conectaImportar() {
    const inp = $("#imArchivos"), z = $("#imZona");
    if (inp) {
      const muestra = () => {
        IMP.archivos = [...inp.files];
        $("#imNombres").textContent = IMP.archivos.map(f => f.name).join(" · ");
        z.classList.toggle("lleno", IMP.archivos.length > 0);
      };
      inp.onchange = muestra;
      z.ondragover = e => { e.preventDefault(); z.classList.add("encima"); };
      z.ondragleave = () => z.classList.remove("encima");
      z.ondrop = e => {
        e.preventDefault();
        z.classList.remove("encima");
        inp.files = e.dataTransfer.files;
        muestra();
      };
    }
    if (IMP.origen === "ia" && !IMP.prompt) {
      const url = IMP.destino === "banco" ? "api/prompt-banco" : "api/prompt";
      api("GET", url).then(j => { IMP.prompt = j.texto; const pre = $("#imPrompt"); if (pre) pre.textContent = j.texto; });
    }
    document.querySelectorAll(".imCatSel").forEach(s => {
      s.onchange = () => { IMP.cats[s.dataset.fila] = s.value; };
    });
  }

  async function imRevisar() {
    const fd = new FormData();
    fd.append("origen", IMP.origen);
    fd.append("destino", IMP.destino);
    const inp = $("#imArchivos");
    if (inp) [...inp.files].forEach(f => fd.append("archivos", f));
    const txt = $("#imTexto");
    if (txt) fd.append("texto", txt.value);
    const b = $("#imRevisarBtn"), fallo = $("#imFallo");
    fallo.hidden = true;
    b.disabled = true;
    b.textContent = "Revisando y buscando precios…";
    try {
      const r = await fetch("api/importar/previsualizar", { method: "POST", body: fd });
      const j = await r.json().catch(() => ({}));
      if (!r.ok || !j.ok) throw new Error((j.errores || ["Algo ha fallado al leerlo."]).join("\n"));
      IMP.informe = j.informe;
      IMP.token = j.token;
      IMP.hecho = null;
      IMP.cats = {};
      pinta();
    } catch (x) {
      fallo.textContent = x.message;
      fallo.hidden = false;
      b.disabled = false;
      b.textContent = "Revisar antes de importar";
    }
  }

  function vistaPrevia() {
    const inf = IMP.informe;
    if (inf.tipoImport === "banco") return vistaPreviaBanco();
    const t = inf.totales;
    const n = inf.añadidos + inf.saldos;
    const cifra = (et, v, extra = "") => `<div class="cifra"><span>${et}</span><b>${v}</b>${extra ? `<small>${extra}</small>` : ""}</div>`;
    const errores = inf.errores.length ? `<div class="imErr"><b>${inf.errores.length} ${inf.errores.length === 1 ? "fila tiene" : "filas tienen"} problemas y no se importará${inf.errores.length === 1 ? "" : "n"}:</b>
      <ul>${inf.errores.map(e => `<li><span class="fila">${typeof e.fila === "number" ? "Fila " + e.fila : esc(e.fila)}</span>${esc(e.mensaje)}</li>`).join("")}</ul></div>` : "";
    const avisos = inf.avisos.map(a => `<div class="av"><span>⚠</span><span>${esc(a)}</span></div>`).join("");
    const nuevos = inf.productosNuevos.length ? `<div class="imNuevos"><div class="secc">Productos nuevos que se crearán</div>
      ${inf.productosNuevos.map(p => `<div class="imProd"><b>${esc(p.nombre)}</b>
        <span class="meta"><span>${esc(E.tipos[p.tipo] || p.tipo)}</span><span>${esc(p.codigo || "valor a mano")}</span>
        <span>${esc(E.fuentes[p.fuente])}</span>${p.precio ? `<span>${num(p.precio)} ${esc(p.monedaPrecio)} · ${fecha(p.fechaPrecio)}</span>` : ""}</span></div>`).join("")}</div>` : "";
    const ESTADO = { nuevo: "Nuevo", repetido: "Ya estaba", error: "Con error" };
    const filas = inf.filas.map(f => `<tr class="est-${f.estado}"><td>${fecha(f.fecha)}</td>
      <td style="text-align:left">${esc(f.productoNombre)}</td><td style="text-align:left">${esc(E.tiposMov[f.tipo] || "Saldo")}</td>
      <td>${f.unidades ? num(f.unidades) : "—"}</td><td>${eur(f.importe)}</td>
      <td style="text-align:left">${f.marcas.map(m => `<span class="etqImp">${esc(m)}</span>`).join("")}</td>
      <td><span class="estado">${ESTADO[f.estado]}</span></td></tr>`).join("");
    return `<section class="tarjeta"><header><h2>Vista previa</h2>
        <span class="subt">Todavía no se ha guardado nada.</span></header>
      <div class="cifras">
        ${cifra("Movimientos nuevos", inf.añadidos, t.numCompras ? `${t.numCompras} compras` : "")}
        ${cifra("Invertido en compras", eur(t.compras))}
        ${cifra("Ventas y dividendos", eur(t.ventas + t.dividendos))}
        ${inf.saldos ? cifra("Saldos anotados", inf.saldos) : ""}
        ${inf.repetidos ? cifra("Ya estaban", inf.repetidos, "se omiten") : ""}
        ${inf.sustituidos ? cifra("Sustituyen a", inf.sustituidos, "importados antes") : ""}
      </div>
      <div class="comprueba"><b>Compara estas cifras con tu banco antes de confirmar.</b>
        ${IMP.origen === "ia" ? "Una IA puede equivocarse al copiar números o saltarse alguna fila: revisa sobre todo el total invertido." : ""}</div>
      ${avisos}${errores}${nuevos}
      ${filas ? `<div class="tablaEnv alto" style="margin-top:16px"><table class="dt"><thead><tr><th>Fecha</th>
        <th style="text-align:left">Producto</th><th style="text-align:left">Tipo</th><th>Unidades</th><th>Importe</th>
        <th style="text-align:left"></th><th>Estado</th></tr></thead><tbody>${filas}</tbody></table></div>` : ""}
      <div class="imAcc"><button class="btn" data-acc="imCancelar">Cancelar</button><span class="sp"></span>
        <button class="btn prim" data-acc="imConfirmar" id="imConfirmarBtn"${n ? "" : " disabled"}>
          ${n ? `Importar ${n} ${n === 1 ? "dato" : "datos"}` : "No hay nada nuevo que importar"}</button></div></section>`;
  }

  function vistaPreviaBanco() {
    const inf = IMP.informe, t = inf.totalesBanco || { ingresos: 0, gastos: 0, numIngresos: 0, numGastos: 0 };
    const n = inf.flujosAñadidos;
    const cats = (E.cfg.config || {}).categorias || [];
    const porTipo = {
      ingreso: cats.filter(c => c.tipo === "ingreso").map(c => c.nombre),
      gasto: cats.filter(c => c.tipo === "gasto").map(c => c.nombre),
    };
    const cifra = (et, v, extra = "") => `<div class="cifra"><span>${et}</span><b>${v}</b>${extra ? `<small>${extra}</small>` : ""}</div>`;
    const errores = inf.errores.length ? `<div class="imErr"><b>${inf.errores.length} ${inf.errores.length === 1 ? "fila tiene" : "filas tienen"} problemas y no se importará${inf.errores.length === 1 ? "" : "n"}:</b>
      <ul>${inf.errores.map(e => `<li><span class="fila">${typeof e.fila === "number" ? "Fila " + e.fila : esc(e.fila)}</span>${esc(e.mensaje)}</li>`).join("")}</ul></div>` : "";
    const sinCats = !cats.length ? `<div class="av"><span>ⓘ</span><span>Todavía no has creado categorías de ingresos y gastos.
      Puedes importar sin categoría ahora y clasificarlos luego, o crearlas en <b>Configuración</b> y volver a revisar.</span></div>` : "";
    const ESTADO = { nuevo: "Nuevo", repetido: "Ya estaba", error: "Con error" };
    const selCat = f => {
      if (f.estado !== "nuevo") return f.categoria ? esc(f.categoria) : "—";
      const cur = IMP.cats[f.fila] != null ? IMP.cats[f.fila] : (f.categoria || "");
      const ops = porTipo[f.tipo] || [];
      return `<select class="imCatSel" data-fila="${f.fila}">
        <option value="">— sin categoría —</option>
        ${ops.map(c => `<option${c === cur ? " selected" : ""}>${esc(c)}</option>`).join("")}
        ${cur && !ops.includes(cur) ? `<option selected>${esc(cur)}</option>` : ""}</select>`;
    };
    const filas = inf.flujosFilas.map(f => `<tr class="est-${f.estado}"><td>${fecha(f.fecha)}</td>
      <td style="text-align:left">${esc(f.concepto) || "<span class=\"muted\">(sin concepto)</span>"}</td>
      <td class="${f.tipo === "ingreso" ? "pos" : "neg"}">${f.tipo === "ingreso" ? "Ingreso" : "Gasto"}</td>
      <td style="text-align:left">${selCat(f)}</td>
      <td class="${f.tipo === "ingreso" ? "pos" : "neg"}">${f.tipo === "gasto" ? "−" : ""}${eur(f.importe)}</td>
      <td><span class="estado">${ESTADO[f.estado]}</span></td></tr>`).join("");
    return `<section class="tarjeta"><header><h2>Vista previa · Datos del banco</h2>
        <span class="subt">Ingresos y gastos que se añadirán a tus flujos. Todavía no se ha guardado nada.</span></header>
      <div class="cifras">
        ${cifra("Ingresos nuevos", t.numIngresos, eur(t.ingresos))}
        ${cifra("Gastos nuevos", t.numGastos, eur(t.gastos))}
        ${cifra("Balance del lote", `${t.ingresos - t.gastos >= 0 ? "+" : "−"}${eur(Math.abs(t.ingresos - t.gastos))}`)}
        ${inf.flujosRepetidos ? cifra("Ya estaban", inf.flujosRepetidos, "se omiten") : ""}
      </div>
      <div class="comprueba"><b>Revisa la categoría de cada movimiento antes de confirmar.</b>
        Puedes cambiarla en la columna «Categoría». Lo que no reconozca la app queda «sin categoría» y podrás clasificarlo luego.</div>
      ${sinCats}${errores}
      ${filas ? `<div class="tablaEnv alto" style="margin-top:16px"><table class="dt"><thead><tr><th>Fecha</th>
        <th style="text-align:left">Concepto</th><th>Tipo</th><th style="text-align:left">Categoría</th><th>Importe</th>
        <th>Estado</th></tr></thead><tbody>${filas}</tbody></table></div>` : ""}
      <div class="imAcc"><button class="btn" data-acc="imCancelar">Cancelar</button>
        <label class="imRecordar" title="Se asigna a todos los apuntes de esta importación (si es nueva, se guarda)">Entidad / banco:
          <input id="imEntidad" list="imEnts" placeholder="BBVA, ING…" style="width:130px">
          <datalist id="imEnts">${[...new Set([...(((E.cfg.config || {}).entidades) || []), ...(E.cfg.flujos || []).map(v => v.entidad).filter(Boolean)])].map(e => `<option value="${esc(e)}">`).join("")}</datalist></label>
        <label class="imRecordar" title="Guarda tus categorías como reglas para la próxima importación">
          <input type="checkbox" id="imRecordar" checked> Recordar mis correcciones</label>
        <span class="sp"></span>
        <button class="btn prim" data-acc="imConfirmar" id="imConfirmarBtn"${n ? "" : " disabled"}>
          ${n ? `Importar ${n} ${n === 1 ? "movimiento" : "movimientos"}` : "No hay nada nuevo que importar"}</button></div></section>`;
  }

  async function imConfirmar() {
    const b = $("#imConfirmarBtn");
    b.disabled = true;
    b.textContent = "Importando…";
    try {
      const cuerpo = { token: IMP.token };
      if (IMP.informe && IMP.informe.tipoImport === "banco") {
        cuerpo.categorias = IMP.cats;
        const rec = $("#imRecordar");
        cuerpo.recordar = rec ? rec.checked : false;
        const ent = $("#imEntidad");
        if (ent && ent.value) cuerpo.entidad = ent.value;
      }
      const j = await api("POST", "api/importar/confirmar", cuerpo);
      E.cfg = j.cartera;
      window.EDITOR_SUCIO = true;
      const i = j.informe;
      const pl = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;
      if (IMP.informe && IMP.informe.tipoImport === "banco") {
        IMP.hecho = "Importado: " + (pl(i.flujosAñadidos || 0, "movimiento del banco", "movimientos del banco")) +
          (i.flujosRepetidos ? `. ${pl(i.flujosRepetidos, "ya estaba y se ha omitido", "ya estaban y se han omitido")}` : "") + "." +
          (i.reglasAprendidas ? ` Aprendí ${pl(i.reglasAprendidas, "regla de categoría", "reglas de categoría")} para la próxima vez.` : "");
      } else {
        IMP.hecho = "Importado: " + [i.añadidos && pl(i.añadidos, "movimiento", "movimientos"),
          i.saldos && pl(i.saldos, "saldo", "saldos")].filter(Boolean).join(" y ") +
          (i.repetidos ? `. ${pl(i.repetidos, "ya estaba y se ha omitido", "ya estaban y se han omitido")}` : "") + ".";
      }
      IMP.informe = null;
      IMP.token = null;
      pinta();
      avisa(j.avisos);
    } catch (x) {
      alert(x.message);
      b.disabled = false;
    }
  }

  /* ---------------------------------------------- copias y web */
  const COP = { lista: null };

  function vistaCopias() {
    if (COP.lista === null) {
      api("GET", "api/copias").then(j => { COP.lista = j.copias; if (E.vista === "copias") pinta(); });
    }
    const propio = E.modo === "propio";
    const ultimaCopia = recuerda.lee("patrimonio.ultimaCopia");
    const diasCopia = ultimaCopia ? Math.floor((Date.now() - Date.parse(ultimaCopia)) / 864e5) : null;
    const tieneDatos = (E.cfg.productos || []).length || (E.cfg.movimientos || []).length;
    const avisoCopia = propio && tieneDatos && (diasCopia === null || diasCopia >= 30);
    const filas = (COP.lista || []).map(c => `<tr><td>${fecha(c.fecha.slice(0, 10))} <small>${c.fecha.slice(11, 16)}</small></td>
      <td style="text-align:left">${esc(c.motivo)}</td><td>${c.productos}</td><td>${c.movimientos}</td>
      <td class="acc"><button data-acc="recuperarCopia" data-id="${esc(c.archivo)}">Recuperar</button></td></tr>`).join("");
    return `<section class="tarjeta"><header><h2>Copia de seguridad</h2>
        <span class="subt">Un archivo con todo tu patrimonio, para guardarlo donde quieras o pasarlo a otro ordenador.</span></header>
      <div class="dosCol">
        <div class="bloque"><b>Guardar una copia</b>
          <p class="ayuda">Descarga un archivo <code>.json</code> con todos tus productos, movimientos y saldos.
            Guárdalo en tu nube o en un USB de vez en cuando.</p>
          ${propio ? `<a class="btn prim" href="api/copia/descargar" download data-acc="marcaCopia">Descargar copia</a>
            <p class="ayuda" style="margin-top:8px">${ultimaCopia ? `Última copia descargada: hace ${diasCopia} día${diasCopia === 1 ? "" : "s"}.` : "Todavía no has descargado ninguna copia."}</p>
            ${avisoCopia ? `<div class="av" style="margin-top:8px"><span>💾</span><span>${ultimaCopia ? "Hace tiempo que no guardas una copia de seguridad." : "Guarda una copia para no perder tus datos si le pasa algo al ordenador."} Pulsa «Descargar copia».</span></div>` : ""}`
            : '<span class="subt">Disponible cuando empieces tu propio patrimonio.</span>'}</div>
        <div class="bloque"><b>Recuperar desde un archivo</b>
          <p class="ayuda">Sube una copia <code>.json</code> que descargaste antes. Puedes <b>crear un patrimonio nuevo</b> con ella
            (así no pierdes el actual) o <b>sustituir</b> el que tienes abierto. En ambos casos, lo que haya ahora se guarda
            antes en «Copias automáticas» (abajo), así que podrás volver atrás.</p>
          ${zona(".json", false, "Arrastra aquí tu copia")}
          <div class="imErr" id="copFallo" hidden></div>
          <div class="imAcc" style="gap:8px"><span class="sp"></span>
            <button class="btn" data-acc="subirCopiaNuevo" id="copNuevoBtn">Crear un patrimonio nuevo</button>
            <button class="btn prim" data-acc="subirCopiaSustituir" id="copSubirBtn">Sustituir este patrimonio</button></div></div>
      </div></section>

      <section class="tarjeta"><header><h2>Copias automáticas</h2>
        <span class="subt">Antes de cada cambio se guarda una copia (las últimas 20). Si te equivocas, vuelve a una anterior.</span>
        ${propio && filas ? '<span class="sp"></span><button class="btn" data-acc="deshacer">↩ Deshacer el último cambio</button>' : ""}</header>
      ${COP.lista === null ? '<p class="cargando">Cargando…</p>' : filas
        ? `<div class="tablaEnv alto"><table class="dt"><thead><tr><th>Fecha</th><th style="text-align:left">Motivo</th>
          <th>Productos</th><th>Movimientos</th><th></th></tr></thead><tbody>${filas}</tbody></table></div>`
        : '<p class="subt">Todavía no hay copias: se crean solas en cuanto cambias algo.</p>'}</section>

      ${propio ? `<section class="tarjeta"><header><h2>Empezar de nuevo</h2>
        <span class="subt">Vacía este patrimonio o vuelve al de ejemplo. Se guarda una copia antes, por si acaso.</span>
        <span class="sp"></span><button class="btn" data-acc="reiniciar">Empezar de nuevo…</button></header></section>` : ""}

      ${propio ? `<section class="tarjeta zonaPeligro"><header><h2>Eliminar este patrimonio</h2>
        <span class="subt">Borra por completo el patrimonio que tienes abierto.</span></header>
      <p class="ayuda">Se eliminarán <b>todos los datos</b> de este patrimonio y <b>no se puede deshacer</b>. Antes de borrar
        se te descargará una copia (.json) por si acaso. Necesitas tener <b>más de un patrimonio</b> (si solo tienes este,
        crea otro desde el selector de arriba antes de poder borrarlo).</p>
      <button class="btn danger" data-acc="borrarPatrimonio">🗑 Eliminar este patrimonio…</button></section>` : ""}

      <section class="tarjeta"><header><h2>Publicar como web</h2>
        <span class="subt">Tu panel en un solo archivo, de solo lectura, para enseñarlo o subirlo a internet.</span></header>
      <label class="interruptor"><input type="checkbox" id="webOcultar"><span class="pista"></span>
        <span><b>Ocultar importes</b><small>Solo se ven porcentajes y la forma de las gráficas. Las cantidades reales no
          van dentro del archivo, ni siquiera escondidas.</small></span></label>
      <ol class="pasos" style="margin-top:18px">
        <li><button class="btn prim" data-acc="exportarWeb">Descargar la web</button>
          Puedes abrirla con doble clic o mandarla por correo.</li>
        <li>Para tener un enlace: crea una carpeta, mete dentro el archivo, cámbiale el nombre a <code>index.html</code>
          y arrastra la carpeta a <a href="https://app.netlify.com/drop" target="_blank" rel="noopener">app.netlify.com/drop</a>.
          En unos segundos te da una dirección para compartir.</li>
      </ol>
      <p class="ayuda">La web lleva la fecha de hoy: cuando actualices tus datos, vuelve a descargarla y súbela otra vez.</p></section>`;
  }

  async function subirCopia(destino) {
    const inp = $("#imArchivos"), fallo = $("#copFallo");
    fallo.hidden = true;
    if (!inp.files.length) { fallo.textContent = "Elige primero el archivo de la copia."; fallo.hidden = false; return; }
    if (destino === "nuevo") {
      const nombre = (prompt("Nombre del nuevo patrimonio (déjalo vacío para usar el de la copia):") || "").trim();
      return enviaCopia("nuevo", nombre);
    }
    if (E.modo !== "propio") return enviaCopia("sustituir");
    // Sustituir: modal de confirmación que NOMBRA el patrimonio que se va a reemplazar.
    abreModal("Sustituir patrimonio", `
      <p>Vas a <b>sustituir</b> por completo el patrimonio <b>«${esc(E.cfg.titular || "Mi patrimonio")}»</b> por el de la copia que has elegido.</p>
      <p class="ayuda">El patrimonio actual se guarda antes en <b>«Copias automáticas»</b> (abajo), así que podrás volver atrás si te arrepientes.</p>`,
    async () => { await enviaCopia("sustituir"); }, "Sustituir este patrimonio");
  }

  async function enviaCopia(destino, nombre) {
    const inp = $("#imArchivos");
    const fd = new FormData();
    fd.append("archivo", inp.files[0]);
    if (destino === "nuevo") { fd.append("destino", "nuevo"); if (nombre) fd.append("nombre", nombre); }
    const r = await fetch("api/copia/subir", { method: "POST", body: fd });
    const j = await r.json().catch(() => ({}));
    if (!r.ok || !j.ok) {
      const msg = (j.errores || ["No he podido leer la copia."]).join("\n");
      const fallo = $("#copFallo");
      if (fallo) { fallo.textContent = msg; fallo.hidden = false; }
      throw new Error(msg);   // si venimos de un modal, lo muestra ahí también
    }
    recuerda.guarda("patrimonio.tab", "datos");
    recuerda.guarda("patrimonio.editor", "activos");
    location.reload();
  }

  async function recuperarCopia(archivo) {
    const c = COP.lista.find(x => x.archivo === archivo);
    if (!confirm(`¿Volver a la copia del ${fecha(c.fecha.slice(0, 10))} a las ${c.fecha.slice(11, 16)} (${c.productos} productos, ${c.movimientos} movimientos)?\n\nTu patrimonio actual se guarda antes, así que puedes deshacerlo.`)) return;
    try {
      await api("POST", "api/copia/recuperar", { archivo });
      recuerda.guarda("patrimonio.tab", "datos");
      location.reload();
    } catch (x) { alert(x.message); }
  }

  /* ---------------------------------------------- aviso y descarga de versión nueva */
  // Descarga el .exe de la última versión y lo deja JUNTO al actual (nombre con versión,
  // p. ej. «Liberty 1.8.2.exe»). No ejecuta ni sobrescribe nada: solo descarga + escribe.
  // Usa fetch crudo porque el endpoint devuelve ok:false (200) en casos normales (dev/al día).
  function actualizaLiberty(btn, onMsg) {
    const etq = btn ? btn.textContent : "";
    if (btn) { btn.disabled = true; btn.textContent = "Descargando… (puede tardar un poco)"; }
    const reactiva = () => { if (btn) { btn.disabled = false; btn.textContent = etq || "⬇ Descargar la nueva versión"; } };
    return fetch("api/descargar-version", { method: "POST", headers: { "Content-Type": "application/json" } })
      .then(r => r.json())
      .then(res => {
        if (res.ok) {
          onMsg(`<b>✅ Descargada la versión ${esc(res.ultima)}</b> como <code>${esc(res.archivo)}</code> en la carpeta de la app
            (te he abierto la carpeta). <b>Cierra Liberty y abre ese archivo.</b> Cuando veas que va bien, puedes borrar el anterior.`, true);
        } else {
          const web = res.descarga ? ` <a href="${esc(res.descarga)}" target="_blank" rel="noopener">Abrir la web de Liberty</a>.` : "";
          onMsg(`${esc(res.mensaje || "No se ha podido actualizar.")}${web}`, false);
          reactiva();
        }
      })
      .catch(() => {
        onMsg(`No se ha podido conectar. <a href="https://alonsovine.github.io/liberty/" target="_blank" rel="noopener">Abrir la web de Liberty</a>.`, false);
        reactiva();
      });
  }
  window.actualizaLiberty = actualizaLiberty;
  // Botón siempre visible en Ayuda: descarga la última versión aquí mismo (si corre como .exe).
  {
    const bAqui = $("#btnDescargarAqui");
    if (bAqui) bAqui.onclick = () => {
      const est = $("#descargaAquiEstado");
      if (est) { est.hidden = false; est.innerHTML = "Descargando…"; }
      actualizaLiberty(bAqui, (html, ok) => {
        if (est) { est.hidden = false; est.innerHTML = html; est.classList.toggle("ok", !!ok); }
      });
    };
  }
  api("GET", "api/version").then(v => {
    const pie = $("#ayudaVersion");
    if (pie) pie.innerHTML = `Versión ${esc(v.actual)}. ¿Otra duda o un fallo? Cuéntalo en la
      <a href="${esc(v.repo)}" target="_blank" rel="noopener">página del proyecto en GitHub</a>.`;
    if (!v.hayNueva) return;
    const t = $("#bannerVersionTexto");
    t.innerHTML = `<b>Hay una versión nueva (${esc(v.ultima)}).</b>
      Puedo descargártela y dejarla junto a la actual (se llamará <code>Liberty ${esc(v.ultima)}.exe</code>), para que solo tengas que abrirla.
      <button type="button" class="btn mini" id="btnActualizar">⬇ Descargar la nueva versión</button>
      <span class="subt"> · o a mano en <a href="${esc(v.descarga || v.repo)}" target="_blank" rel="noopener">la web</a></span>`;
    const btn = $("#btnActualizar");
    if (btn) btn.onclick = () => actualizaLiberty(btn, html => { t.innerHTML = html; });
    $("#bannerVersion").hidden = false;
  }).catch(() => { /* sin internet: no pasa nada */ });

  /* ---------------------------------------------- acciones */
  const ACC = {
    empezar,
    reiniciar,
    verNotas: ref => window.Editor && window.Editor.verEntidad(ref),
    borrarPatrimonio: soloPropio(() => { if (window.borrarPatrimonio) window.borrarPatrimonio(); }),
    verPanel() { recuerda.guarda("patrimonio.tab", "panel"); location.reload(); },
    nuevoProducto: soloPropio(() => formProducto(null)),
    nuevaDeuda: soloPropio(() => formProducto(null, "deuda")),
    irImportar() { E.vista = "importar"; recuerda.guarda("patrimonio.editor", "importar"); pinta(); },
    ocultarAsistente: soloPropio(async () => {
      try { await guardaConfig({ asistenteOculto: true }); pinta(); } catch (x) { alert(x.message); }
    }),
    editarProducto: soloPropio(id => formProducto(prod(id))),
    duplicarProducto: soloPropio(id => { const p = prod(id); if (p) formProducto({ ...p, id: undefined, slot: siguienteColor(), nombre: (p.nombre || "") + " (copia)" }); }),
    borrarProducto: soloPropio(borrarProducto),
    nuevoMov: soloPropio(() => formMovimiento(null)),
    editarMov: soloPropio(id => formMovimiento(E.cfg.movimientos.find(m => m.id === id))),
    duplicarMov: soloPropio(id => { const m = E.cfg.movimientos.find(x => x.id === id); if (m) formMovimiento({ ...m, id: undefined }); }),
    borrarMov: soloPropio(borrarMov),
    nuevoValor: soloPropio(id => formValor(null, id)),
    editarValor: soloPropio(id => formValor(E.cfg.valoraciones.find(v => v.id === id))),
    borrarValor: soloPropio(borrarValor),
    todosValores: soloPropio(todosValores),
    menuMarca: soloPropio(id => abreMenuMarca(id)),
    verObs: soloPropio(id => abreObs(id)),
    nuevoApartado: soloPropio(() => formApartado(null)),
    editarApartado: soloPropio(id => formApartado((E.cfg.apartados || []).find(a => a.id === id))),
    borrarApartado: soloPropio(borrarApartado),
    editarConfig: soloPropio(formHogar),
    nuevoFlujo: soloPropio(() => formFlujo(null)),
    editarFlujo: soloPropio(id => formFlujo((E.cfg.flujos || []).find(x => x.id === id))),
    borrarFlujo: soloPropio(borrarFlujo),
    repartirColores: soloPropio(async () => {
      try {
        const j = await api("POST", "api/repartir-colores");
        E.cfg = j.cartera;
        window.EDITOR_SUCIO = true;
        pinta();
        avisa(["✓ Colores repartidos: cada elemento tiene ahora un color distinto. Se verá en el panel."]);
      } catch (x) { alert(x.message); }
    }),
    repartirColoresApartados: soloPropio(async () => {
      try {
        const j = await api("POST", "api/repartir-colores", { que: "apartados" });
        E.cfg = j.cartera;
        window.EDITOR_SUCIO = true;
        pinta();
        avisa(["✓ Colores repartidos entre los reservados."]);
      } catch (x) { alert(x.message); }
    }),
    imDestino(id) {
      if (IMP.destino === id) return;
      IMP.destino = id;
      // MyInvestor solo aplica a activos; al ir al banco, caer en «Plantilla».
      if (id === "banco" && IMP.origen === "myinvestor") IMP.origen = "plantilla";
      IMP.hecho = null; IMP.prompt = null; IMP.informe = null; IMP.token = null;
      pinta();
    },
    imOrigen(id) { IMP.origen = id; IMP.hecho = null; IMP.prompt = null; pinta(); },
    imRevisar: soloPropio(imRevisar),
    imCancelar() { IMP.informe = null; IMP.token = null; pinta(); },
    imConfirmar,
    subirCopiaSustituir: () => subirCopia("sustituir"),
    subirCopiaNuevo: () => subirCopia("nuevo"),
    recuperarCopia,
    marcaCopia() { try { recuerda.guarda("patrimonio.ultimaCopia", new Date().toISOString()); } catch (e) { /* noop */ } },
    deshacer: soloPropio(() => {
      const lista = (COP.lista || []).slice().sort((a, b) => (a.fecha < b.fecha ? 1 : -1));
      if (!lista.length) { alert("Todavía no hay ningún cambio que deshacer."); return; }
      recuperarCopia(lista[0].archivo);
    }),
    exportarWeb() { location.href = "api/exportar-web?ocultar=" + ($("#webOcultar").checked ? "1" : "0"); },
    verPanelDatos() { recuerda.guarda("patrimonio.tab", "panel"); location.reload(); },
    async imCopiar() {
      const url = IMP.destino === "banco" ? "api/prompt-banco" : "api/prompt";
      const txt = IMP.prompt || (await api("GET", url)).texto;
      IMP.prompt = txt;
      try { await navigator.clipboard.writeText(txt); } catch (e) {
        const ta = document.createElement("textarea"); ta.value = txt; document.body.appendChild(ta); ta.select();
        document.execCommand("copy"); ta.remove();
      }
      const b = $("#imCopiarBtn");
      if (b) { b.textContent = "✓ Copiado"; setTimeout(() => { b.textContent = "Copiar prompt"; }, 2000); }
    },
  };
  document.addEventListener("click", e => {
    const b = e.target.closest("[data-acc]");
    if (b && ACC[b.dataset.acc]) ACC[b.dataset.acc](b.dataset.id);
  });
  const btnEmpezar = $("#btnEmpezar");
  if (btnEmpezar) btnEmpezar.onclick = empezar;

  /* ---------------------------------------------- el canal del autor */
  // Una tarjeta pequeña, la primera vez que ves tu propio panel con datos. Si pulsas
  // «Ahora no», vuelve como mucho una vez más al cabo de un mes; luego, nunca.
  (function canal() {
    const K = window.CANAL;
    if (!K) return;
    document.querySelectorAll(".autorCanal").forEach(el => { el.textContent = K.autor; });
    document.querySelectorAll(".enlaceCanal").forEach(el => { el.href = K.canal; });
    document.querySelectorAll(".enlaceSuscribir").forEach(el => { el.href = K.suscribir; });
    const tut = $("#ayudaTutorial");
    if (tut) tut.href = K.tutorial || K.canal + "/videos";

    if (!D || D.modo !== "propio" || !(D.productos || []).length) return;
    let est = {};
    try { est = JSON.parse(recuerda.lee("patrimonio.canal") || "{}"); } catch (e) { est = {}; }
    const MES = 30 * 24 * 3600 * 1000;
    if (est.hecho || (est.veces || 0) >= 2 || (est.veces === 1 && Date.now() - (est.ultima || 0) < MES)) return;
    const guarda = cambios => recuerda.guarda("patrimonio.canal", JSON.stringify({ ...est, ...cambios }));

    setTimeout(() => {
      if (document.body.classList.contains("video") || $("#modal").open) return;
      const t = document.createElement("div");
      t.className = "tarjetaCanal";
      t.setAttribute("role", "dialog");
      t.innerHTML = `<button class="x" aria-label="Cerrar">×</button>
        <b>¿Te está siendo útil?</b>
        <p>Liberty es gratuita. Si te sirve, puedes ver en qué más trabajo y seguirme. — ${esc(K.autorApp)}</p>
        <div class="botones"><a class="btn prim" href="${esc(K.portfolio)}" target="_blank" rel="noopener">🌐 Mi portfolio</a>
          <a class="btn" href="${esc(K.linkedin)}" target="_blank" rel="noopener">💼 LinkedIn</a>
          <button class="ahoraNo">Ahora no</button></div>
        <p class="canalNota">Liberty es un fork de <a href="${esc(K.rumbo)}" target="_blank" rel="noopener">Rumbo</a>, de ${esc(K.autor)} — si te interesan las inversiones, también puedes <a href="${esc(K.canal)}" target="_blank" rel="noopener">seguir su canal</a>.</p>`;
      const cierra = () => { t.remove(); guarda({ veces: (est.veces || 0) + 1, ultima: Date.now() }); };
      t.querySelector(".x").onclick = cierra;
      t.querySelector(".ahoraNo").onclick = cierra;
      t.querySelector("a").onclick = () => { guarda({ hecho: true }); setTimeout(() => t.remove(), 300); };
      document.body.appendChild(t);
    }, 6000);
  })();

  /* ---------------------------------------------- Notas (lista + tablero + agenda) */
  async function guardaNotas(notas) {
    const j = await api("POST", "api/notas", { notas });
    E.cfg = j.cartera; pintarNotas();   // no marca EDITOR_SUCIO: no afecta al panel
  }
  async function guardaTablero(tablero) {
    const j = await api("POST", "api/tablero", { tablero });
    E.cfg = j.cartera; pintarNotas();
  }
  async function guardaRecordatorios(recordatorios) {
    const j = await api("POST", "api/recordatorios", { recordatorios });
    E.cfg = j.cartera; pintarNotas();
  }
  // Días desde hoy hasta una fecha ISO (negativo = ya pasó).
  function diasHasta(iso) {
    const h = new Date(); h.setHours(0, 0, 0, 0);
    const d = new Date(iso + "T00:00:00");
    return Math.round((d - h) / 86400000);
  }
  // Para recordatorios que se repiten: la próxima ocurrencia a partir de hoy.
  function proximaFecha(iso, repetir) {
    if (repetir === "no") return iso;
    const d = new Date(iso + "T00:00:00"), h = new Date(); h.setHours(0, 0, 0, 0);
    let guarda = 0;
    while (d < h && guarda++ < 600) {
      if (repetir === "mensual") d.setMonth(d.getMonth() + 1); else d.setFullYear(d.getFullYear() + 1);
    }
    return d.toISOString().slice(0, 10);
  }
  const VINC_ETIQ = { activo: "activo", deuda: "deuda", reservado: "reservado", categoria: "categoría" };
  function nombreVinculo(v) {
    if (!v) return "";
    if (v.tipo === "categoria") return v.ref;
    if (v.tipo === "reservado") { const a = (E.cfg.apartados || []).find(x => x.id === v.ref); return a ? a.nombre : v.ref; }
    const p = (E.cfg.productos || []).find(x => x.id === v.ref);
    return p ? nombre(p) : v.ref;
  }
  function opcionesRefNota(tipo, sel) {
    const prods = E.cfg.productos || [];
    const lista = tipo === "activo" ? prods.filter(p => p.tipo !== "deuda").map(p => ({ v: p.id, t: nombre(p) }))
      : tipo === "deuda" ? prods.filter(p => p.tipo === "deuda").map(p => ({ v: p.id, t: nombre(p) }))
      : tipo === "reservado" ? (E.cfg.apartados || []).map(a => ({ v: a.id, t: a.nombre }))
      : tipo === "categoria" ? ((E.cfg.config || {}).categorias || []).map(c => ({ v: c.nombre, t: c.nombre })) : [];
    return `<option value="">—</option>` + lista.map(o => `<option value="${esc(o.v)}"${o.v === sel ? " selected" : ""}>${esc(o.t)}</option>`).join("");
  }
  // Selector de vínculo reutilizable (nota y recordatorio). «categoría» solo aparece si
  // la entidad ya la tenía (legado); los nuevos se enlazan a activo/deuda/reservado.
  function vinculoCamposHTML(vinc) {
    vinc = vinc || {};
    const legado = vinc.tipo === "categoria";
    return `${campo("Relacionar con", `<select name="vinculoTipo">
        <option value="">Nada</option>
        <option value="activo"${vinc.tipo === "activo" ? " selected" : ""}>Un activo</option>
        <option value="deuda"${vinc.tipo === "deuda" ? " selected" : ""}>Una deuda</option>
        <option value="reservado"${vinc.tipo === "reservado" ? " selected" : ""}>Un reservado</option>
        ${legado ? '<option value="categoria" selected>Una categoría (antigua)</option>' : ""}</select>`)}
      ${campo("¿Cuál?", `<select name="vinculoRef">${opcionesRefNota(vinc.tipo || "", vinc.ref || "")}</select>`)}`;
  }
  function wireVinculo(f) {
    if (!f.elements.vinculoTipo) return;
    f.elements.vinculoTipo.onchange = () => { f.elements.vinculoRef.innerHTML = opcionesRefNota(f.elements.vinculoTipo.value, ""); };
  }
  function leeVinculo(d) { return d.vinculoTipo && d.vinculoRef ? { tipo: d.vinculoTipo, ref: d.vinculoRef } : null; }
  function formNota(n) {
    const nuevo = !n; n = n || {};
    const vinc = n.vinculo || {};
    const f = abreModal(nuevo ? "Nueva nota" : "Editar nota", `
      <div class="rejilla">
        ${campo("Título", '<input name="titulo" maxlength="120">', "", "ancho")}
        ${campo("Texto", '<textarea name="texto" rows="7"></textarea>', "Para una lista de tareas, escribe «- [ ] comprar X» (se vuelve una casilla).", "ancho")}
        ${campo("Etiquetas", '<input name="etiquetas" placeholder="casa, urgente, revisar">', "sepáralas por comas", "ancho")}
        ${campo("Fijar arriba", '<label class="chkLinea"><input type="checkbox" name="fijada"> Mantener esta nota arriba del todo</label>', "", "ancho")}
        ${vinculoCamposHTML(vinc)}
      </div>`,
    async f => {
      const d = campos(f);
      const etiquetas = (d.etiquetas || "").split(/[,\n;]/).map(s => s.trim()).filter(Boolean);
      const vinculo = leeVinculo(d);
      const comun = { titulo: d.titulo, texto: d.texto, etiquetas, fijada: !!f.elements.fijada.checked, editada: hoy() };
      if (vinculo) comun.vinculo = vinculo;
      const notas = (E.cfg.notas || []).slice();
      if (nuevo) notas.push({ id: "n" + Date.now(), fecha: hoy(), ...comun });
      else { const i = notas.findIndex(x => x.id === n.id); if (i >= 0) { const { vinculo: _v, ...resto } = notas[i]; notas[i] = { ...resto, ...comun }; } }
      await guardaNotas(notas);
    }, "Guardar");
    rellena(f, n);
    wireVinculo(f);
    f.elements.etiquetas.value = (n.etiquetas || []).join(", ");
    f.elements.fijada.checked = !!n.fijada;
    return f;
  }

  // Texto de una nota como HTML: las líneas «- [ ] algo» se vuelven casillas marcables.
  function notaTextoHTML(n) {
    return String(n.texto || "").split("\n").map((ln, i) => {
      const m = ln.match(/^(\s*)[-*]\s+\[([ xX])\]\s?(.*)$/);
      if (m) {
        const hecha = m[2].toLowerCase() === "x";
        return `<label class="notaChk${hecha ? " hecha" : ""}"><input type="checkbox"${hecha ? " checked" : ""} data-chk="${esc(n.id)}" data-ln="${i}"><span>${esc(m[3])}</span></label>`;
      }
      return `<div class="notaLn">${esc(ln) || "&nbsp;"}</div>`;
    }).join("");
  }
  function montaNotasLista() {
    const cont = $("#notasCuerpo"); if (!cont) return;
    const busca = (E.notaBusca || "").trim().toLowerCase();
    const tagSel = E.notaTag || "";
    const orden = E.notaOrden || "fecha";
    const tagsTodas = [...new Set((E.cfg.notas || []).flatMap(n => n.etiquetas || []))].sort((a, b) => a.localeCompare(b));
    const vincRef = E.notaVincRef || "";
    let notas = (E.cfg.notas || []).slice();
    if (vincRef) notas = notas.filter(n => n.vinculo && n.vinculo.ref === vincRef);
    if (busca) notas = notas.filter(n => ((n.titulo || "") + " " + (n.texto || "") + " " + (n.etiquetas || []).join(" ")).toLowerCase().includes(busca));
    if (tagSel) notas = notas.filter(n => (n.etiquetas || []).includes(tagSel));
    notas.sort((a, b) => {
      if (!!b.fijada !== !!a.fijada) return a.fijada ? -1 : 1;    // fijadas primero
      if (orden === "titulo") return (a.titulo || "").localeCompare(b.titulo || "");
      return a.fecha < b.fecha ? 1 : a.fecha > b.fecha ? -1 : 0;  // por fecha, recientes primero
    });
    const card = n => {
      const tags = (n.etiquetas || []).map(t => `<button class="notaTag" data-tagf="${esc(t)}">${esc(t)}</button>`).join("");
      const vinc = n.vinculo ? `<span class="notaVinc" title="Relacionada con ${esc(n.vinculo.tipo)}">🔗 ${esc(nombreVinculo(n.vinculo))}</span>` : "";
      const ed = n.editada && n.editada !== n.fecha ? ` · editada ${fecha(n.editada)}` : "";
      return `<div class="notaCard${n.fijada ? " fijada" : ""}">
        <div class="notaCabe"><div class="notaTit">${esc(n.titulo || "(sin título)")}</div>
          <button class="notaPin${n.fijada ? " on" : ""}" data-nacc="fijar" data-id="${esc(n.id)}" title="${n.fijada ? "Dejar de fijar" : "Fijar arriba"}" aria-label="Fijar">📌</button></div>
        <div class="notaTxt">${notaTextoHTML(n)}</div>
        ${(tags || vinc) ? `<div class="notaMeta">${vinc}${tags}</div>` : ""}
        <div class="notaPie"><span class="subt">${fecha(n.fecha)}${ed}</span><span class="sp"></span>
          <button class="btn mini" data-nacc="editar" data-id="${esc(n.id)}">Editar</button>
          <button class="btn mini" data-nacc="borrar" data-id="${esc(n.id)}">Borrar</button></div></div>`;
    };
    const hayNotas = (E.cfg.notas || []).length > 0;
    const herramientas = hayNotas ? `<div class="notasTools">
        <label class="buscaTabla">${LUPA}<input type="search" data-nbusca placeholder="Buscar en notas…" value="${esc(E.notaBusca || "")}" aria-label="Buscar notas"></label>
        ${tagsTodas.length ? `<select data-ntag aria-label="Filtrar por etiqueta"><option value="">Todas las etiquetas</option>${tagsTodas.map(t => `<option value="${esc(t)}"${t === tagSel ? " selected" : ""}>${esc(t)}</option>`).join("")}</select>` : ""}
        <select data-norden aria-label="Ordenar"><option value="fecha"${orden === "fecha" ? " selected" : ""}>Más recientes</option><option value="titulo"${orden === "titulo" ? " selected" : ""}>Por título</option></select>
      </div>` : "";
    const cards = notas.map(card).join("");
    let nomEnt = vincRef;
    if (vincRef) { const p = (E.cfg.productos || []).find(x => x.id === vincRef); const a = (E.cfg.apartados || []).find(x => x.id === vincRef); nomEnt = p ? nombre(p) : a ? a.nombre : vincRef; }
    const banner = vincRef ? `<div class="notaFiltroEnt">Notas de <b>${esc(nomEnt)}</b> <button class="btn mini" data-limpiavinc>✕ ver todas</button></div>` : "";
    cont.innerHTML = `<section class="tarjeta"><header><h2>Notas</h2>
        <span class="subt">Apuntes libres: ideas, pendientes, enlaces… (no afectan a tus cifras)</span>
        <span class="sp"></span><button class="btn prim" data-nacc="nueva">+ Nueva nota</button></header>
      ${banner}${herramientas}
      ${!hayNotas ? '<p class="subt">Todavía no has escrito ninguna nota.</p>'
        : cards ? `<div class="notasGrid">${cards}</div>`
        : vincRef ? '<p class="subt">No hay notas asociadas a esto todavía.</p>' : '<p class="subt">Ninguna nota coincide con la búsqueda.</p>'}</section>`;
    const lv = cont.querySelector("[data-limpiavinc]"); if (lv) lv.onclick = () => { E.notaVincRef = null; montaNotasLista(); };
    const refiltra = () => montaNotasLista();
    const bq = cont.querySelector("[data-nbusca]");
    if (bq) bq.oninput = e => { E.notaBusca = e.target.value; const pos = bq.selectionStart; refiltra(); const nb = $("[data-nbusca]"); if (nb) { nb.focus(); try { nb.setSelectionRange(pos, pos); } catch (_) { /* */ } } };
    const tsel = cont.querySelector("[data-ntag]"); if (tsel) tsel.onchange = e => { E.notaTag = e.target.value; refiltra(); };
    const osel = cont.querySelector("[data-norden]"); if (osel) osel.onchange = e => { E.notaOrden = e.target.value; recuerda.guarda("patrimonio.notaOrden", e.target.value); refiltra(); };
    cont.querySelectorAll("[data-tagf]").forEach(b => b.onclick = () => { E.notaTag = b.dataset.tagf; refiltra(); });
    cont.querySelectorAll("[data-chk]").forEach(cb => cb.onchange = () => {
      const notas = (E.cfg.notas || []).slice();
      const i = notas.findIndex(x => x.id === cb.dataset.chk); if (i < 0) return;
      const ls = String(notas[i].texto || "").split("\n"); const k = +cb.dataset.ln;
      ls[k] = ls[k].replace(/\[([ xX])\]/, (mm, c) => c.toLowerCase() === "x" ? "[ ]" : "[x]");
      notas[i] = { ...notas[i], texto: ls.join("\n"), editada: hoy() };
      guardaNotas(notas);
    });
    cont.querySelectorAll("[data-nacc]").forEach(b => {
      b.onclick = () => {
        const id = b.dataset.id, acc = b.dataset.nacc;
        if (acc === "nueva") return formNota(null);
        const n = (E.cfg.notas || []).find(x => x.id === id);
        if (acc === "editar") return formNota(n);
        if (acc === "fijar") { const l = (E.cfg.notas || []).map(x => x.id === id ? { ...x, fijada: !x.fijada } : x); return guardaNotas(l); }
        if (acc === "borrar" && confirm(`¿Borrar la nota «${n ? (n.titulo || "sin título") : ""}»?`)) {
          guardaNotas((E.cfg.notas || []).filter(x => x.id !== id));
        }
      };
    });
  }

  const TABLERO_DEFECTO = () => ({ columnas: [{ id: "porhacer", nombre: "Por hacer" }, { id: "encurso", nombre: "En curso" }, { id: "hecho", nombre: "Hecho" }], tarjetas: [] });
  const COLORES_TARJETA = ["", "s6", "s2", "s8", "s14", "s11"];   // "" = sin color
  function montaTablero() {
    const cont = $("#notasCuerpo"); if (!cont) return;
    let tab = E.cfg.tablero;
    if (!tab || !(tab.columnas || []).length) tab = TABLERO_DEFECTO();
    const guardar = () => guardaTablero(tab);
    const tarjetaHTML = t => {
      const borde = t.color ? ` style="border-left:4px solid var(--${esc(t.color)})"` : "";
      let venceChip = "";
      if (t.vence) { const d = diasHasta(t.vence); venceChip = `<span class="kVence${d < 0 ? " vencido" : d <= 7 ? " cerca" : ""}">📅 ${fecha(t.vence)}</span>`; }
      return `<div class="kCard" draggable="true" data-id="${esc(t.id)}"${borde}>
        <div class="kTxt" data-tedit="${esc(t.id)}" title="Doble clic para editar">${esc(t.texto).replace(/\n/g, "<br>")}</div>
        <button class="kDel" data-tdel="${esc(t.id)}" title="Borrar tarjeta" aria-label="Borrar">×</button>
        ${venceChip ? `<div class="kMeta">${venceChip}</div>` : ""}</div>`;
    };
    const cols = tab.columnas.map(c => {
      const dec = (tab.tarjetas || []).filter(t => t.col === c.id);
      return `<div class="kCol"><div class="kColHead"><b>${esc(c.nombre)}</b><span class="kCount">${dec.length}</span><span class="sp"></span>
          <button class="kIco" data-cren="${esc(c.id)}" title="Renombrar columna">✎</button>
          <button class="kIco" data-cdel="${esc(c.id)}" title="Borrar columna">🗑</button></div>
        <div class="kCards" data-col="${esc(c.id)}">${dec.map(tarjetaHTML).join("")}</div>
        <button class="kAdd" data-cadd="${esc(c.id)}">+ Tarjeta</button></div>`;
    }).join("");
    cont.innerHTML = `<section class="tarjeta"><header><h2>Tablero</h2>
        <span class="subt">Tipo Trello: arrastra para mover u ordenar. Doble clic en una tarjeta para editarla.</span>
        <span class="sp"></span><button class="btn" data-knuevacol>+ Columna</button></header>
      <div class="kBoard">${cols}</div></section>`;

    // Editor inline de tarjeta (nueva o existente): textarea + colores + fecha.
    function abreEditorTarjeta(ancla, colId, t) {
      if (cont.querySelector(".kEditor")) return;        // uno a la vez
      const ed = document.createElement("div");
      ed.className = "kEditor";
      ed.innerHTML = `<textarea class="kEdTxt" rows="2" placeholder="Texto de la tarjeta">${t ? esc(t.texto) : ""}</textarea>
        <div class="kEdColores">${COLORES_TARJETA.map(c => `<button type="button" class="kColor${(t && t.color || "") === c ? " sel" : ""}" data-color="${c}" title="${c ? "Color" : "Sin color"}"${c ? ` style="background:var(--${c})"` : ""}>${c ? "" : "∅"}</button>`).join("")}
          <input type="date" class="kEdVence" value="${t && t.vence ? esc(t.vence) : ""}" title="Fecha de vencimiento (opcional)"></div>
        <div class="kEdAcc"><button type="button" class="btn mini prim" data-edok>Guardar</button><button type="button" class="btn mini" data-edcancel>Cancelar</button></div>`;
      if (t) { ancla.replaceWith(ed); } else { ancla.before(ed); }
      let color = (t && t.color) || "";
      ed.querySelectorAll("[data-color]").forEach(b => b.onclick = () => { color = b.dataset.color; ed.querySelectorAll("[data-color]").forEach(x => x.classList.toggle("sel", x === b)); });
      const ta = ed.querySelector(".kEdTxt"); ta.focus();
      const cancelar = () => montaTablero();
      const ok = () => {
        const txt = ta.value.trim(); if (!txt) return cancelar();
        const vence = ed.querySelector(".kEdVence").value || "";
        if (t) {
          const i = (tab.tarjetas || []).findIndex(x => x.id === t.id);
          if (i >= 0) { const { color: _c, vence: _v, ...resto } = tab.tarjetas[i]; tab.tarjetas[i] = { ...resto, texto: txt, ...(color ? { color } : {}), ...(vence ? { vence } : {}) }; }
        } else {
          (tab.tarjetas = tab.tarjetas || []).push({ id: "t" + Date.now(), col: colId, texto: txt, ...(color ? { color } : {}), ...(vence ? { vence } : {}) });
        }
        guardar();
      };
      ed.querySelector("[data-edok]").onclick = ok;
      ed.querySelector("[data-edcancel]").onclick = cancelar;
      ta.onkeydown = e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ok(); } if (e.key === "Escape") cancelar(); };
    }
    cont.querySelector("[data-knuevacol]").onclick = () => {
      const nombre = (prompt("Nombre de la nueva columna:") || "").trim();
      if (!nombre) return;
      tab.columnas.push({ id: "c" + Date.now(), nombre }); guardar();
    };
    cont.querySelectorAll("[data-cadd]").forEach(b => b.onclick = () => abreEditorTarjeta(b, b.dataset.cadd, null));
    cont.querySelectorAll("[data-tedit]").forEach(el => el.ondblclick = () => {
      const t = (tab.tarjetas || []).find(x => x.id === el.dataset.tedit);
      if (t) abreEditorTarjeta(el.closest(".kCard"), t.col, t);
    });
    cont.querySelectorAll("[data-tdel]").forEach(b => b.onclick = () => {
      tab.tarjetas = (tab.tarjetas || []).filter(t => t.id !== b.dataset.tdel); guardar();
    });
    cont.querySelectorAll("[data-cren]").forEach(b => b.onclick = () => {
      const c = tab.columnas.find(x => x.id === b.dataset.cren);
      const nombre = (prompt("Nuevo nombre:", c ? c.nombre : "") || "").trim();
      if (c && nombre) { c.nombre = nombre; guardar(); }
    });
    cont.querySelectorAll("[data-cdel]").forEach(b => b.onclick = () => {
      if (!confirm("¿Borrar esta columna y sus tarjetas?")) return;
      tab.columnas = tab.columnas.filter(x => x.id !== b.dataset.cdel);
      tab.tarjetas = (tab.tarjetas || []).filter(t => t.col !== b.dataset.cdel); guardar();
    });
    // Arrastrar: mover entre columnas Y reordenar dentro de una columna.
    let dragId = null;
    function mueve(id, col, antesId) {
      const arr = tab.tarjetas || [], card = arr.find(t => t.id === id); if (!card) return;
      card.col = col;
      const sin = arr.filter(t => t.id !== id), out = []; let ins = false;
      for (const t of sin) { if (t.id === antesId) { out.push(card); ins = true; } out.push(t); }
      if (!ins) out.push(card);
      tab.tarjetas = out; guardar();
    }
    cont.querySelectorAll(".kCard").forEach(card => {
      card.addEventListener("dragstart", e => { dragId = card.dataset.id; card.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; });
      card.addEventListener("dragend", () => card.classList.remove("dragging"));
    });
    cont.querySelectorAll(".kCards").forEach(zone => {
      zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("over"); });
      zone.addEventListener("dragleave", () => zone.classList.remove("over"));
      zone.addEventListener("drop", e => {
        e.preventDefault(); zone.classList.remove("over");
        if (!dragId) return;
        let antes = null;
        for (const el of zone.querySelectorAll(".kCard:not(.dragging)")) {
          const r = el.getBoundingClientRect();
          if (e.clientY < r.top + r.height / 2) { antes = el.dataset.id; break; }
        }
        mueve(dragId, zone.dataset.col, antes); dragId = null;
      });
    });
  }

  function formRecordatorio(r, fechaPrefijada) {
    const nuevo = !r; r = r || {};
    const vinc = r.vinculo || {};
    const f = abreModal(nuevo ? "Nuevo recordatorio" : "Editar recordatorio", `
      <div class="rejilla">
        ${campo("Qué", '<input name="texto" maxlength="300" placeholder="Renovar el seguro del coche">', "", "ancho")}
        ${campo("Fecha", '<input name="fecha" type="date" required>')}
        ${campo("Repetir", `<select name="repetir"><option value="no">No se repite</option><option value="mensual">Cada mes</option><option value="anual">Cada año</option></select>`)}
        ${vinculoCamposHTML(vinc)}
      </div>`,
    async f => {
      const d = campos(f);
      const vinculo = leeVinculo(d);
      const base = { texto: d.texto, fecha: d.fecha, repetir: d.repetir };
      const lista = (E.cfg.recordatorios || []).slice();
      if (nuevo) lista.push({ id: "r" + Date.now(), ...base, hecho: false, ...(vinculo ? { vinculo } : {}) });
      else { const i = lista.findIndex(x => x.id === r.id); if (i >= 0) { const { vinculo: _v, ...resto } = lista[i]; lista[i] = { ...resto, ...base, ...(vinculo ? { vinculo } : {}) }; } }
      await guardaRecordatorios(lista);
    }, "Guardar");
    rellena(f, r);
    wireVinculo(f);
    if (nuevo && fechaPrefijada) f.elements.fecha.value = fechaPrefijada;
    return f;
  }
  const MESES_LARGO = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  // Items unificados de la agenda (recordatorios con fecha efectiva + vencimientos).
  function agendaItems() {
    const items = [];
    (E.cfg.recordatorios || []).forEach(r => {
      const fEff = (r.repetir !== "no" && !r.hecho) ? proximaFecha(r.fecha, r.repetir) : r.fecha;
      items.push({ clase: "rec", id: r.id, texto: r.texto, fecha: fEff, hecho: !!r.hecho, repetir: r.repetir, vinculo: r.vinculo });
    });
    ((window.DATOS && window.DATOS.vencimientos) || []).forEach(v => items.push({ clase: "venc", texto: v.nombre, fecha: v.fecha,
      meta: (v.clase || "") + (v.entidad ? " · " + v.entidad : ""), tipo: v.tipo, estado: v.estado }));
    // Tarjetas del tablero que tengan fecha de vencimiento (solo lectura en la agenda;
    // se gestionan en el Tablero). Se muestran diferenciadas con un badge «Tablero».
    const tab = E.cfg.tablero || {}, colNom = {};
    (tab.columnas || []).forEach(c => { colNom[c.id] = c.nombre; });
    (tab.tarjetas || []).forEach(t => { if (t.vence) items.push({ clase: "tar", id: t.id, texto: t.texto, fecha: t.vence, colNombre: colNom[t.col] || "" }); });
    return items;
  }
  function irTablero() { E.notasVista = "tablero"; recuerda.guarda("patrimonio.notasVista", "tablero"); pintarNotas(); }
  function montaAgenda() {
    const cont = $("#notasCuerpo"); if (!cont) return;
    const v = E.agendaVista || "calendario";
    cont.innerHTML = `<section class="tarjeta"><header><h2>Agenda</h2>
        <span class="subt">Tus recordatorios, los vencimientos que la app detecta (depósitos, deudas, reservados) y las tarjetas del tablero con fecha.</span>
        <span class="sp"></span><button class="btn prim" data-rnuevo>+ Recordatorio</button></header>
      <div class="segm agNav">
        <button data-av="calendario" aria-pressed="${v === "calendario"}">📅 Calendario</button>
        <button data-av="lista" aria-pressed="${v === "lista"}">📋 Lista</button></div>
      <div id="agCuerpo"></div></section>`;
    cont.querySelector("[data-rnuevo]").onclick = () => formRecordatorio(null);
    cont.querySelectorAll("[data-av]").forEach(b => b.onclick = () => { E.agendaVista = b.dataset.av; recuerda.guarda("patrimonio.agendaVista", b.dataset.av); montaAgenda(); });
    if (v === "lista") montaAgendaLista(); else montaAgendaCalendario();
  }
  function montaAgendaLista() {
    const cont = $("#agCuerpo"); if (!cont) return;
    const items = agendaItems();
    const pend = items.filter(i => !(i.clase === "rec" && i.hecho)).sort((a, b) => a.fecha < b.fecha ? -1 : a.fecha > b.fecha ? 1 : 0);
    const hechos = items.filter(i => i.clase === "rec" && i.hecho).sort((a, b) => a.fecha < b.fecha ? 1 : -1);
    const fila = i => {
      const d = diasHasta(i.fecha);
      const etqD = d < 0 ? `hace ${-d} d` : d === 0 ? "hoy" : d === 1 ? "mañana" : `en ${d} d`;
      const clD = d < 0 ? "neg" : d <= 7 ? "aviso" : "";
      if (i.clase === "venc") {
        return `<div class="agItem venc"><span class="agFecha">${fecha(i.fecha)}</span>
          <span class="agDias ${clD}">${etqD}</span>
          <span class="agTxt">${esc(i.texto)}${i.meta ? ` <span class="agMeta">${esc(i.meta)}</span>` : ""}</span>
          <span class="agBadge" title="Se gestiona en Mis datos">${esc(i.tipo || "Vencimiento")}</span></div>`;
      }
      if (i.clase === "tar") {
        return `<div class="agItem tar" data-irtablero title="Tarjeta del tablero — pulsa para abrir el tablero"><span class="agFecha">${fecha(i.fecha)}</span>
          <span class="agDias ${clD}">${etqD}</span>
          <span class="agTxt">${esc(i.texto)}${i.colNombre ? ` <span class="agMeta">${esc(i.colNombre)}</span>` : ""}</span>
          <span class="agBadge tablero">📋 Tablero</span></div>`;
      }
      const rep = i.repetir !== "no" ? `<span class="agRep">🔁 ${i.repetir === "mensual" ? "mensual" : "anual"}</span>` : "";
      const vinc = i.vinculo ? `<span class="notaVinc" title="Relacionado con ${esc(VINC_ETIQ[i.vinculo.tipo] || "")}">🔗 ${esc(nombreVinculo(i.vinculo))}</span>` : "";
      return `<div class="agItem${i.hecho ? " hecha" : ""}"><span class="agFecha">${fecha(i.fecha)}</span>
        <span class="agDias ${i.hecho ? "" : clD}">${i.hecho ? "hecho" : etqD}</span>
        <span class="agTxt">${esc(i.texto)} ${rep} ${vinc}</span>
        ${i.repetir === "no" ? `<input type="checkbox" class="agChk"${i.hecho ? " checked" : ""} data-rdone="${esc(i.id)}" title="Marcar como hecho">` : ""}
        <button class="btn mini" data-redit="${esc(i.id)}">Editar</button>
        <button class="btn mini" data-rdel="${esc(i.id)}">Borrar</button></div>`;
    };
    cont.innerHTML = `${pend.length ? `<div class="agLista">${pend.map(fila).join("")}</div>` : '<p class="subt">No hay nada pendiente en la agenda.</p>'}
      ${hechos.length ? `<details class="agHechos"><summary>${hechos.length} hecho${hechos.length === 1 ? "" : "s"}</summary><div class="agLista">${hechos.map(fila).join("")}</div></details>` : ""}`;
    cont.querySelectorAll("[data-redit]").forEach(b => b.onclick = () => formRecordatorio((E.cfg.recordatorios || []).find(x => x.id === b.dataset.redit)));
    cont.querySelectorAll("[data-rdel]").forEach(b => b.onclick = () => { if (confirm("¿Borrar este recordatorio?")) guardaRecordatorios((E.cfg.recordatorios || []).filter(x => x.id !== b.dataset.rdel)); });
    cont.querySelectorAll("[data-rdone]").forEach(cb => cb.onchange = () => guardaRecordatorios((E.cfg.recordatorios || []).map(x => x.id === cb.dataset.rdone ? { ...x, hecho: cb.checked } : x)));
    cont.querySelectorAll("[data-irtablero]").forEach(el => el.onclick = () => irTablero());
  }
  function montaAgendaCalendario() {
    const cont = $("#agCuerpo"); if (!cont) return;
    if (!E.calMes) { const h = new Date(); E.calMes = h.getFullYear() + "-" + String(h.getMonth() + 1).padStart(2, "0"); }
    const [Y, M] = E.calMes.split("-").map(Number);       // M = 1..12
    const ultimo = new Date(Y, M, 0).getDate();
    const inicioSemana = (new Date(Y, M - 1, 1).getDay() + 6) % 7;   // lunes = 0
    const hoyISO = hoy();
    // Repartir recordatorios y vencimientos por día del mes mostrado.
    const porDia = {}; for (let d = 1; d <= ultimo; d++) porDia[d] = [];
    const diaEnMes = (iso, repetir) => {
      const [fy, fm, fd] = iso.split("-").map(Number);
      if (!repetir || repetir === "no") return (fy === Y && fm === M) ? fd : null;
      if (Y * 12 + (M - 1) < fy * 12 + (fm - 1)) return null;        // antes de empezar
      if (repetir === "mensual") return Math.min(fd, ultimo);
      if (repetir === "anual") return fm === M ? Math.min(fd, ultimo) : null;
      return null;
    };
    (E.cfg.recordatorios || []).forEach(r => {
      if (r.hecho && r.repetir === "no") return;
      const d = diaEnMes(r.fecha, r.repetir);
      if (d) porDia[d].push({ clase: "rec", id: r.id, texto: r.texto, repetir: r.repetir });
    });
    ((window.DATOS && window.DATOS.vencimientos) || []).forEach(v => {
      const d = diaEnMes(v.fecha, "no");
      if (d) porDia[d].push({ clase: "venc", texto: v.nombre, tipo: v.tipo });
    });
    ((E.cfg.tablero || {}).tarjetas || []).forEach(t => {
      if (!t.vence) return;
      const d = diaEnMes(t.vence, "no");
      if (d) porDia[d].push({ clase: "tar", id: t.id, texto: t.texto });
    });
    const celdas = [];
    for (let i = 0; i < inicioSemana; i++) celdas.push('<div class="calDia vacio"></div>');
    for (let d = 1; d <= ultimo; d++) {
      const iso = `${Y}-${String(M).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      const chips = porDia[d].map(it => it.clase === "rec"
        ? `<button class="calChip rec" data-cedit="${esc(it.id)}" title="${esc(it.texto)}">${it.repetir !== "no" ? "🔁 " : ""}${esc(it.texto)}</button>`
        : it.clase === "tar"
          ? `<button class="calChip tar" data-ctablero title="${esc(it.texto)} · Tablero">📋 ${esc(it.texto)}</button>`
          : `<span class="calChip venc" title="${esc(it.texto)} · ${esc(it.tipo || "")}">${esc(it.texto)}</span>`).join("");
      celdas.push(`<div class="calDia${iso === hoyISO ? " hoy" : ""}" data-cnuevo="${iso}">
        <div class="calNum">${d}</div><div class="calChips">${chips}</div></div>`);
    }
    const anios = []; for (let a = Y - 6; a <= Y + 3; a++) anios.push(a);
    cont.innerHTML = `<div class="calBarra">
        <button class="btn mini" data-cmes="-1" aria-label="Mes anterior">‹</button>
        <select data-cmessel>${MESES_LARGO.map((m, i) => `<option value="${i + 1}"${i + 1 === M ? " selected" : ""}>${m[0].toUpperCase() + m.slice(1)}</option>`).join("")}</select>
        <select data-caniosel>${anios.map(a => `<option value="${a}"${a === Y ? " selected" : ""}>${a}</option>`).join("")}</select>
        <button class="btn mini" data-cmes="1" aria-label="Mes siguiente">›</button>
        <button class="btn mini" data-choy>Hoy</button></div>
      <div class="calCab">${["L", "M", "X", "J", "V", "S", "D"].map(x => `<div>${x}</div>`).join("")}</div>
      <div class="calRejilla">${celdas.join("")}</div>
      <p class="subt" style="margin-top:8px">Pulsa un día para añadir un recordatorio; pulsa uno existente para editarlo.</p>`;
    const irMes = (y, m) => { E.calMes = y + "-" + String(m).padStart(2, "0"); montaAgendaCalendario(); };
    cont.querySelector("[data-cmes='-1']").onclick = () => irMes(M === 1 ? Y - 1 : Y, M === 1 ? 12 : M - 1);
    cont.querySelector("[data-cmes='1']").onclick = () => irMes(M === 12 ? Y + 1 : Y, M === 12 ? 1 : M + 1);
    cont.querySelector("[data-choy]").onclick = () => { const h = new Date(); irMes(h.getFullYear(), h.getMonth() + 1); };
    cont.querySelector("[data-cmessel]").onchange = e => irMes(Y, +e.target.value);
    cont.querySelector("[data-caniosel]").onchange = e => irMes(+e.target.value, M);
    cont.querySelectorAll("[data-cedit]").forEach(b => b.onclick = e => { e.stopPropagation(); formRecordatorio((E.cfg.recordatorios || []).find(x => x.id === b.dataset.cedit)); });
    cont.querySelectorAll("[data-ctablero]").forEach(b => b.onclick = e => { e.stopPropagation(); irTablero(); });
    cont.querySelectorAll("[data-cnuevo]").forEach(c => c.onclick = () => formRecordatorio(null, c.dataset.cnuevo));
  }

  function pintarNotas() {
    const cont = $("#notas"); if (!cont) return;
    if (E.modo !== "propio") {
      cont.innerHTML = `<section class="tarjeta"><header><h2>Notas</h2></header>
        <p class="subt">Las notas y el tablero están disponibles cuando empieces tu propio patrimonio. Ve a «Mis datos → Empezar con mis datos».</p></section>`;
      return;
    }
    const v = E.notasVista || "lista";
    cont.innerHTML = `<div class="segm notasNav">
        <button data-nv="lista" aria-pressed="${v === "lista"}">📝 Lista de notas</button>
        <button data-nv="tablero" aria-pressed="${v === "tablero"}">📋 Tablero</button>
        <button data-nv="agenda" aria-pressed="${v === "agenda"}">🗓️ Agenda</button></div>
      <div id="notasCuerpo"></div>`;
    cont.querySelectorAll("[data-nv]").forEach(b => b.onclick = () => {
      E.notasVista = b.dataset.nv; recuerda.guarda("patrimonio.notasVista", b.dataset.nv); pintarNotas();
    });
    if (v === "tablero") montaTablero(); else if (v === "agenda") montaAgenda(); else montaNotasLista();
  }
  E.notasVista = recuerda.lee("patrimonio.notasVista") || "lista";
  E.notaOrden = recuerda.lee("patrimonio.notaOrden") || "fecha";
  E.agendaVista = recuerda.lee("patrimonio.agendaVista") || "calendario";

  window.Editor = {
    mostrar: pinta,
    notas: pintarNotas,
    // Navegar a una sección de «Mis datos» desde fuera (p. ej. la paleta de acciones).
    ir(v) {
      if (["activos", "deudas", "apartados", "flujos", "saldos", "config", "importar", "copias"].includes(v)) {
        E.vista = v; recuerda.guarda("patrimonio.editor", v);
      }
      pinta();
    },
    // Abrir la pestaña Notas y mostrar las notas enlazadas a una entidad (activo/deuda/
    // reservado), resaltadas. Lo usan los indicadores «📝» del resto de la app.
    verEntidad(ref) {
      if (!ref) return;
      E.notasVista = "lista"; E.notaVincRef = ref; E.notaBusca = ""; E.notaTag = "";
      const tab = document.querySelector('[data-tab="notas"]');
      if (tab) tab.click();
      pintarNotas();
    },
  };
  carga().then(() => {
    pinta();
    // Si al cargar la pestaña activa es «Notas», re-dibujarla ya con los datos reales.
    if ($("#tab-notas") && !$("#tab-notas").hidden) pintarNotas();
  }).catch(x => {
    const cont = $("#editor");
    if (cont) cont.innerHTML = `<div class="av"><span>⚠</span><span>${esc(x.message)}</span></div>`;
  });
})();
