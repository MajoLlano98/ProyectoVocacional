<?php
// Recibe una respuesta de la encuesta (JSON) y la agrega a datos/respuestas.jsonl (una línea por respuesta).
require __DIR__ . '/config.php';
header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); echo '{"ok":false,"error":"metodo"}'; exit; }
$crudo = file_get_contents('php://input', false, null, 0, 200000);   // límite: 200 KB por respuesta
$fila = json_decode($crudo, true);
if (!is_array($fila) || empty($fila['codigo']) || empty($fila['version'])) {
  http_response_code(400); echo '{"ok":false,"error":"formato"}'; exit;
}
// Solo valores simples (texto o número): nada de estructuras anidadas
foreach ($fila as $k => $v) {
  if (!preg_match('/^[A-Za-z0-9_]{1,60}$/', $k) || (!is_scalar($v) && $v !== null)) {
    http_response_code(400); echo '{"ok":false,"error":"campo"}'; exit;
  }
}
$fila['recibido'] = gmdate('c');
if (!is_dir(CARPETA_DATOS)) { mkdir(CARPETA_DATOS, 0750, true); }
$ok = file_put_contents(CARPETA_DATOS . '/respuestas.jsonl', json_encode($fila, JSON_UNESCAPED_UNICODE) . "\n", FILE_APPEND | LOCK_EX);
if ($ok === false) { http_response_code(500); echo '{"ok":false,"error":"escritura"}'; exit; }
echo '{"ok":true}';
