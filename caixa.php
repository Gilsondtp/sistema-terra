<?php
// Arquivo: api/caixa.php

session_start();
header('Content-Type: application/json');
require_once '../config/Database.php';

// Ajuste para o nome da tabela que você usar
$tabela = 'lancamentos_caixa';

// Conectar ao banco
$db = (new Database())->getConnection();

// Função auxiliar para limpar valor monetário
function limparValor($valor) {
    return floatval(str_replace(['R$', '.', ','], ['', '', '.'], $valor));
}

// Ação da requisição (create, read, update, delete, clear, resumo)
$action = $_GET['action'] ?? $_POST['action'] ?? 'read';

switch ($action) {
    case 'create':
        $descricao = $_POST['descricao'] ?? '';
        $data = $_POST['data'] ?? '';
        $valor = limparValor($_POST['valor'] ?? '0');
        $operacao = $_POST['operacao'] ?? '';
        $sql = "INSERT INTO $tabela (descricao, data, valor, operacao) VALUES (?, ?, ?, ?)";
        $stmt = $db->prepare($sql);
        $ok = $stmt->execute([$descricao, date('Y-m-d', strtotime(str_replace('/','-',$data))), $valor, $operacao]);
        echo json_encode(['success'=>$ok]);
        break;

    case 'read':
        $sql = "SELECT * FROM $tabela ORDER BY data DESC, id DESC";
        $stmt = $db->query($sql);
        $dados = $stmt->fetchAll(PDO::FETCH_ASSOC);
        echo json_encode(['data'=>$dados]);
        break;

    case 'update':
        $id = intval($_POST['id']);
        $descricao = $_POST['descricao'] ?? '';
        $data = $_POST['data'] ?? '';
        $valor = limparValor($_POST['valor'] ?? '0');
        $operacao = $_POST['operacao'] ?? '';
        $sql = "UPDATE $tabela SET descricao=?, data=?, valor=?, operacao=? WHERE id=?";
        $stmt = $db->prepare($sql);
        $ok = $stmt->execute([$descricao, date('Y-m-d', strtotime(str_replace('/','-',$data))), $valor, $operacao, $id]);
        echo json_encode(['success'=>$ok]);
        break;

    case 'delete':
        $id = intval($_POST['id']);
        $sql = "DELETE FROM $tabela WHERE id=?";
        $stmt = $db->prepare($sql);
        $ok = $stmt->execute([$id]);
        echo json_encode(['success'=>$ok]);
        break;

    case 'clear':
        $sql = "TRUNCATE TABLE $tabela";
        $ok = $db->exec($sql) !== false;
        echo json_encode(['success'=>$ok]);
        break;

    case 'resumo':
        // Totais por operação
        $resumo = [];
        $operacoes = ['receita', 'despesa', 'pago', 'recebido', 'a_receber', 'transferido'];
        foreach($operacoes as $op) {
            $stmt = $db->prepare("SELECT SUM(valor) as total FROM $tabela WHERE operacao=?");
            $stmt->execute([$op]);
            $resumo[$op] = number_format($stmt->fetchColumn() ?: 0, 2, ',', '.');
        }
        // Total geral
        $stmt = $db->prepare("SELECT 
            SUM(CASE WHEN operacao='receita' THEN valor ELSE 0 END) -
            SUM(CASE WHEN operacao='despesa' THEN valor ELSE 0 END) as total_geral
            FROM $tabela");
        $stmt->execute();
        $resumo['total_geral'] = number_format($stmt->fetchColumn() ?: 0, 2, ',', '.');
        echo json_encode($resumo);
        break;
}
?>