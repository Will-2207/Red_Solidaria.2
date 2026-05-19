<?php
$host = "127.0.0.1";
$port = "3307"; // Tu puerto de MySQL
$user = "root";
$pass = ""; // Pon tu contraseña si tienes
$dbname = "donaciones_db";

try {
    $pdo = new PDO("mysql:host=$host;port=$port;dbname=$dbname;charset=utf8", $user, $pass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    die("Error de conexión: " . $e->getMessage());
}
?>