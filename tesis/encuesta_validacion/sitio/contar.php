<?php
// Consulta de solo lectura: cuántas respuestas hay. No escribe ni borra nada.
// Uso: contar.php?clave=TU_CLAVE
require __DIR__ . '/config.php';
if (!isset($_GET['clave']) || !hash_equals(CLAVE_EXPORTAR, (string)$_GET['clave'])) { http_response_code(403); exit('Clave incorrecta'); }
header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-store');
date_default_timezone_set('America/Guayaquil');
$NOMBRES = [
  'ingenieria-en-computacion' => 'Ingeniería en Computación',
  'ingenieria-de-software' => 'Ingeniería de Software',
  'ciencia-de-datos-e-inteligencia-artificial' => 'Ciencia de Datos e Inteligencia Artificial',
  'ingenieria-mecatronica' => 'Ingeniería Mecatrónica',
  'ingenieria-civil' => 'Ingeniería Civil',
  'ingenieria-mecanica' => 'Ingeniería Mecánica',
  'ingenieria-electrica' => 'Ingeniería Eléctrica',
  'ingenieria-electronica-y-automatizacion' => 'Ingeniería Electrónica y Automatización',
  'ingenieria-quimica' => 'Ingeniería Química',
  'ingenieria-industrial' => 'Ingeniería Industrial',
  'ingenieria-en-telecomunicaciones' => 'Ingeniería en Telecomunicaciones',
  'ingenieria-en-ciberseguridad' => 'Ingeniería en Ciberseguridad',
  'ingenieria-en-geologia' => 'Ingeniería en Geología',
  'ingenieria-de-minas' => 'Ingeniería de Minas',
  'ingenieria-en-petroleos' => 'Ingeniería en Petróleos',
  'ingenieria-ambiental' => 'Ingeniería Ambiental',
  'ingenieria-en-alimentos' => 'Ingeniería en Alimentos',
  'ingenieria-biomedica' => 'Ingeniería Biomédica',
  'medicina' => 'Medicina',
  'odontologia' => 'Odontología',
  'enfermeria' => 'Enfermería',
  'psicologia-clinica' => 'Psicología Clínica',
  'fisioterapia' => 'Fisioterapia',
  'nutricion-y-dietetica' => 'Nutrición y Dietética',
  'bioquimica-y-farmacia' => 'Bioquímica y Farmacia',
  'fonoaudiologia' => 'Fonoaudiología',
  'terapia-ocupacional' => 'Terapia Ocupacional',
  'medicina-veterinaria' => 'Medicina Veterinaria',
  'obstetricia' => 'Obstetricia',
  'radiologia-e-imagenologia' => 'Radiología e Imagenología',
  'administracion-de-empresas' => 'Administración de Empresas',
  'economia' => 'Economía',
  'contabilidad-y-auditoria' => 'Contabilidad y Auditoría',
  'finanzas' => 'Finanzas',
  'marketing' => 'Marketing',
  'comercio-exterior' => 'Comercio Exterior',
  'gestion-del-talento-humano' => 'Gestión del Talento Humano',
  'administracion-publica' => 'Administración Pública',
  'gestion-y-emprendimiento' => 'Gestión y Emprendimiento',
  'auditoria-y-control-de-gestion' => 'Auditoría y Control de Gestión',
  'administracion-turistica-y-hotelera' => 'Administración Turística y Hotelera',
  'gestion-de-la-produccion-y-logistica' => 'Gestión de la Producción y Logística',
  'derecho' => 'Derecho',
  'relaciones-internacionales' => 'Relaciones Internacionales',
  'ciencias-politicas' => 'Ciencias Políticas',
  'sociologia' => 'Sociología',
  'antropologia' => 'Antropología',
  'trabajo-social' => 'Trabajo Social',
  'comunicacion-y-periodismo' => 'Comunicación y Periodismo',
  'pedagogia-de-idiomas-extranjeros' => 'Pedagogía de Idiomas Extranjeros',
  'educacion-basica' => 'Educación Básica',
  'educacion-inicial' => 'Educación Inicial',
  'psicopedagogia' => 'Psicopedagogía',
  'filosofia' => 'Filosofía',
  'arquitectura' => 'Arquitectura',
  'diseno-grafico' => 'Diseño Gráfico',
  'diseno-de-productos-e-industrial' => 'Diseño de Productos e Industrial',
  'diseno-de-modas' => 'Diseño de Modas',
  'artes-visuales' => 'Artes Visuales',
  'cine-y-medios-audiovisuales' => 'Cine y Medios Audiovisuales',
  'artes-musicales' => 'Artes Musicales',
  'artes-escenicas-y-teatro' => 'Artes Escénicas y Teatro',
  'animacion-digital-y-videojuegos' => 'Animación Digital y Videojuegos',
  'diseno-de-interiores' => 'Diseño de Interiores',
  'biologia' => 'Biología',
  'biotecnologia' => 'Biotecnología',
  'matematicas' => 'Matemáticas',
  'fisica' => 'Física',
  'quimica' => 'Química',
  'agronomia' => 'Agronomía',
  'zootecnia' => 'Zootecnia',
  'agroindustria' => 'Agroindustria',
  'tecnologia-superior-en-desarrollo-de-software' => 'Tecnología Superior en Desarrollo de Software',
  'tecnologia-superior-en-electromecanica' => 'Tecnología Superior en Electromecánica',
  'tecnologia-superior-en-redes-y-telecomunicaciones' => 'Tecnología Superior en Redes y Telecomunicaciones',
  'tecnologia-superior-en-mecanica-automotriz' => 'Tecnología Superior en Mecánica Automotriz',
  'tecnologia-superior-en-contabilidad' => 'Tecnología Superior en Contabilidad',
  'tecnologia-superior-en-gastronomia' => 'Tecnología Superior en Gastronomía',
  'tecnologia-superior-en-guia-nacional-de-turismo' => 'Tecnología Superior en Guía Nacional de Turismo',
  'tecnologia-superior-en-logistica-y-transporte' => 'Tecnología Superior en Logística y Transporte',
  'oficial-de-ejercito-ciencias-militares' => 'Oficial de Ejército (Ciencias Militares)',
  'oficial-de-marina-ciencias-navales' => 'Oficial de Marina (Ciencias Navales)',
  'oficial-de-aviacion-militar' => 'Oficial de Aviación Militar',
  'ciencias-policiales-y-seguridad-ciudadana' => 'Ciencias Policiales y Seguridad Ciudadana',
  'seguridad-ciudadana' => 'Seguridad Ciudadana',
  'criminalistica' => 'Criminalística',
  'gestion-de-riesgos-y-desastres' => 'Gestión de Riesgos y Desastres'
];
$ruta = CARPETA_DATOS . '/respuestas.jsonl';
$filas = [];
if (is_file($ruta) && ($fh = fopen($ruta, 'r'))) {
  while (($linea = fgets($fh)) !== false) { $f = json_decode(trim($linea), true); if (is_array($f)) $filas[] = $f; }
  fclose($fh);
}
$esPrueba = function ($f) { return stripos(($f['codigo'] ?? '') . ' ' . ($f['carrera_otra'] ?? '') . ' ' . ($f['version'] ?? ''), 'PRUEBA') !== false || ($f['version'] ?? '') === 'test'; };
$pruebas = array_values(array_filter($filas, $esPrueba));
$reales = array_values(array_filter($filas, function ($f) use ($esPrueba) { return !$esPrueba($f); }));
$atentas = count(array_filter($reales, function ($f) { return (string)($f['atencion_ok'] ?? '') === '1'; }));
$hoy = date('Y-m-d'); $deHoy = 0; $ultima = null;
foreach ($reales as $f) { if (!empty($f['recibido'])) { $t = strtotime($f['recibido']); if ($t) { if (date('Y-m-d', $t) === $hoy) $deHoy++; if (!$ultima || $t > $ultima) $ultima = $t; } } }
$contar = function ($campo, $nombre = null) use ($reales) {
  $c = [];
  foreach ($reales as $f) {
    $v = (string)($f[$campo] ?? ''); if ($v === '') $v = '(sin dato)';
    if ($campo === 'carrera_id' && $v === 'otra') $v = 'Otra: ' . trim((string)($f['carrera_otra'] ?? ''));
    elseif ($nombre && isset($nombre[$v])) $v = $nombre[$v];
    $c[$v] = ($c[$v] ?? 0) + 1;
  }
  arsort($c); return $c;
};
$h = function ($s) { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); };
$tabla = function ($titulo, $c) use ($h) {
  if (!$c) return '';
  $o = '<h2>' . $h($titulo) . '</h2><table>';
  foreach ($c as $k => $n) $o .= '<tr><td>' . $h($k) . '</td><td class="n">' . $n . '</td></tr>';
  return $o . '</table>';
};
?><!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Respuestas · Encuesta Vocacional</title>
<style>
:root{--bg:#f4f5f8;--s:#fff;--l:#dbdfe7;--fg:#141823;--f3:#6f7788;--a:#2f3d8a;--ok:#1baf7a}
@media (prefers-color-scheme:dark){:root{--bg:#111318;--s:#191c23;--l:#2d3240;--fg:#eef0f5;--f3:#8b92a3;--a:#9eabf2}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,"Segoe UI",sans-serif}
main{max-width:640px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:1.3rem;margin:0 0 4px}h2{font-size:1rem;margin:28px 0 8px}
.sutil{color:var(--f3);font-size:.88rem}
.cifras{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-top:16px}
.cifra{background:var(--s);border:1px solid var(--l);border-radius:12px;padding:14px}
.cifra b{display:block;font-size:2rem;line-height:1.1;font-variant-numeric:tabular-nums}
.cifra.grande b{color:var(--ok)}
table{width:100%;border-collapse:collapse;background:var(--s);border:1px solid var(--l);border-radius:12px;overflow:hidden}
td{padding:8px 12px;border-top:1px solid var(--l)}tr:first-child td{border-top:0}
td.n{text-align:right;font-variant-numeric:tabular-nums;font-weight:700;width:60px}
a{color:var(--a)}
</style></head><body><main>
<h1>Respuestas de la encuesta</h1>
<p class="sutil">Consultado: <?= date('d/m/Y H:i') ?> (hora de Ecuador) · Solo lectura</p>
<div class="cifras">
  <div class="cifra grande"><b><?= count($reales) ?></b>respuestas</div>
  <div class="cifra"><b><?= $atentas ?></b>pasaron el control de atención</div>
  <div class="cifra"><b><?= $deHoy ?></b>hoy</div>
</div>
<p class="sutil">Última respuesta: <?= $ultima ? date('d/m/Y H:i', $ultima) : '—' ?><?= $pruebas ? ' · ' . count($pruebas) . ' de prueba no contadas' : '' ?></p>
<?= $tabla('Por carrera', $contar('carrera_id', $NOMBRES)) ?>
<?= $tabla('Por tipo de colegio', $contar('tipo_colegio')) ?>
<?= $tabla('Satisfacción con la carrera (1 a 5)', $contar('satisfaccion')) ?>
<p class="sutil" style="margin-top:28px"><a href="exportar.php?clave=<?= $h($_GET['clave']) ?>">Descargar todo en CSV</a></p>
</main></body></html>
