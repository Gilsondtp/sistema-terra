<?php
require_once '../config/config.php';
require_once '../config/Database.php';
require_once '../class/Lancamento.php';
require_once __DIR__ . '/../includes/header.php'; 

// Este endpoint usa a MESMA lógica de fechamento de modules/relatorios.php
// (Lancamento::fecharFatura), que transfere o saldo devedor para a fatura
// anterior do cliente antes de apagar os lançamentos — tudo em transação.
// Não implementar lógica própria aqui para evitar divergência.

if ($_SERVER['REQUEST_METHOD'] !== 'POST' || empty($_POST['cliente_id'])) {
    header('Location: relatorios.php?erro=' . urlencode('Cliente não informado!'));
    exit;
}

$cliente_id = (int)$_POST['cliente_id'];
$data_inicio = !empty($_POST['data_inicio']) ? $_POST['data_inicio'] : null;
$data_fim = !empty($_POST['data_fim']) ? $_POST['data_fim'] : null;

$database = new Database();
$db = $database->getConnection();
$lancamento = new Lancamento($db);

$saldo_transferido = $lancamento->fecharFatura($cliente_id, $data_inicio, $data_fim);

if ($saldo_transferido === false) {
    header('Location: relatorios.php?erro=' . urlencode('Erro ao fechar a fatura. Nenhuma alteração foi feita.'));
} else {
    header('Location: relatorios.php?mensagem=' . urlencode('Fatura fechada com sucesso! Saldo devedor de R$ ' . number_format($saldo_transferido, 2, ',', '.') . ' transferido para a próxima fatura do cliente.'));
}
exit;
