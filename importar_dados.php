<?php
require_once '../config/Database.php';

// Configura cabeçalhos para JSON e desativa exibição de erros
header('Content-Type: application/json');
error_reporting(0);
ini_set('display_errors', 0);

function json_response($success, $message, $code = 200) {
    http_response_code($code);
    die(json_encode([
        'success' => $success,
        'message' => strip_tags($message) // Remove qualquer HTML
    ], JSON_UNESCAPED_UNICODE));
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST' || !isset($_FILES['sql_file'])) {
    json_response(false, 'Requisição inválida', 400);
}

try {
    $database = new Database();
    $db = $database->getConnection();

    $tmpName = $_FILES['sql_file']['tmp_name'];
    $content = file_get_contents($tmpName);
    
    // Limpeza rigorosa do conteúdo
    $content = preg_replace('/<[^>]*>/', '', $content); // Remove HTML
    $content = preg_replace('/\s+/', ' ', $content); // Normaliza espaços
    $content = trim($content);

    if (empty($content)) {
        throw new Exception('Arquivo SQL vazio ou inválido');
    }

    // Execução segura em transação
    $db->beginTransaction();
    $db->exec($content);
    $db->commit();

    json_response(true, 'Importação concluída com sucesso!');

} catch (Exception $e) {
    if (isset($db) && $db->inTransaction()) {
        $db->rollBack();
    }
    json_response(false, 'Falha na importação: ' . $e->getMessage(), 500);
}