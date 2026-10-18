<?php
// Descarga todas las respuestas como CSV: exportar.php?clave=TU_CLAVE
require __DIR__ . '/config.php';
if (CLAVE_EXPORTAR === 'cambia-esta-clave' || strlen(CLAVE_EXPORTAR) < 12 || !isset($_GET['clave']) || !hash_equals(CLAVE_EXPORTAR, (string)$_GET['clave'])) { http_response_code(403); exit('Clave incorrecta'); }
$ruta = CARPETA_DATOS . '/respuestas.jsonl';
$filas = [];
if (is_file($ruta)) {
  foreach (file($ruta, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $linea) {
    $f = json_decode($linea, true); if (is_array($f)) $filas[] = $f;
  }
}
$cab = [];                                   // unión de columnas, en el orden en que aparecen
foreach ($filas as $f) foreach (array_keys($f) as $k) if (!in_array($k, $cab, true)) $cab[] = $k;
header('Content-Type: text/csv; charset=utf-8');
header('Content-Disposition: attachment; filename="encuesta_vocacional_' . gmdate('Y-m-d') . '.csv"');
$out = fopen('php://output', 'w');
fwrite($out, "\xEF\xBB\xBF");                // BOM para que Excel lea las tildes
fputcsv($out, $cab);
foreach ($filas as $f) { fputcsv($out, array_map(fn($k) => $f[$k] ?? '', $cab)); }
fclose($out);
