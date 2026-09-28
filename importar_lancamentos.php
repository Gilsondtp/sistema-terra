<?php
require_once '../config/config.php';
require_once '../config/Database.php';

$jsonFile = 'lancamentos.json';

$jsonData = file_get_contents($jsonFile);
$lancamentos = json_decode($jsonData, true);

if (!$lancamentos) {
    die("Falha ao ler ou decodificar o JSON!");
}

$database = new Database();
$db = $database->getConnection();

$stmt = $db->prepare("INSERT INTO lancamentos (id, cliente_id, data_lancamento, valor_entrega, valor_pagamento) VALUES (?, ?, ?, ?, ?) 
    ON DUPLICATE KEY UPDATE cliente_id=VALUES(cliente_id), data_lancamento=VALUES(data_lancamento), valor_entrega=VALUES(valor_entrega), valor_pagamento=VALUES(valor_pagamento)");

foreach ($lancamentos as $l) {
    $stmt->execute([
        $l['id'],
        $l['cliente_id'],
        $l['data_lancamento'],
        $l['valor_entrega'],
        $l['valor_pagamento']
    ]);
}
echo "Importação concluída!";
?>