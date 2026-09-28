<?php
require_once '../config/Database.php';

header('Content-Type: application/json');

try {
    $database = new Database();
    $db = $database->getConnection();

    // Exporta banco principal
    $result = $db->query("SHOW TABLES");
    $tables = $result->fetchAll(PDO::FETCH_COLUMN);

    $output = "";
    foreach ($tables as $table) {
        $output .= "-- Estrutura para tabela `$table`\n";
        $result = $db->query("SHOW CREATE TABLE `$table`");
        $output .= $result->fetch()[1] . ";\n\n";
        
        $result = $db->query("SELECT * FROM `$table`");
        while ($row = $result->fetch(PDO::FETCH_ASSOC)) {
            $values = array_map(function($v) {
                if ($v === null) return 'NULL';
                return "'" . str_replace("'", "''", $v) . "'"; // Usa aspas duplas para escapar
            }, $row);
            
            $output .= "INSERT INTO `$table` VALUES(" . implode(', ', $values) . ");\n";
        }
        $output .= "\n";
    }

    echo json_encode([
        'success' => true,
        'filename' => 'backup_' . date('Y-m-d') . '.sql',
        'content' => $output
    ], JSON_UNESCAPED_UNICODE);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => 'Erro na exportação: ' . $e->getMessage()
    ], JSON_UNESCAPED_UNICODE);
}