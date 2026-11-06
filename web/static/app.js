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
  buscar: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  excel: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="m9 12 6 6M15 12l-6 6"/>',
  descarga: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5M12 15V3"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  filtro: '<path d="M22 3H2l8 9.5V19l4 2v-8.5z"/>',
  izq: '<path d="m15 18-6-6 6-6"/>',
  der: '<path d="m9 18 6-6-6-6"/>',
  copiar: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  vacio: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3M8 11h6"/>',
};
const icono = (n) => `<svg class="icono" viewBox="0 0 24 24" aria-hidden="true">${ICONOS[n] || ""}</svg>`;

// ---------- Utilidades ----------
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 4 });
const SIN_SEPARADOR = new Set(["articulo", "nivel", "fila_excel", "orden", "id", "n_componentes", "padre_id", "raiz_id"]);
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
    h += vs.map((v) => `<a class="menu__item" href="#/${v.id}" data-vista="${v.id}">${icono(v.icono)}
      <span>${esc(v.titulo)}</span><small>${fmt.format(v.total)}</small></a>`).join("");
  }
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
  $("#rejilla").innerHTML = VISTAS.map((v) => {
    const r = conteos?.[v.id];
    const clase = conteos ? (r?.coincidencias ? "con-resultados" : "sin-resultados") : "";
    const insignia = conteos ? `<span class="insignia">${r ? fmt.format(r.coincidencias) : "—"}</span>` : "";
    return `<button class="tarjeta-vista ${clase}" data-vista="${v.id}">
      <div class="tarjeta-vista__icono">${icono(v.icono)}</div>
      <div><h3>${esc(v.titulo)}</h3><p>${esc(v.descripcion)}</p>
        <div class="cifra"><b>${fmt.format(v.total)}</b> filas</div></div>${insignia}</button>`;
  }).join("");
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
  if (typeof valor === "number") {
    return `<td class="num">${SIN_SEPARADOR.has(col) ? valor : fmt.format(valor)}</td>`;
  }
  const clase = COL_CODIGO.has(col) ? "cod" : "";
  return `<td class="${clase}"><div class="recorte" title="${esc(valor)}">${resaltar(valor, palabras)}</div></td>`;
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
  marco.querySelectorAll("tbody tr").forEach((tr) => tr.addEventListener("click", () => abrirDetalle(d, +tr.dataset.i)));
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
    return `<div class="campo"><dt>${esc(c.etiqueta)}</dt><dd class="${vacio ? "vacio" : ""}">${esc(txt)}</dd></div>`;
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

// ---------- Arranque ----------
function render() {
  marcarMenu();
  if (estado.vista) pintarVista();
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
