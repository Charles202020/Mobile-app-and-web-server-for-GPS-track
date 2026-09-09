<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$host = "TU_ENDPOINT_AQUI";
$port = "5432";
$dbname = "gpsdb";
$user = "gpstracker";
$password = "TU_CONTRASEÑA_AQUI";

try {
    $pdo = new PDO("pgsql:host=$host;port=$port;dbname=$dbname", $user, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $stmt = $pdo->query("
        SELECT 
            latitud, 
            longitud, 
            timestamp,
            to_char(fecha_recepcion AT TIME ZONE 'UTC' AT TIME ZONE 'America/Bogota', 'YYYY-MM-DD HH24:MI:SS') AS fecha_recepcion,
            ip_origen 
        FROM ubicaciones 
        ORDER BY id DESC 
        LIMIT 1
    ");
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
    if ($row) {
        echo json_encode($row);
    } else {
        echo json_encode(["error" => "Sin datos aún"]);
    }
} catch (Exception $e) {
    echo json_encode(["error" => $e->getMessage()]);
}
?>