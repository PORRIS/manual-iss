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
    if (g === "Cotizador") h += `<a class="menu__item" href="#/cotizar" data-vista="cotizar">${icono("calculadora")}<span>Cotizar</span></a>`;
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
        portátil, bilateral, varios conjuntos en un mismo acto y regiones del art. 134.</p></div></button>` + VISTAS.map((v) => {
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

function pedidoCot() {
  const lista = (op) => Object.keys(cot.opc).filter((c) => cot.opc[c][op]);
  return {
    items: cot.items,
    solo_muestra: lista("solo-muestra"), biopsia_multiple: lista("biopsia-multiple"),
    portatil_eco: lista("portatil-eco"), bilateral: lista("bilateral"),
    portatil_rx: Object.fromEntries(Object.entries(cot.rx).filter(([, v]) => v)),
    tecnecio: cot.tecnecio, mismo_acto: cot.mismoActo || null,
    region: cot.depto ? `${cot.depto}:${cot.muni || "OTRO"}` : null,
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
    } else if (t.dataset.rx !== undefined) {
      cot.rx[t.dataset.rx] = t.value;
    } else if (t.dataset.op !== undefined) {
      (cot.opc[t.dataset.cod] ||= {})[t.dataset.op] = t.checked;
    } else return;
    recalcular();
  });
  $("#cotCondiciones").addEventListener("change", (ev) => {
    const t = ev.target;
    if (t.id === "cotDepto") { cot.depto = t.value; cot.muni = ""; }
    else if (t.id === "cotMuni") cot.muni = t.value;
    else if (t.name === "mismoActo") cot.mismoActo = t.value;
    else if (t.id === "cotTecnecio") cot.tecnecio = t.checked;
    else return;
    recalcular();
  });
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

function htmlOpciones(f) {
  const regla = (op, variante = "") => COT_CFG.reglas.find((r) => r.opcion === op && (!variante || r.variante === variante));
  const titulo = (r) => (r ? `${r.texto} — ${r.cita}` : "");
  return f.aplicables.map((op) => {
    if (op === "portatil-rx") {
      const v = cot.rx[f.codigo] || "";
      return `<label class="opcion${v ? " activa" : ""}" title="${esc(titulo(regla(op, "simple")))}">${OPC_ETIQUETA[op]}
        <select data-rx="${esc(f.codigo)}"><option value="">no</option>
          <option value="simple"${v === "simple" ? " selected" : ""}>simple</option>
          <option value="fluoroscopia"${v === "fluoroscopia" ? " selected" : ""}>con fluoroscopia</option></select></label>`;
    }
    const marcado = cot.opc[f.codigo]?.[op];
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

function pintarCondiciones() {
  const g = cotRes.globales;
  const deptos = COT_CFG.regiones.filter((r) => r.clase === "departamento");
  const regiones = COT_CFG.regiones.filter((r) => r.clase === "region");
  const sel = COT_CFG.regiones.find((r) => r.clave === cot.depto);
  const opt = (r) => `<option value="${esc(r.clave)}"${r.clave === cot.depto ? " selected" : ""}>${esc(r.nombre)}</option>`;
  const muni = sel ? `<label class="campo-form"><span>Municipio</span><select id="cotMuni">
      <option value="">${sel.clase === "region" ? "Municipio de la región (con incremento)" : "Otro municipio (con incremento)"}</option>
      ${sel.exceptuadas.map((e) => `<option value="${esc(e.clave)}"${e.clave === cot.muni ? " selected" : ""}>${esc(e.nombre)} (sin incremento, par. 2)</option>`).join("")}
    </select></label>${sel.observacion ? `<p class="nota-campo">${esc(sel.observacion)}</p>` : ""}` : "";
  const radio = (v, t, sub) => `<label class="radio"><input type="radio" name="mismoActo" value="${v}"${cot.mismoActo === v ? " checked" : ""}>
    <span>${t}${sub ? `<small>${sub}</small>` : ""}</span></label>`;
  $("#cotCondiciones").innerHTML = `
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
      <label class="radio"><input type="checkbox" id="cotTecnecio"${cot.tecnecio ? " checked" : ""}>
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

// ---------- Arranque ----------
function render() {
  marcarMenu();
  if (estado.vista === "fuentes") pintarFuentes();
  else if (estado.vista === "cotizar") pintarCotizar();
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
