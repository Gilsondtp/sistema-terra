<?php
require_once '../config/config.php';
require_once '../config/Database.php';
require_once '../class/Lancamento.php';
require_once __DIR__ . '/../includes/header.php'; 

if ($_SERVER['REQUEST_METHOD'] !== 'POST' || empty($_POST['cliente_id'])) {
    header('Location: relatorios.php?erro=' . urlencode('Cliente não informado!'));
    exit;
}

$cliente_id = (int)$_POST['cliente_id'];

$database = new Database();
$db = $database->getConnection();
$lancamento = new Lancamento($db);

try {
    // Inicia transação
    $db->beginTransaction();

    // Busca todos os lançamentos do cliente
    $lancamentos = $lancamento->listar(['cliente_id' => $cliente_id]);

    if (empty($lancamentos)) {
        throw new Exception('Nenhum lançamento encontrado para o cliente selecionado.');
    }

    // Exclui cada lançamento
    foreach ($lancamentos as $l) {
        if (empty($l['id']) || !$lancamento->excluir($l['id'])) {
            throw new Exception("Erro ao excluir lançamento #" . $l['id']);
        }
    }

    // Confirma as alterações
    $db->commit();

    // Redireciona com mensagem de sucesso
    header('Location: relatorios.php?mensagem=' . urlencode('Fatura fechada com sucesso!'));
    exit;

} catch (Exception $e) {
    // Desfaz as alterações em caso de erro
    if ($db->inTransaction()) {
        $db->rollBack();
    }
    header('Location: relatorios.php?erro=' . urlencode('Erro ao fechar fatura: ' . $e->getMessage()));
    exit;
}