<?php
require_once 'config.php';

// Función para generar un UUID v4 manual en PHP
function generarUUID() {
    return sprintf('%04x%04x-%04x-%04x-%04x-%04x%04x%04x',
        mt_rand(0, 0xffff), mt_rand(0, 0xffff),
        mt_rand(0, 0xffff),
        mt_rand(0, 0x0fff) | 0x4000,
        mt_rand(0, 0x3fff) | 0x8000,
        mt_rand(0, 0xffff), mt_rand(0, 0xffff), mt_rand(0, 0xffff)
    );
}

// Simularemos que Flask nos envía el usuario_id por una petición POST
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $usuario_id = $_POST['usuario_id'];
    $nuevo_token = generarUUID();
    
    // El token expirará en 24 horas
    $fecha_expiracion = date('Y-m-d H:i:s', strtotime('+24 hours'));

    try {
        $stmt = $pdo->prepare("INSERT INTO soporte_tokens (usuario_id, token, fecha_expiracion) VALUES (?, ?, ?)");
        $stmt->execute([$usuario_id, $nuevo_token, $fecha_expiracion]);

        echo json_encode([
            "status" => "success",
            "token" => $nuevo_token,
            "mensaje" => "Token generado correctamente para el usuario $usuario_id"
        ]);
    } catch (Exception $e) {
        echo json_encode(["status" => "error", "mensaje" => $e->getMessage()]);
    }
}
?>