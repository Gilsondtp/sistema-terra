<?php
require_once '../config/config.php';
require_once '../config/Database.php';

// Caminho do arquivo JSON
$jsonFile = 'clientes.json';

// Lê o arquivo JSON
$jsonData = file_get_contents($jsonFile);
$clientes = json_decode($jsonData, true);

if (!$clientes) {
    die("Falha ao ler ou decodificar o JSON!");
}

// Conexão com o banco
$database = new Database();
$db = $database->getConnection();

// Prepara o insert
$stmt = $db->prepare("INSERT INTO clientes (id, nome, email, telefone) VALUES (?, ?, ?, ?) 
    ON DUPLICATE KEY UPDATE nome=VALUES(nome), email=VALUES(email), telefone=VALUES(telefone)");

// Importa cada cliente
foreach ($clientes as $cliente) {
    $stmt->execute([
        $cliente['id'],
        $cliente['nome'],
        $cliente['email'],
        $cliente['telefone']
    ]);
}

echo "Importação concluída!";
?>