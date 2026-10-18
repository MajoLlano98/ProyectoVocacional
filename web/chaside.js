/* Test CHASIDE para estudiantes: código de acceso → consentimiento → 98 preguntas → envío.
   Las respuestas en curso se guardan solo en este dispositivo (por si se cierra la página) y se borran al enviar. */
(() => {
  'use strict';
  const app = document.getElementById('app');
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const POR_PAG = 7;
  const E = { codigo: '', datos: null, R: {}, pag: 0 };
  const clave = () => 'vb-test-' + E.codigo;
  const guardarBorrador = () => { try { localStorage.setItem(clave(), JSON.stringify({ R: E.R, pag: E.pag })); } catch (_) {} };
  const leerBorrador = () => { try { return JSON.parse(localStorage.getItem(clave())); } catch (_) { return null; } };
  const borrarBorrador = () => { try { localStorage.removeItem(clave()); } catch (_) {} };

  async function api(url, body) {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Vocacional': '1' }, body: JSON.stringify(body) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.error || 'No se pudo conectar. Revisa tu internet e inténtalo otra vez.');
    return d;
  }
  const marca = `<svg width="34" height="34" viewBox="0 0 26 26" aria-hidden="true"><rect x="1" y="1" width="24" height="24" rx="6" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.5"/><line x1="13" y1="4" x2="13" y2="22" stroke="currentColor" stroke-width="1.2" opacity="0.5"/><line x1="4" y1="13" x2="22" y2="13" stroke="currentColor" stroke-width="1.2" opacity="0.5"/><circle cx="18" cy="8" r="3" fill="var(--z-vc)"/><circle cx="8.5" cy="17.5" r="2.4" fill="var(--z-tn)"/></svg>`;

  function pantallaCodigo(msg) {
    app.innerHTML = `<div class="marca-sola">${marca}<h1>Test vocacional CHASIDE</h1>
        <p class="sutil">Descubre qué áreas te atraen más. Toma unos 10 minutos.</p></div>
      <form class="panel g-form" id="f">
        <label>Tu código de acceso <input name="codigo" id="codigo" inputmode="text" autocomplete="off" autocapitalize="characters"
          placeholder="ABCD-1234" maxlength="12" required class="codigo-in"></label>
        <p class="sutil">Te lo entregó tu orientador(a). Sirve una sola vez.</p>
        <p class="g-error" id="err" role="alert" ${msg ? '' : 'hidden'}>${esc(msg || '')}</p>
        <button class="boton grande-b" id="b">Continuar</button></form>`;
    const inp = document.getElementById('codigo');
    inp.focus();
    inp.addEventListener('input', () => {
      let v = inp.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8);
      if (v.length > 4) v = v.slice(0, 4) + '-' + v.slice(4);
      inp.value = v;
    });
    document.getElementById('f').addEventListener('submit', async e => {
      e.preventDefault();
      const b = document.getElementById('b'); b.disabled = true; b.textContent = 'Verificando…';
      try {
        E.datos = await api('/api/chaside/abrir', { codigo: inp.value });
        E.codigo = inp.value;
        const bor = leerBorrador();
        if (bor) { E.R = bor.R || {}; E.pag = bor.pag || 0; }
        pantallaInicio();
      } catch (err) { pantallaCodigo(err.message); }
    });
  }

  function pantallaInicio() {
    const n = Object.keys(E.R).length;
    app.innerHTML = `<div class="marca-sola">${marca}<h1>Hola, ${esc(E.datos.nombre)}</h1></div>
      <div class="panel test-intro">
        <p>Vas a leer <b>98 frases</b> sobre actividades y habilidades. Responde <b>Sí</b> o <b>No</b> según lo que sientes hoy.
        No hay respuestas buenas ni malas: lo importante es que seas sincero(a).</p>
        <ul class="g-lista">
          <li>Tus respuestas las revisa el DECE de tu colegio para acompañarte en tu orientación vocacional, junto con tus notas.</li>
          <li>No se comparten con nadie más. El resultado es una guía: no decide por ti.</li>
          <li>Si se cierra la página, tu avance queda guardado en este dispositivo.</li>
        </ul>
        ${E.datos.modalidad === 'supervisada' ? '<p class="sutil">Este test es para responderlo en el aula.</p>' : ''}
        <label class="check"><input type="checkbox" id="ok"> Entiendo y quiero responder el test</label>
        <button class="boton grande-b" id="b" disabled>${n ? `Continuar (llevas ${n} de 98)` : 'Empezar'}</button></div>`;
    const ok = document.getElementById('ok'), b = document.getElementById('b');
    ok.addEventListener('change', () => { b.disabled = !ok.checked; });
    b.addEventListener('click', () => pantallaPreguntas());
  }

  function pantallaPreguntas() {
    const P = E.datos.preguntas, total = P.length, pags = Math.ceil(total / POR_PAG);
    const lote = P.slice(E.pag * POR_PAG, (E.pag + 1) * POR_PAG);
    const n = Object.keys(E.R).length;
    app.innerHTML = `<div class="test-cab"><span class="sutil">Página ${E.pag + 1} de ${pags}</span><span class="sutil">${n} de ${total} respondidas</span></div>
      <div class="progreso"><i style="width:${n / total * 100}%"></i></div>
      <ol class="preguntas test-preg">${lote.map(p => `<li data-n="${p.item}" class="${E.R[p.item] != null ? 'ok' : ''}">
          <span class="pt">${esc(p.texto)}</span>
          <span class="sn grande"><button type="button" data-v="1" aria-pressed="${E.R[p.item] === 1}">Sí</button><button type="button" data-v="0" aria-pressed="${E.R[p.item] === 0}">No</button></span></li>`).join('')}</ol>
      <div class="test-pie"><button class="boton sec" id="ant" ${E.pag === 0 ? 'disabled' : ''}>Anterior</button>
        ${E.pag < pags - 1 ? '<button class="boton" id="sig">Siguiente</button>' : '<button class="boton" id="fin">Revisar y enviar</button>'}</div>`;
    window.scrollTo(0, 0);
    app.querySelector('.preguntas').addEventListener('click', e => {
      const b = e.target.closest('[data-v]'); if (!b) return;
      const li = b.closest('li'); E.R[li.dataset.n] = +b.dataset.v;
      li.classList.add('ok'); li.querySelectorAll('[data-v]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
      guardarBorrador();
      const m = Object.keys(E.R).length;
      app.querySelector('.progreso i').style.width = (m / total * 100) + '%';
      app.querySelector('.test-cab span:last-child').textContent = `${m} de ${total} respondidas`;
      const sig = li.nextElementSibling;
      if (sig && E.R[sig.dataset.n] == null) sig.scrollIntoView({ block: 'center', behavior: 'smooth' });
    });
    document.getElementById('ant')?.addEventListener('click', () => { E.pag--; guardarBorrador(); pantallaPreguntas(); });
    document.getElementById('sig')?.addEventListener('click', () => { E.pag++; guardarBorrador(); pantallaPreguntas(); });
    document.getElementById('fin')?.addEventListener('click', pantallaRevision);
  }

  function pantallaRevision(msg) {
    const P = E.datos.preguntas, faltan = P.filter(p => E.R[p.item] == null);
    app.innerHTML = `<div class="marca-sola"><h1>${faltan.length ? 'Casi listo' : '¡Terminaste!'}</h1></div>
      <div class="panel test-intro">
        ${faltan.length ? `<p>Te faltan <b>${faltan.length}</b> pregunta${faltan.length > 1 ? 's' : ''}. Si las respondes, tu resultado será más preciso.</p>
          <button class="boton sec" id="ir">Ir a la primera sin responder</button>` : '<p>Respondiste las 98 preguntas. Revisa que todo esté bien y envía tus respuestas.</p>'}
        <p class="g-error" role="alert" ${typeof msg === 'string' ? '' : 'hidden'}>${esc(typeof msg === 'string' ? msg : '')}</p>
        <button class="boton grande-b" id="enviar">Enviar mis respuestas</button>
        <button class="boton sec" id="volver">Volver a las preguntas</button></div>`;
    document.getElementById('ir')?.addEventListener('click', () => {
      E.pag = Math.floor(P.findIndex(p => E.R[p.item] == null) / POR_PAG); pantallaPreguntas();
    });
    document.getElementById('volver').addEventListener('click', pantallaPreguntas);
    document.getElementById('enviar').addEventListener('click', async e => {
      if (faltan.length > P.length * 0.2 && !confirm(`Te faltan ${faltan.length} preguntas. ¿Enviar de todos modos?`)) return;
      e.target.disabled = true; e.target.textContent = 'Enviando…';
      try {
        await api('/api/chaside/enviar', { codigo: E.codigo, respuestas: E.R });
        borrarBorrador();
        app.innerHTML = `<div class="marca-sola">${marca}<h1>¡Gracias, ${esc(E.datos.nombre)}!</h1></div>
          <div class="panel test-intro"><p>Tus respuestas se enviaron correctamente.</p>
          <p>Tu orientador(a) revisará los resultados contigo: verán juntos qué áreas te atraen, en cuáles te va bien y qué carreras podrían interesarte.</p>
          <p class="sutil">Ya puedes cerrar esta página.</p></div>`;
      } catch (err) { pantallaRevision(err.message); }
    });
  }

  pantallaCodigo();
})();
