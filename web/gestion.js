/* Vocacional Bayesiano · conexión con el servidor y pestaña «Gestión»
   window.VB.api()      → llamadas al servidor (sesión, protección CSRF, errores legibles)
   window.VB.gestion    → estudiantes y códigos, carga de datos, materias, modelo, usuarios, bitácora, cuenta */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fecha = f => f ? new Date(f).toLocaleDateString('es-EC', { day: 'numeric', month: 'short', year: 'numeric' }) : '—';
  const fechaHora = f => f ? new Date(f).toLocaleString('es-EC', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—';
  const AREAS = ['C', 'H', 'A', 'S', 'I', 'D', 'E'];
  const NOM_AREA = { C: 'Administración', H: 'Humanidades', A: 'Artes', S: 'Salud', I: 'Ingeniería', D: 'Defensa', E: 'Ciencias' };

  /* ───────────── API ───────────── */
  async function api(url, { method = 'GET', body, form } = {}) {
    const op = { method, credentials: 'same-origin', headers: { 'X-Vocacional': '1' } };
    if (form) op.body = form;
    else if (body !== undefined) { op.body = JSON.stringify(body); op.headers['Content-Type'] = 'application/json'; }
    const r = await fetch(url, op);
    if (r.status === 401) { location.href = '/entrar'; throw new Error('Sesión vencida'); }
    const tipo = r.headers.get('content-type') || '';
    const d = tipo.includes('json') ? await r.json() : await r.text();
    if (!r.ok) throw new Error((d && d.error) || `Error ${r.status}`);
    return d;
  }
  async function esperarTrabajo(id, alAvanzar) {
    for (;;) {
      const t = await api(`api/trabajos/${id}`);
      alAvanzar?.(t);
      if (t.estado === 'listo' || t.estado === 'error') return t;
      await new Promise(r => setTimeout(r, 700));
    }
  }
  function aviso(t) {
    const n = document.createElement('div'); n.className = 'aviso-flot'; n.setAttribute('role', 'status'); n.textContent = t;
    document.body.appendChild(n); setTimeout(() => n.remove(), 6000);
  }
  function modal(html, { ancho = 640, alCerrar } = {}) {
    const capa = document.createElement('div');
    capa.className = 'capa'; capa.setAttribute('role', 'dialog'); capa.setAttribute('aria-modal', 'true');
    capa.innerHTML = `<div class="hoja g-hoja" style="width:min(${ancho}px,100%)">${html}</div>`;
    document.body.appendChild(capa);
    const cerrar = () => { capa.remove(); alCerrar?.(); };
    capa.addEventListener('click', e => { if (e.target === capa || e.target.closest('[data-cerrar]')) cerrar(); });
    capa.addEventListener('keydown', e => { if (e.key === 'Escape') cerrar(); });
    capa.querySelector('input,select,button,textarea')?.focus();
    return { capa, cerrar };
  }

  /* ───────────── sesión y cabecera ───────────── */
  const VB = window.VB = { api, esperarTrabajo, aviso, yo: null, colegio: '' };
  VB.iniciar = async () => {
    const yo = await api('api/yo');
    VB.yo = yo; VB.colegio = yo.colegio;
    const u = $('#usuario');
    if (u) {
      u.innerHTML = `<button class="usuario-b" id="usuario-b" aria-haspopup="true" aria-expanded="false">
          <span class="usuario-ini" aria-hidden="true">${esc((yo.nombre || '?').trim()[0] || '?')}</span>
          <span class="usuario-n">${esc(yo.nombre)}<small>${yo.rol === 'admin' ? 'Administración' : 'Orientación'}</small></span></button>
        <div class="usuario-menu" id="usuario-menu" hidden>
          <button data-u="cuenta">Mi contraseña</button><button data-u="salir">Cerrar sesión</button></div>`;
      const b = $('#usuario-b'), m = $('#usuario-menu');
      b.addEventListener('click', () => { m.hidden = !m.hidden; b.setAttribute('aria-expanded', String(!m.hidden)); });
      document.addEventListener('click', e => { if (!u.contains(e.target)) { m.hidden = true; b.setAttribute('aria-expanded', 'false'); } });
      m.addEventListener('click', async e => {
        const x = e.target.closest('[data-u]'); if (!x) return;
        m.hidden = true;
        if (x.dataset.u === 'salir') { await api('api/sesion', { method: 'DELETE' }).catch(() => {}); location.href = '/entrar'; }
        if (x.dataset.u === 'cuenta') { G.seccion = 'cuenta'; document.querySelector('[data-vista="gestion"]')?.click(); }
      });
    }
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
    return yo;
  };

  /* ───────────── Gestión ───────────── */
  const G = VB.gestion = { seccion: 'estudiantes', filtro: 'todos', q: '', sel: new Set() };
  const esAdmin = () => VB.yo?.rol === 'admin';
  const SECCIONES = () => [
    ['estudiantes', 'Estudiantes y códigos'], ...(esAdmin() ? [['datos', 'Cargar datos']] : []), ['materias', 'Materias'],
    ['modelo', 'Modelo'], ...(esAdmin() ? [['usuarios', 'Usuarios'], ['bitacora', 'Bitácora']] : []), ['cuenta', 'Mi cuenta']];
  let ctx = {}, raiz = null;

  G.pintar = (cont, contexto) => {
    ctx = contexto || ctx; raiz = cont;
    if (!SECCIONES().some(([k]) => k === G.seccion)) G.seccion = 'estudiantes';
    cont.innerHTML = `<div class="gestion">
      <nav class="g-nav" aria-label="Secciones de gestión">${SECCIONES().map(([k, t]) => `<button data-sec="${k}" aria-current="${k === G.seccion ? 'page' : 'false'}">${esc(t)}</button>`).join('')}</nav>
      <div class="g-cuerpo" id="g-cuerpo"><div class="panel vacio">Cargando…</div></div></div>`;
    cont.querySelector('.g-nav').addEventListener('click', e => {
      const b = e.target.closest('[data-sec]'); if (!b) return;
      G.seccion = b.dataset.sec; G.pintar(cont);
    });
    ({ estudiantes, datos, materias, modelo, usuarios, bitacora, cuenta })[G.seccion]($('#g-cuerpo', cont)).catch(err => {
      $('#g-cuerpo', cont).innerHTML = `<div class="panel vacio">${esc(err.message)}</div>`;
    });
  };
  const repintar = () => raiz && G.pintar(raiz);

  /* ── Estudiantes y códigos ── */
  const ESTADO = {
    listo: ['Listo', 'ok', 'Tiene notas y CHASIDE: su resultado está disponible'],
    falta_chaside: ['Falta CHASIDE', 'pend', 'Tiene notas; genera un código para que responda el test'],
    falta_notas: ['Faltan notas', 'pend', 'Respondió el CHASIDE; falta cargar su reporte de notas'],
    sin_datos: ['Sin datos', 'nada', 'Está en la nómina pero aún no tiene notas ni CHASIDE'],
  };
  async function estudiantes(el) {
    const lista = await api('api/estudiantes');
    const cuenta = k => lista.filter(e => e.estado === k).length;
    const vigente = e => !!e.codigo_expira;
    const visibles = () => lista.filter(e => (G.filtro === 'todos' || (G.filtro === 'codigo' ? vigente(e) : e.estado === G.filtro))
      && (!G.q || e.nombre.toLowerCase().includes(G.q.toLowerCase()) || e.id.toLowerCase().includes(G.q.toLowerCase())));
    if (!lista.length) {
      el.innerHTML = `<div class="panel g-vacio"><h2>Todavía no hay estudiantes</h2>
        <p>Los estudiantes aparecen al ${esAdmin() ? '<a href="#" data-ir="datos">cargar el reporte de notas o la nómina</a>' : 'que la administración cargue el reporte de notas'}.</p>
        <ol class="pasos"><li>Cargar el reporte de notas del sistema académico.</li><li>Generar códigos y que cada estudiante responda el CHASIDE en su teléfono.</li><li>Revisar los resultados en la pestaña Estudiante.</li></ol></div>`;
      el.querySelector('[data-ir]')?.addEventListener('click', e => { e.preventDefault(); G.seccion = 'datos'; repintar(); });
      return;
    }
    const filtros = [['todos', 'Todos', lista.length], ['falta_chaside', 'Falta CHASIDE', cuenta('falta_chaside')], ['listo', 'Listos', cuenta('listo')],
      ['falta_notas', 'Faltan notas', cuenta('falta_notas')], ['codigo', 'Con código vigente', lista.filter(vigente).length]];
    const fila = e => {
      const [t, cls, tip] = ESTADO[e.estado];
      return `<tr><td><input type="checkbox" data-id="${esc(e.id)}" ${G.sel.has(e.id) ? 'checked' : ''} aria-label="Seleccionar a ${esc(e.nombre)}"></td>
        <td><b>${esc(e.nombre)}</b>${e.nombre_ficticio ? ' <span class="ficticio">ficticio</span>' : ''}<div class="sutil mono">${esc(e.id)}</div></td>
        <td class="num">${e.grado_actual ?? '—'}${e.paralelo ? ' ' + esc(e.paralelo) : ''}</td>
        <td class="num">${e.n_notas || '—'}</td>
        <td>${e.chaside_fecha ? `${fecha(e.chaside_fecha + 'T12:00')}<div class="sutil">${({ en_linea: 'en línea', dece: 'DECE', archivo: 'archivo' })[e.chaside_origen] || ''}</div>` : '—'}</td>
        <td><span class="estado-b ${cls}" data-tip="${esc(tip)}">${t}</span></td>
        <td>${e.codigo_expira ? `<span class="sutil">vence ${fecha(e.codigo_expira)}</span>` : ''}</td>
        <td>${e.estado === 'listo' ? `<button class="boton sec mini-b" data-ver="${esc(e.id)}">Ver resultado</button>` : ''}</td></tr>`;
    };
    el.innerHTML = `<div class="tiles">
        <div class="tile"><span class="etiqueta">Estudiantes</span><span class="v">${lista.length}</span><span class="d">en el sistema</span></div>
        <div class="tile"><span class="etiqueta">Con resultado</span><span class="v">${cuenta('listo')}</span><span class="d">notas + CHASIDE</span></div>
        <div class="tile"><span class="etiqueta">Falta CHASIDE</span><span class="v">${cuenta('falta_chaside')}</span><span class="d">genera sus códigos</span></div>
        <div class="tile"><span class="etiqueta">Faltan notas</span><span class="v">${cuenta('falta_notas')}</span><span class="d">carga su reporte</span></div></div>
      <div class="panel" style="margin-top:16px">
        <div class="g-barra">
          <input type="search" id="g-q" placeholder="Buscar por nombre o ID…" value="${esc(G.q)}" aria-label="Buscar estudiante">
          <div class="filtros">${filtros.map(([k, t, n]) => `<button class="chip-f" data-filtro="${k}" aria-pressed="${G.filtro === k}">${t} · ${n}</button>`).join('')}</div>
        </div>
        <div class="g-acciones" id="g-acciones"></div>
        <div class="tabla-wrap"><table class="met g-tabla"><thead><tr><th><input type="checkbox" id="g-todos" aria-label="Seleccionar todos los visibles"></th>
          <th>Estudiante</th><th class="num">Grado</th><th class="num">Notas</th><th>CHASIDE</th><th>Estado</th><th>Código</th><th></th></tr></thead>
          <tbody id="g-filas"></tbody></table></div></div>`;
    const pintarFilas = () => {
      const v = visibles();
      $('#g-filas', el).innerHTML = v.map(fila).join('') || `<tr><td colspan="8" class="sutil">Ningún estudiante coincide.</td></tr>`;
      $('#g-todos', el).checked = v.length > 0 && v.every(e => G.sel.has(e.id));
      const n = G.sel.size;
      $('#g-acciones', el).innerHTML = n ? `<span><b>${n}</b> seleccionado${n > 1 ? 's' : ''}</span>
          <button class="boton" data-acc="codigos">Generar códigos para el CHASIDE</button>
          <button class="boton sec" data-acc="limpiar">Quitar selección</button>`
        : `<span class="sutil">Selecciona estudiantes para generar sus códigos del test. Tip: filtra por «Falta CHASIDE» y marca todos.</span>`;
    };
    pintarFilas();
    $('#g-q', el).addEventListener('input', e => { G.q = e.target.value; pintarFilas(); });
    el.querySelector('.filtros').addEventListener('click', e => {
      const b = e.target.closest('[data-filtro]'); if (!b) return;
      G.filtro = b.dataset.filtro; el.querySelectorAll('[data-filtro]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); pintarFilas();
    });
    el.addEventListener('change', e => {
      if (e.target.id === 'g-todos') { visibles().forEach(x => e.target.checked ? G.sel.add(x.id) : G.sel.delete(x.id)); pintarFilas(); }
      else if (e.target.dataset.id) { e.target.checked ? G.sel.add(e.target.dataset.id) : G.sel.delete(e.target.dataset.id); pintarFilas(); }
    });
    el.addEventListener('click', e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.ver) ctx.abrir?.(b.dataset.ver);
      if (b.dataset.acc === 'limpiar') { G.sel.clear(); pintarFilas(); }
      if (b.dataset.acc === 'codigos') dialogoCodigos([...G.sel], lista);
    });
  }

  function dialogoCodigos(ids, lista) {
    const { capa, cerrar } = modal(`<div class="hoja-cab"><div><span class="etiqueta">Test CHASIDE en línea</span><h2>Códigos para ${ids.length} estudiante${ids.length > 1 ? 's' : ''}</h2></div>
        <button class="flecha" data-cerrar aria-label="Cerrar">×</button></div>
      <div class="g-form">
        <label>¿Cómo lo van a responder?
          <select id="c-mod"><option value="supervisada">En el aula, con el DECE presente</option><option value="autonoma">En casa, sin supervisión</option></select></label>
        <label>Vigencia del código
          <select id="c-dias"><option value="7">7 días</option><option value="15">15 días</option><option value="30" selected>30 días</option><option value="60">60 días</option></select></label>
        <p class="sutil">Cada código sirve <b>una sola vez</b>. Si un estudiante ya tenía uno sin usar, se reemplaza. Responder en casa reduce un poco la confianza del resultado.</p>
      </div>
      <div class="hoja-pie"><button class="boton sec" data-cerrar>Cancelar</button><button class="boton" id="c-ok">Generar</button></div>`, { ancho: 560 });
    $('#c-ok', capa).addEventListener('click', async () => {
      try {
        const r = await api('api/codigos', { method: 'POST', body: { ids, modalidad: $('#c-mod', capa).value, dias: +$('#c-dias', capa).value } });
        cerrar(); G.sel.clear(); hojaCodigos(r); repintar();
      } catch (err) { aviso(err.message); }
    });
  }
  function hojaCodigos(r) {
    const url = `${location.origin}/chaside`;
    const filas = r.codigos.map(c => `<tr><td>${esc(c.nombre)}</td><td class="mono codigo-g">${esc(c.codigo)}</td></tr>`).join('');
    const { capa } = modal(`<div class="hoja-cab"><div><span class="etiqueta">Guarda o imprime esta hoja ahora: los códigos no se vuelven a mostrar</span>
        <h2>Códigos del test CHASIDE</h2></div><button class="flecha" data-cerrar aria-label="Cerrar">×</button></div>
      <div class="g-imprimible" id="c-hoja">
        <p><b>Entra a</b> <span class="mono">${esc(url)}</span> desde el teléfono o la computadora y escribe tu código.
        ${r.modalidad === 'supervisada' ? 'Responde en el aula.' : 'Puedes responder desde casa.'} Vence en ${r.expira_dias} días · sirve una sola vez.</p>
        <table class="met"><thead><tr><th>Estudiante</th><th>Código</th></tr></thead><tbody>${filas}</tbody></table>
        <div class="tarjetas">${r.codigos.map(c => `<div class="tarjeta"><b>${esc(c.nombre)}</b><span>Test vocacional CHASIDE</span>
          <span class="mono">${esc(url)}</span><span class="mono codigo-g">${esc(c.codigo)}</span></div>`).join('')}</div>
      </div>
      <div class="hoja-pie"><button class="boton sec" id="c-copiar">Copiar lista</button><button class="boton" id="c-imprimir">Imprimir tarjetas</button></div>`, { ancho: 720 });
    $('#c-imprimir', capa).addEventListener('click', () => { document.body.classList.add('imprimiendo'); window.print(); document.body.classList.remove('imprimiendo'); });
    $('#c-copiar', capa).addEventListener('click', async e => {
      const t = `Test CHASIDE · ${url}\n` + r.codigos.map(c => `${c.nombre}\t${c.codigo}`).join('\n');
      try { await navigator.clipboard.writeText(t); e.target.textContent = 'Copiado'; } catch (_) { aviso('No se pudo copiar: selecciona la tabla y copia.'); }
    });
  }
  G.codigoIndividual = (id, nombre) => {
    dialogoCodigos([id], [{ id, nombre }]);
  };

  /* ── Cargar datos (administración) ── */
  function plantillaChaside() {
    const cab = ['id', 'fecha_aplicacion', 'modalidad', ...Array.from({ length: 98 }, (_, i) => 'P' + (i + 1))];
    const ej = ['ID_DEL_COLEGIO', new Date().toISOString().slice(0, 10), 'supervisada', ...Array.from({ length: 98 }, () => '')];
    return '﻿' + cab.join(',') + '\n' + ej.join(',') + '\n';
  }
  function descargar(nombre, texto) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([texto], { type: 'text/csv;charset=utf-8' })); a.download = nombre;
    document.body.appendChild(a); a.click(); a.remove();
  }
  async function datos(el) {
    const cargas = await api('api/cargas');
    const TIPO = { notas: 'Notas', nomina: 'Nómina', chaside: 'CHASIDE' };
    el.innerHTML = `<div class="g-cargas">
      <div class="panel g-carga"><h2>1 · Reporte de notas</h2>
        <p>El export del sistema académico (<b>CSV o Excel</b>), igual al <span class="mono">Report_7.csv</span>. Columnas: <span class="mono">Student ID (System)</span>, <span class="mono">Grade Level</span>, <span class="mono">Year</span>, <span class="mono">Grade Level 1</span>, <span class="mono">Final grade AVG</span>, <span class="mono">Final grade</span>, <span class="mono">Course</span>.</p>
        <p class="sutil">Solo se guardan las notas de 9.º a 12.º. Volver a subir un reporte actualiza las notas sin duplicarlas. El ID del colegio no se guarda: se reemplaza por un seudónimo.</p>
        <label class="boton g-subir">Elegir archivo<input type="file" accept=".csv,.xlsx" data-tipo="notas" hidden></label></div>
      <div class="panel g-carga"><h2>2 · Nómina <span class="sutil">(opcional)</span></h2>
        <p>Para ver <b>nombres reales</b> en lugar de los ficticios. CSV con columnas <span class="mono">id_colegio, nombre, genero, grado_actual, paralelo</span>.</p>
        <p class="sutil">Mientras sea una fase de pruebas, no la cargues: el sistema usa nombres ficticios.</p>
        <div class="g-fila-b"><label class="boton g-subir">Elegir archivo<input type="file" accept=".csv" data-tipo="nomina" hidden></label>
        <button class="boton sec" data-plantilla="nomina">Descargar plantilla</button></div></div>
      <div class="panel g-carga"><h2>3 · CHASIDE en papel <span class="sutil">(opcional)</span></h2>
        <p>Si algunos estudiantes respondieron en papel: CSV con <span class="mono">id, fecha_aplicacion, modalidad, P1 … P98</span> (Sí/No). El <span class="mono">id</span> es el del colegio.</p>
        <p class="sutil">Lo normal es que respondan en línea con su código (sección Estudiantes y códigos).</p>
        <div class="g-fila-b"><label class="boton g-subir">Elegir archivo<input type="file" accept=".csv" data-tipo="chaside" hidden></label>
        <button class="boton sec" data-plantilla="chaside">Descargar plantilla</button></div></div>
      </div>
      <div class="panel g-resultado" id="g-res" hidden></div>
      <div class="panel" style="margin-top:16px"><div class="panel-cab"><h2>Cargas anteriores</h2></div>
        ${cargas.length ? `<div class="tabla-wrap"><table class="met"><thead><tr><th>Fecha</th><th>Tipo</th><th>Archivo</th><th>Por</th><th>Resumen</th></tr></thead><tbody>
        ${cargas.map(c => `<tr><td>${fechaHora(c.fecha)}</td><td>${TIPO[c.tipo] || esc(c.tipo)}</td><td class="mono">${esc(c.archivo)}</td><td>${esc(c.usuario)}</td>
          <td class="sutil">${c.tipo === 'notas' ? `${c.resumen.estudiantes ?? '?'} estudiantes · ${c.resumen.nuevos ?? 0} nuevos` : c.resumen.filas != null ? `${c.resumen.filas} filas` : ''}</td></tr>`).join('')}
        </tbody></table></div>` : '<p class="sutil">Aún no se ha cargado ningún archivo.</p>'}</div>`;
    el.addEventListener('click', e => {
      const p = e.target.closest('[data-plantilla]'); if (!p) return;
      if (p.dataset.plantilla === 'nomina') descargar('plantilla_nomina.csv', '﻿id_colegio,nombre,genero,grado_actual,paralelo\n1234567,Apellido Apellido Nombre Nombre,F,12,A\n');
      else descargar('plantilla_chaside.csv', plantillaChaside());
    });
    el.addEventListener('change', async e => {
      const inp = e.target.closest('input[type=file]'); if (!inp || !inp.files[0]) return;
      const res = $('#g-res', el); res.hidden = false;
      res.innerHTML = `<p>Subiendo <b>${esc(inp.files[0].name)}</b>…</p>`;
      const form = new FormData(); form.append('archivo', inp.files[0]);
      try {
        const r = await api(`api/cargas/${inp.dataset.tipo}`, { method: 'POST', form });
        inp.value = '';
        res.innerHTML = resumenCarga(inp.dataset.tipo, r) + (r.trabajo ? `<div class="progreso g-prog"><i id="g-barra"></i></div><p class="sutil" id="g-msg">Calculando resultados…</p>` : '');
        if (r.trabajo) {
          const t = await esperarTrabajo(r.trabajo, x => { const b = $('#g-barra', res); if (b) b.style.width = (x.progreso * 100) + '%'; const m = $('#g-msg', res); if (m && x.mensaje) m.textContent = x.mensaje; });
          $('#g-msg', res).textContent = t.estado === 'listo' ? '✓ Resultados actualizados.' : `⚠ ${t.mensaje}`;
        }
        await ctx.recargar?.();
      } catch (err) { res.innerHTML = `<p class="g-error">⚠ ${esc(err.message)}</p>`; }
    });
  }
  function resumenCarga(tipo, r) {
    if (tipo === 'notas') return `<h3>✓ Reporte de notas cargado</h3><ul class="g-lista">
        <li><b>${r.estudiantes}</b> estudiantes (${r.nuevos} nuevos, ${r.actualizados} ya existían)</li>
        <li><b>${r.filas_guardadas}</b> notas de secundaria guardadas · ${r.filas_otros_niveles} de otros niveles descartadas</li>
        ${r.materias_sin_regla.length ? `<li class="g-error">⚠ ${r.materias_sin_regla.length} materia(s) sin clasificar no entran al cálculo: ${r.materias_sin_regla.map(esc).join(', ')}. Agrégalas en <b>Materias</b>.</li>` : '<li>Todas las materias están clasificadas.</li>'}</ul>`;
    if (tipo === 'nomina') return `<h3>✓ Nómina cargada</h3><p>${r.actualizados} estudiantes con nombre real (${r.nuevos} nuevos).</p>`;
    return `<h3>✓ CHASIDE cargado</h3><p>${r.registradas} aplicaciones registradas.</p>${r.errores.length ? `<ul class="g-lista g-error">${r.errores.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}`;
  }

  /* ── Materias ── */
  async function materias(el) {
    const [lista, reglas] = await Promise.all([api('api/materias'), esAdmin() ? api('api/config/mapeo') : Promise.resolve(null)]);
    const sin = lista.filter(m => m.estado === 'sin_regla');
    const EST = { incluida: 'Incluida', excluida: 'Excluida', sin_regla: 'Sin regla' };
    el.innerHTML = `<div class="panel"><div class="panel-cab"><h2>Materias de los reportes</h2>
        <span class="sutil">${lista.length} materias · ${sin.length ? `<b class="g-error">${sin.length} sin regla</b>` : 'todas clasificadas'}</span></div>
      <p class="sutil">Cada materia se clasifica con la primera regla cuyo patrón aparece en su nombre. Las incluidas aportan a las áreas CHASIDE con peso 1 a 3; las excluidas (conducta, educación física, formación religiosa, deportes, clubes) no cuentan.</p>
      ${lista.length ? `<div class="tabla-wrap"><table class="met"><thead><tr><th>Materia</th><th class="num">Estudiantes</th><th>Estado</th><th>Áreas</th></tr></thead><tbody>
      ${[...sin, ...lista.filter(m => m.estado !== 'sin_regla')].map(m => `<tr><td>${esc(m.materia)}</td><td class="num">${m.estudiantes}</td>
        <td><span class="estado-b ${m.estado === 'incluida' ? 'ok' : m.estado === 'sin_regla' ? 'mal' : 'nada'}">${EST[m.estado]}</span></td>
        <td class="mono">${esc(m.areas)}</td></tr>`).join('')}</tbody></table></div>` : '<p class="sutil">Aún no hay notas cargadas.</p>'}</div>
      ${reglas ? `<div class="panel" style="margin-top:16px"><div class="panel-cab"><h2>Reglas de clasificación</h2><span class="sutil">El orden importa: gana la primera que coincide</span></div>
        <div class="g-probar"><label>Probar con un nombre de materia <input id="r-prueba" placeholder="ej. AP Calculus BC"></label><span id="r-res" class="sutil"></span></div>
        <div class="tabla-wrap"><table class="met g-reglas"><thead><tr><th>#</th><th>Patrón (expresión regular)</th><th>Incluir</th>${AREAS.map(a => `<th class="num" title="${NOM_AREA[a]}">${a}</th>`).join('')}<th>Justificación</th><th></th></tr></thead>
        <tbody id="r-filas"></tbody></table></div>
        <div class="g-fila-b" style="margin-top:12px"><button class="boton sec" id="r-nueva">Agregar regla</button><button class="boton" id="r-guardar">Guardar y recalcular</button></div>
        <p class="sutil">Se guarda una copia de las reglas anteriores en el servidor antes de reemplazarlas.</p></div>` : ''}`;
    if (!reglas) return;
    const R = reglas.map(r => ({ ...r }));
    const pintar = () => {
      $('#r-filas', el).innerHTML = R.map((r, i) => `<tr data-i="${i}"><td class="num">${i + 1}</td>
        <td><input class="mono r-pat" value="${esc(r.patron)}" aria-label="Patrón de la regla ${i + 1}"></td>
        <td><select class="r-inc" aria-label="Incluir"><option value="si" ${r.incluir === 'si' ? 'selected' : ''}>Sí</option><option value="no" ${r.incluir !== 'si' ? 'selected' : ''}>No</option></select></td>
        ${AREAS.map(a => `<td><input class="r-w" data-a="${a}" type="number" min="0" max="3" value="${r.pesos[a] || 0}" aria-label="Peso ${NOM_AREA[a]}" ${r.incluir !== 'si' ? 'disabled' : ''}></td>`).join('')}
        <td><input class="r-just" value="${esc(r.justificacion)}" aria-label="Justificación"></td>
        <td class="g-mover"><button data-m="-1" aria-label="Subir">↑</button><button data-m="1" aria-label="Bajar">↓</button><button data-m="x" aria-label="Eliminar">×</button></td></tr>`).join('');
    };
    pintar();
    const leer = () => $('#r-filas', el).querySelectorAll('tr').forEach(tr => {
      const r = R[+tr.dataset.i];
      r.patron = tr.querySelector('.r-pat').value; r.incluir = tr.querySelector('.r-inc').value; r.justificacion = tr.querySelector('.r-just').value;
      tr.querySelectorAll('.r-w').forEach(w => { r.pesos[w.dataset.a] = +w.value || 0; });
    });
    const probar = () => {
      leer();
      const m = $('#r-prueba', el).value.toLowerCase().trim(); if (!m) { $('#r-res', el).textContent = ''; return; }
      const i = R.findIndex(r => { try { return new RegExp(r.patron).test(m); } catch (_) { return false; } });
      $('#r-res', el).innerHTML = i < 0 ? '<b class="g-error">Ninguna regla coincide: quedaría sin clasificar</b>'
        : `Regla ${i + 1} → ${R[i].incluir === 'si' ? `incluida: ${AREAS.filter(a => R[i].pesos[a] > 0).map(a => `${a}×${R[i].pesos[a]}`).join(' ')}` : 'excluida'} <span class="sutil">(${esc(R[i].justificacion)})</span>`;
    };
    $('#r-prueba', el).addEventListener('input', probar);
    $('#r-filas', el).addEventListener('change', e => { if (e.target.classList.contains('r-inc')) { leer(); pintar(); } });
    $('#r-filas', el).addEventListener('click', e => {
      const b = e.target.closest('[data-m]'); if (!b) return;
      leer(); const i = +b.closest('tr').dataset.i;
      if (b.dataset.m === 'x') { if (confirm('¿Eliminar esta regla?')) R.splice(i, 1); }
      else { const j = i + +b.dataset.m; if (j >= 0 && j < R.length) [R[i], R[j]] = [R[j], R[i]]; }
      pintar();
    });
    $('#r-nueva', el).addEventListener('click', () => { leer(); R.unshift({ patron: '', incluir: 'si', pesos: {}, justificacion: '' }); pintar(); $('.r-pat', el).focus(); });
    $('#r-guardar', el).addEventListener('click', async e => {
      leer(); e.target.disabled = true;
      try {
        const r = await api('api/config/mapeo', { method: 'PUT', body: { reglas: R } });
        aviso('Reglas guardadas. Recalculando a todos los estudiantes…');
        await esperarTrabajo(r.trabajo); await ctx.recargar?.(); repintar();
      } catch (err) { aviso(err.message); e.target.disabled = false; }
    });
  }

  /* ── Modelo ── */
  async function modelo(el) {
    const m = await api('api/modelo');
    const c = m.conteos, min = m.minimos;
    const barra = (n, meta) => `<span class="g-meta"><i style="width:${Math.min(100, n / meta * 100)}%"></i></span><span class="mono">${n} / ${meta}</span>`;
    const origen = m.origen === 'referencia_tesis' ? 'Calibración de referencia (cohorte de la tesis)' : 'Calibrado con los datos del colegio';
    el.innerHTML = `<div class="rejilla-2">
      <div class="panel"><div class="panel-cab"><h2>Calibración activa</h2></div>
        <p><b>${origen}</b><br><span class="sutil">${fechaHora(m.fecha)} · modelo v${esc(m.version_modelo)} · γ carreras = ${m.gamma}</span></p>
        <p class="sutil">El modelo aprende de la cohorte las normas de cada materia, la confiabilidad del CHASIDE (KR‑20) y la relación entre interés, autopercepción y notas. Con pocos datos usa la calibración de la tesis; cuando el colegio tenga suficientes estudiantes conviene recalibrar.</p>
        <table class="met"><tbody>
          <tr><td>Estudiantes con notas (normas de notas)</td><td>${barra(c.con_notas, min.notas)}</td></tr>
          <tr><td>Con CHASIDE (normas y KR‑20)</td><td>${barra(c.con_chaside, min.chaside)}</td></tr>
          <tr><td>Con ambos (parámetros y carreras)</td><td>${barra(c.listos, min.aprender)}</td></tr></tbody></table>
        ${esAdmin() ? `<div class="g-fila-b" style="margin-top:14px"><button class="boton" id="m-recal" ${c.con_notas < min.notas && c.con_chaside < min.chaside ? 'disabled' : ''}>Recalibrar con los datos del colegio</button>
          <button class="boton sec" id="m-recalc">Recalcular resultados</button></div>
          <p class="sutil">Recomendado al inicio de cada año lectivo, cuando la mayoría del curso ya respondió el CHASIDE. Las calibraciones anteriores quedan guardadas y se pueden reactivar.</p>
          <div id="m-prog"></div>` : ''}
        ${m.preguntas_origen === 'prototipo' ? `<p class="g-error">⚠ Las 98 preguntas del CHASIDE son de prototipo (redacción propia). Para uso real, reemplazar el texto por el oficial en <span class="mono">config/chaside_preguntas.csv</span>.</p>` : ''}
        ${m.carreras_descartadas?.length ? `<p class="g-error">⚠ Carreras descartadas por perfil inválido: ${m.carreras_descartadas.map(esc).join(', ')}</p>` : ''}
      </div>
      <div class="panel"><div class="panel-cab"><h2>Parámetros por área</h2></div>
        <div class="tabla-wrap"><table class="met"><thead><tr><th>Área</th><th class="num">α notas</th><th class="num">λ² autopercepción</th><th class="num">ρ interés–rend.</th><th class="num">W mediana</th></tr></thead><tbody>
        ${AREAS.map(a => { const p = m.param[a]; return `<tr><td>${NOM_AREA[a]}</td><td class="num">${p.alfa_notas.toFixed(2)}</td><td class="num">${(p.lam_apt ** 2).toFixed(2)}</td><td class="num">${p.rho.toFixed(2)}</td><td class="num">${p.W_med.toFixed(1)}</td></tr>`; }).join('')}
        </tbody></table></div>
        ${m.evaluacion?.perfil ? `<p class="sutil" style="margin-top:10px">Fidelidad medida en la tesis (${esc(m.evaluacion.origen)}): zona correcta ${Math.round(m.evaluacion.perfil.exactitud_zona * 100)} %, recuperación del rendimiento r = ${m.evaluacion.perfil.r_R.toFixed(2)}, del interés r = ${m.evaluacion.perfil.r_I.toFixed(2)}.</p>` : ''}</div></div>
      <div class="panel" style="margin-top:16px"><div class="panel-cab"><h2>Historial de calibraciones</h2></div>
        <div class="tabla-wrap"><table class="met"><thead><tr><th>#</th><th>Fecha</th><th>Por</th><th>Qué se recalibró</th><th></th></tr></thead><tbody>
        ${m.historial.map(h => `<tr><td class="num">${h.id}</td><td>${fechaHora(h.fecha)}</td><td>${esc(h.usuario)}</td>
          <td class="sutil">${h.resumen.origen === 'referencia_tesis' ? 'Referencia de la tesis' : Object.keys(h.resumen.recalibrado || {}).join(', ') + ` · ${h.resumen.n_nucleo ?? '?'} con núcleo completo`}</td>
          <td>${h.activa ? '<span class="estado-b ok">Activa</span>' : esAdmin() ? `<button class="boton sec mini-b" data-activar="${h.id}">Activar</button>` : ''}</td></tr>`).join('')}
        </tbody></table></div></div>
      ${esAdmin() ? `<div class="panel" style="margin-top:16px"><div class="panel-cab"><h2>Respaldos y exportación</h2></div>
        <p class="sutil">Cada noche el servidor guarda una copia de la base de datos y de la configuración (se conservan las últimas 30).</p>
        <div class="g-fila-b"><button class="boton sec" id="m-resp">Crear respaldo ahora</button><a class="boton sec" href="api/exportar/resultados.csv">Exportar resultados (CSV)</a></div>
        <div id="m-resp-lista"></div></div>` : ''}`;
    if (!esAdmin()) return;
    const prog = $('#m-prog', el);
    const correr = async (url, txt) => {
      try {
        const r = await api(url, { method: 'POST' });
        prog.innerHTML = `<div class="progreso g-prog"><i id="m-barra"></i></div><p class="sutil" id="m-msg">${txt}</p>`;
        const t = await esperarTrabajo(r.trabajo, x => { $('#m-barra', el).style.width = (x.progreso * 100) + '%'; if (x.mensaje) $('#m-msg', el).textContent = x.mensaje; });
        if (t.estado === 'error') { prog.innerHTML = `<p class="g-error">⚠ ${esc(t.mensaje)}</p>`; return; }
        await ctx.recargar?.(); aviso('Listo.'); repintar();
      } catch (err) { prog.innerHTML = `<p class="g-error">⚠ ${esc(err.message)}</p>`; }
    };
    $('#m-recal', el)?.addEventListener('click', () => { if (confirm('¿Recalibrar el modelo con los datos actuales del colegio y recalcular a todos los estudiantes?')) correr('api/modelo/recalibrar', 'Recalibrando…'); });
    $('#m-recalc', el)?.addEventListener('click', () => correr('api/modelo/recalcular', 'Recalculando…'));
    el.querySelectorAll('[data-activar]').forEach(b => b.addEventListener('click', () => {
      if (confirm('¿Volver a esta calibración? Se recalcularán todos los resultados.')) correr(`api/modelo/activar/${b.dataset.activar}`, 'Recalculando…');
    }));
    const listaResp = async () => {
      const l = await api('api/respaldos');
      $('#m-resp-lista', el).innerHTML = l.length ? `<ul class="g-lista sutil">${l.slice(0, 5).map(x => `<li class="mono">${esc(x.archivo)} · ${(x.bytes / 1e6).toFixed(1)} MB</li>`).join('')}</ul>` : '';
    };
    listaResp();
    $('#m-resp', el).addEventListener('click', async e => {
      e.target.disabled = true;
      try { await api('api/respaldos', { method: 'POST' }); aviso('Respaldo creado.'); listaResp(); } catch (err) { aviso(err.message); }
      e.target.disabled = false;
    });
  }

  /* ── Usuarios ── */
  async function usuarios(el) {
    const l = await api('api/usuarios');
    el.innerHTML = `<div class="rejilla-2"><div class="panel"><div class="panel-cab"><h2>Usuarios</h2></div>
        <div class="tabla-wrap"><table class="met"><thead><tr><th>Nombre</th><th>Rol</th><th>Último acceso</th><th>Estado</th><th></th></tr></thead><tbody>
        ${l.map(u => `<tr data-id="${u.id}"><td><b>${esc(u.nombre)}</b><div class="sutil">${esc(u.usuario)}</div></td>
          <td><select data-campo="rol" aria-label="Rol"><option value="orientador" ${u.rol === 'orientador' ? 'selected' : ''}>Orientación</option><option value="admin" ${u.rol === 'admin' ? 'selected' : ''}>Administración</option></select></td>
          <td class="sutil">${fechaHora(u.ultimo_acceso)}</td>
          <td><span class="estado-b ${u.activo ? 'ok' : 'nada'}">${u.activo ? 'Activo' : 'Desactivado'}</span></td>
          <td class="g-fila-b"><button class="boton sec mini-b" data-u="clave">Nueva contraseña</button><button class="boton sec mini-b" data-u="activo">${u.activo ? 'Desactivar' : 'Activar'}</button></td></tr>`).join('')}
        </tbody></table></div>
        <p class="sutil"><b>Orientación</b>: ve estudiantes y cohorte, genera códigos y registra el CHASIDE. <b>Administración</b>: además carga datos, edita materias, recalibra y gestiona usuarios.</p></div>
      <div class="panel"><div class="panel-cab"><h2>Nuevo usuario</h2></div>
        <form class="g-form" id="u-nuevo">
          <label>Nombre <input name="nombre" required autocomplete="off"></label>
          <label>Usuario (correo) <input name="usuario" type="email" required autocomplete="off"></label>
          <label>Rol <select name="rol"><option value="orientador">Orientación</option><option value="admin">Administración</option></select></label>
          <label>Contraseña temporal <input name="clave" type="text" required minlength="10" autocomplete="off"></label>
          <p class="sutil">Mínimo 10 caracteres con mayúsculas, minúsculas y números. Entrégala en persona y pide que la cambie en «Mi cuenta».</p>
          <button class="boton">Crear usuario</button></form></div></div>`;
    $('#u-nuevo', el).addEventListener('submit', async e => {
      e.preventDefault();
      try { await api('api/usuarios', { method: 'POST', body: Object.fromEntries(new FormData(e.target)) }); aviso('Usuario creado.'); repintar(); }
      catch (err) { aviso(err.message); }
    });
    el.addEventListener('change', async e => {
      if (e.target.dataset.campo !== 'rol') return;
      try { await api(`api/usuarios/${e.target.closest('tr').dataset.id}`, { method: 'PATCH', body: { rol: e.target.value } }); aviso('Rol actualizado.'); }
      catch (err) { aviso(err.message); repintar(); }
    });
    el.addEventListener('click', async e => {
      const b = e.target.closest('[data-u]'); if (!b) return;
      const id = b.closest('tr').dataset.id, u = l.find(x => String(x.id) === id);
      try {
        if (b.dataset.u === 'activo') await api(`api/usuarios/${id}`, { method: 'PATCH', body: { activo: !u.activo } });
        if (b.dataset.u === 'clave') {
          const c = prompt(`Nueva contraseña temporal para ${u.nombre} (mín. 10, con mayúsculas, minúsculas y números):`);
          if (!c) return;
          await api(`api/usuarios/${id}`, { method: 'PATCH', body: { clave: c } });
        }
        aviso('Listo. Las sesiones abiertas de ese usuario se cerraron.'); repintar();
      } catch (err) { aviso(err.message); }
    });
  }

  /* ── Bitácora ── */
  const ACC = {
    login: 'Inicio de sesión', login_fallido: 'Intento fallido de inicio de sesión', logout: 'Cierre de sesión', cargar_notas: 'Cargó notas',
    cargar_nomina: 'Cargó nómina', cargar_chaside: 'Cargó CHASIDE (archivo)', generar_codigos: 'Generó códigos', chaside_en_linea: 'CHASIDE respondido en línea',
    registrar_chaside: 'Registró un CHASIDE', anular_chaside: 'Anuló un CHASIDE', ver_estudiante: 'Vio la ficha de un estudiante', recalibrar: 'Recalibró el modelo',
    activar_calibracion: 'Activó una calibración', editar_mapeo_materias: 'Editó las reglas de materias', crear_usuario: 'Creó un usuario', editar_usuario: 'Editó un usuario',
    cambiar_clave: 'Cambió su contraseña', exportar_resultados: 'Exportó resultados', respaldo_manual: 'Respaldo manual', respaldo_diario: 'Respaldo diario',
    ajustes: 'Cambió ajustes', editar_estudiante: 'Editó un estudiante'
  };
  async function bitacora(el) {
    const l = await api('api/auditoria?limite=500');
    el.innerHTML = `<div class="panel"><div class="panel-cab"><h2>Bitácora</h2><span class="sutil">Últimos ${l.length} eventos · quién vio, cargó o cambió datos</span></div>
      <input type="search" id="b-q" placeholder="Filtrar por usuario, acción o estudiante…" style="margin-bottom:10px" aria-label="Filtrar bitácora">
      <div class="tabla-wrap"><table class="met"><thead><tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Objeto</th><th>IP</th></tr></thead><tbody id="b-filas"></tbody></table></div></div>`;
    const pintar = q => {
      q = (q || '').toLowerCase();
      $('#b-filas', el).innerHTML = l.filter(x => !q || [x.usuario, x.accion, ACC[x.accion], x.objeto].join(' ').toLowerCase().includes(q))
        .map(x => `<tr><td class="sutil">${fechaHora(x.fecha)}</td><td>${esc(x.usuario)}</td><td>${esc(ACC[x.accion] || x.accion)}</td><td class="mono">${esc(x.objeto || '')}</td><td class="mono sutil">${esc(x.ip || '')}</td></tr>`).join('');
    };
    pintar(); $('#b-q', el).addEventListener('input', e => pintar(e.target.value));
  }

  /* ── Mi cuenta ── */
  async function cuenta(el) {
    const aj = await api('api/ajustes');
    el.innerHTML = `<div class="rejilla-2"><div class="panel"><div class="panel-cab"><h2>Cambiar mi contraseña</h2></div>
        <form class="g-form" id="k-form"><label>Contraseña actual <input name="actual" type="password" required autocomplete="current-password"></label>
          <label>Nueva contraseña <input name="nueva" type="password" required minlength="10" autocomplete="new-password"></label>
          <label>Repite la nueva <input name="repite" type="password" required minlength="10" autocomplete="new-password"></label>
          <p class="sutil">Mínimo 10 caracteres con mayúsculas, minúsculas y números.</p><button class="boton">Cambiar</button></form></div>
      ${esAdmin() ? `<div class="panel"><div class="panel-cab"><h2>Institución</h2></div><form class="g-form" id="a-form">
          <label>Nombre del colegio <input name="nombre_colegio" value="${esc(aj.nombre_colegio)}"></label><button class="boton sec">Guardar</button></form></div>` : ''}</div>`;
    $('#k-form', el).addEventListener('submit', async e => {
      e.preventDefault();
      const f = Object.fromEntries(new FormData(e.target));
      if (f.nueva !== f.repite) { aviso('Las contraseñas nuevas no coinciden.'); return; }
      try { const r = await api('api/yo/clave', { method: 'POST', body: f }); aviso(r.mensaje); setTimeout(() => { location.href = '/entrar'; }, 1500); }
      catch (err) { aviso(err.message); }
    });
    $('#a-form', el)?.addEventListener('submit', async e => {
      e.preventDefault();
      try { await api('api/ajustes', { method: 'PUT', body: Object.fromEntries(new FormData(e.target)) }); aviso('Guardado.'); } catch (err) { aviso(err.message); }
    });
  }
})();
