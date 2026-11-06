"use strict";

// ---------- Íconos (trazos estilo Lucide) ----------
const ICONOS = {
  inicio: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M10 21v-6h4v6"/>',
  libro: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/><path d="M9 7h7M9 11h5"/>',
  etiqueta: '<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
  matraz: '<path d="M9 3h6"/><path d="M10 3v6.5L4.6 18.4A1.7 1.7 0 0 0 6 21h12a1.7 1.7 0 0 0 1.4-2.6L14 9.5V3"/><path d="M7 15h10"/>',
  radiografia: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 7v10M8 9h8M8 12h8M9 15h6"/>',
  bisturi: '<path d="m3 21 9.5-9.5"/><path d="M12.5 11.5 20 4a2.1 2.1 0 0 1 0 3l-5 5-2.5-.5z"/>',
  caja: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
  piezas: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path d="M17.5 14v7M14 17.5h7"/>',
  arbol: '<rect x="9" y="2" width="6" height="5" rx="1"/><rect x="2" y="17" width="6" height="5" rx="1"/><rect x="16" y="17" width="6" height="5" rx="1"/><path d="M12 7v5M5 17v-2.5h14V17M12 12v2.5"/>',
  alerta: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
  lista: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  papelera: '<path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6M10 11v6M14 11v6"/>',
  texto: '<path d="M4 7V4h16v3M9 20h6M12 4v16"/>',
  capas: '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5M2 12l10 5 10-5"/>',
  check: '<circle cx="12" cy="12" r="10"/><path d="m8 12 3 3 5-6"/>',
  escudo: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
  ojo: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  documento: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
  externo: '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3"/>',
  buscar: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  excel: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="m9 12 6 6M15 12l-6 6"/>',
  descarga: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5M12 15V3"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  filtro: '<path d="M22 3H2l8 9.5V19l4 2v-8.5z"/>',
  izq: '<path d="m15 18-6-6 6-6"/>',
  der: '<path d="m9 18 6-6-6-6"/>',
  copiar: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  porcentaje: '<path d="M19 5 5 19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
  mapa: '<path d="M12 22s7-6.1 7-12a7 7 0 0 0-14 0c0 5.9 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/>',
  calculadora: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8M8 11h.01M12 11h.01M16 11h.01M8 15h.01M12 15h.01M16 15h.01M8 19h.01M12 19h4"/>',
  mas: '<path d="M12 5v14M5 12h14"/>',
  calendario: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  lupa: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h5"/><path d="M14 2v6h6v3"/><circle cx="16.5" cy="16.5" r="3.5"/><path d="m22 22-3-3"/>',
  subir: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5M12 3v12"/>',
  vacio: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3M8 11h6"/>',
};
const icono = (n) => `<svg class="icono" viewBox="0 0 24 24" aria-hidden="true">${ICONOS[n] || ""}</svg>`;

// ---------- Utilidades ----------
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 4 });
const SIN_SEPARADOR = new Set(["pagina_pdf", "articulo", "nivel", "fila_excel", "orden", "id", "n_componentes", "padre_id", "raiz_id"]);
const COL_CODIGO = new Set(["codigo", "ref", "paquete", "paquete_codigo", "componente_codigo", "pb", "marca"]);
const sinTildes = (c) => c.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase();

function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

function avisar(msg, error = false) {
  const a = $("#aviso");
  a.textContent = msg;
  a.className = "aviso visible" + (error ? " error" : "");
  clearTimeout(avisar.t);
  avisar.t = setTimeout(() => (a.className = "aviso"), 3200);
}

async function api(url) {
  const r = await fetch(url);
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch { /* sin cuerpo JSON */ }
    throw new Error(msg);
  }
  return r.json();
}

/** Resalta las palabras buscadas sin distinguir mayúsculas ni tildes. */
function resaltar(texto, palabras) {
  const s = String(texto);
  if (!palabras.length) return esc(s);
  const n = Array.from(s, sinTildes).join("");
  if (n.length !== s.length) return esc(s);
  const marcas = new Array(s.length).fill(false);
  for (const p of palabras) {
    let i = n.indexOf(p);
    while (p && i !== -1) {
      for (let k = i; k < i + p.length; k++) marcas[k] = true;
      i = n.indexOf(p, i + p.length);
    }
  }
  let out = "", dentro = false;
  for (let i = 0; i < s.length; i++) {
    if (marcas[i] && !dentro) { out += "<mark>"; dentro = true; }
    if (!marcas[i] && dentro) { out += "</mark>"; dentro = false; }
    out += esc(s[i]);
  }
  return out + (dentro ? "</mark>" : "");
}

// ---------- Estado y rutas (#/vista?q=...&modo=...) ----------
let VISTAS = [];
let estado = {};
let ultimaRespuesta = null;

function leerRuta() {
  const [ruta, qs] = location.hash.replace(/^#\/?/, "").split("?");
  const p = new URLSearchParams(qs || "");
  return {
    vista: ruta || "",
    q: p.get("q") || "",
    modo: p.get("modo") || "auto",
    pagina: Math.max(1, parseInt(p.get("p") || "1", 10)),
    tamano: parseInt(p.get("t") || "25", 10),
    orden: p.get("o") || "",
    dir: p.get("d") || "asc",
  };
}

function escribirRuta(e, reemplazar = false) {
  const p = new URLSearchParams();
  if (e.q) p.set("q", e.q);
  if (e.modo && e.modo !== "auto") p.set("modo", e.modo);
  if (e.vista) {
    if (e.pagina > 1) p.set("p", e.pagina);
    if (e.tamano !== 25) p.set("t", e.tamano);
    if (e.orden) { p.set("o", e.orden); p.set("d", e.dir); }
  }
  const h = `#/${e.vista}${p.toString() ? "?" + p : ""}`;
  if (h === location.hash) return false;
  if (reemplazar) history.replaceState(null, "", h);
  else history.pushState(null, "", h);
  return true;
}

function navegar(cambios, reemplazar = false) {
  estado = { ...estado, ...cambios };
  escribirRuta(estado, reemplazar);
  render();
}

// ---------- Menú ----------
function pintarMenu() {
  const grupos = {};
  VISTAS.forEach((v) => (grupos[v.grupo] ||= []).push(v));
  let h = `<a class="menu__item" href="#/" data-vista="">${icono("inicio")}<span>Inicio</span></a>`;
  for (const [g, vs] of Object.entries(grupos)) {
    h += `<div class="menu__grupo">${esc(g)}</div>`;
    if (g === "Cotizar y auditar") h += `<a class="menu__item" href="#/cotizar" data-vista="cotizar">${icono("calculadora")}<span>Cotizar</span></a>
      <a class="menu__item" href="#/auditar" data-vista="auditar">${icono("lupa")}<span>Auditar factura</span></a>`;
    if (g === "SOAT y tarifas propias") h += `<a class="menu__item" href="#/soat-versiones" data-vista="soat-versiones">${icono("calendario")}<span>Versiones de tarifa SOAT</span></a>
      <a class="menu__item" href="#/tarifas-propias" data-vista="tarifas-propias">${icono("subir")}<span>Manuales de tarifas propias</span></a>`;
    h += vs.map((v) => `<a class="menu__item" href="#/${v.id}" data-vista="${v.id}">${icono(v.icono)}
      <span>${esc(v.titulo)}</span><small>${fmt.format(v.total)}</small></a>`).join("");
  }
  h += `<div class="menu__grupo">Fuentes</div>
    <a class="menu__item" href="#/fuentes" data-vista="fuentes">${icono("documento")}<span>PDF y Excel originales</span></a>`;
  $("#menu").innerHTML = h;
  $("#menu").addEventListener("click", (ev) => {
    const a = ev.target.closest(".menu__item");
    if (!a) return;
    ev.preventDefault();
    cerrarMenuMovil();
    volverAuditoria = false;
    // al cambiar de vista se conserva la búsqueda, para seguir el mismo código por varias vistas
    navegar({ vista: a.dataset.vista, pagina: 1, orden: "", dir: "asc" });
  });
}

function marcarMenu() {
  document.querySelectorAll(".menu__item").forEach((a) => a.classList.toggle("activo", a.dataset.vista === estado.vista));
}

// ---------- Buscador compartido ----------
function htmlBuscador(porCodigo, placeholder) {
  const m = estado.modo;
  return `
    <div class="buscador">
      ${icono("buscar")}
      <input id="q" type="search" autocomplete="off" spellcheck="false" placeholder="${esc(placeholder)}" value="${esc(estado.q)}">
      <div class="segmentado" role="group" aria-label="Tipo de búsqueda">
        <button data-modo="auto" class="${m === "auto" ? "activo" : ""}" title="Detecta si escribió códigos o texto">Auto</button>
        <button data-modo="codigo" class="${m === "codigo" ? "activo" : ""}" ${porCodigo ? "" : "disabled"}>Código</button>
        <button data-modo="texto" class="${m === "texto" ? "activo" : ""}">Texto</button>
      </div>
    </div>`;
}

function enlazarBuscador() {
  const q = $("#q");
  const buscar = debounce(() => navegar({ q: q.value.trim(), pagina: 1 }, true), 300);
  q.addEventListener("input", buscar);
  q.addEventListener("keydown", (e) => { if (e.key === "Escape") { q.value = ""; navegar({ q: "", pagina: 1 }, true); } });
  document.querySelectorAll(".segmentado button").forEach((b) =>
    b.addEventListener("click", () => navegar({ modo: b.dataset.modo, pagina: 1 }, true)));
}

const AYUDA = `<b>Código:</b> uno o varios separados por coma o espacio (<code>791703, 020101</code>), o un prefijo con
  asterisco (<code>9030*</code>). <b>Texto:</b> todas las palabras en cualquier orden, sin importar mayúsculas ni
  tildes (<code>colecistectomia laparoscopica</code>).`;

// ---------- Inicio ----------
async function pintarInicio() {
  $("#migaVista").textContent = "Inicio";
  const c = $("#contenido");
  const enfocado = document.activeElement?.id === "q";
  const pos = enfocado ? document.activeElement.selectionStart : null;
  if (!c.querySelector(".hero")) {
    c.innerHTML = `
      <section class="hero">
        <h1>Consulta del Manual Tarifario ISS 2001</h1>
        <p>Busque un código o un texto en todo el Manual (Acuerdo 256 de 2001). Verá cuántas coincidencias hay en cada
          vista; abra la que necesite para ver el detalle y exportarlo a Excel.</p>
        ${htmlBuscador(true, "Código CUPS, REF o texto…  ej. 791703 o colecistectomía")}
        <div class="ayuda">${AYUDA}</div>
      </section>
      <div class="rejilla" id="rejilla"></div>`;
    enlazarBuscador();
  } else {
    document.querySelectorAll(".segmentado button").forEach((b) => b.classList.toggle("activo", b.dataset.modo === estado.modo));
    if (!enfocado) $("#q").value = estado.q;
  }
  if (enfocado) { $("#q").focus(); $("#q").setSelectionRange(pos, pos); }

  let conteos = null;
  if (estado.q) {
    try {
      conteos = Object.fromEntries((await api(`/api/buscar?${new URLSearchParams({ q: estado.q, modo: estado.modo })}`)).map((r) => [r.id, r]));
    } catch (e) { avisar(e.message, true); }
  }
  $("#rejilla").innerHTML = `<button class="tarjeta-vista tarjeta-cotizar" data-vista="cotizar">
      <div class="tarjeta-vista__icono">${icono("calculadora")}</div>
      <div><h3>Cotizar</h3><p>Sume las tarifas de varios códigos y aplique los recargos y descuentos del Manual:
        portátil, bilateral, varios conjuntos en un mismo acto y regiones del art. 134.</p></div></button>
    <button class="tarjeta-vista tarjeta-cotizar" data-vista="auditar">
      <div class="tarjeta-vista__icono">${icono("lupa")}</div>
      <div><h3>Auditar factura</h3><p>Cargue el RIPS (JSON) o la factura electrónica (XML), o digite las líneas: compara
        cada cobro con el Manual, señala sobrecobros y dobles cobros, y exporta el informe de glosas a Excel.</p></div></button>` + VISTAS.map((v) => {
    const r = conteos?.[v.id];
    const clase = conteos ? (r?.coincidencias ? "con-resultados" : "sin-resultados") : "";
    const insignia = conteos ? `<span class="insignia">${r ? fmt.format(r.coincidencias) : "—"}</span>` : "";
    return `<button class="tarjeta-vista ${clase}" data-vista="${v.id}">
      <div class="tarjeta-vista__icono">${icono(v.icono)}</div>
      <div><h3>${esc(v.titulo)}</h3><p>${esc(v.descripcion)}</p>
        <div class="cifra"><b>${fmt.format(v.total)}</b> filas</div></div>${insignia}</button>`;
  }).join("") + `<button class="tarjeta-vista tarjeta-fuentes" data-vista="fuentes">
      <div class="tarjeta-vista__icono">${icono("documento")}</div>
      <div><h3>PDF y Excel originales</h3><p>Descargue los documentos de donde sale la información:
        el PDF oficial del Acuerdo 256 de 2001 y el Excel de origen.</p></div></button>`;
  document.querySelectorAll(".tarjeta-vista").forEach((t) =>
    t.addEventListener("click", () => navegar({ vista: t.dataset.vista, pagina: 1, orden: "", dir: "asc" })));
}

// ---------- Vista ----------
async function pintarVista() {
  const v = VISTAS.find((x) => x.id === estado.vista);
  if (!v) { navegar({ vista: "" }, true); return; }
  if (!v.por_codigo && estado.modo === "codigo") estado.modo = "texto";
  $("#migaVista").textContent = v.titulo;
  const c = $("#contenido");

  if (c.dataset.vista !== v.id) {
    c.dataset.vista = v.id;
    c.innerHTML = `
      <section class="panel">
        <div class="cabecera">
          <div class="cabecera__icono">${icono(v.icono)}</div>
          <div><h1>${esc(v.titulo)}</h1><p>${esc(v.descripcion)}</p></div>
        </div>
        <div class="barra">
          ${htmlBuscador(v.por_codigo, v.por_codigo ? "Buscar por código o texto…" : "Buscar por texto…")}
          <div class="exportar">
            <button class="boton boton--borde" id="expFiltrado" title="Exporta las filas que coinciden con la búsqueda">${icono("filtro")}<span>Excel filtrado</span></button>
            <button class="boton boton--morado" id="expCompleto" title="Exporta todas las filas de la vista">${icono("excel")}<span>Excel completo</span></button>
          </div>
        </div>
        <div class="ayuda">${v.por_codigo ? AYUDA : "Búsqueda por texto: todas las palabras en cualquier orden, sin importar mayúsculas ni tildes."}</div>
        <div class="resumen" id="resumen"></div>
        <div class="tabla-marco" id="marco"><div class="estado">Cargando…</div></div>
        <div class="paginacion" id="paginacion"></div>
      </section>`;
    enlazarBuscador();
    $("#expFiltrado").addEventListener("click", (e) => exportar(false, e.currentTarget));
    $("#expCompleto").addEventListener("click", (e) => exportar(true, e.currentTarget));
  } else {
    document.querySelectorAll(".segmentado button").forEach((b) => b.classList.toggle("activo", b.dataset.modo === estado.modo));
    if (document.activeElement?.id !== "q") $("#q").value = estado.q;
  }

  const marco = $("#marco");
  marco.classList.add("cargando");
  const params = new URLSearchParams({ q: estado.q, modo: estado.modo, pagina: estado.pagina, tamano: estado.tamano, orden: estado.orden, dir: estado.dir });
  let d;
  try {
    d = await api(`/api/datos/${v.id}?${params}`);
  } catch (e) {
    marco.classList.remove("cargando");
    marco.innerHTML = `<div class="estado">${icono("alerta")}<div>${esc(e.message)}</div></div>`;
    $("#resumen").innerHTML = "";
    $("#paginacion").innerHTML = "";
    return;
  }
  if (estado.vista !== v.id) return; // el usuario cambió de vista mientras cargaba
  ultimaRespuesta = d;
  marco.classList.remove("cargando");
  pintarResumen(d);
  pintarTabla(d);
  pintarPaginacion(d);
  $("#expFiltrado").disabled = !estado.q;
}

function pintarResumen(d) {
  const filtrado = !!estado.q;
  let h = filtrado
    ? `<span class="chip">${icono("filtro")}${fmt.format(d.filtrados)} de ${fmt.format(d.total)} filas</span>
       <span class="chip chip--morado">Búsqueda por ${d.modo === "codigo" ? "código" : "texto"}</span>`
    : `<span class="chip chip--gris">${fmt.format(d.total)} filas</span>`;
  if (estado.orden) {
    const col = d.columnas.find((c) => c.id === estado.orden);
    h += `<span class="chip chip--gris">Orden: ${esc(col?.etiqueta || estado.orden)} ${estado.dir === "desc" ? "↓" : "↑"}</span>`;
  }
  $("#resumen").innerHTML = h;
}

function palabrasResaltado(d) {
  if (!estado.q) return [];
  return estado.q.split(/[\s,;]+/).filter(Boolean).map((t) => sinTildes(t.replace(/\*$/, ""))).filter(Boolean);
}

function celda(col, valor, palabras) {
  if (valor === null || valor === undefined || valor === "") return `<td class="vacio">—</td>`;
  if (col === "tipo_fila") return `<td><span class="etiqueta-fila">${esc(valor)}</span></td>`;
  if (col === "pagina_pdf" || col === "paginas_pdf") return `<td class="num">${enlacesPaginas(valor)}</td>`;
  if (col === "resultado") return `<td><span class="resultado ${valor === "OK" ? "ok" : "revisar"}">${esc(valor)}</span></td>`;
  if (typeof valor === "number") {
    return `<td class="num">${SIN_SEPARADOR.has(col) ? valor : fmt.format(valor)}</td>`;
  }
  const clase = COL_CODIGO.has(col) ? "cod" : "";
  return `<td class="${clase}"><div class="recorte" title="${esc(valor)}">${resaltar(valor, palabras)}</div></td>`;
}

/** Páginas del PDF como enlaces que abren el PDF en esa página ("3,9,25" -> 3 enlaces). */
function enlacesPaginas(valor) {
  return String(valor).split(/\s*,\s*/).filter(Boolean).map((p) => /^\d+$/.test(p)
    ? `<a class="pagina" href="/fuentes/pdf#page=${p}" target="_blank" rel="noopener" title="Abrir el PDF en la página ${p}">${p}</a>`
    : esc(p)).join(", ");
}

function pintarTabla(d) {
  const marco = $("#marco");
  if (!d.filas.length) {
    marco.innerHTML = `<div class="estado">${icono("vacio")}<div>No hay filas que coincidan con <b>${esc(estado.q)}</b>.</div></div>`;
    return;
  }
  const numericas = new Set(d.columnas.filter((c, i) => d.filas.some((f) => typeof f[i] === "number")).map((c) => c.id));
  const cab = d.columnas.map((c) => {
    const f = estado.orden === c.id ? (estado.dir === "desc" ? "↓" : "↑") : "";
    return `<th data-col="${c.id}" class="${numericas.has(c.id) ? "num" : ""}">${esc(c.etiqueta)}<span class="flecha">${f}</span></th>`;
  }).join("");
  const iTipo = d.columnas.findIndex((c) => c.id === "tipo_fila");
  const palabras = palabrasResaltado(d);
  const cuerpo = d.filas.map((f, i) => {
    const clase = iTipo >= 0 && f[iTipo] ? "f-" + String(f[iTipo]).toLowerCase() : "";
    return `<tr class="${clase}" data-i="${i}">${f.map((v, j) => celda(d.columnas[j].id, v, palabras)).join("")}</tr>`;
  }).join("");
  marco.innerHTML = `<table><thead><tr>${cab}</tr></thead><tbody>${cuerpo}</tbody></table>`;
  marco.scrollTop = 0;
  marco.querySelectorAll("th").forEach((th) => th.addEventListener("click", () => {
    const col = th.dataset.col;
    // tres estados: ascendente → descendente → orden original de la vista
    if (estado.orden !== col) navegar({ orden: col, dir: "asc", pagina: 1 });
    else if (estado.dir === "asc") navegar({ dir: "desc", pagina: 1 });
    else navegar({ orden: "", dir: "asc", pagina: 1 });
  }));
  marco.querySelectorAll("tbody tr").forEach((tr) => tr.addEventListener("click", (ev) => {
    if (ev.target.closest("a")) return; // enlace a una página del PDF
    abrirDetalle(d, +tr.dataset.i);
  }));
}

function pintarPaginacion(d) {
  const paginas = Math.max(1, Math.ceil(d.filtrados / d.tamano));
  const p = Math.min(estado.pagina, paginas);
  const desde = d.filtrados ? (p - 1) * d.tamano + 1 : 0;
  const hasta = Math.min(p * d.tamano, d.filtrados);
  const nums = new Set([1, paginas, p - 1, p, p + 1].filter((n) => n >= 1 && n <= paginas));
  let botones = "", prev = 0;
  for (const n of [...nums].sort((a, b) => a - b)) {
    if (n - prev > 1) botones += `<span class="puntos">…</span>`;
    botones += `<button data-p="${n}" class="${n === p ? "activo" : ""}">${fmt.format(n)}</button>`;
    prev = n;
  }
  $("#paginacion").innerHTML = `
    <div>Mostrando ${fmt.format(desde)}–${fmt.format(hasta)} de ${fmt.format(d.filtrados)} · clic en una fila para ver el detalle</div>
    <div class="paginas">
      <button data-p="${p - 1}" ${p <= 1 ? "disabled" : ""} aria-label="Anterior">${icono("izq")}</button>
      ${botones}
      <button data-p="${p + 1}" ${p >= paginas ? "disabled" : ""} aria-label="Siguiente">${icono("der")}</button>
    </div>
    <label class="tamano">Mostrar
      <select id="tamano">${[10, 25, 50, 100, 250].map((n) => `<option ${n === d.tamano ? "selected" : ""}>${n}</option>`).join("")}</select>
      filas</label>`;
  $("#paginacion").querySelectorAll("button[data-p]").forEach((b) =>
    b.addEventListener("click", () => navegar({ pagina: +b.dataset.p })));
  $("#tamano").addEventListener("change", (e) => navegar({ tamano: +e.target.value, pagina: 1 }));
}

// ---------- Detalle ----------
function abrirDetalle(d, i) {
  const f = d.filas[i];
  const val = (id) => f[d.columnas.findIndex((c) => c.id === id)];
  const codigo = val("codigo") ?? val("componente_codigo");
  $("#cajonTitulo").textContent = codigo ? `Código ${codigo}` : (val("nombre") || val("tipo_fila") || "Detalle");
  let h = `<dl>${d.columnas.map((c, j) => {
    const v = f[j];
    const vacio = v === null || v === undefined || v === "";
    const txt = vacio ? "—" : typeof v === "number" && !SIN_SEPARADOR.has(c.id) ? fmt.format(v) : v;
    const html = !vacio && (c.id === "pagina_pdf" || c.id === "paginas_pdf") ? enlacesPaginas(v) : esc(txt);
    return `<div class="campo"><dt>${esc(c.etiqueta)}</dt><dd class="${vacio ? "vacio" : ""}">${html}</dd></div>`;
  }).join("")}</dl>`;
  if (codigo) {
    h += `<div class="cajon__acciones">
      <button class="boton boton--verde" id="buscarTodo">${icono("buscar")}Buscar ${esc(codigo)} en todas las vistas</button>
      <button class="boton boton--borde" id="copiar">${icono("copiar")}Copiar código</button></div>`;
  }
  $("#cajonCuerpo").innerHTML = h;
  $("#buscarTodo")?.addEventListener("click", () => { cerrarDetalle(); navegar({ vista: "", q: String(codigo), modo: "codigo" }); });
  $("#copiar")?.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(String(codigo)); avisar("Código copiado"); }
    catch { avisar("No se pudo copiar", true); }
  });
  $("#cajon").classList.add("abierto");
  $("#cajon").setAttribute("aria-hidden", "false");
  $("#velo").classList.add("visible");
}

function cerrarDetalle() {
  $("#cajon").classList.remove("abierto");
  $("#cajon").setAttribute("aria-hidden", "true");
  if (!$("#sidebar").classList.contains("abierto")) $("#velo").classList.remove("visible");
}

function cerrarMenuMovil() {
  $("#sidebar").classList.remove("abierto");
  if (!$("#cajon").classList.contains("abierto")) $("#velo").classList.remove("visible");
}

// ---------- Exportar ----------
async function exportar(completo, boton) {
  const params = new URLSearchParams({ q: estado.q, modo: estado.modo, orden: estado.orden, dir: estado.dir, completo });
  const original = boton.innerHTML;
  boton.disabled = true;
  boton.innerHTML = `<span class="giro" style="${completo ? "" : "border-color:#cfd6da;border-top-color:var(--verde)"}"></span><span>Generando…</span>`;
  try {
    const r = await fetch(`/api/exportar/${estado.vista}?${params}`);
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
    const nombre = (r.headers.get("Content-Disposition") || "").match(/filename="(.+)"/)?.[1] || "manual_iss.xlsx";
    const url = URL.createObjectURL(await r.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: nombre });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    avisar(`Descargado ${nombre}`);
  } catch (e) {
    avisar("No se pudo exportar: " + e.message, true);
  } finally {
    boton.disabled = false;
    boton.innerHTML = original;
    if (!completo) boton.disabled = !estado.q;
  }
}

// ---------- Fuentes (PDF y Excel originales) ----------
const mb = (b) => fmt.format(Math.round(b / 104857.6) / 10) + " MB";

async function pintarFuentes() {
  $("#migaVista").textContent = "PDF y Excel originales";
  const c = $("#contenido");
  c.dataset.vista = "fuentes";
  c.innerHTML = `<section class="panel"><div class="cabecera">
      <div class="cabecera__icono">${icono("documento")}</div>
      <div><h1>PDF y Excel originales</h1><p>Los documentos de donde sale la información de esta base.
        Se publican tal como se recibieron, sin modificaciones. El código SHA-256 permite comprobar que
        un archivo es exactamente el mismo.</p></div></div>
      <div class="fuentes" id="fuentes"><div class="estado">Cargando…</div></div></section>`;
  let fs;
  try { fs = await api("/api/fuentes"); } catch (e) { $("#fuentes").innerHTML = `<div class="estado">${esc(e.message)}</div>`; return; }
  $("#fuentes").innerHTML = fs.map((f) => `
    <article class="fuente">
      <div class="fuente__icono ${f.id}">${icono(f.id === "pdf" ? "documento" : "excel")}</div>
      <div class="fuente__texto">
        <h3>${esc(f.titulo)}</h3>
        <p>${esc(f.descripcion)}</p>
        <div class="fuente__meta"><span>${esc(f.archivo)}</span><span>${mb(f.bytes)}</span></div>
        <div class="fuente__hash" title="SHA-256">SHA-256: <code>${esc(f.sha256)}</code></div>
      </div>
      <div class="fuente__acciones">
        ${f.id === "pdf" ? `<a class="boton boton--borde" href="/fuentes/pdf" target="_blank" rel="noopener">${icono("externo")}Ver</a>` : ""}
        <a class="boton ${f.id === "pdf" ? "boton--verde" : "boton--morado"}" href="/fuentes/${f.id}?descargar=1">${icono("descarga")}Descargar</a>
      </div>
    </article>`).join("") + `<p class="ayuda">En las vistas de novedades y validación, el número de página del PDF
      es un enlace: abre el PDF directamente en esa página.</p>`;
}

// ---------- Cotizador ----------
// Mismo cálculo que cotizar.py (POST /api/cotizar). La cotización se guarda en este navegador.
const OPC_ETIQUETA = {
  "solo-muestra": "Solo toma de muestra", "biopsia-multiple": "Biopsia múltiple",
  "portatil-eco": "Ecografía portátil", bilateral: "Bilateral", "portatil-rx": "Radiología portátil",
};
const RE_ITEM = /^([A-Za-z]?\d{4,6})(?:x(\d+))?(?:@(\w+))?$/i;
const pesos = (v) => (v < 0 ? "−" : "") + "$" + new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 }).format(Math.abs(v));
const normCod = (c) => { c = c.toUpperCase(); return /^\d+$/.test(c) ? c.padStart(6, "0") : c; };
const partesItem = (s) => { const m = s.match(RE_ITEM); return m ? { cod: normCod(m[1]), cant: +(m[2] || 1), ref: m[3] || "" } : null; };
const armarItem = (p) => p.cod + (p.cant > 1 ? "x" + p.cant : "") + (p.ref ? "@" + p.ref : "");
const cotVacia = () => ({ items: [], opc: {}, rx: {}, tecnecio: false, mismoActo: "", depto: "", muni: "" });
let COT_CFG = null;
let cotRes = null;
let cotSeq = 0;
let cot = (() => {
  try { return { ...cotVacia(), ...JSON.parse(localStorage.getItem("cotizacion") || "{}") }; } catch { return cotVacia(); }
})();
function guardarCot() { try { localStorage.setItem("cotizacion", JSON.stringify(cot)); } catch { /* sin almacenamiento */ } }

function pedidoCot(s = cot) {
  const lista = (op) => Object.keys(s.opc).filter((c) => s.opc[c][op]);
  return {
    items: s.items,
    solo_muestra: lista("solo-muestra"), biopsia_multiple: lista("biopsia-multiple"),
    portatil_eco: lista("portatil-eco"), bilateral: lista("bilateral"),
    portatil_rx: Object.fromEntries(Object.entries(s.rx).filter(([, v]) => v)),
    tecnecio: s.tecnecio, mismo_acto: s.mismoActo || null,
    region: s.depto ? `${s.depto}:${s.muni || "OTRO"}` : null,
  };
}

/** Quita las opciones de los códigos que ya no están en la cotización. */
function podarCot() {
  const vivos = new Set(cot.items.map((i) => partesItem(i)?.cod || i.toUpperCase()));
  for (const k of Object.keys(cot.opc)) if (!vivos.has(k)) delete cot.opc[k];
  for (const k of Object.keys(cot.rx)) if (!vivos.has(k)) delete cot.rx[k];
}

async function postJSON(url, cuerpo) {
  return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
}

const recalcular = debounce(async () => {
  guardarCot();
  const n = ++cotSeq;
  $("#cotItems")?.classList.add("cargando");
  try {
    const r = await postJSON("/api/cotizar", pedidoCot());
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
    const d = await r.json();
    if (n !== cotSeq) return;
    // opciones globales que dejaron de aplicar (se quitó el código que las permitía)
    let otraVez = false;
    if (cot.tecnecio && !d.globales.tecnecio) { cot.tecnecio = false; otraVez = true; }
    if (cot.mismoActo && !d.globales.conjuntos) { cot.mismoActo = ""; otraVez = true; }
    cotRes = d;
    pintarCotResultado();
    if (otraVez) recalcular();
  } catch (e) {
    avisar("No se pudo cotizar: " + e.message, true);
  } finally {
    if (n === cotSeq) $("#cotItems")?.classList.remove("cargando");
  }
}, 120);

function agregarItems(texto) {
  const nuevos = texto.split(/[\s,;]+/).map((x) => x.trim()).filter(Boolean);
  if (!nuevos.length) return;
  cot.items.push(...nuevos);
  recalcular();
}

async function pintarCotizar() {
  $("#migaVista").textContent = "Cotizar";
  const c = $("#contenido");
  c.dataset.vista = "cotizar";
  if (!COT_CFG) {
    try { COT_CFG = await api("/api/cotizador"); } catch (e) {
      c.innerHTML = `<div class="panel estado">${icono("alerta")}<div>${esc(e.message)}</div></div>`;
      return;
    }
  }
  c.innerHTML = `
    <section class="panel">
      <div class="cabecera">
        <div class="cabecera__icono">${icono("calculadora")}</div>
        <div><h1>Cotizar</h1><p>Agregue los códigos de la atención de un paciente. Se suman las tarifas en pesos y se
          aplican solo los recargos y descuentos que usted marque, con el artículo y la página del PDF de cada uno.
          Los procedimientos en UVR (arts. 1-18) no se suman.</p></div>
      </div>
      <form class="cot-agregar" id="cotForm" autocomplete="off">
        <label class="buscador">${icono("mas")}
          <input id="cotCodigo" placeholder="Códigos: 903801, 871112x2, C40402, 697100@41501" aria-label="Códigos a agregar"></label>
        <button class="boton boton--verde" type="submit">${icono("mas")}Agregar</button>
      </form>
      <div class="ayuda"><code>CODIGO</code> una vez, <code>CODIGOx2</code> con cantidad, <code>CODIGO@REF</code> cuando el código
        tiene varios valores en el Manual. Puede pegar varios separados por coma o espacio.</div>
    </section>
    <div class="cot-rejilla">
      <div class="cot-principal">
        <section class="panel" id="cotItems"></section>
        <section class="panel" id="cotNotas"></section>
      </div>
      <aside class="cot-lateral">
        <section class="panel" id="cotCondiciones"></section>
        <section class="panel cot-total" id="cotTotal"></section>
      </aside>
    </div>`;
  $("#cotForm").addEventListener("submit", (ev) => {
    ev.preventDefault();
    agregarItems($("#cotCodigo").value);
    $("#cotCodigo").value = "";
  });
  enlazarCotizar();
  if (cotRes) pintarCotResultado();
  recalcular();
  $("#cotCodigo").focus();
}

function enlazarCotizar() {
  $("#cotItems").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-quitar]");
    if (!b) return;
    cot.items.splice(+b.dataset.quitar, 1);
    podarCot();
    recalcular();
  });
  $("#cotItems").addEventListener("change", (ev) => {
    const t = ev.target;
    if (t.dataset.cant !== undefined) {
      const p = partesItem(cot.items[+t.dataset.cant]);
      p.cant = Math.max(1, Math.min(999, parseInt(t.value, 10) || 1));
      cot.items[+t.dataset.cant] = armarItem(p);
    } else if (!cambiarOpcion(t, cot)) return;
    recalcular();
  });
  enlazarCondiciones($("#cotCondiciones"), () => cot, recalcular);
  $("#cotTotal").addEventListener("click", async (ev) => {
    const b = ev.target.closest("button");
    if (!b) return;
    if (b.id === "cotLimpiar") {
      if (cot.items.length && !confirm("¿Borrar la cotización?")) return;
      cot = cotVacia();
      recalcular();
    } else if (b.id === "cotExcel") exportarCot(b);
  });
}

/** Marca o desmarca una opción por línea (portátil, bilateral...). */
function cambiarOpcion(t, s) {
  if (t.dataset.rx !== undefined) s.rx[t.dataset.rx] = t.value;
  else if (t.dataset.op !== undefined) (s.opc[t.dataset.cod] ||= {})[t.dataset.op] = t.checked;
  else return false;
  return true;
}

/** Lugar de la atención, mismo acto y tecnecio: compartido por Cotizar y Auditar. */
function enlazarCondiciones(el, estadoDe, recalc) {
  el.addEventListener("change", (ev) => {
    const t = ev.target, s = estadoDe();
    if (t.id === "cotDepto") { s.depto = t.value; s.muni = ""; }
    else if (t.id === "cotMuni") s.muni = t.value;
    else if (t.name === "mismoActo") s.mismoActo = t.value;
    else if (t.id === "cotTecnecio") s.tecnecio = t.checked;
    else return;
    recalc();
  });
}

function htmlOpciones(f, s = cot) {
  const regla = (op, variante = "") => COT_CFG.reglas.find((r) => r.opcion === op && (!variante || r.variante === variante));
  const titulo = (r) => (r ? `${r.texto} — ${r.cita}` : "");
  return f.aplicables.map((op) => {
    if (op === "portatil-rx") {
      const v = s.rx[f.codigo] || "";
      return `<label class="opcion${v ? " activa" : ""}" title="${esc(titulo(regla(op, "simple")))}">${OPC_ETIQUETA[op]}
        <select data-rx="${esc(f.codigo)}"><option value="">no</option>
          <option value="simple"${v === "simple" ? " selected" : ""}>simple</option>
          <option value="fluoroscopia"${v === "fluoroscopia" ? " selected" : ""}>con fluoroscopia</option></select></label>`;
    }
    const marcado = s.opc[f.codigo]?.[op];
    return `<label class="opcion${marcado ? " activa" : ""}" title="${esc(titulo(regla(op)))}">
      <input type="checkbox" data-op="${op}" data-cod="${esc(f.codigo)}"${marcado ? " checked" : ""}>${OPC_ETIQUETA[op] || op}</label>`;
  }).join("");
}

function pintarCotResultado() {
  if (!$("#cotItems") || !cotRes) return;
  const d = cotRes;
  // empareja cada ítem escrito con su fila resuelta (los que tienen error no traen fila)
  const pendientes = [...d.filas];
  const filasHtml = cot.items.map((it, i) => {
    const p = partesItem(it);
    const k = pendientes.findIndex((f) => p && f.codigo === p.cod && f.cantidad === p.cant);
    const quitar = `<button class="boton-icono" type="button" data-quitar="${i}" title="Quitar">${icono("x")}</button>`;
    if (k < 0) {
      const err = d.errores.find((e) => e.startsWith(p ? p.cod : it) || e.startsWith(it)) || "Revise el código";
      return `<tr class="cot-error"><td class="cod">${esc(it)}</td><td colspan="5">${esc(err)}</td><td></td><td>${quitar}</td></tr>`;
    }
    const f = pendientes.splice(k, 1)[0];
    const enPesos = f.unidad === "pesos";
    return `<tr>
      <td class="cod">${esc(f.codigo)}${p.ref ? `<small>@${esc(p.ref)}</small>` : ""}</td>
      <td><div class="recorte">${esc(f.descripcion)}</div><small class="sutil">${esc(f.agrupador || "")}</small></td>
      <td class="num">${f.articulo}</td>
      <td class="num">${enPesos ? pesos(f.valor) : `${fmt.format(f.valor)} ${esc(f.unidad)}`}</td>
      <td class="num"><input class="cant" type="number" min="1" max="999" value="${f.cantidad}" data-cant="${i}" aria-label="Cantidad"></td>
      <td class="num"><b>${f.base == null ? "—" : pesos(f.base)}</b></td>
      <td><div class="opciones">${htmlOpciones(f)}</div></td>
      <td>${quitar}</td></tr>`;
  }).join("");
  $("#cotItems").innerHTML = `
    <h2 class="subtitulo">${icono("lista")}Servicios (${cot.items.length})</h2>
    ${cot.items.length ? `<div class="tabla-marco cot-tabla"><table>
      <thead><tr><th>Código</th><th>Descripción</th><th class="num">Art.</th><th class="num">Valor</th>
        <th class="num">Cant.</th><th class="num">Subtotal</th><th>Recargos y descuentos</th><th></th></tr></thead>
      <tbody>${filasHtml}</tbody></table></div>`
      : `<div class="estado">${icono("calculadora")}<div>Agregue códigos para empezar.</div></div>`}`;

  // ajustes aplicados
  const ajustes = d.ajustes.length ? `<h2 class="subtitulo">${icono("porcentaje")}Recargos y descuentos aplicados</h2>
    <div class="tabla-marco cot-tabla"><table><thead><tr><th>Código</th><th>Regla</th><th>Cita</th><th class="num">Monto</th></tr></thead>
    <tbody>${d.ajustes.map((a) => `<tr><td class="cod">${esc(a.codigo || "por paciente")}</td><td>${esc(a.texto)}</td>
      <td class="sin-salto">${enlacesCita(a.cita)}</td>
      <td class="num monto ${a.monto < 0 ? "neg" : "pos"}">${a.monto < 0 ? "" : "+"}${pesos(a.monto)}</td></tr>`).join("")}</tbody></table></div>` : "";
  const avisos = d.avisos.length ? `<details class="cot-detalles" open><summary>${icono("alerta")}Avisos (${d.avisos.length}): revíselos, no se aplicaron</summary>
    <ul>${d.avisos.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></details>` : "";
  const parr = d.parrafos.length ? `<details class="cot-detalles"><summary>${icono("documento")}Parágrafos que pueden modificar el valor (${d.parrafos.length})</summary>
    <ul>${d.parrafos.map((p) => `<li><span class="chip ${p.opcion ? "" : "chip--gris"}">art. ${p.articulo}${p.opcion === "pendiente" ? " · pendiente" : p.opcion ? " · se puede marcar" : ""}</span> ${esc(p.texto)}</li>`).join("")}</ul></details>` : "";
  $("#cotNotas").innerHTML = ajustes + avisos + parr;
  $("#cotNotas").hidden = !(ajustes || avisos || parr);

  pintarCondiciones();
  const sumaAj = d.ajustes.reduce((s, a) => s + a.monto, 0);
  $("#cotTotal").innerHTML = `
    <div class="cot-linea"><span>Tarifas</span><b>${pesos(d.base)}</b></div>
    <div class="cot-linea"><span>Recargos y descuentos</span><b class="monto ${sumaAj < 0 ? "neg" : "pos"}">${sumaAj < 0 ? "" : "+"}${pesos(sumaAj)}</b></div>
    <div class="cot-gran-total"><span>Total</span><strong>${d.total == null ? "—" : pesos(d.total)}</strong></div>
    ${d.errores.length ? `<div class="cot-errores">${icono("alerta")}<div><b>No se calcula el total mientras haya errores:</b>
      <ul>${d.errores.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></div></div>` : ""}
    <div class="cot-acciones">
      <button class="boton boton--verde" id="cotExcel" type="button"${d.total == null || !cot.items.length ? " disabled" : ""}>${icono("excel")}Excel</button>
      <button class="boton boton--borde" id="cotLimpiar" type="button">${icono("papelera")}Limpiar</button>
    </div>`;
}

/** "art. 95 par. 7 (pág. 188)" -> la página enlazada al PDF. */
function enlacesCita(cita) {
  return esc(cita).replace(/pág\. (\d+)/, (_, n) => `pág. <a class="pagina" href="/fuentes/pdf#page=${n}" target="_blank" rel="noopener">${n}</a>`);
}

function pintarCondiciones(s = cot, el = $("#cotCondiciones"), g = cotRes.globales) {
  const deptos = COT_CFG.regiones.filter((r) => r.clase === "departamento");
  const regiones = COT_CFG.regiones.filter((r) => r.clase === "region");
  const sel = COT_CFG.regiones.find((r) => r.clave === s.depto);
  const opt = (r) => `<option value="${esc(r.clave)}"${r.clave === s.depto ? " selected" : ""}>${esc(r.nombre)}</option>`;
  const muni = sel ? `<label class="campo-form"><span>Municipio</span><select id="cotMuni">
      <option value="">${sel.clase === "region" ? "Municipio de la región (con incremento)" : "Otro municipio (con incremento)"}</option>
      ${sel.exceptuadas.map((e) => `<option value="${esc(e.clave)}"${e.clave === s.muni ? " selected" : ""}>${esc(e.nombre)} (sin incremento, par. 2)</option>`).join("")}
    </select></label>${sel.observacion ? `<p class="nota-campo">${esc(sel.observacion)}</p>` : ""}` : "";
  const radio = (v, t, sub) => `<label class="radio"><input type="radio" name="mismoActo" value="${v}"${s.mismoActo === v ? " checked" : ""}>
    <span>${t}${sub ? `<small>${sub}</small>` : ""}</span></label>`;
  el.innerHTML = `
    <h2 class="subtitulo">${icono("mapa")}Lugar de la atención</h2>
    <label class="campo-form"><span>Departamento o región (art. 134, <a class="pagina" href="/fuentes/pdf#page=204" target="_blank" rel="noopener">pág. 204</a>)</span>
      <select id="cotDepto"><option value="">Fuera de las regiones del art. 134</option>
        <optgroup label="Departamentos">${deptos.map(opt).join("")}</optgroup>
        <optgroup label="Región">${regiones.map(opt).join("")}</optgroup></select></label>
    ${muni}
    <p class="nota-campo">Con incremento: +15 % en exámenes y procedimientos del Capítulo II (arts. 19-41) y +14 % en los conjuntos (art. 95).
      Solo si el prestador aporta los recursos dentro del área.</p>
    <h2 class="subtitulo">${icono("bisturi")}Varios conjuntos en un mismo acto</h2>
    ${g.conjuntos ? `${radio("", "No")}
      ${radio("igual", "Mismo especialista, igual vía de acceso", "100 % del mayor + 25 % del siguiente")}
      ${radio("diferente", "Otra vía de acceso o distinta especialidad", "100 % del mayor + 70 % de cada uno de los demás")}
      <p class="nota-campo">Art. 95 par. 7, <a class="pagina" href="/fuentes/pdf#page=188" target="_blank" rel="noopener">pág. 188</a>.</p>`
      : `<p class="nota-campo">Aplica cuando la cotización tiene conjuntos del art. 95 (códigos C…).</p>`}
    ${g.tecnecio ? `<h2 class="subtitulo">${icono("radiografia")}Medicina nuclear</h2>
      <label class="radio"><input type="checkbox" id="cotTecnecio"${s.tecnecio ? " checked" : ""}>
        <span>Con tecnecio 99<small>+$13.120 por paciente (art. 27 par. 16)</small></span></label>` : ""}`;
}

async function exportarCot(boton) {
  const original = boton.innerHTML;
  boton.disabled = true;
  boton.innerHTML = `<span class="giro"></span><span>Generando…</span>`;
  try {
    const r = await postJSON("/api/cotizar/excel", pedidoCot());
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
    const nombre = (r.headers.get("Content-Disposition") || "").match(/filename="(.+)"/)?.[1] || "cotizacion.xlsx";
    const url = URL.createObjectURL(await r.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: nombre });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    avisar(`Descargado ${nombre}`);
  } catch (e) {
    avisar("No se pudo exportar: " + e.message, true);
  } finally {
    boton.disabled = false;
    boton.innerHTML = original;
  }
}

// ---------- Auditar factura ----------
// La factura se procesa en el servidor sin guardarse; aquí vive solo en memoria (no en el navegador).
const ESTADOS = ["Conforme", "Glosa", "Revisar"];
const audVacia = () => ({ archivo: null, grupo: "", lineas: [], dec: [], abiertas: new Set(), filtro: "",
  tarifario: "", uvb: null, propiaVersion: null, soatVersion: "base", contrato: 0, opc: {}, rx: {}, tecnecio: false, mismoActo: "", depto: "", muni: "" });
let TAR_CFG = null;
const nombreTarifario = (id = aud.tarifario) => TAR_CFG?.tarifarios.find((t) => t.id === id)?.nombre || "la tarifa";
const ETQ_TARIFARIO = { iss: "ISS 2001", soat: "SOAT", propia: "Tarifa propia" };
const grupoActual = () => aud.archivo?.grupos.find((g) => g.id === aud.grupo);
const ETQ_EPISODIO = { urgencias: "Urgencias", hospitalizacion: "Hospitalización", recienNacidos: "Recién nacido" };
let aud = audVacia();
let audRes = null;
let audSeq = 0;
const num = (v) => (v === "" || v == null ? null : Number(String(v).replace(/\./g, "").replace(",", ".")));

function pedidoAud() {
  return { ...pedidoCot(aud), items: [], lineas: aud.lineas, decisiones: aud.lineas.map((_, i) => aud.dec[i] || {}),
    contrato_pct: aud.tarifario === "propia" ? 0 : aud.contrato || 0, tarifario: aud.tarifario || "iss",
    uvb: aud.uvb || versionSoat()?.uvb || TAR_CFG?.uvb || 12110, propia_version_id: aud.propiaVersion,
    soat_version: String(aud.soatVersion || "base"),
    no_tarifadas: aud.tarifario === "propia" ? [] : grupoActual()?.no_tarifadas || [],
    factura: aud.archivo?.factura || "", grupo: grupoActual()?.etiqueta || "Líneas digitadas" };
}

const recalcularAud = debounce(async () => {
  if (!aud.tarifario) { pintarAudPendiente(); return; }
  if (aud.tarifario === "propia" && !aud.propiaVersion) { await cargarPropias(); pintarAudPendiente(); return; }
  const n = ++audSeq;
  $("#audLineas")?.classList.add("cargando");
  try {
    const r = await postJSON("/api/auditar", pedidoAud());
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
    const d = await r.json();
    if (n !== audSeq) return;
    let otraVez = false;
    if (aud.tecnecio && !d.globales.tecnecio) { aud.tecnecio = false; otraVez = true; }
    if (aud.mismoActo && !d.globales.conjuntos) { aud.mismoActo = ""; otraVez = true; }
    audRes = d;
    pintarAudResultado();
    if (otraVez) recalcularAud();
  } catch (e) {
    avisar("No se pudo auditar: " + e.message, true);
  } finally {
    if (n === audSeq) $("#audLineas")?.classList.remove("cargando");
  }
}, 120);

async function cargarFactura(archivo) {
  if (!archivo) return;
  if (archivo.size > 15e6) { avisar("El archivo pasa de 15 MB", true); return; }
  try {
    const r = await postJSON("/api/auditar/leer", { nombre: archivo.name, contenido: await archivo.text() });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
    const f = await r.json();
    if (!f.grupos.length) throw new Error("La factura no trae líneas");
    aud = { ...audVacia(), archivo: { ...f, nombre: archivo.name } };
    elegirGrupo(f.grupos[0].id);
    avisar(`Cargado ${archivo.name}`);
  } catch (e) {
    avisar(e.message, true);
  }
}

/** Mientras no se elija el tarifario, no se calcula nada. */
function pintarAudPendiente() {
  if (!$("#audLineas")) return;
  audRes = null;
  const propia = aud.tarifario === "propia";
  $("#audLineas").innerHTML = `<div class="estado">${icono("capas")}<div><b>${propia ? "¿Con qué manual de tarifas propias?" : "¿Con qué tarifario se hace la auditoría?"}</b><br>
    ${propia ? "Elija el manual y la versión a la derecha, o suba uno nuevo." : "Elíjalo arriba (ISS 2001, SOAT o tarifa propia)"} para comparar las ${aud.lineas.length} líneas.</div></div>`;
  $("#audNotas").hidden = true;
  $("#audCondiciones").innerHTML = propia ? htmlElegirPropia() : "";
  $("#audTotal").innerHTML = `<p class="nota-campo">Elija el tarifario para ver los totales.</p>
    <div class="cot-acciones"><button class="boton boton--borde" id="audNueva" type="button">${icono("papelera")}Nueva</button></div>`;
}

/** Líneas del paciente según el tarifario: con tarifa propia también se comparan insumos y medicamentos. */
function lineasDelGrupo(g) {
  return [...g.lineas, ...(aud.tarifario === "propia" ? g.no_tarifadas : [])].map((l) => ({ ...l }));
}

async function elegirTarifario(id) {
  if (id === aud.tarifario) return;
  if (id === "propia") await cargarPropias(true);
  if (id === "soat") await cargarSoat();
  if (aud.dec.some((d) => d) && !confirm("Al cambiar de tarifario se pierden las decisiones tomadas. ¿Continuar?")) return;
  aud.tarifario = id;
  if (aud.archivo) {
    const digitadas = aud.lineas.filter((l) => l.origen === "digitada");
    aud.lineas = [...lineasDelGrupo(grupoActual()), ...digitadas];
  }
  aud.dec = []; aud.abiertas = new Set(); aud.filtro = "";
  pintarAudCarga();
  recalcularAud();
}

function elegirGrupo(id) {
  const g = aud.archivo.grupos.find((x) => x.id === id);
  aud.grupo = id;
  aud.lineas = lineasDelGrupo(g);
  aud.dec = [];
  aud.abiertas = new Set();
  aud.opc = {}; aud.rx = {}; aud.tecnecio = false; aud.mismoActo = ""; aud.filtro = "";
  pintarAudCarga();
  recalcularAud();
}

async function pintarAuditar() {
  $("#migaVista").textContent = "Auditar factura";
  const c = $("#contenido");
  c.dataset.vista = "auditar";
  if (!COT_CFG || !TAR_CFG || (aud.tarifario === "propia" && !PROP_CFG)) {
    try {
      COT_CFG ||= await api("/api/cotizador"); TAR_CFG ||= await api("/api/tarifarios");
      if (aud.tarifario === "propia") await cargarPropias();
      if (aud.tarifario === "soat") await cargarSoat();
    } catch (e) {
      c.innerHTML = `<div class="panel estado">${icono("alerta")}<div>${esc(e.message)}</div></div>`;
      return;
    }
  }
  c.innerHTML = `
    <section class="panel">
      <div class="cabecera">
        <div class="cabecera__icono">${icono("lupa")}</div>
        <div><h1>Auditar factura</h1><p>Cargue el RIPS (JSON) o la factura electrónica (XML), digite las líneas o combine
          las dos cosas, y elija con qué tarifario se audita: Manual ISS 2001, SOAT o tarifa propia.
          El estado de cada línea es una sugerencia: usted decide si es conforme, glosa o queda en revisión.</p></div>
      </div>
      <div class="aud-entrada">
        <label class="zona-carga" id="zonaCarga">
          <input type="file" id="audArchivo" accept=".json,.xml,application/json,text/xml,application/xml" hidden>
          ${icono("subir")}<span><b>Cargar factura</b><small>Arrastre aquí el RIPS .json o la factura .xml, o haga clic para elegirlo</small></span>
        </label>
        <form class="aud-manual" id="audManual" autocomplete="off">
          <div class="aud-manual__titulo">${icono("mas")}<b>Digitar una línea</b></div>
          <input name="codigo" placeholder="Código" aria-label="Código" required>
          <input name="cantidad" type="number" min="1" value="1" aria-label="Cantidad" title="Cantidad">
          <input name="valor" inputmode="decimal" placeholder="Valor unitario cobrado" aria-label="Valor unitario cobrado">
          <button class="boton boton--verde" type="submit">Agregar</button>
        </form>
      </div>
      <div id="audCarga"></div>
      <p class="ayuda">El archivo se lee en el servidor solo para esta consulta: no se guarda. Los documentos de los pacientes
        se muestran enmascarados.</p>
    </section>
    <div class="cot-rejilla">
      <div class="cot-principal">
        <section class="panel" id="audLineas"></section>
        <section class="panel" id="audNotas"></section>
      </div>
      <aside class="cot-lateral">
        <section class="panel" id="audCondiciones"></section>
        <section class="panel cot-total" id="audTotal"></section>
      </aside>
    </div>`;
  const zona = $("#zonaCarga");
  $("#audArchivo").addEventListener("change", (ev) => { cargarFactura(ev.target.files[0]); ev.target.value = ""; });
  ["dragenter", "dragover"].forEach((t) => zona.addEventListener(t, (ev) => { ev.preventDefault(); zona.classList.add("encima"); }));
  ["dragleave", "drop"].forEach((t) => zona.addEventListener(t, () => zona.classList.remove("encima")));
  zona.addEventListener("drop", (ev) => { ev.preventDefault(); cargarFactura(ev.dataTransfer.files[0]); });
  $("#audManual").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const f = ev.target;
    const codigo = f.codigo.value.trim();
    if (!codigo) return;
    aud.lineas.push({ codigo, cantidad: Math.max(1, +f.cantidad.value || 1), valor_unitario: num(f.valor.value),
      descripcion: "", origen: "digitada", fecha: "" });
    f.reset();
    f.codigo.focus();
    recalcularAud();
  });
  enlazarAuditar();
  pintarAudCarga();
  if (audRes) pintarAudResultado();
  recalcularAud();
}

function htmlTarifario() {
  return `<div class="aud-tarifario${aud.tarifario ? "" : " pendiente"}">
    <span>${icono("capas")}<b>${aud.tarifario ? "Auditando con" : "¿Con qué tarifario se hace la auditoría?"}</b></span>
    <div class="aud-tarifario__opciones">${(TAR_CFG?.tarifarios || []).map((t) =>
      `<button type="button" data-tarifario="${esc(t.id)}" class="${aud.tarifario === t.id ? "activo" : ""}" title="${esc(t.descripcion)}">
        <b>${esc(ETQ_TARIFARIO[t.id] || t.id)}</b><small>${esc(t.nombre)}</small></button>`).join("")}</div></div>`;
}

function pintarAudCarga() {
  const a = aud.archivo;
  if (!$("#audCarga")) return;
  if (!a) { $("#audCarga").innerHTML = htmlTarifario(); return; }
  const g = a.grupos.find((x) => x.id === aud.grupo);
  $("#audCarga").innerHTML = htmlTarifario() + `<div class="aud-archivo">
    <span class="chip">${icono("documento")}${esc(a.formato)}</span>
    <span class="chip chip--gris">${esc(a.nombre)}</span>
    ${a.factura ? `<span class="chip chip--morado">Factura ${esc(a.factura)}</span>` : ""}
    ${a.grupos.length > 1 ? `<label class="aud-grupo">Paciente
      <select id="audGrupo">${a.grupos.map((x) => `<option value="${esc(x.id)}"${x.id === aud.grupo ? " selected" : ""}>${esc(x.etiqueta)} (${x.lineas.length} líneas)</option>`).join("")}</select></label>
      <small class="sutil">Se audita un paciente a la vez (${a.grupos.length} en el RIPS).</small>` : ""}
  </div>
  ${a.aviso ? `<p class="nota-campo aud-aviso">${icono("alerta")}${esc(a.aviso)}${a.total != null ? ` Total de la factura: <b>${pesos(a.total)}</b>.` : ""}</p>` : ""}
  ${g ? htmlPaciente(g) : ""}`;
  $("#audGrupo")?.addEventListener("change", (ev) => {
    if (aud.dec.some((d) => d) && !confirm("Se pierden las decisiones del paciente actual. ¿Cambiar de paciente?")) {
      ev.target.value = aud.grupo; return;
    }
    elegirGrupo(ev.target.value);
  });
}

/** Datos del usuario del RIPS, episodios (urgencias, hospitalización) e ítems sin tarifa por código. */
function htmlPaciente(g) {
  const u = g.usuario || {};
  const campos = Object.entries(u).filter(([k, v]) => v !== null && v !== "" && k !== "consecutivo");
  const sinTarifa = {};
  for (const o of g.no_tarifadas) {
    const k = o.motivo.split(":")[0];
    const t = (sinTarifa[k] ||= { n: 0, valor: 0, motivo: o.motivo });
    t.n++; t.valor += (o.valor_unitario || 0) * (o.cantidad || 1);
  }
  const tabla = (obj) => `<dl class="aud-campos">${Object.entries(obj).filter(([, v]) => v !== null && v !== "")
    .map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl>`;
  return `<div class="aud-paciente">
    ${campos.length ? `<details><summary>${icono("documento")}Datos del usuario en el RIPS</summary>${tabla(Object.fromEntries(campos))}</details>` : ""}
    ${g.episodios.length ? `<details><summary>${icono("lista")}Urgencias, hospitalización y recién nacidos (${g.episodios.length})</summary>
      ${g.episodios.map((e) => `<h4>${esc(ETQ_EPISODIO[e.tipo] || e.tipo)}</h4>${tabla(e.datos)}`).join("")}</details>` : ""}
    ${Object.keys(sinTarifa).length ? `<details><summary>${icono("caja")}Sin tarifa por código en el Manual (${g.no_tarifadas.length}): se revisan aparte</summary>
      <ul>${Object.entries(sinTarifa).map(([k, t]) => `<li><b>${esc(k)}</b>: ${t.n} ítem(s) por ${pesos(t.valor)}. ${esc(t.motivo.split(": ").slice(1).join(": "))}</li>`).join("")}</ul>
      <p class="sutil">Van en la hoja «Sin tarifa por código» del informe Excel.</p></details>` : ""}
  </div>`;
}

function enlazarAuditar() {
  const tabla = $("#audLineas");
  tabla.addEventListener("click", (ev) => {
    const q = ev.target.closest("[data-quitar]");
    const v = ev.target.closest("[data-ver]");
    if (q) {
      const i = +q.dataset.quitar;
      aud.lineas.splice(i, 1);
      aud.dec.splice(i, 1);
      aud.abiertas = new Set([...aud.abiertas].filter((x) => x !== i).map((x) => (x > i ? x - 1 : x)));
      recalcularAud();
    } else if (v) {
      const i = +v.dataset.ver;
      aud.abiertas.has(i) ? aud.abiertas.delete(i) : aud.abiertas.add(i);
      pintarAudResultado();
    }
  });
  tabla.addEventListener("change", (ev) => {
    const t = ev.target;
    const i = +(t.closest("[data-i]")?.dataset.i ?? -1);
    if (t.dataset.campo) {
      const l = aud.lineas[i];
      if (t.dataset.campo === "codigo") l.codigo = t.value.trim();
      if (t.dataset.campo === "cantidad") l.cantidad = Math.max(1, +t.value || 1);
      if (t.dataset.campo === "valor") l.valor_unitario = num(t.value);
      aud.dec[i] = undefined; // cambió la base: vuelve a la sugerencia
      recalcularAud();
    } else if (t.dataset.dec) {
      const d = (aud.dec[i] ||= {});
      if (t.dataset.dec === "estado") d.estado = t.value;
      if (t.dataset.dec === "glosa") d.glosa = num(t.value);
      if (t.dataset.dec === "observacion") d.observacion = t.value;
      pintarAudResultado();
    } else if (cambiarOpcion(t, aud)) recalcularAud();
  });
  enlazarCondiciones($("#audCondiciones"), () => aud, recalcularAud);
  $("#audCondiciones").addEventListener("change", (ev) => {
    if (ev.target.id === "audContrato") aud.contrato = Number(String(ev.target.value).replace(",", ".")) || 0;
    else if (ev.target.id === "audUvb") aud.uvb = num(ev.target.value) || null;
    else if (ev.target.id === "audSoatVersion") {
      if (aud.dec.some((x) => x) && !confirm("Al cambiar la versión SOAT se pierden las decisiones tomadas. ¿Continuar?")) { ev.target.value = aud.soatVersion; return; }
      aud.soatVersion = ev.target.value; aud.uvb = versionSoat()?.uvb || null; aud.dec = [];
    }
    else if (ev.target.id === "audPropia") {
      if (aud.dec.some((x) => x) && !confirm("Al cambiar de manual se pierden las decisiones tomadas. ¿Continuar?")) { ev.target.value = aud.propiaVersion || ""; return; }
      aud.propiaVersion = Number(ev.target.value) || null; aud.dec = [];
    }
    else return;
    recalcularAud();
  });
  $("#audCondiciones").addEventListener("click", (ev) => {
    if (ev.target.closest("[data-subir-propia], [data-subir-soat]")) volverAuditoria = true;
  });
  $("#audCarga").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-tarifario]");
    if (b) elegirTarifario(b.dataset.tarifario);
  });
  tabla.addEventListener("click", (ev) => {
    const f = ev.target.closest("[data-filtro]");
    if (!f) return;
    aud.filtro = f.dataset.filtro;
    pintarAudResultado();
  });
  $("#audTotal").addEventListener("click", (ev) => {
    const b = ev.target.closest("button");
    if (!b) return;
    if (b.id === "audNueva") {
      if (aud.lineas.length && !confirm("¿Empezar una auditoría nueva? Se borra la actual.")) return;
      aud = audVacia();
      audRes = null;
      pintarAuditar();
    } else if (b.id === "audExcel") exportarAud(b);
  });
}

const estadoLinea = (i) => aud.dec[i]?.estado || audRes.lineas[i]?.estado || "Revisar";
function glosaLinea(i) {
  if (estadoLinea(i) !== "Glosa") return 0;
  const g = aud.dec[i]?.glosa;
  if (g != null) return g;
  const x = audRes.lineas[i];
  return x.estado === "Glosa" || x.estado === "Revisar" ? x.glosa || x.diferencia || 0 : 0;
}

function pintarAudResultado() {
  if (!$("#audLineas") || !audRes) return;
  const d = audRes;
  const n = aud.lineas.length;
  const filas = d.lineas.map((x, i) => {
    const l = aud.lineas[i] || {};
    const est = estadoLinea(i);
    if (aud.filtro && est !== aud.filtro) return "";
    const sugerido = est === x.estado && !aud.dec[i]?.estado;
    const abierta = aud.abiertas.has(i);
    const alertas = x.alertas.length;
    const dif = x.diferencia;
    const detalle = abierta ? `<tr class="aud-detalle" data-i="${i}"><td colspan="11">
        ${x.manual ? `<p><b>${esc(x.manual.codigo)}</b> · ${esc(x.manual.descripcion)}${x.manual.articulo ? ` · art. ${x.manual.articulo}` : ""}${x.manual.agrupador ? ` · <span class="sutil">${esc(x.manual.agrupador)}</span>` : ""}</p>` : ""}
        ${x.descripcion_factura ? `<p class="sutil">En la factura: ${esc(x.descripcion_factura)}</p>` : ""}
        ${x.codigo_factura ? `<p class="sutil">Código en la factura: <b>${esc(x.codigo_factura)}</b> (homologado)</p>` : ""}
        ${x.aplicables?.length ? `<div class="aud-bloque"><span>Recargos que aplican a este código</span><div class="opciones">${htmlOpciones({ codigo: x.manual.codigo, aplicables: x.aplicables }, aud)}</div></div>` : ""}
        ${x.ajustes.length ? `<div class="aud-bloque"><span>Cómo se calcula el valor según ${esc(nombreTarifario())}</span><ul>${x.ajustes.map((a) =>
          `<li><b class="monto ${a.monto < 0 ? "neg" : "pos"}">${a.monto < 0 ? "" : "+"}${pesos(a.monto)}</b> ${esc(a.texto)} · ${enlacesCita(a.cita)}</li>`).join("")}</ul></div>` : ""}
        ${alertas ? `<div class="aud-bloque"><span>Alertas</span><ul>${x.alertas.map((a) =>
          `<li><span class="etiqueta-alerta t-${esc(a.tipo.replace(/\s+/g, "-").toLowerCase())}">${esc(a.tipo)}</span> ${esc(a.texto)}${a.cita ? ` · ${enlacesCita(a.cita)}` : ""}</li>`).join("")}</ul></div>` : ""}
        ${Object.keys(x.datos || {}).length ? `<details class="aud-bloque"><summary>Todos los campos del RIPS (${Object.keys(x.datos).length})</summary>
          <dl class="aud-campos">${Object.entries(x.datos).filter(([, v]) => v !== null && v !== "").map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl></details>` : ""}
        <label class="aud-bloque"><span>Observación del auditor</span>
          <textarea data-dec="observacion" rows="2" placeholder="Sustento de la glosa o de la revisión">${esc(aud.dec[i]?.observacion || "")}</textarea></label>
      </td></tr>` : "";
    return `<tr data-i="${i}" class="aud-fila e-${est.toLowerCase()}">
      <td class="sutil">${esc(x.origen)}</td>
      <td><input class="aud-input cod" data-campo="codigo" value="${esc(l.codigo ?? x.codigo)}" aria-label="Código">
        ${x.manual && (x.codigo_factura || (aud.tarifario === "soat" && x.manual.codigo !== x.codigo)) ? `<small class="aud-homo" title="Código con el que se compara">→ ${esc(ETQ_TARIFARIO[aud.tarifario])} ${esc(x.manual.codigo)}</small>` : ""}</td>
      <td><div class="recorte">${esc(x.manual?.descripcion || x.descripcion_factura || "—")}</div></td>
      <td class="num"><input class="cant" type="number" min="1" data-campo="cantidad" value="${x.cantidad}" aria-label="Cantidad"></td>
      <td class="num"><input class="aud-input num" data-campo="valor" inputmode="decimal" value="${l.valor_unitario ?? ""}" aria-label="Valor unitario cobrado"></td>
      <td class="num">${x.facturado == null ? "—" : pesos(x.facturado)}</td>
      <td class="num">${x.esperado == null ? "—" : pesos(x.esperado)}</td>
      <td class="num monto ${dif > 1 ? "neg" : ""}">${dif == null ? "—" : (dif > 0 ? "+" : "") + pesos(dif)}</td>
      <td><select class="aud-estado e-${est.toLowerCase()}" data-dec="estado" title="${esc(x.motivo)}${sugerido ? " (sugerido)" : ""}">
        ${ESTADOS.map((e) => `<option${e === est ? " selected" : ""}>${e}</option>`).join("")}</select>
        ${est === "Glosa" ? `<input class="aud-input num aud-glosa" data-dec="glosa" inputmode="decimal" value="${glosaLinea(i)}" title="Valor a glosar" aria-label="Valor a glosar">` : ""}</td>
      <td><button class="aud-ver${alertas ? " con" : ""}" type="button" data-ver="${i}" title="Ver detalle">${alertas ? `${icono("alerta")}${alertas}` : icono("der")}</button></td>
      <td><button class="boton-icono" type="button" data-quitar="${i}" title="Quitar línea">${icono("x")}</button></td>
    </tr>${detalle}`;
  }).join("");
  $("#audLineas").innerHTML = `
    <div class="aud-cabecera-lineas"><h2 class="subtitulo">${icono("lista")}Líneas de la factura (${n})</h2>
      <div class="segmentado">${[["", "Todas"], ...ESTADOS.map((e) => [e, e])].map(([v, t]) =>
        `<button type="button" data-filtro="${v}" class="${aud.filtro === v ? "activo" : ""}">${t}</button>`).join("")}</div></div>
    ${n ? `<div class="tabla-marco cot-tabla aud-tabla"><table>
      <thead><tr><th>Origen</th><th>Código</th><th>Descripción</th><th class="num">Cant.</th><th class="num">V. unit. cobrado</th>
        <th class="num">Facturado</th><th class="num">Según ${esc(ETQ_TARIFARIO[aud.tarifario] || "tarifa")}</th><th class="num">Diferencia</th><th>Estado</th><th></th><th></th></tr></thead>
      <tbody>${filas}</tbody></table></div>`
      : `<div class="estado">${icono("lupa")}<div>Cargue una factura o digite la primera línea.</div></div>`}`;

  const avisos = d.avisos.length ? `<details class="cot-detalles" open><summary>${icono("alerta")}Avisos (${d.avisos.length})</summary>
    <ul>${d.avisos.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></details>` : "";
  const parr = d.parrafos.length ? `<details class="cot-detalles"><summary>${icono("documento")}Parágrafos que pueden modificar el valor (${d.parrafos.length})</summary>
    <ul>${d.parrafos.map((p) => `<li><span class="chip ${p.opcion ? "" : "chip--gris"}">art. ${p.articulo}</span> ${esc(p.texto)}</li>`).join("")}</ul></details>` : "";
  $("#audNotas").innerHTML = avisos + parr;
  $("#audNotas").hidden = !(avisos || parr);

  const etq = ETQ_TARIFARIO[aud.tarifario];
  if (aud.tarifario === "propia") { $("#audCondiciones").innerHTML = htmlElegirPropia(); }
  else if (aud.tarifario === "iss") pintarCondiciones(aud, $("#audCondiciones"), d.globales);
  else $("#audCondiciones").innerHTML = aud.tarifario === "soat" ? `<h2 class="subtitulo">${icono("etiqueta")}SOAT</h2>
    <label class="campo-form"><span>Versión de la tarifa SOAT</span><select id="audSoatVersion">
      ${(SOAT_CFG?.versiones || [{ id: "base", nombre: "SOAT 2026 (por defecto)", anio: 2026, estado: "activo" }]).map((v) =>
        `<option value="${esc(v.id)}"${String(v.id) === String(aud.soatVersion) ? " selected" : ""}>${esc(v.nombre)}${v.estado !== "activo" ? " · inactiva" : ""}</option>`).join("")}</select></label>
    <a class="boton boton--borde" href="#/soat-versiones" data-subir-soat>${icono("subir")}Subir tarifa SOAT nueva</a>
    <label class="campo-form" style="margin-top:12px"><span>Valor de la UVB (de la versión: ${pesos(versionSoat()?.uvb || 12110)}). Cámbielo si la factura es de otro año.</span>
      <input class="aud-input" id="audUvb" inputmode="decimal" value="${aud.uvb || versionSoat()?.uvb || 12110}"></label>
    <p class="nota-campo">Valor SOAT = factor UVB del código × UVB. La cirugía por grupo quirúrgico aún no se liquida: esas líneas quedan en Revisar.</p>`
    : "";
  if (aud.tarifario !== "propia") $("#audCondiciones").insertAdjacentHTML("afterbegin", `<h2 class="subtitulo">${icono("porcentaje")}Contrato</h2>
    <label class="campo-form"><span>Porcentaje pactado sobre la tarifa ${esc(etq)} (ej. 30 para «${esc(etq)} + 30 %», −5 para «${esc(etq)} − 5 %»)</span>
      <input class="aud-input" id="audContrato" type="number" step="0.01" value="${aud.contrato || 0}"></label>`);
  const cuenta = Object.fromEntries(ESTADOS.map((e) => [e, 0]));
  d.lineas.forEach((_, i) => cuenta[estadoLinea(i)]++);
  const glosa = d.lineas.reduce((s, _, i) => s + (glosaLinea(i) || 0), 0);
  const s = d.resumen;
  $("#audTotal").innerHTML = `
    <div class="cot-linea"><span>Facturado</span><b>${pesos(s.facturado)}</b></div>
    <div class="cot-linea"><span>Según ${esc(nombreTarifario())}</span><b>${pesos(s.esperado)}</b></div>
    <div class="cot-linea"><span>Líneas comparadas</span><b>${s.comparables} de ${s.lineas}</b></div>
    <div class="aud-cuentas">${ESTADOS.map((e) => `<span class="aud-cuenta e-${e.toLowerCase()}"><b>${cuenta[e]}</b>${e}</span>`).join("")}</div>
    <div class="cot-gran-total"><span>Total a glosar</span><strong class="aud-total-glosa">${pesos(glosa)}</strong></div>
    ${d.errores.length ? `<div class="cot-errores">${icono("alerta")}<div><b>Revise las condiciones:</b>
      <ul>${d.errores.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></div></div>` : ""}
    <div class="cot-acciones">
      <button class="boton boton--verde" id="audExcel" type="button"${n ? "" : " disabled"}>${icono("excel")}Informe Excel</button>
      <button class="boton boton--borde" id="audNueva" type="button">${icono("papelera")}Nueva</button>
    </div>`;
}

async function exportarAud(boton) {
  const original = boton.innerHTML;
  boton.disabled = true;
  boton.innerHTML = `<span class="giro"></span><span>Generando…</span>`;
  try {
    const pedido = pedidoAud();
    pedido.decisiones = aud.lineas.map((_, i) => ({ estado: estadoLinea(i), glosa: glosaLinea(i), observacion: aud.dec[i]?.observacion || "" }));
    const r = await postJSON("/api/auditar/excel", pedido);
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
    const nombre = (r.headers.get("Content-Disposition") || "").match(/filename="(.+)"/)?.[1] || "auditoria.xlsx";
    const url = URL.createObjectURL(await r.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: nombre });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    avisar(`Descargado ${nombre}`);
  } catch (e) {
    avisar("No se pudo exportar: " + e.message, true);
  } finally {
    boton.disabled = false;
    boton.innerHTML = original;
  }
}

// ---------- Manuales de tarifas propias ----------
// Se suben como Excel (CUPS, CUMS, INSUMOS, MATERIALES), con versión, vigencia y estado; se guardan en la base
// de tarifas propias (TARIFAS_DB_URL). Cada subida a un código existente crea una versión nueva.
let PROP_CFG = null;
let volverAuditoria = false;
const ETQ_BASE = { valor_fijo: "Valor fijo ($)", soat: "Factor sobre SOAT", iss: "Factor sobre ISS 2001" };
const ETQ_ESTADO = { borrador: "Borrador", activo: "Activo", inactivo: "Inactivo", vencido: "Vencido" };

async function cargarPropias(forzar = false) {
  if (PROP_CFG && !forzar) return PROP_CFG;
  try { PROP_CFG = await api("/api/propias"); } catch (e) { avisar(e.message, true); PROP_CFG = { destino: "", manuales: [] }; }
  return PROP_CFG;
}

function htmlElegirPropia() {
  const ms = PROP_CFG?.manuales || [];
  const opciones = ms.map((m) => `<optgroup label="${esc(m.codigo)} · ${esc(m.nombre)}">${m.versiones.map((v) =>
    `<option value="${v.id}"${v.id === aud.propiaVersion ? " selected" : ""}>v${v.version} · ${esc(ETQ_ESTADO[v.estado_vigente])} · ${esc(ETQ_BASE[v.tipo_base])}${v.factor_pct ? ` ${v.factor_pct > 0 ? "+" : ""}${v.factor_pct} %` : ""} · ${v.filas} códigos</option>`).join("")}</optgroup>`).join("");
  const v = ms.flatMap((m) => m.versiones.map((x) => ({ ...x, nombre: m.nombre }))).find((x) => x.id === aud.propiaVersion);
  return `<h2 class="subtitulo">${icono("etiqueta")}Manual de tarifas propias</h2>
    ${ms.length ? `<label class="campo-form"><span>Manual y versión</span><select id="audPropia"><option value="">Elija…</option>${opciones}</select></label>` :
      `<p class="nota-campo">Aún no hay manuales de tarifas propias.</p>`}
    ${v ? `<p class="nota-campo">${esc(v.nombre)} · vigencia ${esc(v.vigencia_inicio || "—")} a ${esc(v.vigencia_fin || "—")} · ${esc(v.archivo || "")}
      ${v.estado_vigente !== "activo" ? `<br><b class="monto neg">Esta versión está ${esc(ETQ_ESTADO[v.estado_vigente]).toLowerCase()}.</b>` : ""}</p>` : ""}
    <a class="boton boton--borde" href="#/tarifas-propias" data-subir-propia>${icono("subir")}Subir manual nuevo</a>`;
}

const leerBase64 = (archivo) => new Promise((ok, mal) => {
  const r = new FileReader();
  r.onload = () => ok(String(r.result).split(",")[1] || "");
  r.onerror = () => mal(new Error("No se pudo leer el archivo"));
  r.readAsDataURL(archivo);
});

async function pintarPropias() {
  $("#migaVista").textContent = "Manuales de tarifas propias";
  const c = $("#contenido");
  c.dataset.vista = "tarifas-propias";
  await cargarPropias(true);
  const codigos = PROP_CFG.manuales.map((m) => `<option value="${esc(m.codigo)}">${esc(m.nombre)}</option>`).join("");
  c.innerHTML = `
    <section class="panel">
      <div class="cabecera">
        <div class="cabecera__icono">${icono("subir")}</div>
        <div><h1>Manuales de tarifas propias</h1><p>Registre el manual pactado con cada pagador: código propio, nombre,
          tipo de liquidación (valor fijo o factor sobre SOAT o ISS), vigencia y estado. Suba el Excel del anexo de contratación;
          si el código ya existe se crea una versión nueva y las anteriores se conservan para las glosas de vigencias pasadas.</p></div>
      </div>
      ${volverAuditoria ? `<p><a class="boton boton--morado" href="#/auditar">${icono("izq")}Volver a la auditoría</a></p>` : ""}
      <form class="propia-form" id="propiaForm" autocomplete="off">
        <label class="campo-form"><span>Código del manual *</span><input class="aud-input" name="codigo" list="propiaCodigos" required placeholder="TAR-PROPIA-2026-01" pattern="[A-Za-z0-9][A-Za-z0-9._\\-]{2,49}"></label>
        <datalist id="propiaCodigos">${codigos}</datalist>
        <label class="campo-form"><span>Nombre del manual *</span><input class="aud-input" name="nombre_manual" required placeholder="Tarifario Preferencial Convenio X"></label>
        <label class="campo-form"><span>Pagador / convenio</span><input class="aud-input" name="pagador"></label>
        <label class="campo-form"><span>Tipo de liquidación base</span><select name="tipo_base">
          ${Object.entries(ETQ_BASE).map(([k, t]) => `<option value="${k}">${t}</option>`).join("")}</select></label>
        <label class="campo-form"><span>Factor % sobre la base (ej. −5)</span><input class="aud-input" name="factor_pct" type="number" step="0.01" value="0"></label>
        <label class="campo-form"><span>Vigencia: inicio</span><input class="aud-input" name="vigencia_inicio" type="date"></label>
        <label class="campo-form"><span>Vigencia: fin</span><input class="aud-input" name="vigencia_fin" type="date"></label>
        <label class="campo-form"><span>Estado</span><select name="estado">
          <option value="borrador">Borrador</option><option value="activo">Activo</option><option value="inactivo">Inactivo</option></select></label>
        <label class="campo-form propia-ancho"><span>Observación</span><input class="aud-input" name="observacion"></label>
        <label class="zona-carga propia-ancho" id="propiaZona">
          <input type="file" name="archivo" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" hidden required>
          ${icono("subir")}<span><b id="propiaArchivo">Elegir el Excel del manual (.xlsx)</b><small>Hojas CUPS, CUMS (o MEDICAMENTOS), INSUMOS y MATERIALES con Código, Descripción, Tarifa y, opcionales, Tipo liquidación y Factor %</small></span>
        </label>
        <div class="cot-acciones propia-ancho">
          <button class="boton boton--borde" type="button" id="propiaPrevia">${icono("ojo")}Vista previa</button>
          <button class="boton boton--verde" type="submit" id="propiaGuardar" disabled>${icono("descarga")}Guardar versión</button>
          <a class="boton boton--borde" href="/api/propias-plantilla">${icono("excel")}Plantilla para llenar</a>
        </div>
        <p class="ayuda propia-ancho">Descargue la plantilla, llene las hojas CUPS, CUMS, INSUMOS y MATERIALES (la hoja INSTRUCCIONES
          trae ejemplos y no se carga), y súbala aquí con los datos del manual.</p>
      </form>
      <div id="propiaPreviaRes"></div>
      <p class="ayuda">Se guarda en: ${esc(PROP_CFG.destino || "—")}</p>
    </section>
    <section class="panel" id="propiaLista"></section>`;
  pintarListaPropias();
  enlazarListaPropias();
  const f = $("#propiaForm");
  let previaOk = false;
  const invalidar = () => { previaOk = false; $("#propiaGuardar").disabled = true; };
  f.addEventListener("input", invalidar);
  f.archivo.addEventListener("change", () => { $("#propiaArchivo").textContent = f.archivo.files[0]?.name || "Elegir el Excel del manual (.xlsx)"; invalidar(); });
  f.codigo.addEventListener("change", () => {
    const m = PROP_CFG.manuales.find((x) => x.codigo === f.codigo.value.trim().toUpperCase());
    if (m && !f.nombre_manual.value) { f.nombre_manual.value = m.nombre; f.pagador.value = m.pagador || ""; }
  });
  $("#propiaPrevia").addEventListener("click", async () => {
    const a = f.archivo.files[0];
    if (!a) { avisar("Elija el archivo Excel", true); return; }
    try {
      const r = await postJSON("/api/propias/previa", { nombre: a.name, contenido_b64: await leerBase64(a), tipo_base: f.tipo_base.value });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
      const d = await r.json();
      previaOk = !d.errores.length;
      $("#propiaGuardar").disabled = !previaOk;
      $("#propiaPreviaRes").innerHTML = `<div class="propia-previa">
        <p><b>${d.filas} códigos</b>: ${Object.entries(d.por_tipo).map(([t, n]) => `${esc(t)} ${n}`).join(" · ")}</p>
        ${d.errores.length ? `<div class="cot-errores">${icono("alerta")}<div><b>No se puede guardar:</b><ul>${d.errores.slice(0, 20).map((e) => `<li>${esc(e)}</li>`).join("")}</ul></div></div>` : ""}
        ${d.avisos.length ? `<details class="cot-detalles" open><summary>${icono("alerta")}Avisos (${d.avisos.length})</summary><ul>${d.avisos.slice(0, 30).map((x) => `<li>${esc(x)}</li>`).join("")}</ul></details>` : ""}
        <div class="tabla-marco cot-tabla"><table><thead><tr><th>Hoja</th><th>Tipo</th><th>Código</th><th>Descripción</th><th class="num">Tarifa</th><th>Liquidación</th><th class="num">Factor %</th></tr></thead>
        <tbody>${d.muestra.map((x) => `<tr><td>${esc(x.hoja)}</td><td>${esc(x.tipo)}</td><td class="cod">${esc(x.codigo)}</td><td>${esc(x.descripcion)}</td>
          <td class="num">${x.tarifa == null ? "—" : pesos(x.tarifa)}</td><td>${esc(x.tipo_liquidacion ? ETQ_BASE[x.tipo_liquidacion] : "del manual")}</td>
          <td class="num">${x.factor_pct ?? "—"}</td></tr>`).join("")}</tbody></table></div>
        ${d.filas > 20 ? `<p class="sutil">Se muestran las primeras 20.</p>` : ""}</div>`;
    } catch (e) { avisar(e.message, true); }
  });
  f.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!previaOk) return;
    const a = f.archivo.files[0];
    const datos = Object.fromEntries(new FormData(f).entries());
    delete datos.archivo;
    datos.factor_pct = Number(datos.factor_pct) || 0;
    for (const k of ["vigencia_inicio", "vigencia_fin"]) if (!datos[k]) datos[k] = null;
    try {
      const r = await postJSON("/api/propias", { ...datos, nombre: a.name, contenido_b64: await leerBase64(a) });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
      const v = await r.json();
      avisar(`Guardado ${v.manual} versión ${v.version} (${v.filas} códigos)`);
      if (volverAuditoria) { aud.tarifario = "propia"; aud.propiaVersion = v.id; aud.dec = []; }
      await cargarPropias(true);
      pintarPropias();
    } catch (e) { avisar(e.message, true); }
  });
}

function pintarListaPropias() {
  const ms = PROP_CFG.manuales;
  $("#propiaLista").innerHTML = `<h2 class="subtitulo">${icono("capas")}Manuales registrados (${ms.length})</h2>
    ${ms.length ? ms.map((m) => `<article class="propia-manual">
      <h3><span class="cod">${esc(m.codigo)}</span> ${esc(m.nombre)} ${m.pagador ? `<small class="sutil">· ${esc(m.pagador)}</small>` : ""}</h3>
      <div class="tabla-marco cot-tabla"><table><thead><tr><th>Versión</th><th>Estado</th><th>Liquidación</th><th>Vigencia</th><th class="num">Códigos</th><th>Archivo</th><th>Cargado</th><th></th></tr></thead>
      <tbody>${m.versiones.map((v) => `<tr data-version="${v.id}">
        <td><b>v${v.version}</b></td>
        <td><select class="aud-estado e-${v.estado_vigente === "activo" ? "conforme" : v.estado_vigente === "borrador" ? "revisar" : "glosa"}" data-estado-version="${v.id}">
          ${["borrador", "activo", "inactivo"].map((e) => `<option value="${e}"${e === v.estado ? " selected" : ""}>${ETQ_ESTADO[e]}</option>`).join("")}</select>
          ${v.estado_vigente === "vencido" ? `<small class="monto neg">vencido</small>` : ""}</td>
        <td>${esc(ETQ_BASE[v.tipo_base])}${v.factor_pct ? ` ${v.factor_pct > 0 ? "+" : ""}${v.factor_pct} %` : ""}</td>
        <td class="sin-salto">${esc(v.vigencia_inicio || "—")} a ${esc(v.vigencia_fin || "—")}</td>
        <td class="num">${v.filas}</td>
        <td><a class="pagina" href="/api/propias/${v.id}/archivo">${esc(v.archivo || "Excel")}</a></td>
        <td class="sutil sin-salto">${esc(String(v.cargado_en || "").slice(0, 16).replace("T", " "))}</td>
        <td class="sin-salto"><button class="boton-icono" type="button" data-items="${v.id}" title="Ver códigos">${icono("lista")}</button>
          <button class="boton-icono" type="button" data-usar="${v.id}" title="Usar en una auditoría">${icono("lupa")}</button></td>
      </tr>`).join("")}</tbody></table></div></article>`).join("")
      : `<div class="estado">${icono("vacio")}<div>Aún no hay manuales. Suba el primero arriba.</div></div>`}`;
}

function enlazarListaPropias() {
  const lista = $("#propiaLista");
  lista.addEventListener("change", async (ev) => {
    const id = ev.target.dataset.estadoVersion;
    if (!id) return;
    try {
      const r = await postJSON(`/api/propias/${id}/estado`, { estado: ev.target.value });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
      avisar("Estado actualizado");
      await cargarPropias(true);
      pintarListaPropias();
    } catch (e) { avisar(e.message, true); }
  });
  lista.addEventListener("click", async (ev) => {
    const b = ev.target.closest("button");
    if (!b) return;
    if (b.dataset.usar) {
      aud.tarifario = "propia"; aud.propiaVersion = Number(b.dataset.usar); aud.dec = [];
      if (aud.archivo) aud.lineas = [...lineasDelGrupo(grupoActual()), ...aud.lineas.filter((l) => l.origen === "digitada")];
      navegar({ vista: "auditar" });
    } else if (b.dataset.items) {
      try {
        const its = await api(`/api/propias/${b.dataset.items}/items`);
        $("#cajonTitulo").textContent = `Códigos de la versión (${its.length})`;
        $("#cajonCuerpo").innerHTML = `<div class="tabla-marco cot-tabla"><table><thead><tr><th>Tipo</th><th>Código</th><th>Descripción</th><th class="num">Tarifa</th><th>Liq.</th><th class="num">%</th></tr></thead>
          <tbody>${its.map((x) => `<tr><td>${esc(x.tipo)}</td><td class="cod">${esc(x.codigo)}</td><td>${esc(x.descripcion || "")}</td>
          <td class="num">${x.tarifa == null ? "—" : pesos(x.tarifa)}</td><td>${esc(x.tipo_liquidacion || "")}</td><td class="num">${x.factor_pct ?? ""}</td></tr>`).join("")}</tbody></table></div>`;
        $("#cajon").classList.add("abierto");
        $("#velo").classList.add("visible");
      } catch (e) { avisar(e.message, true); }
    }
  });
}

// ---------- Versiones de la tarifa SOAT ----------
// La SOAT 2026 viene en el repositorio (por defecto); las de otros años se suben como Excel (hojas TABLA y TD).
let SOAT_CFG = null;
const versionSoat = () => SOAT_CFG?.versiones.find((v) => String(v.id) === String(aud.soatVersion || "base"));

async function cargarSoat(forzar = false) {
  if (SOAT_CFG && !forzar) return SOAT_CFG;
  try { SOAT_CFG = await api("/api/soat/versiones"); } catch (e) { avisar(e.message, true); }
  return SOAT_CFG;
}

async function pintarSoatVersiones() {
  $("#migaVista").textContent = "Versiones de tarifa SOAT";
  const c = $("#contenido");
  c.dataset.vista = "soat-versiones";
  await cargarSoat(true);
  const anio = new Date().getFullYear();
  c.innerHTML = `
    <section class="panel">
      <div class="cabecera">
        <div class="cabecera__icono">${icono("calendario")}</div>
        <div><h1>Versiones de tarifa SOAT</h1><p>La tarifa SOAT cambia cada año (valor de la UVB y, a veces, los factores).
          La SOAT 2026 viene con el sistema y es la versión por defecto. Suba la de otro año con el mismo formato del maestro SOAT:
          hoja <b>TABLA</b> (código, descripción, % SMLV, factor UVT, factor UVB) y hoja <b>TD</b> (valor de la UVB). Al auditar se elige
          la versión. La relación CUPS-SOAT y los grupos quirúrgicos (Decreto 780) se comparten entre versiones; si a una tabla le falta
          un componente de cirugía se calcula con el decreto.</p></div>
      </div>
      ${volverAuditoria ? `<p><a class="boton boton--morado" href="#/auditar">${icono("izq")}Volver a la auditoría</a></p>` : ""}
      <form class="propia-form" id="soatForm" autocomplete="off">
        <label class="campo-form"><span>Año *</span><input class="aud-input" name="anio" type="number" min="2000" max="2100" value="${anio + 1}" required></label>
        <label class="campo-form"><span>Nombre</span><input class="aud-input" name="nombre_version" placeholder="SOAT ${anio + 1}"></label>
        <label class="campo-form"><span>Valor de la UVB (si no viene en la hoja TD)</span><input class="aud-input" name="uvb" inputmode="decimal"></label>
        <label class="campo-form"><span>Estado</span><select name="estado"><option value="activo">Activo</option><option value="inactivo">Inactivo</option></select></label>
        <label class="campo-form propia-ancho"><span>Observación (norma, resolución)</span><input class="aud-input" name="observacion"></label>
        <label class="zona-carga propia-ancho">
          <input type="file" name="archivo" accept=".xlsx" hidden required>
          ${icono("subir")}<span><b id="soatArchivo">Elegir el Excel de la tarifa SOAT (.xlsx)</b><small>Mismo formato que «SOAT A SALARIO MINIMO_UVT_UVB.xlsx»</small></span>
        </label>
        <div class="cot-acciones propia-ancho">
          <button class="boton boton--borde" type="button" id="soatPrevia">${icono("ojo")}Vista previa</button>
          <button class="boton boton--verde" type="submit" id="soatGuardar" disabled>${icono("descarga")}Guardar versión</button>
          <a class="boton boton--borde" href="/api/soat/plantilla" title="Excel prellenado con la SOAT 2026: actualice la UVB y los factores">${icono("excel")}Plantilla (prellenada con SOAT 2026)</a>
        </div>
        <p class="ayuda propia-ancho">¿Cómo preparar la tarifa del año nuevo? Descargue la plantilla (trae todos los códigos y factores
          vigentes), cambie la UVB en la hoja TD y los factores que cambien en la hoja TABLA, y súbala aquí.</p>
      </form>
      <div id="soatPreviaRes"></div>
      <p class="ayuda">Las versiones subidas se guardan en: ${esc(SOAT_CFG?.destino || "—")}</p>
    </section>
    <section class="panel" id="soatLista"></section>`;
  pintarListaSoat();
  const f = $("#soatForm");
  let ok = false;
  const invalidar = () => { ok = false; $("#soatGuardar").disabled = true; };
  f.addEventListener("input", invalidar);
  f.archivo.addEventListener("change", () => { $("#soatArchivo").textContent = f.archivo.files[0]?.name || "Elegir el Excel de la tarifa SOAT (.xlsx)"; invalidar(); });
  $("#soatPrevia").addEventListener("click", async () => {
    const a = f.archivo.files[0];
    if (!a) { avisar("Elija el archivo Excel", true); return; }
    try {
      const r = await postJSON("/api/soat/previa", { nombre: a.name, contenido_b64: await leerBase64(a) });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
      const d = await r.json();
      if (d.uvb && !f.uvb.value) f.uvb.value = d.uvb;
      ok = Boolean(d.uvb || num(f.uvb.value));
      $("#soatGuardar").disabled = !ok;
      $("#soatPreviaRes").innerHTML = `<div class="propia-previa">
        <p><b>${d.filas} códigos</b> · UVB en la hoja TD: <b>${d.uvb ? pesos(d.uvb) : "no viene (escríbala arriba)"}</b> · componentes de cirugía: ${d.componentes_cirugia}
          ${d.calculados.length ? ` · <span class="monto neg">calculados con el Decreto 780: ${esc(d.calculados.join(", "))}</span>` : ""}</p>
        <div class="tabla-marco cot-tabla"><table><thead><tr><th>Código</th><th>Descripción</th><th class="num">Factor UVB</th><th>Origen</th></tr></thead>
        <tbody>${d.muestra.map((x) => `<tr><td class="cod">${esc(x.codigo)}</td><td>${esc(x.descripcion)}</td><td class="num">${x.factor_uvb}</td><td>${esc(x.origen)}</td></tr>`).join("")}</tbody></table></div>
        <p class="sutil">Primeras 20 filas.</p></div>`;
    } catch (e) { avisar(e.message, true); }
  });
  f.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!ok) return;
    const a = f.archivo.files[0];
    const datos = Object.fromEntries(new FormData(f).entries());
    delete datos.archivo;
    datos.anio = Number(datos.anio);
    datos.uvb = num(datos.uvb) || null;
    try {
      const r = await postJSON("/api/soat/versiones", { ...datos, nombre: a.name, contenido_b64: await leerBase64(a) });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
      const v = await r.json();
      avisar(`Guardada SOAT ${v.anio} (UVB ${pesos(v.uvb)}, ${v.filas} códigos)`);
      await cargarSoat(true);
      if (volverAuditoria) { aud.tarifario = "soat"; aud.soatVersion = String(v.id); aud.uvb = v.uvb; aud.dec = []; }
      pintarSoatVersiones();
    } catch (e) { avisar(e.message, true); }
  });
  $("#soatLista").addEventListener("change", async (ev) => {
    const id = ev.target.dataset.estadoSoat;
    if (!id) return;
    try {
      const r = await postJSON(`/api/soat/versiones/${id}/estado`, { estado: ev.target.value });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
      avisar("Estado actualizado"); await cargarSoat(true); pintarListaSoat();
    } catch (e) { avisar(e.message, true); }
  });
  $("#soatLista").addEventListener("click", async (ev) => {
    const b = ev.target.closest("button");
    if (!b) return;
    if (b.dataset.usarSoat) {
      const v = SOAT_CFG.versiones.find((x) => String(x.id) === b.dataset.usarSoat);
      aud.tarifario = "soat"; aud.soatVersion = String(v.id); aud.uvb = v.uvb; aud.dec = [];
      navegar({ vista: "auditar" });
    } else if (b.dataset.tarifasSoat) {
      try {
        const ts = await api(`/api/soat/versiones/${b.dataset.tarifasSoat}/tarifas`);
        $("#cajonTitulo").textContent = `Tarifas de la versión (${ts.length})`;
        $("#cajonCuerpo").innerHTML = `<div class="tabla-marco cot-tabla"><table><thead><tr><th>Código</th><th>Descripción</th><th class="num">Factor UVB</th><th>Origen</th></tr></thead>
          <tbody>${ts.map((x) => `<tr><td class="cod">${esc(x.codigo)}</td><td>${esc(x.descripcion || "")}</td><td class="num">${x.factor_uvb}</td><td>${esc(x.origen || "")}</td></tr>`).join("")}</tbody></table></div>`;
        $("#cajon").classList.add("abierto"); $("#velo").classList.add("visible");
      } catch (e) { avisar(e.message, true); }
    }
  });
}

function pintarListaSoat() {
  const vs = SOAT_CFG?.versiones || [];
  $("#soatLista").innerHTML = `<h2 class="subtitulo">${icono("calendario")}Versiones disponibles (${vs.length})</h2>
    <div class="tabla-marco cot-tabla"><table><thead><tr><th>Año</th><th>Nombre</th><th class="num">UVB</th><th>Estado</th><th class="num">Códigos</th><th>Archivo</th><th>Cargada</th><th></th></tr></thead>
    <tbody>${vs.map((v) => `<tr>
      <td><b>${v.anio}</b></td><td>${esc(v.nombre)}${v.predeterminada ? ` <span class="chip">por defecto</span>` : ""}</td>
      <td class="num">${pesos(v.uvb)}</td>
      <td>${v.predeterminada ? `<span class="chip">Activo</span>` : `<select class="aud-estado e-${v.estado === "activo" ? "conforme" : "glosa"}" data-estado-soat="${v.id}">
        ${["activo", "inactivo"].map((e) => `<option value="${e}"${e === v.estado ? " selected" : ""}>${e === "activo" ? "Activo" : "Inactivo"}</option>`).join("")}</select>`}</td>
      <td class="num">${v.filas}</td>
      <td>${v.predeterminada ? esc(v.archivo) : `<a class="pagina" href="/api/soat/versiones/${v.id}/archivo">${esc(v.archivo || "Excel")}</a>`}</td>
      <td class="sutil sin-salto">${esc(String(v.cargado_en || "con el sistema").slice(0, 16).replace("T", " "))}</td>
      <td class="sin-salto"><a class="boton-icono" href="/api/soat/plantilla?version=${esc(v.id)}" title="Plantilla prellenada con esta versión">${icono("excel")}</a>
        ${v.predeterminada ? "" : `<button class="boton-icono" type="button" data-tarifas-soat="${v.id}" title="Ver tarifas">${icono("lista")}</button>`}
        <button class="boton-icono" type="button" data-usar-soat="${v.id}" title="Usar en una auditoría">${icono("lupa")}</button></td></tr>`).join("")}</tbody></table></div>
    <p class="ayuda">Las tarifas de la versión por defecto se consultan en «SOAT 2026» y «Cirugía SOAT por grupo».</p>`;
}

// ---------- Arranque ----------
function render() {
  marcarMenu();
  if (estado.vista === "fuentes") pintarFuentes();
  else if (estado.vista === "cotizar") pintarCotizar();
  else if (estado.vista === "auditar") pintarAuditar();
  else if (estado.vista === "tarifas-propias") pintarPropias();
  else if (estado.vista === "soat-versiones") pintarSoatVersiones();
  else if (estado.vista) pintarVista();
  else { $("#contenido").dataset.vista = ""; pintarInicio(); }
}

async function iniciar() {
  $("#abrirMenu").innerHTML = icono("menu");
  $("#cerrarCajon").innerHTML = icono("x");
  $("#cerrarCajon").addEventListener("click", cerrarDetalle);
  $("#abrirMenu").addEventListener("click", () => { $("#sidebar").classList.add("abierto"); $("#velo").classList.add("visible"); });
  $("#velo").addEventListener("click", () => { cerrarDetalle(); cerrarMenuMovil(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrarDetalle(); });
  try {
    VISTAS = await api("/api/vistas");
  } catch (e) {
    $("#contenido").innerHTML = `<div class="panel estado">${icono("alerta")}<div>${esc(e.message)}</div></div>`;
    return;
  }
  pintarMenu();
  estado = leerRuta();
  window.addEventListener("popstate", () => { estado = leerRuta(); render(); });
  render();
}

iniciar();
