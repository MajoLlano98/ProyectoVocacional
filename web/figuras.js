/* Figuras de profesión — dibujo SVG propio de la interfaz original del proyecto (mismo código), con un vestuario agregado para Seguridad y defensa. */
(() => {
  const SKIN = '#F6C92C', SKIN_DARK = '#D9A900', FACE = '#1F2330';
  const OUTFITS = [
    { id:'seguridad', re:/militar|ej[eé]rcito|naval|marina|policial|seguridad ciudadana|criminal[ií]stic|riesgos/, torso:'#4B5A3A', legs:'#3A4630', jacket:true, hat:'cap', prop:'shield', label:'Seguridad y defensa' },
    { id:'salud',      re:/medicina|enfermer|odontolog|obstetric|fisioterap|radiolog|terapia|fonoaudiolog|nutrici/, torso:'#FFFFFF', legs:'#4DA3D6', coat:true, prop:'steth', label:'Salud' },
    { id:'vet',        re:/veterinari|zootecn/, torso:'#3FA37A', legs:'#2E7D5B', prop:'steth', label:'Veterinaria' },
    { id:'ciencia',    re:/bioqu|qu[ií]mica|biotecnolog|biolog|f[ií]sica|matem[aá]tic|farmacia|alimentos/, torso:'#FFFFFF', legs:'#2F4A7A', coat:true, hat:'goggles', prop:'flask', label:'Ciencia' },
    { id:'obra',       re:/civil|minas|geolog|petr[oó]leo|arquitect/, torso:'#F28C28', legs:'#2F4A7A', vest:true, hat:'hardhat', prop:'plan', label:'Construcción' },
    { id:'tecnico',    re:/mec[aá]nic|mecatr[oó]nic|el[eé]ctric|electr[oó]nic|automotriz|electromec|industrial|producci/, torso:'#2F6DB5', legs:'#2F6DB5', overall:true, hat:'hardhatWhite', prop:'wrench', label:'Técnica' },
    { id:'tech',       re:/computaci|software|datos|ciberseg|telecom|redes|animaci|videojuego/, torso:'#2B3A55', legs:'#3E5C8A', hoodie:true, hat:'headset', prop:'laptop', label:'Tecnología' },
    { id:'ley',        re:/derecho|relaciones internacionales|pol[ií]tic|p[uú]blica/, torso:'#1E2433', legs:'#1E2433', suit:true, tie:'#2A78D6', prop:'briefcase', label:'Leyes' },
    { id:'negocio',    re:/administraci|econom|finanz|contab|auditor|marketing|comercio|gesti[oó]n|talento|log[ií]stic/, torso:'#23355C', legs:'#23355C', suit:true, tie:'#D23F3F', prop:'chart', label:'Negocios' },
    { id:'docente',    re:/educaci|pedagog|idiomas/, torso:'#8E3B4E', legs:'#3B4252', cardigan:true, prop:'book', label:'Educación' },
    { id:'social',     re:/psicolog|trabajo social|sociolog|antropolog|filosof/, torso:'#6A55B5', legs:'#3B4252', prop:'notebook', label:'Social' },
    { id:'medios',     re:/comunicaci|periodis|cine|audiovisual/, torso:'#C0392B', legs:'#2B3A55', jacket:true, prop:'mic', label:'Medios' },
    { id:'arte',       re:/arte|dise[nñ]o|moda|interiores|teatro|m[uú]sic/, torso:'#F2F2F2', legs:'#2B3A55', stripes:true, hat:'beret', prop:'palette', label:'Arte' },
    { id:'chef',       re:/gastronom/, torso:'#FFFFFF', legs:'#5B6576', chef:true, hat:'chef', prop:'spoon', label:'Gastronomía' },
    { id:'turismo',    re:/turis|hotel/, torso:'#1F3B73', legs:'#1F3B73', suit:true, tie:'#EDA100', hat:'cap', prop:'suitcase', label:'Turismo' },
    { id:'campo',      re:/agronom|agroindustr|ambiental/, torso:'#5E8C31', legs:'#6B4F2A', hat:'straw', prop:'sprout', label:'Campo y ambiente' },
  ];
  const OUTFIT_DEFAULT = { id:'general', torso:'#2A78D6', legs:'#2F4A7A', prop:null, label:'Profesional' };
  function outfitFor(careerName){
    const n = careerName.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
    return OUTFITS.find(o=>o.re.test(n) || o.re.test(careerName.toLowerCase())) || OUTFIT_DEFAULT;
  }

  function figureSVG(o, gender){
    const P = [];
    const ln = 'stroke="rgba(15,23,42,.35)" stroke-width="1"';
    // pelo largo detrás de la cabeza (mujer)
    if (gender==='F') P.push(`<path d="M34 58 Q34 32 60 31 Q86 32 86 58 L88 104 Q80 108 74 102 L76 64 L44 64 L46 102 Q40 108 32 104 Z" fill="#7A3E1D"/>`);
    // piernas y cadera
    P.push(`<rect x="37" y="146" width="46" height="12" rx="2" fill="${o.legs}" ${ln}/>`);
    P.push(`<rect x="37" y="156" width="22" height="40" rx="3" fill="${o.legs}" ${ln}/>`);
    P.push(`<rect x="61" y="156" width="22" height="40" rx="3" fill="${o.legs}" ${ln}/>`);
    P.push(`<rect x="37" y="190" width="22" height="6" rx="2" fill="rgba(0,0,0,.18)"/><rect x="61" y="190" width="22" height="6" rx="2" fill="rgba(0,0,0,.18)"/>`);
    // brazos (mangas) y manos
    const sleeve = o.vest ? '#8A93A3' : (o.overall ? '#E9EEF5' : o.torso);
    P.push(`<path d="M42 96 L30 100 L22 134 L34 137 L41 112 Z" fill="${sleeve}" ${ln}/>`);
    P.push(`<path d="M78 96 L90 100 L98 134 L86 137 L79 112 Z" fill="${sleeve}" ${ln}/>`);
    P.push(`<circle cx="27" cy="141" r="7" fill="${SKIN}" stroke="${SKIN_DARK}" stroke-width="1.2"/><circle cx="93" cy="141" r="7" fill="${SKIN}" stroke="${SKIN_DARK}" stroke-width="1.2"/>`);
    // torso
    P.push(`<path d="M43 92 L77 92 L84 147 L36 147 Z" fill="${o.torso}" ${ln}/>`);
    if (o.overall){ P.push(`<path d="M43 92 L77 92 L84 147 L36 147 Z" fill="#E9EEF5"/><path d="M47 108 L73 108 L80 147 L40 147 Z" fill="${o.torso}"/><rect x="47" y="92" width="5" height="18" fill="${o.torso}"/><rect x="68" y="92" width="5" height="18" fill="${o.torso}"/><rect x="54" y="116" width="12" height="9" rx="1" fill="rgba(0,0,0,.15)"/>`); }
    if (o.vest){ P.push(`<path d="M43 92 L77 92 L84 147 L36 147 Z" fill="#8A93A3"/><path d="M44 92 L56 92 L55 147 L37 147 Z" fill="${o.torso}"/><path d="M64 92 L76 92 L83 147 L65 147 Z" fill="${o.torso}"/><rect x="38" y="124" width="17" height="4" fill="#FFE14D"/><rect x="65" y="124" width="17" height="4" fill="#FFE14D"/>`); }
    if (o.suit){ P.push(`<path d="M52 92 L60 112 L68 92 Z" fill="#FFFFFF"/><path d="M58 96 L62 96 L63 116 L60 121 L57 116 Z" fill="${o.tie}"/><path d="M52 92 L60 118 L48 104 Z" fill="rgba(255,255,255,.12)"/><path d="M68 92 L60 118 L72 104 Z" fill="rgba(255,255,255,.12)"/>`); }
    if (o.coat){ P.push(`<path d="M53 92 L60 106 L67 92 Z" fill="#9CC3E8"/><line x1="60" y1="106" x2="60" y2="147" stroke="rgba(15,23,42,.25)" stroke-width="1.2"/><rect x="66" y="112" width="9" height="7" rx="1" fill="none" stroke="rgba(15,23,42,.25)"/>`); }
    if (o.cardigan){ P.push(`<path d="M52 92 L60 108 L68 92 L65 147 L55 147 Z" fill="#F4EFE6"/><circle cx="57" cy="122" r="1.4" fill="#F4EFE6"/><circle cx="57" cy="134" r="1.4" fill="#F4EFE6"/>`); }
    if (o.hoodie){ P.push(`<path d="M47 92 Q60 104 73 92" fill="none" stroke="rgba(255,255,255,.35)" stroke-width="3"/><rect x="50" y="126" width="20" height="10" rx="3" fill="rgba(255,255,255,.12)"/>`); }
    if (o.jacket){ P.push(`<path d="M54 92 L60 104 L66 92 Z" fill="#1F2330"/><line x1="60" y1="104" x2="60" y2="147" stroke="rgba(0,0,0,.3)" stroke-width="1.4"/>`); }
    if (o.stripes){ for (let y=100;y<146;y+=9) P.push(`<rect x="${40-(y-92)*0.07}" y="${y}" width="${40+(y-92)*0.14}" height="4" fill="#2A78D6" opacity=".8"/>`); }
    if (o.chef){ P.push(`<path d="M50 92 L60 102 L70 92 L66 104 L54 104 Z" fill="#D23F3F"/>${[52,68].flatMap(x=>[114,126,138].map(y=>`<circle cx="${x}" cy="${y}" r="1.6" fill="#5B6576"/>`)).join('')}`); }
    if (o.prop==='steth'){ P.push(`<path d="M50 94 Q48 118 58 122 Q68 118 70 94" fill="none" stroke="#5B6576" stroke-width="2"/><circle cx="58" cy="124" r="3.2" fill="#8A93A3"/>`); }
    // cuello y cabeza
    P.push(`<rect x="52" y="84" width="16" height="10" fill="${SKIN_DARK}"/>`);
    P.push(`<rect x="50" y="36" width="20" height="9" rx="2" fill="${SKIN}" stroke="${SKIN_DARK}" stroke-width="1.2"/>`);
    P.push(`<rect x="39" y="43" width="42" height="44" rx="9" fill="${SKIN}" stroke="${SKIN_DARK}" stroke-width="1.2"/>`);
    // cara
    P.push(`<circle cx="52" cy="64" r="2.8" fill="${FACE}"/><circle cx="68" cy="64" r="2.8" fill="${FACE}"/>`);
    if (gender==='F') P.push(`<path d="M48.5 60 L50.5 61.5 M71.5 60 L69.5 61.5" stroke="${FACE}" stroke-width="1.4"/><path d="M53 74 Q60 79 67 74" fill="none" stroke="#C0392B" stroke-width="2.4" stroke-linecap="round"/>`);
    else P.push(`<path d="M52 73 Q60 79 68 73" fill="none" stroke="${FACE}" stroke-width="2.2" stroke-linecap="round"/>`);
    // pelo (encima de la cabeza)
    if (gender==='F') P.push(`<path d="M37 60 Q36 36 60 35 Q84 36 83 60 Q76 48 60 47 Q48 47 42 53 Z" fill="#8B4A22"/>`);
    if (gender==='M') P.push(`<path d="M38 58 Q38 36 60 35 Q82 36 82 58 L79 52 Q70 46 60 46 Q49 46 41 52 Z" fill="#4A2C1A"/>`);
    // sombreros / accesorios de cabeza
    const hats = {
      hardhat:      `<path d="M36 50 Q36 28 60 27 Q84 28 84 50 Z" fill="#F5C400" stroke="#C99D00"/><rect x="32" y="48" width="56" height="6" rx="3" fill="#F5C400" stroke="#C99D00"/>`,
      hardhatWhite: `<path d="M36 50 Q36 28 60 27 Q84 28 84 50 Z" fill="#FFFFFF" stroke="#AEB7C4"/><rect x="32" y="48" width="56" height="6" rx="3" fill="#FFFFFF" stroke="#AEB7C4"/>`,
      chef:         `<rect x="42" y="30" width="36" height="16" fill="#FFFFFF" stroke="#C9D2DE"/><circle cx="48" cy="24" r="10" fill="#FFFFFF" stroke="#C9D2DE"/><circle cx="60" cy="19" r="12" fill="#FFFFFF" stroke="#C9D2DE"/><circle cx="72" cy="24" r="10" fill="#FFFFFF" stroke="#C9D2DE"/><rect x="43" y="28" width="34" height="10" fill="#FFFFFF"/>`,
      beret:        `<ellipse cx="58" cy="42" rx="26" ry="9" fill="#C0392B"/><circle cx="60" cy="33" r="2.5" fill="#C0392B"/>`,
      cap:          `<path d="M38 48 Q38 30 60 29 Q82 30 82 48 Z" fill="#1F3B73"/><rect x="36" y="45" width="48" height="6" rx="2" fill="#15294F"/><circle cx="60" cy="38" r="3.5" fill="#EDA100"/>`,
      straw:        `<ellipse cx="60" cy="45" rx="34" ry="7" fill="#E4C06A" stroke="#B8923C"/><path d="M42 45 Q42 26 60 25 Q78 26 78 45 Z" fill="#E4C06A" stroke="#B8923C"/><rect x="42" y="38" width="36" height="4" fill="#8B5A2B"/>`,
      goggles:      `<rect x="40" y="46" width="40" height="10" rx="5" fill="#7FC4E8" opacity=".85" stroke="#2F6DB5"/><rect x="38" y="49" width="44" height="3" fill="#2F6DB5" opacity=".5"/>`,
      headset:      `<path d="M37 64 Q37 30 60 30 Q83 30 83 64" fill="none" stroke="#2B3A55" stroke-width="4"/><rect x="33" y="58" width="8" height="14" rx="3" fill="#2B3A55"/><rect x="79" y="58" width="8" height="14" rx="3" fill="#2B3A55"/><path d="M37 70 Q40 80 50 79" fill="none" stroke="#2B3A55" stroke-width="2"/>`,
    };
    if (o.hat && hats[o.hat]) P.push(hats[o.hat]);
    // objeto en la mano derecha
    const props = {
      flask:     `<path d="M96 118 L102 118 L102 126 L108 140 Q109 144 104 144 L94 144 Q89 144 90 140 L96 126 Z" fill="#BFE3F5" stroke="#2F6DB5"/><path d="M92 136 L106 136 L108 140 Q109 144 104 144 L94 144 Q89 144 90 140 Z" fill="#3FA37A"/>`,
      plan:      `<rect x="92" y="118" width="10" height="30" rx="4" fill="#9CC3E8" stroke="#2F6DB5"/>`,
      wrench:    `<rect x="95" y="116" width="5" height="24" rx="2" fill="#8A93A3"/><circle cx="97.5" cy="115" r="5" fill="none" stroke="#8A93A3" stroke-width="3"/>`,
      laptop:    `<rect x="88" y="124" width="24" height="16" rx="2" fill="#2B3A55"/><rect x="90" y="126" width="20" height="12" fill="#7FC4E8"/>`,
      briefcase: `<rect x="86" y="140" width="22" height="16" rx="2" fill="#8B5A2B"/><rect x="93" y="136" width="8" height="5" rx="1" fill="none" stroke="#8B5A2B" stroke-width="2"/>`,
      chart:     `<rect x="88" y="120" width="20" height="16" rx="1" fill="#FFFFFF" stroke="#8A93A3"/><path d="M91 132 L96 127 L100 130 L105 123" fill="none" stroke="#177A3D" stroke-width="2"/>`,
      book:      `<rect x="88" y="126" width="18" height="22" rx="1" fill="#177A3D"/><rect x="90" y="128" width="3" height="18" fill="rgba(255,255,255,.4)"/>`,
      notebook:  `<rect x="89" y="124" width="16" height="20" rx="1" fill="#FFFFFF" stroke="#8A93A3"/><line x1="92" y1="130" x2="102" y2="130" stroke="#AEB7C4"/><line x1="92" y1="135" x2="102" y2="135" stroke="#AEB7C4"/>`,
      mic:       `<rect x="94" y="126" width="6" height="16" rx="2" fill="#2B3A55"/><circle cx="97" cy="123" r="6" fill="#5B6576"/>`,
      palette:   `<ellipse cx="100" cy="132" rx="12" ry="9" fill="#E4C06A" stroke="#B8923C"/><circle cx="95" cy="129" r="2.2" fill="#D23F3F"/><circle cx="101" cy="127" r="2.2" fill="#2A78D6"/><circle cx="106" cy="131" r="2.2" fill="#177A3D"/>`,
      spoon:     `<rect x="95" y="118" width="4" height="26" rx="2" fill="#8B5A2B"/><ellipse cx="97" cy="116" rx="5" ry="7" fill="#8B5A2B"/>`,
      suitcase:  `<rect x="86" y="138" width="20" height="20" rx="3" fill="#2A78D6"/><rect x="93" y="133" width="6" height="6" rx="1" fill="none" stroke="#1D5FBF" stroke-width="2"/>`,
      shield:    `<path d="M97 120 L108 124 L107 136 Q104 144 97 147 Q90 144 87 136 L86 124 Z" fill="#C9A227" stroke="#8A6D12"/><path d="M97 127 L99 132 L104 132 L100 135 L102 140 L97 137 L92 140 L94 135 L90 132 L95 132 Z" fill="#FFF4C2"/>`,
      sprout:    `<rect x="92" y="136" width="12" height="10" rx="2" fill="#8B5A2B"/><path d="M98 136 Q98 126 92 122 M98 132 Q100 124 106 122" fill="none" stroke="#3FA37A" stroke-width="3" stroke-linecap="round"/>`,
    };
    if (o.prop && props[o.prop]) P.push(props[o.prop]);
    return `<svg viewBox="0 0 120 200" role="img" aria-label="Figura: ${o.label}">${P.join('')}</svg>`;
  }


  window.FIGURAS = { outfitFor, figureSVG };
})();
