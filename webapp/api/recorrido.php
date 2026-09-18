<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Cargar variables de entorno desde la ruta absoluta
$env = parse_ini_file('/home/ubuntu/.env');
$host = $env['DB_HOST'] ?? 'localhost';
$port = $env['DB_PORT'] ?? '5432';
$dbname = $env['DB_NAME'] ?? 'tu_bd';
$user = $env['DB_USER'] ?? 'postgres';
$password = $env['DB_PASS'] ?? '';

// Obtener parámetros de la solicitud GET
$inicio = isset($_GET['inicio']) ? trim($_GET['inicio']) : null;
$fin = isset($_GET['fin']) ? trim($_GET['fin']) : null;

if (!$inicio || !$fin) {
    echo json_encode(["errror" => "Faltan parámetros inicio y fin"]);
    exit;
}

try {
    // Conexión a PostgreSQL con PDO
    $pdo = new PDO("pgsql:host=$host;port=$port;dbname=$dbname", $user, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // Consulta directa usando la fecha almacenada en la base de datos
	$stmt = $pdo->prepare("
	    SELECT
	        CAST(latitud AS DOUBLE PRECISION) AS lat,
	        CAST(longitud AS DOUBLE PRECISION) AS lng,
	        to_char(fecha_recepcion - INTERVAL '5 hours', 'YYYY-MM-DD HH24:MI:SS') AS fecha
	    FROM ubicaciones
	    WHERE (fecha_recepcion - INTERVAL '5 hours') BETWEEN 
	        TO_TIMESTAMP(:inicio, 'YYYY-MM-DD HH24:MI:SS')
	        AND
	        TO_TIMESTAMP(:fin, 'YYYY-MM-DD HH24:MI:SS')
	    ORDER BY id ASC
	");

	    $stmt->execute([
	        ':inicio' => $inicio,
	        ':fin' => $fin
	    ]);

    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

    // Devolver el resultado como JSON
    echo json_encode($rows);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(["error" => "Error DB: " . $e->getMessage()]);
}
?>
