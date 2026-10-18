/* Vocacional Bayesiano · interfaz vanilla
   Lee del servidor el mismo contrato del Módulo 9 de la tesis: datos/cohorte.json, datos/carreras.json,
   datos/estudiantes/<id>.json (protegidos con sesión). Una nueva aplicación del CHASIDE se guarda en el
   servidor, que recalcula con el modelo y devuelve el resultado. La pestaña «Gestión» está en gestion.js. */
(() => {
  'use strict';

  const AREAS = {
    C: 'Administrativas y Contables', H: 'Humanísticas y Ciencias Sociales', A: 'Artísticas',
    S: 'Ciencias de la Salud', I: 'Ingenierías, Técnicas y Computación', D: 'Defensa y Seguridad',
    E: 'Ciencias Exactas y Agrarias'
  };
  const CORTO = { C: 'Administración', H: 'Humanidades', A: 'Artes', S: 'Salud', I: 'Ingeniería', D: 'Defensa', E: 'Ciencias' };
  const CODIGOS = Object.keys(AREAS);
  const ZONAS = {
    vocacion_consolidada: { txt: 'Vocación consolidada', color: 'var(--z-vc)', corto: 'Consolidada', guia: 'Le gusta y le va bien' },
    interes_a_fortalecer: { txt: 'Interés a fortalecer', color: 'var(--z-if)', corto: 'Fortalecer', guia: 'Le gusta, pero aún no le va tan bien' },
    talento_no_explorado: { txt: 'Talento no explorado', color: 'var(--z-tn)', corto: 'Talento', guia: 'Le va bien, aunque no le atrae tanto' },
    no_prioritaria: { txt: 'Área no prioritaria', color: 'var(--z-np)', corto: 'No prioritaria', guia: 'Ni le atrae ni destaca' },
    indeterminado: { txt: 'Indeterminado: falta evidencia', color: 'transparent', corto: 'Indeterminado', guia: 'Falta evidencia para decidir' }
  };
  const ORDEN_Z = ['vocacion_consolidada', 'interes_a_fortalecer', 'talento_no_explorado', 'no_prioritaria', 'indeterminado'];
  const ALERTAS_CHASIDE = new Set(['consistencia', 'completitud', 'antiguedad', 'modalidad']);

  const $ = (s, r = document) => r.querySelector(s);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const pct = v => `${Math.round(v * 100)} %`;
  const fmt = n => n == null ? '—' : n.toFixed(1);
  const sinTilde = t => String(t).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const phi = z => window.MOTOR.phi(z);
  const fechaLarga = f => f ? new Date(f + 'T12:00').toLocaleDateString('es-EC', { day: 'numeric', month: 'long', year: 'numeric' }) : 'sin fecha';
  const hoy = () => new Date().toISOString().slice(0, 10);
  const guardar = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, JSON.stringify(v)); } catch (_) {} };
  const leer = k => { try { return JSON.parse(localStorage.getItem(k)); } catch (_) { return null; } };

  /* ───────────── Datos ───────────── */
  const D = { cohorte: null, carreras: [], gamma: 1, normas: null, cache: new Map(), modo: '' };
  const NUEVO = new Map();   // id → { respuestas, meta, anterior }

  function fijarCarreras(k) { D.carreras = k.carreras; D.gamma = k.gamma ?? 1; D.normas = k.normas || null; }
  async function iniciarDatos() {
    try {
      const [c, k] = await Promise.all([window.VB.api('datos/cohorte.json'), window.VB.api('datos/carreras.json')]);
      D.cohorte = c; fijarCarreras(k);
      D.modo = window.VB.colegio || 'servidor';
      return true;
    } catch (_) { return false; }
  }
  async function original(id) {
    if (D.cache.has(id)) return D.cache.get(id);
    const j = await window.VB.api(`datos/estudiantes/${encodeURIComponent(id)}.json`);
    D.cache.set(id, j); return j;
  }
  // Si en esta sesión se registró un CHASIDE nuevo, NUEVO guarda el resultado anterior para comparar en el plano
  async function estudiante(id) {
    return NUEVO.get(id)?.resultado || await original(id);
  }

  /* ───────────── Estado ───────────── */
  const S = { vista: 'estudiante', id: null, area: null, beta: 0.5, ciudad: '', filtros: new Set(), fuente: 'notas', anio: null, comparar: true };
  const b0 = parseFloat(leer('vb-beta')); if ([0.3, 0.5, 0.7].includes(b0)) S.beta = b0;

  /* ───────────── Tooltip ───────────── */
  const tip = $('#tip');
  document.addEventListener('mousemove', e => {
    const t = e.target.closest?.('[data-tip]');
    if (!t) { tip.hidden = true; return; }
    tip.innerHTML = t.getAttribute('data-tip'); tip.hidden = false;
    const w = tip.offsetWidth, h = tip.offsetHeight;
    let x = e.clientX + 14, y = e.clientY + 14;
    if (x + w > innerWidth - 8) x = e.clientX - w - 14;
    if (y + h > innerHeight - 8) y = e.clientY - h - 14;
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  });
  document.addEventListener('scroll', () => { tip.hidden = true; }, true);

  /* ───────────── Barra y pestañas ───────────── */
  function pintarEstado() {
    const c = D.cohorte;
    if (!c || !c.estudiantes.length) { $('#estado').innerHTML = `Aún no hay estudiantes con resultados · ${esc(D.modo || '')}`; return; }
    const f = new Date(c.generado);
    $('#estado').innerHTML = `<b>${c.n_estudiantes}</b> estudiantes · modelo ejecutado el <b>${f.toLocaleDateString('es-EC', { day: 'numeric', month: 'short', year: 'numeric' })}</b> · ${esc(D.modo)}`;
  }
  document.querySelectorAll('.pestanas button').forEach(b => b.addEventListener('click', () => cambiarVista(b.dataset.vista)));
  function cambiarVista(v) {
    S.vista = v;
    document.querySelectorAll('.pestanas button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.vista === v)));
    ['estudiante', 'cohorte', 'gestion'].forEach(x => { $('#vista-' + x).hidden = x !== v; });
    $('#selector').hidden = v !== 'estudiante' || !D.cohorte?.estudiantes.length;
    if (v === 'cohorte') pintarCohorte();
    if (v === 'gestion') pintarGestion();
    if (v === 'estudiante' && !D.cohorte?.estudiantes.length) { $('#vista-estudiante').innerHTML = `<div class="panel vacio">Aún no hay estudiantes con resultados. Un estudiante aparece aquí cuando tiene <b>notas y CHASIDE</b>. Revisa la pestaña <b>Gestión</b>.</div>`; return; }
    if (v === 'estudiante' && S.id) abrirEstudiante(S.id);
  }

  /* ───────────── Buscador de estudiantes ───────────── */
  const nIndet = e => Object.values(e.perfil || {}).filter(p => p[2] === 'indeterminado').length;
  // Coincidencia: cada palabra escrita debe aparecer en el nombre, el ID o una carrera. Puntaje para ordenar.
  function coincidencia(e, q) {
    const toks = sinTilde(q).split(/\s+/).filter(Boolean);
    if (!toks.length) return 1;
    const nom = sinTilde(e.nombre || ''), palabras = nom.split(/\s+/), id = e.id.toLowerCase(), car = e.top3.map(sinTilde).join(' | ');
    let p = 0;
    for (const t of toks) {
      if (nom.startsWith(t)) p += 6;
      else if (palabras.some(w => w.startsWith(t))) p += 4;
      else if (nom.includes(t)) p += 2;
      else if (id.includes(t)) p += 3;
      else if (car.includes(t)) p += 1;
      else return 0;
    }
    return p;
  }
  function filtrados(q = '') {
    return (D.cohorte?.estudiantes || []).map(e => ({ e, p: coincidencia(e, q) })).filter(({ e, p }) => {
      if (!p) return false;
      if (S.filtros.has('alertas') && !e.n_alertas) return false;
      if (S.filtros.has('cons') && !(e.vocacion_consolidada || []).length) return false;
      if (S.filtros.has('ind') && nIndet(e) < 3) return false;
      return true;
    }).sort((a, b) => b.p - a.p || (a.e.nombre || a.e.id).localeCompare(b.e.nombre || b.e.id, 'es')).map(x => x.e);
  }
  function resaltar(texto, q) {
    const toks = sinTilde(q).split(/\s+/).filter(Boolean);
    if (!toks.length) return esc(texto);
    const base = sinTilde(texto), marca = new Array(texto.length).fill(false);
    toks.forEach(t => { let i = base.indexOf(t); while (i >= 0) { for (let j = i; j < i + t.length; j++) marca[j] = true; i = base.indexOf(t, i + 1); } });
    let out = '', abierto = false;
    [...texto].forEach((ch, i) => {
      if (marca[i] && !abierto) { out += '<mark>'; abierto = true; }
      if (!marca[i] && abierto) { out += '</mark>'; abierto = false; }
      out += esc(ch);
    });
    return out + (abierto ? '</mark>' : '');
  }
  function firma(e) {
    return `<span class="firma" aria-hidden="true">${CODIGOS.map(a => {
      const z = (e.perfil || {})[a]?.[2] || 'indeterminado';
      return `<i class="${z === 'indeterminado' ? 'hatch' : ''}" style="background:${ZONAS[z].color}"></i>`;
    }).join('')}</span>`;
  }
  const entrada = $('#buscar'), opciones = $('#opciones');
  let activa = -1, visibles = [];
  function abrirOpciones(q) {
    visibles = filtrados(q).slice(0, 200);
    activa = q.trim() ? 0 : visibles.findIndex(e => e.id === S.id);
    opciones.innerHTML = visibles.map((e, i) => `<li role="option" id="op-${i}" data-id="${esc(e.id)}" aria-selected="${i === activa}">
        <span class="n">${resaltar(e.nombre || e.id, q)}</span>${firma(e)}
        <span class="s">${e.grado_actual}.º · ${esc(e.top3[0] || '')}${e.n_alertas ? ` · ${e.n_alertas} alerta${e.n_alertas > 1 ? 's' : ''}` : ''}</span></li>`).join('')
      || `<li class="vacio sutil">Ningún estudiante coincide con "${esc(q)}". Prueba con otra parte del nombre o quita los filtros.</li>`;
    opciones.hidden = false; entrada.setAttribute('aria-expanded', 'true');
    $('#buscar-cuenta').textContent = q.trim() ? `${visibles.length} coincidencia${visibles.length === 1 ? '' : 's'}` : '';
    opciones.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' });
  }
  function cerrarOpciones() { opciones.hidden = true; entrada.setAttribute('aria-expanded', 'false'); $('#buscar-cuenta').textContent = ''; }
  function marcar(i) {
    activa = Math.max(0, Math.min(visibles.length - 1, i));
    opciones.querySelectorAll('li[role="option"]').forEach((li, j) => li.setAttribute('aria-selected', String(j === activa)));
    const li = $('#op-' + activa); li?.scrollIntoView({ block: 'nearest' });
    entrada.setAttribute('aria-activedescendant', li ? li.id : '');
  }
  function elegir(id) {
    cerrarOpciones(); S.area = null; S.anio = null; abrirEstudiante(id);
    if (S.vista !== 'estudiante') cambiarVista('estudiante');
  }
  function pintarSelector() {
    const l = filtrados(), i = l.findIndex(e => e.id === S.id);
    const e = D.cohorte?.estudiantes.find(x => x.id === S.id);
    if (e && document.activeElement !== entrada) entrada.value = e.nombre || e.id;
    $('#contador').textContent = l.length ? `${i >= 0 ? i + 1 : '–'} de ${l.length}` : '0 casos';
  }
  entrada.addEventListener('focus', () => { entrada.select(); abrirOpciones(''); });
  entrada.addEventListener('input', () => abrirOpciones(entrada.value));
  entrada.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { e.preventDefault(); if (opciones.hidden) abrirOpciones(''); marcar(activa + 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); marcar(activa - 1); }
    else if (e.key === 'Enter') { e.preventDefault(); const x = visibles[activa] || visibles[0]; if (x) { elegir(x.id); entrada.blur(); } }
    else if (e.key === 'Escape') { cerrarOpciones(); pintarSelector(); entrada.blur(); }
  });
  entrada.addEventListener('blur', () => setTimeout(() => { cerrarOpciones(); pintarSelector(); }, 150));
  opciones.addEventListener('mousedown', e => { const li = e.target.closest('li[data-id]'); if (li) { e.preventDefault(); elegir(li.dataset.id); entrada.blur(); } });
  $('#combo-abrir').addEventListener('click', () => { if (opciones.hidden) entrada.focus(); else cerrarOpciones(); });
  const paso = d => { const l = filtrados(); if (!l.length) return; const i = l.findIndex(e => e.id === S.id); elegir(l[(i + d + l.length) % l.length].id); };
  $('#anterior').addEventListener('click', () => paso(-1));
  $('#siguiente').addEventListener('click', () => paso(1));
  $('#filtros').addEventListener('click', e => {
    const b = e.target.closest('.chip-f'); if (!b) return;
    const f = b.dataset.f; if (S.filtros.has(f)) S.filtros.delete(f); else S.filtros.add(f);
    document.querySelectorAll('.chip-f').forEach(c => c.setAttribute('aria-pressed', String(S.filtros.has(c.dataset.f))));
    const l = filtrados();
    if (l.length && !l.some(x => x.id === S.id)) elegir(l[0].id); else pintarSelector();
  });

  /* ───────────── Vista estudiante ───────────── */
  const ICONO = `<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.5 15 14H1z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M8 6v3.6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="8" cy="11.8" r="0.9" fill="currentColor"/></svg>`;
  const CRITICAS = new Set(['consistencia', 'indeterminado', 'completitud']);
  let actual = null;

  async function abrirEstudiante(id) {
    S.id = id; pintarSelector();
    const v = $('#vista-estudiante');
    let d;
    try { d = await estudiante(id); } catch (err) { v.innerHTML = `<div class="panel vacio">${esc(err.message)}</div>`; return; }
    if (S.id !== id) return;
    actual = d;
    if (!S.area || !d.areas.some(a => a.codigo === S.area)) {
      const prio = ['vocacion_consolidada', 'talento_no_explorado', 'interes_a_fortalecer'];
      S.area = [...d.areas].sort((x, y) => (prio.indexOf(x.zona.clave) + 1 || 9) - (prio.indexOf(y.zona.clave) + 1 || 9) || y.zona.certeza - x.zona.certeza)[0].codigo;
    }
    v.innerHTML = `<div class="expediente">
      <aside class="col-fuentes" aria-label="Fuentes de datos"><div class="panel" id="panel-fuente">${htmlFuente(d)}</div></aside>
      <div class="col-resultados">
        ${htmlFicha(d)}
        <div class="panel" id="panel-figuras">${htmlFiguras(d)}</div>
        <div class="panel">
          <div class="panel-cab"><h2>Plano Interés × Rendimiento</h2><span class="sutil">Toca un área para leerla</span></div>
          <div class="plano-y-lectura">
            <div class="plano-wrap" id="plano-wrap">${svgPlano(d)}</div>
            <div class="lectura" id="lectura">${htmlLectura(d)}</div>
          </div>
        </div>
        <div class="panel">
          <div class="panel-cab"><h2>Las 7 áreas CHASIDE</h2><span class="sutil">La zona solo se asigna si la certeza supera ${pct(D.cohorte.parametros.umbral_certeza)}</span></div>
          <div class="areas-tabla" id="areas"><div class="at-cab" aria-hidden="true"><span></span><span>Le gusta</span><span>Le va bien</span><span>Zona · certeza</span></div>${d.areas.map(htmlArea).join('')}</div>
          <p class="sutil" style="margin-top:8px">Barras = percentil frente a su curso; la línea marca el promedio (50).</p>
          ${htmlLeyenda()}
        </div>
        <div class="panel" id="panel-carreras">${htmlCarreras(d)}</div>
      </div></div>`;
    enlazarEstudiante(d);
  }

  function htmlFicha(d) {
    const e = d.estudiante, n = NUEVO.get(e.id);
    const al = d.alertas.map(a => `<div class="alerta ${CRITICAS.has(a.tipo) ? 'critica' : 'aviso'}">${ICONO}<span>${esc(a.texto)}</span>
        ${ALERTAS_CHASIDE.has(a.tipo) ? '<button class="boton sec mini-b" data-accion="test">Repetir CHASIDE</button>' : ''}</div>`).join('');
    const banner = n ? `<div class="banner">
        <div><b>Resultados con el CHASIDE del ${esc(fechaLarga(n.meta.fecha))}.</b> Reemplaza a la prueba del ${esc(fechaLarga(n.anterior?.estudiante.fuentes.chaside?.fecha))}.</div>
        <div class="banner-acc">
          <label class="check"><input type="checkbox" id="comparar" ${S.comparar ? 'checked' : ''}> Ver el cambio en el plano</label>
          <button class="boton sec mini-b" data-accion="deshacer">Anular esta prueba</button>
        </div></div>` : '';
    return `<div class="panel ficha-panel"><div class="ficha">
      <div class="ident"><span class="etiqueta">Estudiante ${e.nombre_ficticio ? '<span class="ficticio" data-tip="Nombre ficticio generado para la simulación. Con la nómina del colegio se muestran los nombres reales.">nombre ficticio</span>' : ''}</span>
        <span class="nombre">${esc(e.nombre || e.id)}</span><span class="sutil mono">${esc(e.id)} · ${e.grado_actual ?? '—'}.º grado</span></div>
      <div class="ficha-der">${al ? `<div class="alertas">${al}</div>` : `<div class="sutil">Sin alertas de calidad en la evidencia.</div>`}
        <button class="boton sec mini-b" data-accion="codigo" data-tip="Genera un código para que el estudiante responda el CHASIDE desde su teléfono">Código para el test en línea</button></div>
    </div>${banner}</div>`;
  }

  /* Las 3 profesiones (figuras) */
  function htmlFiguras(d) {
    const top = rankingCarreras(d).slice(0, 3), F = window.FIGURAS, gen = d.estudiante.genero;
    const nombre = (d.estudiante.nombre || '').split(' ')[0] || 'el estudiante';
    return `<div class="panel-cab"><h2>Las 3 profesiones más cercanas a ${esc(nombre)}</h2><span class="sutil">Enfoque: ${esc(ENFOQUES.find(([b]) => Math.abs(S.beta - b) < 1e-9)?.[1] || '')}</span></div>
      <div class="figuras">${top.map((x, i) => {
        const o = F.outfitFor(x.c.nombre);
        return `<div class="figura"><div aria-hidden="true">${F.figureSVG(o, gen)}</div>
          <div style="min-width:0"><div class="k">${String(i + 1).padStart(2, '0')} · ${esc(o.label)}</div>
          <div class="nm">${esc(x.c.nombre)}</div>
          <div class="pc">${Math.round(x.af)}<small> afinidad</small></div>${x.m ? `<div class="mt">Estabilidad P(top 5): ${pct(x.m.p_top5)}</div>` : ''}
          <div class="mt">${esc([x.c.universidad, x.c.ciudad].filter(Boolean).join(' · '))}</div></div></div>`;
      }).join('')}</div>`;
  }

  /* Plano: cuadrantes con nombre, áreas con palabras, nube de incertidumbre y flecha si cambió el CHASIDE */
  function svgPlano(d) {
    const W = 560, H = 520, L = 40, R = 12, T = 12, B = 44, w = W - L - R, h = H - T - B;
    const X = p => L + p / 100 * w, Y = p => T + (1 - p / 100) * h;
    const ant = S.comparar ? NUEVO.get(d.estudiante.id)?.anterior : null;
    const antPos = ant ? Object.fromEntries(ant.areas.map(a => [a.codigo, a])) : {};
    let s = `<svg class="plano" viewBox="0 0 ${W} ${H}" role="img" aria-label="Plano de interés y rendimiento por área">
      <defs><marker id="punta" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="var(--fg-2)"/></marker></defs>`;
    const cuad = [['vocacion_consolidada', 50, 100], ['interes_a_fortalecer', 0, 100], ['talento_no_explorado', 50, 50], ['no_prioritaria', 0, 50]];
    cuad.forEach(([z, x0, y1]) => {
      s += `<rect x="${X(x0)}" y="${Y(y1)}" width="${w / 2}" height="${h / 2}" fill="${ZONAS[z].color}" opacity="0.09"/>`;
    });
    s += `<rect x="${L}" y="${T}" width="${w}" height="${h}" fill="none" stroke="var(--line)"/>`;
    s += `<line class="eje-medio" x1="${X(50)}" y1="${T}" x2="${X(50)}" y2="${T + h}"/><line class="eje-medio" x1="${L}" y1="${Y(50)}" x2="${L + w}" y2="${Y(50)}"/>`;
    [['vocacion_consolidada', X(99), Y(99) + 14, 'end'], ['interes_a_fortalecer', X(1), Y(99) + 14, 'start'],
     ['talento_no_explorado', X(99), Y(1) - 20, 'end'], ['no_prioritaria', X(1), Y(1) - 20, 'start']].forEach(([z, x, y, an]) => {
      s += `<text class="cuad" x="${x}" y="${y}" text-anchor="${an}">${ZONAS[z].txt}</text><text class="cuad-g" x="${x}" y="${y + 14}" text-anchor="${an}">${ZONAS[z].guia}</text>`;
    });
    [0, 50, 100].forEach(v => {
      s += `<text class="tick" x="${X(v)}" y="${T + h + 15}" text-anchor="${v === 0 ? 'start' : v === 100 ? 'end' : 'middle'}">${v === 50 ? 'promedio' : v}</text>`;
      s += `<text class="tick" x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${v === 50 ? '' : v}</text>`;
    });
    s += `<text class="eje-t" x="${L + w / 2}" y="${H - 6}" text-anchor="middle">Le va bien en el colegio (rendimiento) →</text>`;
    s += `<text class="eje-t" transform="translate(13 ${T + h / 2}) rotate(-90)" text-anchor="middle">Le gusta (interés) →</text>`;
    // nubes de incertidumbre
    d.areas.forEach(a => {
      const cx = X(a.rendimiento.percentil), cy = Y(a.interes.percentil);
      const rx = Math.max(6, (X(a.rendimiento.rango90[1]) - X(a.rendimiento.rango90[0])) / 2), ry = Math.max(6, (Y(a.interes.rango90[0]) - Y(a.interes.rango90[1])) / 2);
      const ccx = (X(a.rendimiento.rango90[0]) + X(a.rendimiento.rango90[1])) / 2, ccy = (Y(a.interes.rango90[0]) + Y(a.interes.rango90[1])) / 2;
      const z = ZONAS[a.zona.clave];
      s += `<ellipse cx="${ccx}" cy="${ccy}" rx="${rx}" ry="${ry}" fill="${a.zona.clave === 'indeterminado' ? 'var(--fg-3)' : z.color}" opacity="${a.codigo === S.area ? 0.16 : 0.07}"/>`;
      if (antPos[a.codigo]) {
        const o = antPos[a.codigo], ox = X(o.rendimiento.percentil), oy = Y(o.interes.percentil);
        if (Math.hypot(ox - cx, oy - cy) > 4) {
          s += `<circle cx="${ox}" cy="${oy}" r="5" fill="none" stroke="var(--fg-3)" stroke-dasharray="2 2"/>`;
          s += `<line x1="${ox}" y1="${oy}" x2="${cx}" y2="${cy}" stroke="var(--fg-2)" stroke-width="1.4" marker-end="url(#punta)" opacity="0.8"/>`;
        }
      }
    });
    // etiquetas sin choques: se prueban 8 posiciones alrededor del punto
    const cajas = d.areas.map(a => ({ x: X(a.rendimiento.percentil) - 8, y: Y(a.interes.percentil) - 8, w: 16, h: 16 }));
    // zonas reservadas para los títulos de los cuadrantes
    cajas.push({ x: L, y: T, w: 190, h: 34 }, { x: L + w - 190, y: T, w: 190, h: 34 }, { x: L, y: T + h - 36, w: 210, h: 36 }, { x: L + w - 230, y: T + h - 36, w: 230, h: 36 });
    const choca = (b) => cajas.some(c => b.x < c.x + c.w && b.x + b.w > c.x && b.y < c.y + c.h && b.y + b.h > c.y) || b.x < L || b.x + b.w > L + w || b.y < T || b.y + b.h > T + h;
    const marcas = d.areas.map(a => {
      const cx = X(a.rendimiento.percentil), cy = Y(a.interes.percentil), txt = CORTO[a.codigo];
      const tw = txt.length * 7.4 + 16, th = 22;
      const cand = [[10, -th / 2], [-10 - tw, -th / 2], [-tw / 2, -12 - th], [-tw / 2, 12], [10, -th - 4], [10, 4], [-10 - tw, -th - 4], [-10 - tw, 4]];
      let pos = cand.map(([dx, dy]) => ({ x: cx + dx, y: cy + dy, w: tw, h: th })).find(b => !choca(b)) || { x: cx + 10, y: cy - th / 2, w: tw, h: th };
      cajas.push(pos);
      return { a, cx, cy, pos, txt };
    });
    marcas.forEach(({ a, cx, cy, pos, txt }) => {
      const z = ZONAS[a.zona.clave], ind = a.zona.clave === 'indeterminado', sel = a.codigo === S.area;
      s += `<g class="punto${sel ? ' sel' : ''}${S.area && !sel ? ' tenue' : ''}" data-area="${a.codigo}" data-tip="${esc(tipArea(a))}" tabindex="0" role="button" aria-label="${esc(a.nombre)}">
        <rect class="hit" x="${Math.min(cx - 10, pos.x)}" y="${Math.min(cy - 10, pos.y)}" width="${Math.max(cx + 10, pos.x + pos.w) - Math.min(cx - 10, pos.x)}" height="${Math.max(cy + 10, pos.y + pos.h) - Math.min(cy - 10, pos.y)}"/>
        <rect class="pastilla" x="${pos.x}" y="${pos.y}" width="${pos.w}" height="${pos.h}" rx="10" style="stroke:${ind ? 'var(--fg-3)' : z.color}"/>
        <text class="palabra" x="${pos.x + pos.w / 2}" y="${pos.y + 15.5}" text-anchor="middle">${txt}</text>
        ${sel ? `<circle cx="${cx}" cy="${cy}" r="12" fill="none" stroke="var(--fg)" stroke-width="2"/>` : ''}
        <circle class="nucleo" cx="${cx}" cy="${cy}" r="7.5" fill="${ind ? 'var(--surface)' : z.color}" style="${ind ? 'stroke:var(--fg-3);stroke-dasharray:3 2' : ''}"/></g>`;
    });
    return s + '</svg>';
  }
  function tipArea(a) {
    return `<b>${esc(a.nombre)}</b><br>Le gusta más que al ${a.interes.percentil} % de su curso<br>Le va mejor que al ${a.rendimiento.percentil} %<br>${esc(ZONAS[a.zona.clave].txt)} · certeza ${pct(a.zona.certeza)}`;
  }

  /* Lectura del área seleccionada (al lado del plano) */
  function htmlLectura(d) {
    const a = d.areas.find(x => x.codigo === S.area) || d.areas[0];
    const nom = (d.estudiante.nombre || 'El estudiante').split(' ')[0], p = a.zona.probabilidades;
    const frase = `A ${esc(nom)} le gusta ${esc(CORTO[a.codigo].toLowerCase())} más que al <b>${a.interes.percentil} %</b> de su curso y le va mejor que al <b>${a.rendimiento.percentil} %</b>.`;
    const probs = ORDEN_Z.slice(0, 4).map(z => `<span>${ZONAS[z].txt}</span><span class="b"><i style="width:${p[z] * 100}%;background:${ZONAS[z].color}"></i></span><span class="num" style="text-align:right">${pct(p[z])}</span>`).join('');
    const ap = [['El CHASIDE (interés)', a.aportes.interes.chaside_interes, 'interés'], ['Las notas', a.aportes.rendimiento.notas, 'rendimiento'], ['Su autopercepción', a.aportes.rendimiento.autopercepcion, 'rendimiento']];
    const aportes = ap.map(([n, v, dim]) => {
      const val = v ?? 0, ancho = Math.min(Math.abs(val), 2) / 2 * 50;
      return `<span>${n}</span><span class="div" data-tip="${esc(`Empuja el ${dim} ${val >= 0 ? 'hacia arriba' : 'hacia abajo'} ${Math.abs(val).toFixed(2)} desviaciones`)}"><i style="${val >= 0 ? `left:50%;width:${ancho}%` : `left:${50 - ancho}%;width:${ancho}%`}"></i></span><span class="num mono" style="text-align:right;font-size:.8rem">${val >= 0 ? '+' : ''}${val.toFixed(2)}</span>`;
    }).join('');
    const mats = a.materias_clave.length ? a.materias_clave.map(m => `<li><span>${esc(m.materia)}</span><b class="mono">${m.nota?.toFixed(1) ?? '—'}</b></li>`).join('') : '<li class="sutil">Sin materias asociadas a esta área.</li>';
    return `<div class="lectura-cab"><span class="etiqueta">Área seleccionada</span><h3>${esc(a.nombre)}</h3>${chipZona(a.zona.clave)} <span class="certeza">certeza ${pct(a.zona.certeza)}</span></div>
      <p class="frase">${frase} ${a.zona.clave === 'indeterminado' ? 'Todavía no hay evidencia suficiente para ubicarla en una zona.' : esc(ZONAS[a.zona.clave].guia) + '.'}</p>
      <div class="bloque"><div class="etiqueta">Probabilidad de cada zona</div><div class="prob">${probs}</div></div>
      <div class="bloque"><div class="etiqueta">Qué empujó el resultado</div><div class="aporte">${aportes}</div>
        ${a.autopercepcion ? `<div class="sutil">Autopercepción: ${esc(a.autopercepcion.texto)}.</div>` : ''}</div>
      <div class="bloque"><div class="etiqueta">Materias clave (último año)</div><ul class="materias">${mats}</ul></div>`;
  }

  function barra(r, que) {
    return `<span class="bar" data-tip="${esc(`${que} más que al ${r.percentil} % de su curso<br>Rango probable: ${r.rango90[0]}–${r.rango90[1]}`)}"><span class="bar-t"><i style="width:${r.percentil}%"></i><span class="bar-m"></span></span><b class="mono">${r.percentil}</b></span>`;
  }
  function chipZona(z) {
    const Z = ZONAS[z];
    return `<span class="zona"><i class="sw ${z === 'indeterminado' ? 'ind' : ''}" style="background:${Z.color}"></i>${esc(Z.corto)}</span>`;
  }
  function htmlLeyenda() {
    return `<div class="leyenda" style="margin-top:12px">${ORDEN_Z.map(z =>
      `<span><i class="sw ${z === 'indeterminado' ? 'ind' : ''}" style="background:${ZONAS[z].color}"></i>${ZONAS[z].txt}</span>`).join('')}</div>`;
  }
  function htmlArea(a) {
    return `<button class="area-f" data-area="${a.codigo}" aria-pressed="${a.codigo === S.area}">
      <span class="nom">${esc(a.nombre)}</span>
      ${barra(a.interes, 'Le gusta')}${barra(a.rendimiento, 'Le va bien')}
      <span class="area-der">${chipZona(a.zona.clave)}<span class="certeza">${pct(a.zona.certeza)}</span></span>
    </button>`;
  }

  /* Carreras: orden recalculado con β (fórmula del Módulo 7); P(top 5) y rango vienen del modelo (β = 0.5) */
  function rankingCarreras(d) {
    const MU = d.areas.map(a => [a.interes.z, a.rendimiento.z]);
    const A = window.MOTOR.afinidad(D.carreras, D.gamma, D.normas || {}, S.beta, MU);
    const mod = new Map(d.carreras.map(c => [c.id, c]));
    return D.carreras.map((c, j) => ({ c, af: A[j], m: mod.get(c.id) }))
      .filter(r => !S.ciudad || r.c.ciudad === S.ciudad).sort((x, y) => y.af - x.af);
  }
  const ENFOQUES = [
    [0.5, 'Equilibrado', 'Interés y rendimiento pesan igual (50/50). Es el enfoque recomendado para la orientación general.'],
    [0.7, 'Priorizar lo que le gusta', 'El interés pesa 70 % y el rendimiento 30 %. Útil cuando el estudiante tiene una vocación clara y sus notas en esas materias pueden mejorar.'],
    [0.3, 'Priorizar lo que le va bien', 'El rendimiento pesa 70 % y el interés 30 %. Útil para explorar opciones realistas: carreras con exámenes de ingreso exigentes o cuando el estudiante aún no tiene claro qué le gusta.']
  ];
  function estabilidad(p) {
    if (p == null) return `<span class="pill">sin dato</span>`;
    if (p >= 0.8) return `<span class="pill alta">estable</span>`;
    if (p >= 0.4) return `<span class="pill media">probable</span>`;
    return `<span class="pill">variable</span>`;
  }
  function htmlCarreras(d) {
    const r = rankingCarreras(d).slice(0, 10);
    const ciudades = [...new Set(D.carreras.map(c => c.ciudad).filter(c => c && !/confirmar/i.test(c)))].sort((a, b) => a.localeCompare(b, 'es'));
    const b50 = Math.abs(S.beta - 0.5) < 1e-9;
    return `<div class="panel-cab"><h2>Profesiones y dónde estudiarlas</h2>
      <div class="controles">
        <div class="segmento" role="radiogroup" aria-label="Qué pesa más al recomendar">${ENFOQUES.map(([b, t, ayuda]) => `<button type="button" role="radio" data-beta="${b}" aria-checked="${Math.abs(S.beta - b) < 1e-9}" data-tip="${esc(ayuda)}">${t}</button>`).join('')}</div>
        <label for="ciudad">Ciudad <select id="ciudad"><option value="">Todas</option>${ciudades.map(c => `<option${c === S.ciudad ? ' selected' : ''}>${esc(c)}</option>`).join('')}</select></label>
      </div></div>
      <p class="sutil enfoque-ayuda">${esc(ENFOQUES.find(([b]) => Math.abs(S.beta - b) < 1e-9)?.[2] || '')}${b50 ? '' : ' La estabilidad P(top 5) se calculó con el enfoque equilibrado.'}</p>
      <ol class="carreras">${r.map((x, i) => {
        const m = x.m, rg = m?.rango90;
        return `<li class="carrera">
          <span class="pos">${String(i + 1).padStart(2, '0')}</span>
          <span style="min-width:0"><div class="cn">${esc(x.c.nombre)}</div><div class="meta">${esc([x.c.universidad, x.c.ciudad].filter(Boolean).join(' · '))}</div></span>
          <span class="afin" data-tip="${esc(`Encaja mejor que el ${Math.round(x.af)} % de su cohorte${rg ? `<br>Rango del 90 %: ${rg[0].toFixed(0)}–${rg[1].toFixed(0)}` : ''}`)}">
            <span class="val">${x.af.toFixed(0)}</span>
            <span class="b"><span class="p" style="width:${x.af}%"></span>${rg ? `<span class="r" style="left:${rg[0]}%;width:${rg[1] - rg[0]}%"></span>` : ''}</span>
          </span>
          <span class="estab" data-tip="${esc(m ? `En el ${Math.round(m.p_top5 * 100)} % de los 1 000 perfiles plausibles quedó entre las 5 más afines` : 'Fuera de las 10 primeras del modelo con 50/50')}">
            <span class="pt">${m ? pct(m.p_top5) : '—'}</span>${estabilidad(m?.p_top5)}</span>
          <span class="razon">${m ? esc(m.razon) : ''}</span>
          ${x.c.habilidades?.length ? `<details><summary>Habilidades que pide</summary>${x.c.habilidades.map(esc).join(' · ')}</details>` : ''}
        </li>`;
      }).join('')}</ol>
      <p class="sutil" style="margin-top:10px">Afinidad 85 = encaja en esa carrera mejor que el 85 % de sus compañeros. P(top 5) = qué tan estable es esa posición con la incertidumbre del modelo.</p>`;
  }

  /* ───────────── Columna izquierda: Fuentes de datos ───────────── */
  function colorNota(n) {
    if (n == null) return '';
    if (n >= 9) return 'background:color-mix(in srgb, var(--z-vc) 22%, transparent)';
    if (n >= 7) return 'background:var(--surface-2)';
    return 'background:color-mix(in srgb, var(--crit) 20%, transparent)';
  }
  function htmlFuente(d) {
    const tab = S.fuente;
    return `<h2 class="titulo-fuentes">Fuentes de datos</h2>
      <div class="subtabs" role="tablist"><button role="tab" data-ft="notas" aria-selected="${tab === 'notas'}">Notas</button><button role="tab" data-ft="chaside" aria-selected="${tab === 'chaside'}">CHASIDE</button></div>
      <div>${tab === 'notas' ? htmlNotas(d) : htmlChaside(d)}</div>`;
  }
  function htmlNotas(d) {
    const anios = (d.origen?.notas || []).filter(a => a.materias.some(m => m.estado === 'incluida'));
    if (!anios.length) return '<p class="sutil">No hay notas de 9.º a 12.º para este estudiante.</p>';
    const abierto = S.anio ?? anios.length - 1;
    const acc = anios.map((a, i) => {
      const inc = a.materias.filter(m => m.estado === 'incluida' && m.final != null);
      const prom = inc.length ? inc.reduce((x, m) => x + m.final, 0) / inc.length : null;
      return `<details class="anio" data-anio="${i}"${i === abierto ? ' open' : ''}><summary><span>${a.grado}.º grado <span class="sutil">${esc(a.periodo || '')}</span></span>
          <span class="nota-pill mono" style="${colorNota(prom)}">${fmt(prom)}</span></summary>
        <table class="notas"><thead><tr><th>Materia</th><th class="n">S1</th><th class="n">S2</th><th class="n">Final</th></tr></thead><tbody>
        ${a.materias.map(m => `<tr class="${m.estado === 'incluida' ? '' : 'fuera'}" ${m.estado === 'incluida' ? `data-tip="${esc(`Aporta a: ${(m.areas || '').split('').map(k => CORTO[k]).join(', ') || '—'}`)}"` : `data-tip="${m.estado === 'excluida' ? 'No académica: el modelo no la usa' : 'Sin regla de mapeo: el modelo no la usa'}"`}>
          <td>${esc(m.materia)}${m.estado === 'incluida' ? '' : ' <span class="sutil">(no usada)</span>'}</td><td class="n">${fmt(m.sem1)}</td><td class="n">${fmt(m.sem2)}</td>
          <td class="n"><span class="nota-pill" style="${m.estado === 'incluida' ? colorNota(m.final) : ''}">${fmt(m.final)}</span></td></tr>`).join('')}
        </tbody></table></details>`;
    }).join('');
    return `<div class="etiqueta" style="margin-bottom:6px">Notas del colegio (0–10)</div>${acc}
      <div class="etiqueta" style="margin:16px 0 6px">Rendimiento por área, grado a grado</div>${htmlTrayectoria(d)}
      <p class="sutil" style="margin:6px 0 0">Percentil de cada área frente a su curso en ese grado; la línea punteada es el promedio.</p>`;
  }
  function htmlChaside(d) {
    const ch = d.origen?.chaside, f = d.estudiante.fuentes.chaside || {};
    if (!ch) return `<div class="vacio-ch"><p>Este estudiante todavía no tiene el CHASIDE.</p>
      <button class="boton" data-accion="test">Tomar el test CHASIDE</button>
      <p class="sutil">Sin el test, el modelo solo puede estimar el rendimiento; el interés queda en el promedio con mucha incertidumbre.</p></div>`;
    const pts = (n, t) => `<span class="puntos">${Array.from({ length: t }, (_, i) => `<i class="${i < n ? 'si' : ''}"></i>`).join('')}</span>`;
    return `<p class="sutil" style="margin:0 0 10px">${esc(fechaLarga(f.fecha))} · ${esc(f.modalidad || '')} · ${ch.respondidas} de ${ch.total} respondidas · ${ch.si} "Sí"</p>
      <div class="ch-lista">${CODIGOS.map(k => { const r = ch.areas[k]; return `<div class="ch-fila"><span class="ch-n">${esc(CORTO[k])}</span>
        <span class="ch-l">Intereses</span>${pts(r.interes[0], r.interes[1])}<span class="mono ch-v">${r.interes[0]}/${r.interes[1]}</span>
        <span class="ch-l">Aptitudes</span>${pts(r.aptitud[0], r.aptitud[1])}<span class="mono ch-v">${r.aptitud[0]}/${r.aptitud[1]}</span></div>`; }).join('')}</div>
      <button class="boton sec" data-accion="test" style="margin-top:14px;width:100%">Repetir el test CHASIDE</button>
      <p class="sutil" style="margin-top:8px">La nueva prueba reemplaza a esta y el modelo recalcula al instante.</p>`;
  }
  function htmlTrayectoria(d) {
    const W = 130, H = 46, L = 2, R = 2, T = 4, B = 4;
    return `<div class="multiples">${CODIGOS.map(k => {
      const pts = d.trayectoria.filter(t => t.area === k).sort((a, b) => a.grado - b.grado);
      if (!pts.length) return `<div class="mini"><div class="t"><span>${esc(CORTO[k])}</span><b>—</b></div></div>`;
      const X = g => L + (g - 9) / 3 * (W - L - R), Y = v => T + (1 - v / 100) * (H - T - B);
      const line = pts.map((p, i) => `${i ? 'L' : 'M'}${X(p.grado).toFixed(1)},${Y(p.rendimiento_percentil).toFixed(1)}`).join('');
      const last = pts.at(-1);
      return `<div class="mini"><div class="t"><span>${esc(CORTO[k])}</span><b>P${Math.round(last.rendimiento_percentil)}</b></div>
        <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Rendimiento en ${esc(AREAS[k])} por grado">
          <line class="m" x1="${L}" y1="${Y(50)}" x2="${W - R}" y2="${Y(50)}"/>
          <path class="a" d="${line}L${X(last.grado)},${Y(0)}L${X(pts[0].grado)},${Y(0)}Z"/><path class="l" d="${line}"/>
          <circle cx="${X(last.grado)}" cy="${Y(last.rendimiento_percentil)}" r="3"/>
          ${pts.map(p => `<rect class="hit" x="${X(p.grado) - 12}" y="0" width="24" height="${H}" data-tip="${esc(`${CORTO[k]} · ${p.grado}.º grado<br>Rendimiento P${Math.round(p.rendimiento_percentil)}`)}"/>`).join('')}
        </svg></div>`;
    }).join('')}</div>`;
  }

  function enlazarEstudiante(d) {
    const v = $('#vista-estudiante');
    const sel = cod => {
      S.area = cod; $('#lectura').innerHTML = htmlLectura(d);
      v.querySelectorAll('.area-f').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.area === cod)));
      $('#plano-wrap').innerHTML = svgPlano(d); enlazarPlano();
    };
    const enlazarPlano = () => v.querySelectorAll('.punto').forEach(g => {
      g.addEventListener('click', () => sel(g.dataset.area));
      g.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); sel(g.dataset.area); } });
    });
    enlazarPlano();
    v.querySelectorAll('.area-f').forEach(b => b.addEventListener('click', () => { sel(b.dataset.area); $('#plano-wrap').scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }));
    const enlazarCarreras = () => {
      $('#panel-carreras').querySelectorAll('[data-beta]').forEach(b => b.addEventListener('click', () => { S.beta = +b.dataset.beta; guardar('vb-beta', S.beta); $('#panel-carreras').innerHTML = htmlCarreras(d); $('#panel-figuras').innerHTML = htmlFiguras(d); enlazarCarreras(); $(`#panel-carreras [data-beta="${S.beta}"]`)?.focus(); }));
      $('#ciudad').addEventListener('change', e => { S.ciudad = e.target.value; $('#panel-carreras').innerHTML = htmlCarreras(d); enlazarCarreras(); });
    };
    enlazarCarreras();
    const pf = $('#panel-fuente');
    pf.addEventListener('click', e => {
      const b = e.target.closest('[data-ft]'); if (b) { S.fuente = b.dataset.ft; pf.innerHTML = htmlFuente(d); }
    });
    // Acordeón: un solo año abierto
    pf.addEventListener('toggle', e => {
      const det = e.target; if (!det.matches?.('details.anio') || !det.open) return;
      S.anio = +det.dataset.anio;
      pf.querySelectorAll('details.anio').forEach(o => { if (o !== det) o.open = false; });
    }, true);
    v.addEventListener('click', e => {
      const b = e.target.closest('[data-accion]'); if (!b) return;
      if (b.dataset.accion === 'test') abrirTest(d);
      if (b.dataset.accion === 'deshacer') deshacer(d.estudiante.id);
      if (b.dataset.accion === 'codigo') window.VB.gestion.codigoIndividual(d.estudiante.id, d.estudiante.nombre);
    });
    $('#comparar')?.addEventListener('change', e => { S.comparar = e.target.checked; $('#plano-wrap').innerHTML = svgPlano(d); enlazarPlano(); });
  }

  /* ───────────── Test CHASIDE (nueva aplicación) ───────────── */
  function abrirTest(d) {
    const M = D.cohorte.modelo;
    if (!M) { alertaPagina('No se pudieron leer los parámetros del modelo. Recarga la página.'); return; }
    const items = M.claves.map(([n]) => n).sort((a, b) => a - b), preg = M.preguntas || null;
    const POR_PAG = preg ? 7 : items.length, paginas = Math.ceil(items.length / POR_PAG);
    const R = {}; let modalidad = 'supervisada', fecha = hoy(), pag = 0;
    const nombre = d.estudiante.nombre || d.estudiante.id;
    const capa = document.createElement('div');
    capa.className = 'capa'; capa.setAttribute('role', 'dialog'); capa.setAttribute('aria-modal', 'true'); capa.setAttribute('aria-label', 'Test CHASIDE');
    capa.innerHTML = `<div class="hoja">
      <div class="hoja-cab"><div><span class="etiqueta">Test CHASIDE</span><h2>${esc(nombre)}</h2></div>
        <button class="flecha" data-c="cerrar" aria-label="Cerrar">×</button></div>
      <div class="hoja-meta">
        <label>Fecha <input type="date" id="t-fecha" value="${fecha}"></label>
        <label>Modalidad <select id="t-modalidad"><option value="supervisada">Aplicada por el DECE</option><option value="autonoma">En línea, sin supervisión</option></select></label>
      </div>
      ${preg ? `<p class="instruccion">Lee cada pregunta y responde <b>Sí</b> o <b>No</b> según lo que sientes hoy. No hay respuestas buenas ni malas. Atajo: teclas S y N.</p>` :
        `<p class="instruccion">Hoja de respuestas: copia lo que marcó el estudiante en el cuadernillo (Sí o No por número). Atajo: teclas S y N.</p>`}
      ${M.preguntas_origen === 'prototipo' ? `<p class="aviso-proto">Preguntas de prototipo con redacción propia. Para aplicar el test real, el administrador debe reemplazar el texto en <code>config/chaside_preguntas.csv</code> del servidor.</p>` : ''}
      <div class="progreso"><i id="t-barra"></i></div>
      <div class="cuerpo-test" id="t-cuerpo"></div>
      <div class="hoja-pie"><span class="sutil" id="t-cuenta"></span>
        <span class="sutil" id="t-aviso"></span>
        ${preg ? '<button class="boton sec" data-c="ant">Anterior</button><button class="boton sec" data-c="sig">Siguiente</button>' : '<button class="boton sec" data-c="cerrar">Cancelar</button>'}
        <button class="boton" data-c="calcular" disabled>Calcular resultados</button></div></div>`;
    document.body.appendChild(capa);
    const cuerpo = $('#t-cuerpo', capa);
    const pintar = () => {
      const lote = items.slice(pag * POR_PAG, (pag + 1) * POR_PAG);
      cuerpo.innerHTML = preg
        ? `<ol class="preguntas">${lote.map(n => `<li data-n="${n}" tabindex="0" class="${R[n] != null ? 'ok' : ''}"><span class="pn mono">${n}</span><span class="pt">${esc(preg[n] || 'Pregunta ' + n)}</span>
            <span class="sn grande"><button type="button" data-v="1" aria-pressed="${R[n] === 1}">Sí</button><button type="button" data-v="0" aria-pressed="${R[n] === 0}">No</button></span></li>`).join('')}</ol>`
        : `<ol class="items">${lote.map(n => `<li data-n="${n}" tabindex="0" class="${R[n] != null ? 'ok' : ''}"><span class="in mono">${n}</span>
            <span class="sn"><button type="button" data-v="1" aria-pressed="${R[n] === 1}">Sí</button><button type="button" data-v="0" aria-pressed="${R[n] === 0}">No</button></span></li>`).join('')}</ol>`;
      if (preg) { $('[data-c="ant"]', capa).disabled = pag === 0; $('[data-c="sig"]', capa).disabled = pag === paginas - 1; }
      cuerpo.scrollTop = 0; actualizar();
      (cuerpo.querySelector('li:not(.ok)') || cuerpo.querySelector('li'))?.focus();
    };
    const actualizar = () => {
      const n = Object.keys(R).length, frac = n / items.length;
      $('#t-barra', capa).style.width = (frac * 100) + '%';
      $('#t-cuenta', capa).textContent = `${n} de ${items.length} respondidas${preg ? ` · página ${pag + 1} de ${paginas}` : ''}`;
      $('#t-aviso', capa).textContent = n && frac < 0.8 ? 'Con menos del 80 % quedará como incompleto.' : n && frac < 0.95 ? 'Quedará como parcial (menos del 95 %).' : '';
      $('[data-c="calcular"]', capa).disabled = n === 0;
    };
    const responder = (li, v) => {
      R[li.dataset.n] = v;
      li.querySelectorAll('[data-v]').forEach(b => b.setAttribute('aria-pressed', String(+b.dataset.v === v)));
      li.classList.add('ok'); actualizar();
      const sig = li.nextElementSibling;
      if (sig) sig.focus();
      else if (preg && pag < paginas - 1 && [...cuerpo.querySelectorAll('li')].every(x => x.classList.contains('ok'))) { pag++; pintar(); }
    };
    capa.addEventListener('click', e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.v != null) responder(b.closest('li'), +b.dataset.v);
      if (b.dataset.c === 'cerrar') cerrar();
      if (b.dataset.c === 'ant' && pag > 0) { pag--; pintar(); }
      if (b.dataset.c === 'sig' && pag < paginas - 1) { pag++; pintar(); }
      if (b.dataset.c === 'calcular') calcular();
    });
    capa.addEventListener('keydown', e => {
      if (e.key === 'Escape') { cerrar(); return; }
      const li = e.target.closest?.('li[data-n]'); if (!li) return;
      if (e.key === 's' || e.key === 'S') responder(li, 1);
      if (e.key === 'n' || e.key === 'N') responder(li, 0);
      if (e.key === 'ArrowDown') { e.preventDefault(); li.nextElementSibling?.focus(); }
      if (e.key === 'ArrowUp') { e.preventDefault(); li.previousElementSibling?.focus(); }
    });
    $('#t-modalidad', capa).addEventListener('change', e => { modalidad = e.target.value; });
    $('#t-fecha', capa).addEventListener('change', e => { fecha = e.target.value || hoy(); });
    pintar();
    function cerrar() { capa.remove(); }
    async function calcular() {
      const id = d.estudiante.id, base = await original(id);
      const btn = $('[data-c="calcular"]', capa); btn.disabled = true; btn.textContent = 'Guardando…';
      try {
        const r = await window.VB.api(`api/estudiantes/${encodeURIComponent(id)}/chaside`, { method: 'POST', body: { respuestas: R, fecha, modalidad } });
        NUEVO.set(id, { meta: { fecha, modalidad }, anterior: NUEVO.get(id)?.resultado || base, resultado: r.resultado });
        D.cache.set(id, r.resultado);
        actualizarIndice(id); cerrar(); S.comparar = true; S.fuente = 'chaside';
        abrirEstudiante(id);
        alertaPagina('CHASIDE guardado: los resultados se recalcularon con la nueva prueba.');
      } catch (err) { btn.disabled = false; btn.textContent = 'Calcular resultados'; alertaPagina(err.message); }
    }
  }
  function actualizarIndice(id) {
    const e = D.cohorte.estudiantes.find(x => x.id === id); if (!e) return;
    const n = NUEVO.get(id)?.resultado || D.cache.get(id); if (!n) return;
    e.top3 = n.carreras.slice(0, 3).map(c => c.nombre);
    e.perfil = Object.fromEntries(n.areas.map(a => [a.codigo, [a.interes.percentil, a.rendimiento.percentil, a.zona.clave]]));
    e.vocacion_consolidada = n.areas.filter(a => a.zona.clave === 'vocacion_consolidada').map(a => a.codigo);
    e.n_alertas = n.alertas.length;
  }
  async function deshacer(id) {
    if (!confirm('¿Anular la última prueba CHASIDE de este estudiante? El resultado volverá a calcularse con la prueba anterior (si existe).')) return;
    try {
      await window.VB.api(`api/estudiantes/${encodeURIComponent(id)}/chaside`, { method: 'DELETE' });
      await recargarDatos(id);
      if (D.cohorte.estudiantes.some(e => e.id === id)) abrirEstudiante(id);
      else { alertaPagina('El estudiante ya no tiene CHASIDE vigente: queda pendiente en Gestión.'); if (S.id) abrirEstudiante(S.id); else cambiarVista('gestion'); }
    } catch (err) { alertaPagina(err.message); }
  }
  function alertaPagina(t) {
    const n = document.createElement('div'); n.className = 'aviso-flot'; n.textContent = t; document.body.appendChild(n);
    setTimeout(() => n.remove(), 6000);
  }

  /* ───────────── Vista cohorte ───────────── */
  function pintarCohorte() {
    const v = $('#vista-cohorte'), c = D.cohorte;
    if (!c || !c.estudiantes.length) { v.innerHTML = `<div class="panel vacio">Aún no hay estudiantes con resultados. Cuando tengan notas y CHASIDE, aquí verás el panorama del curso.</div>`; return; }
    const est = c.estudiantes, n = est.length;
    const tot = { vocacion_consolidada: 0, indeterminado: 0 }; let celdas = 0;
    const porArea = Object.fromEntries(CODIGOS.map(k => [k, Object.fromEntries(ORDEN_Z.map(z => [z, 0]))]));
    est.forEach(e => CODIGOS.forEach(k => { const z = e.perfil?.[k]?.[2]; if (!z) return; porArea[k][z]++; celdas++; if (z in tot) tot[z]++; }));
    const freq = {}; est.forEach(e => e.top3.forEach(t => { freq[t] = (freq[t] || 0) + 1; }));
    const top = Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 12);
    const maxF = top[0]?.[1] || 1;
    const ev = c.evaluacion, pe = ev?.perfil, ra = ev?.ranking;
    const conAl = est.filter(e => e.n_alertas).length;
    const fila = (m, val, sig) => `<tr><td>${m}</td><td class="num">${val}</td><td>${sig}</td></tr>`;
    v.innerHTML = `<div style="display:flex;flex-direction:column;gap:22px">
      <div class="tiles">
        <div class="tile"><span class="etiqueta">Estudiantes</span><span class="v">${n}</span><span class="d">con notas y CHASIDE</span></div>
        <div class="tile"><span class="etiqueta">Áreas consolidadas</span><span class="v">${pct(tot.vocacion_consolidada / celdas)}</span><span class="d">de las ${celdas} áreas evaluadas</span></div>
        <div class="tile"><span class="etiqueta">Áreas indeterminadas</span><span class="v">${pct(tot.indeterminado / celdas)}</span><span class="d">el modelo prefiere decir "falta evidencia"</span></div>
        <div class="tile"><span class="etiqueta">Con alertas</span><span class="v">${conAl}</span><span class="d">estudiantes con evidencia a revisar</span></div>
      </div>
      <div class="panel">
        <div class="panel-cab"><h2>Zona por área en la cohorte</h2><span class="sutil">Proporción de estudiantes en cada zona</span></div>
        ${htmlLeyenda()}
        <div class="apilado" style="margin-top:14px">${CODIGOS.map(k => `<div class="fila-ap"><span>${esc(AREAS[k])}</span>
          <div class="barra-ap">${ORDEN_Z.map(z => { const p = porArea[k][z] / n; return p ? `<i class="${z === 'indeterminado' ? 'hatch' : ''}" style="flex:${p};background:${ZONAS[z].color}" data-tip="${esc(`<b>${AREAS[k]} · ${ZONAS[z].txt}</b><br>${porArea[k][z]} estudiantes (${pct(p)})`)}"></i>` : ''; }).join('')}</div></div>`).join('')}</div>
      </div>
      <div class="rejilla-2">
        <div class="panel">
          <div class="panel-cab"><h2>Carreras que más aparecen en el top 3</h2></div>
          <div class="barras-h">${top.map(([t, f]) => `<div class="bh"><span class="n" title="${esc(t)}">${esc(t)}</span><span class="t" data-tip="${esc(`${t}<br>${f} estudiantes la tienen en su top 3`)}"><i style="width:${f / maxF * 100}%"></i></span><span class="num mono" style="text-align:right">${f}</span></div>`).join('')}</div>
        </div>
        <div class="panel">
          <div class="panel-cab"><h2>Fidelidad del modelo</h2><span class="sutil">${esc(ev?.origen || 'Sin evaluación disponible')}</span></div>
          ${pe ? `<div class="tabla-wrap"><table class="met"><thead><tr><th>Qué se mide</th><th class="num">Valor</th><th>Cómo leerlo</th></tr></thead><tbody>
            ${fila('Recuperación del rendimiento', pe.r_R.toFixed(2), 'Correlación con el valor real (1 = perfecto)')}
            ${fila('Recuperación del interés', pe.r_I.toFixed(2), 'Depende solo del CHASIDE')}
            ${fila('Cobertura del rango 90 %', pct((pe.cobertura90_I + pe.cobertura90_R) / 2), 'Ideal: 90 %. El modelo es honesto con su incertidumbre')}
            ${fila('Zona correcta', pct(pe.exactitud_zona), 'Entre las áreas con zona asignada')}
            ${fila('Área de mayor interés en su top 3', pct(pe.top1_en_top3), '')}
            ${ra ? fila('Carrera #1 real dentro del top 5', pct(ra['#1 verdadera en el top 5']), 'Ranking de carreras') : ''}
          </tbody></table></div>` : '<p class="sutil">Con datos reales no hay "verdad" para comparar; la evaluación se hace con la simulación del Módulo 3B.</p>'}
        </div>
      </div></div>`;
  }

  /* ───────────── Vista gestión (gestion.js) ───────────── */
  function pintarGestion() { window.VB.gestion.pintar($('#vista-gestion'), { recargar: recargarDatos, abrir: id => { elegir(id); } }); }
  async function recargarDatos(idPreferido) {
    D.cache.clear(); NUEVO.clear();
    const ok = await iniciarDatos();
    if (!ok) return;
    D.cohorte.estudiantes.sort((x, y) => (x.nombre || x.id).localeCompare(y.nombre || y.id, 'es'));
    pintarEstado();
    if (idPreferido && D.cohorte.estudiantes.some(e => e.id === idPreferido)) S.id = idPreferido;
    else if (!D.cohorte.estudiantes.some(e => e.id === S.id)) S.id = D.cohorte.estudiantes[0]?.id || null;
    pintarSelector();
  }
  window.VB.recargarDatos = recargarDatos;

  /* ───────────── Arranque ───────────── */
  function arrancar() {
    D.cohorte.estudiantes.sort((x, y) => (x.nombre || x.id).localeCompare(y.nombre || y.id, 'es'));
    pintarEstado();
    const primero = D.cohorte.estudiantes[0];
    if (primero) { S.area = null; S.id = primero.id; }
    cambiarVista('estudiante');
  }
  window.VB.iniciar().then(async () => {
    const ok = await iniciarDatos();
    if (ok && D.cohorte.estudiantes.length) arrancar();
    else { pintarEstado(); cambiarVista('gestion'); }
  });
})();