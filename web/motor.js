/* Motor del modelo en el navegador.
   Aplica las MISMAS fórmulas del Módulo 5 (posterior gaussiano exacto) y del Módulo 7 (afinidad + Monte Carlo)
   con los parámetros que el Colab ya aprendió (cohorte.json → modelo). No entrena nada: solo recalcula
   a un estudiante cuando se registra una nueva aplicación del CHASIDE. */
(() => {
  'use strict';
  const CODIGOS = ['C', 'H', 'A', 'S', 'I', 'D', 'E'];

  // Φ con precisión ~1e-7 (Abramowitz–Stegun 7.1.26 sobre erf)
  function phi(z) {
    const t = 1 / (1 + 0.3275911 * Math.abs(z) / Math.SQRT2);
    const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-z * z / 2);
    return 0.5 * (1 + (z >= 0 ? y : -y));
  }

  // P(X > h, Y > k) para normal bivariada estándar con correlación r (algoritmo de Genz, bvnu)
  function bvnu(h, k, r) {
    const tp = 2 * Math.PI;
    let w, x;
    if (Math.abs(r) < 0.3) { w = [0.1713244923791705, 0.3607615730481384, 0.4679139345726904]; x = [0.9324695142031522, 0.6612093864662647, 0.2386191860831970]; }
    else if (Math.abs(r) < 0.75) { w = [0.04717533638651177, 0.1069393259953183, 0.1600783285433464, 0.2031674267230659, 0.2334925365383547, 0.2491470458134029]; x = [0.9815606342467191, 0.9041172563704750, 0.7699026741943050, 0.5873179542866171, 0.3678314989981802, 0.1252334085114692]; }
    else { w = [0.01761400713915212, 0.04060142980038694, 0.06267204833410906, 0.08327674157670475, 0.1019301198172404, 0.1181945319615184, 0.1316886384491766, 0.1420961093183821, 0.1491729864726037, 0.1527533871307259]; x = [0.9931285991850949, 0.9639719272779138, 0.9122344282513259, 0.8391169718222188, 0.7463319064601508, 0.6360536807265150, 0.5108670019508271, 0.3737060887154196, 0.2277858511416451, 0.07652652113349733]; }
    let hk = h * k, bvn = 0;
    if (Math.abs(r) < 0.925) {
      const hs = (h * h + k * k) / 2, asr = Math.asin(r) / 2;
      for (let i = 0; i < w.length; i++) {
        let sn = Math.sin(asr * (1 - x[i])); bvn += w[i] * Math.exp((sn * hk - hs) / (1 - sn * sn));
        sn = Math.sin(asr * (1 + x[i])); bvn += w[i] * Math.exp((sn * hk - hs) / (1 - sn * sn));
      }
      bvn = bvn * asr / tp + phi(-h) * phi(-k);
    } else {
      if (r < 0) { k = -k; hk = -hk; }
      if (Math.abs(r) < 1) {
        const as = (1 - r) * (1 + r); let a = Math.sqrt(as);
        const bs = (h - k) ** 2, c = (4 - hk) / 8, d = (12 - hk) / 16;
        bvn = a * Math.exp(-(bs / as + hk) / 2) * (1 - c * (bs - as) * (1 - d * bs / 5) / 3 + c * d * as * as / 5);
        if (hk > -160) { const b = Math.sqrt(bs); bvn -= Math.exp(-hk / 2) * Math.sqrt(tp) * phi(-b / a) * b * (1 - c * bs * (1 - d * bs / 5) / 3); }
        a /= 2;
        for (let i = 0; i < w.length; i++) {
          for (const sg of [-1, 1]) {
            const xs = (a * (sg * x[i] + 1)) ** 2, rs = Math.sqrt(1 - xs), asr = -(bs / xs + hk) / 2;
            if (asr > -100) bvn += a * w[i] * Math.exp(asr) * (Math.exp(-hk * xs / (2 * (1 + rs) ** 2)) / rs - (1 + c * xs * (1 + d * xs)));
          }
        }
        bvn = -bvn / tp;
      }
      if (r > 0) bvn += phi(-Math.max(h, k));
      else if (h >= k) bvn = -bvn;
      else bvn = (h < 0 ? phi(k) - phi(h) : phi(-h) - phi(-k)) - bvn;
    }
    return Math.max(0, Math.min(1, bvn));
  }

  /* ── Módulo 4: respuestas → evidencia por área ── */
  function evidenciaChaside(M, respuestas, meta) {
    // respuestas: {numero_item: 1 | 0 | null}
    const porArea = {};
    CODIGOS.forEach(a => { porArea[a] = { interes: [0, 0], aptitud: [0, 0] }; });
    let resp = 0, si = 0;
    M.claves.forEach(([item, a, t]) => {
      const v = respuestas[item];
      if (v === 0 || v === 1) { porArea[a][t][1]++; porArea[a][t][0] += v; resp++; si += v; }
    });
    const punt = {}, z = {};
    CODIGOS.forEach(a => {
      punt[a] = {};
      ['interes', 'aptitud'].forEach(t => {
        const [s, n] = porArea[a][t], [m, sd] = M.normas_chaside[a][t];
        punt[a][t] = n ? s / n : null;
        z[a] = z[a] || {};
        z[a][t] = n ? (s / n - m) / sd : null;
      });
    });
    const total = M.claves.length, comp = resp / total;
    const ints = CODIGOS.map(a => punt[a].interes).filter(v => v != null);
    const media = ints.reduce((x, y) => x + y, 0) / (ints.length || 1);
    const disp = Math.sqrt(ints.reduce((x, y) => x + (y - media) ** 2, 0) / Math.max(1, ints.length - 1));
    const propSi = resp ? si / resp : 0;
    const crit = {
      antiguedad: 'menos_1_anio',
      modalidad: meta.modalidad || 'supervisada',
      completitud: comp >= 0.95 ? 'completa' : comp >= 0.8 ? 'parcial' : 'incompleta',
      consistencia: (disp < M.consistencia.disp_p05 && propSi >= M.consistencia.rango_si[0] && propSi <= M.consistencia.rango_si[1]) ? 'alerta' : 'sin_alertas',
      completitud_pct: Math.round(comp * 100)
    };
    const conteos = {};
    CODIGOS.forEach(a => { conteos[a] = { interes: porArea[a].interes.slice(), aptitud: porArea[a].aptitud.slice() }; });
    return { z, crit, origen: { respondidas: resp, total, si, areas: conteos } };
  }

  /* ── Módulo 5: posterior gaussiano exacto por área ── */
  function s2Fuente(M, alfa, crit) {
    let f = 1;
    ['antiguedad', 'modalidad', 'completitud', 'consistencia'].forEach(c => { if (crit[c]) f *= M.rubrica[c][crit[c]]; });
    return (1 - alfa) / alfa * f;   // validación publicada y equivalencia directa: factor 1
  }
  function posteriorArea(M, a, ev, crit) {
    const p = M.param[a], rho = p.rho;
    const det = 1 - rho * rho;
    let L = [[1 / det, -rho / det], [-rho / det, 1 / det]], b = [0, 0];
    const obs = [];
    if (ev.z_int != null) {
      const al = M.alfa_chaside[a].interes;
      obs.push(['chaside_interes', [1, 0], ev.z_int / Math.sqrt(al), s2Fuente(M, al, crit)]);
    }
    if (ev.z_notas != null) {
      const an = p.alfa_notas, fw = ev.W_efectiva != null ? Math.min(3, Math.max(0.5, p.W_med / ev.W_efectiva)) : 1;
      obs.push(['notas', [0, 1], ev.z_notas / Math.sqrt(an), (1 - an) / an * fw]);
    }
    if (ev.z_apt != null) {
      const lam = p.lam_apt;
      obs.push(['autopercepcion', [0, 1], ev.z_apt / lam, s2Fuente(M, lam * lam, crit)]);
    }
    obs.forEach(([, H, y, s2]) => {
      L = [[L[0][0] + H[0] * H[0] / s2, L[0][1] + H[0] * H[1] / s2], [L[1][0] + H[1] * H[0] / s2, L[1][1] + H[1] * H[1] / s2]];
      b = [b[0] + H[0] * y / s2, b[1] + H[1] * y / s2];
    });
    const d = L[0][0] * L[1][1] - L[0][1] * L[1][0];
    const S = [[L[1][1] / d, -L[0][1] / d], [-L[1][0] / d, L[0][0] / d]];
    const mu = [S[0][0] * b[0] + S[0][1] * b[1], S[1][0] * b[0] + S[1][1] * b[1]];
    const aportes = {};
    obs.forEach(([n, H, y, s2]) => { const v = [H[0] * y / s2, H[1] * y / s2]; aportes[n] = [S[0][0] * v[0] + S[0][1] * v[1], S[1][0] * v[0] + S[1][1] * v[1]]; });
    return { mu, S, aportes };
  }
  function zona(M, mu, S) {
    const sI = Math.sqrt(S[0][0]), sR = Math.sqrt(S[1][1]);
    const pI = phi(mu[0] / sI), pR = phi(mu[1] / sR);
    const pAA = bvnu(-mu[0] / sI, -mu[1] / sR, S[0][1] / (sI * sR));
    const probs = { vocacion_consolidada: pAA, interes_a_fortalecer: pI - pAA, talento_no_explorado: pR - pAA, no_prioritaria: 1 - pI - pR + pAA };
    const mejor = Object.keys(probs).reduce((x, y) => probs[y] > probs[x] ? y : x);
    return { clave: probs[mejor] >= M.umbral_certeza ? mejor : 'indeterminado', certeza: probs[mejor], probabilidades: probs };
  }
  const TXT_ZONA = { vocacion_consolidada: 'Vocación consolidada', interes_a_fortalecer: 'Interés a fortalecer', talento_no_explorado: 'Talento no explorado', no_prioritaria: 'Área no prioritaria', indeterminado: 'Indeterminado: falta evidencia' };
  const eje = (mu, sd) => ({ percentil: Math.round(phi(mu) * 100), rango90: [Math.round(phi(mu - 1.645 * sd) * 100), Math.round(phi(mu + 1.645 * sd) * 100)], z: mu, sd });

  /* ── Módulo 7: afinidad equilibrada + Monte Carlo ── */
  function afinidadCruda(C, gamma, s) {
    return C.map(c => {
      const w = CODIGOS.map(k => Math.pow((c.perfil[k] - 1) / 4, gamma)), sw = w.reduce((x, y) => x + y, 0) || 1;
      return 100 * CODIGOS.reduce((acc, k, i) => acc + w[i] / sw * s[i], 0);
    });
  }
  function afinidad(C, gamma, normas, beta, MU) {
    const s = MU.map(([i, r]) => beta * phi(i) + (1 - beta) * phi(r));
    const x = afinidadCruda(C, gamma, s), n = normas[beta.toFixed(1)];
    return x.map((v, j) => n ? 100 * phi((v - n.media[j]) / n.sd[j]) : v);
  }
  function rng(semilla) {   // mulberry32 + Box–Muller
    let a = semilla >>> 0;
    const u = () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ t >>> 15, t | 1); t ^= t + Math.imul(t ^ t >>> 7, t | 61); return ((t ^ t >>> 14) >>> 0) / 4294967296; };
    return () => Math.sqrt(-2 * Math.log(u() + 1e-12)) * Math.cos(2 * Math.PI * u());
  }
  function monteCarlo(C, gamma, normas, beta, MU, SIG, n, k) {
    const g = rng(20261004), cuenta = new Array(C.length).fill(0), muestras = C.map(() => []);
    const Ls = SIG.map(S => { const l00 = Math.sqrt(S[0][0]), l10 = S[1][0] / l00; return [l00, l10, Math.sqrt(Math.max(1e-12, S[1][1] - l10 * l10))]; });
    for (let t = 0; t < n; t++) {
      const draw = MU.map(([m0, m1], a) => { const e0 = g(), e1 = g(), L = Ls[a]; return [m0 + L[0] * e0, m1 + L[1] * e0 + L[2] * e1]; });
      const A = afinidad(C, gamma, normas, beta, draw);
      const top = A.map((v, j) => [v, j]).sort((x, y) => y[0] - x[0]).slice(0, k);
      top.forEach(([, j]) => cuenta[j]++);
      A.forEach((v, j) => muestras[j].push(v));
    }
    const q = (arr, p) => { const s = arr.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; };
    return { p: cuenta.map(c => c / n), lo: muestras.map(m => q(m, 0.05)), hi: muestras.map(m => q(m, 0.95)) };
  }

  /* ── Recalcular un estudiante completo con un CHASIDE nuevo ── */
  function recalcular(M, carrerasCat, est, respuestas, meta) {
    const E = evidenciaChaside(M, respuestas, meta);
    const N = JSON.parse(JSON.stringify(est));
    const crit = E.crit;
    N.areas.forEach(ar => {
      const a = ar.codigo, ev0 = ar.evidencia || {};
      const ev = { z_int: E.z[a].interes, z_apt: E.z[a].aptitud, z_notas: ev0.z_notas, W_efectiva: ev0.W_efectiva };
      const { mu, S, aportes } = posteriorArea(M, a, ev, crit);
      const zn = zona(M, mu, S);
      ar.interes = eje(mu[0], Math.sqrt(S[0][0])); ar.rendimiento = eje(mu[1], Math.sqrt(S[1][1]));
      ar.zona = { clave: zn.clave, texto: TXT_ZONA[zn.clave], certeza: zn.certeza, probabilidades: zn.probabilidades };
      ar.aportes = { interes: { chaside_interes: aportes.chaside_interes ? aportes.chaside_interes[0] : null },
                     rendimiento: { notas: aportes.notas ? aportes.notas[1] : null, autopercepcion: aportes.autopercepcion ? aportes.autopercepcion[1] : null } };
      if (ev.z_apt != null && ev.z_notas != null) {
        const r = M.param[a].r_apt_notas, br = (ev.z_apt - r * ev.z_notas) / Math.sqrt(1 - r * r);
        const k = br > 1 ? 'por_encima' : br < -1 ? 'por_debajo' : 'coherente';
        ar.autopercepcion = { clave: k, texto: { por_encima: 'se percibe por ENCIMA de sus notas', por_debajo: 'se percibe por DEBAJO de sus notas', coherente: 'coherente con sus notas' }[k] };
      }
      ar.evidencia = ev; ar._S = S;
    });
    // Carreras
    const MU = N.areas.map(a => [a.interes.z, a.rendimiento.z]), SIG = N.areas.map(a => a._S);
    const C = carrerasCat.lista, A = afinidad(C, carrerasCat.gamma, carrerasCat.normas, M.beta, MU);
    const mc = monteCarlo(C, carrerasCat.gamma, carrerasCat.normas, M.beta, MU, SIG, M.n_sim, M.top_k);
    const orden = A.map((v, j) => [v, j]).sort((x, y) => y[0] - x[0]).slice(0, 10);
    N.carreras = orden.map(([v, j]) => ({ id: C[j].id, nombre: C[j].nombre, afinidad: Math.round(v * 10) / 10, rango90: [Math.round(mc.lo[j] * 10) / 10, Math.round(mc.hi[j] * 10) / 10],
      p_top5: Math.round(mc.p[j] * 100) / 100, universidad: C[j].universidad, ciudad: C[j].ciudad, razon: razon(N, C[j], carrerasCat.gamma, M.beta) }));
    N.areas.forEach(a => { delete a._S; });
    // Fuentes, origen y alertas
    N.estudiante.fuentes.chaside = { fecha: meta.fecha, modalidad: crit.modalidad, completitud: crit.completitud, consistencia: crit.consistencia };
    N.origen = { ...(N.origen || {}), chaside: E.origen };
    const al = (N.alertas || []).filter(x => !['consistencia', 'completitud', 'antiguedad', 'modalidad', 'indeterminado'].includes(x.tipo));
    if (crit.consistencia === 'alerta') al.unshift({ tipo: 'consistencia', texto: 'CHASIDE con respuestas poco diferenciadas: confirmar intereses en entrevista.' });
    if (crit.completitud !== 'completa') al.unshift({ tipo: 'completitud', texto: `CHASIDE ${crit.completitud} (${crit.completitud_pct} % respondido).` });
    if (crit.modalidad === 'autonoma') al.push({ tipo: 'modalidad', texto: 'CHASIDE respondido sin supervisión: su confiabilidad se ajustó a la baja.' });
    const nInd = N.areas.filter(a => a.zona.clave === 'indeterminado').length;
    if (nInd >= 3) al.push({ tipo: 'indeterminado', texto: `${nInd} de 7 áreas sin zona clara: falta evidencia (sumar entrevista u otra prueba).` });
    N.alertas = al;
    return N;
  }
  function razon(N, c, gamma, beta) {
    const ap = N.areas.map(a => ({ a, v: Math.pow((c.perfil[a.codigo] - 1) / 4, gamma) * (beta * phi(a.interes.z) + (1 - beta) * phi(a.rendimiento.z)) })).sort((x, y) => y.v - x.v);
    const a = ap[0].a, pI = a.interes.percentil, pR = a.rendimiento.percentil;
    let t = `${a.nombre} (pesa ${c.perfil[a.codigo]}/5 en la carrera): interés P${pI}, rendimiento P${pR}`;
    const mats = (a.materias_clave || []).filter(m => m.nota != null).map(m => `${m.materia} ${m.nota.toFixed(1)}`);
    if (mats.length) t += ' · materias: ' + mats.join(', ');
    if (pI >= 60 && pR < 40) t += ' · interés alto, conviene reforzar el rendimiento';
    else if (pR >= 60 && pI < 40) t += ' · rinde bien aunque declara poco interés';
    if (ap[1].v >= 0.5 * ap[0].v) t += ` · también suma ${ap[1].a.nombre}`;
    return t;
  }

  window.MOTOR = { phi, bvnu, evidenciaChaside, posteriorArea, zona, recalcular, afinidad };
})();
