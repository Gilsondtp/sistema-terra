<?php
// Ativando exibição de erros
error_reporting(E_ALL);
ini_set('display_errors', 1);

$page_title = 'Fatura';

require_once '../config/config.php';
require_once '../config/Database.php';
require_once '../class/Cliente.php';
require_once '../class/Lancamento.php';
require_once __DIR__ . '/../includes/header.php'; 

$database = new Database();
$db = $database->getConnection();
$cliente = new Cliente($db);
$lancamento = new Lancamento($db);

// Fechar Fatura: transfere o saldo devedor para a fatura anterior do cliente
// e apaga os lançamentos do período exibido (tudo em transação, ver Lancamento::fecharFatura)
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['fechar_fatura'])) {
    $cliente_id = isset($_POST['cliente_id']) ? (int)$_POST['cliente_id'] : 0;
    $data_inicio = !empty($_POST['data_inicio']) ? $_POST['data_inicio'] : null;
    $data_fim = !empty($_POST['data_fim']) ? $_POST['data_fim'] : null;

    if ($cliente_id <= 0) {
        header('Location: relatorios.php?erro=' . urlencode('Cliente não informado para fechar a fatura.'));
        exit;
    }

    $saldo_transferido = $lancamento->fecharFatura($cliente_id, $data_inicio, $data_fim);

    if ($saldo_transferido === false) {
        header('Location: relatorios.php?erro=' . urlencode('Erro ao fechar a fatura. Nenhuma alteração foi feita.'));
    } else {
        header('Location: relatorios.php?mensagem=' . urlencode('Fatura fechada com sucesso! Saldo devedor de R$ ' . number_format($saldo_transferido, 2, ',', '.') . ' transferido para a próxima fatura do cliente.'));
    }
    exit;
}

// Lista de clientes para o select
$clientes = $cliente->listar();

// Processamento dos filtros
$filtros = [];
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['cliente_id']) && !empty($_POST['cliente_id'])) {
        $filtros['cliente_id'] = $_POST['cliente_id'];
    }
    if (isset($_POST['data_inicio']) && !empty($_POST['data_inicio'])) {
        $filtros['data_inicio'] = $_POST['data_inicio']; // SEM conversão!
    }
    if (isset($_POST['data_fim']) && !empty($_POST['data_fim'])) {
        $filtros['data_fim'] = $_POST['data_fim']; // SEM conversão!
    }
}

// Busca lançamentos
$lancamentos = [];
$totais = [
    'servicos' => 0,
    'entrega' => 0,
    'pagamento' => 0,
    'saldo_fatura_anterior' => 0,
    'saldo' => 0
];

if (!empty($filtros)) {
    $lancamentos = $lancamento->listar($filtros);
    
    // Calcula totais
    $total_fatura_anterior = 0;
    $total_pagamento_fatura_anterior = 0;
    foreach ($lancamentos as $l) {
        $total_servicos = 0;
        foreach ($l['servicos'] as $s) {
            $total_servicos += $s['valor'];
        }
        $totais['servicos'] += $total_servicos;
        $totais['entrega'] += $l['valor_entrega'];
        $totais['pagamento'] += $l['valor_pagamento'];
        $total_fatura_anterior += $l['fatura_anterior'];
        $total_pagamento_fatura_anterior += $l['pagamento_fatura_anterior'];
    }
    // Obtém fatura anterior do cliente
    $cliente_atual = array_filter($clientes, function($c) use ($filtros) {
        return $c['id'] == $filtros['cliente_id'];
    });
    $cliente_atual = reset($cliente_atual);
    $totais['saldo_fatura_anterior'] = isset($cliente_atual['fatura_anterior']) ? $cliente_atual['fatura_anterior'] : 0;
    $totais['saldo'] = ($totais['servicos'] + $totais['entrega'] - $totais['pagamento']) + $totais['saldo_fatura_anterior'];
}

// Produtos utilizados
$produtos_utilizados = [];
if (!empty($lancamentos)) {
    foreach ($lancamentos as $l) {
        foreach ($l['servicos'] as $s) {
            if (!empty($s['produto_nome'])) {
                if (!isset($produtos_utilizados[$s['produto_nome']])) {
                    $produtos_utilizados[$s['produto_nome']] = 0;
                }
                $produtos_utilizados[$s['produto_nome']] += $s['quantidade'];
            }
        }
    }
    ksort($produtos_utilizados); // Ordena por nome do produto
}
?>

<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fatura</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="/sistema_terra/assets/css/style.css" rel="stylesheet">
    <style>
    .nav-menu {
        display: flex !important;
        background-color: #0D6EFD;
        padding: 10px 0;
    }
    .nav-menu a {
        color: white;
        text-decoration: none;
        padding: 8px 15px;
    }
    .header-container {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 20px;
    }
    .header-image {
        max-width: 200px;
        height: auto;
    }
    .header-text {
        font-size: 11px;
        line-height: 1.2;
        margin: 0;
        padding-top: 5px;
        text-align: left;
    }
    .footer-pix {
        margin-top: 40px;
        padding: 10px 0;
        border-top: 1px solid #ddd;
        display: flex;
        align-items: center;
    }
    .footer-pix img {
        max-width: 60px;
        height: auto;
        margin-right: 15px;
    }
    @media print {
        .no-print, .navbar, header, .nav-menu {
            display: none !important;
        }
        body {
            margin: 0 !important;
            padding: 0 !important;
            background: white;
        }
        .container {
            width: 100% !important;
            max-width: none !important;
            margin: 0 !important;
            padding: 5px !important;
        }
        .header-container {
            display: flex !important;
            margin-bottom: 5px !important;
        }
        .header-image {
            max-width: 100px !important;
        }
        .table {
            font-size: 11px !important;
            width: 100% !important;
        }
        .table td, 
        .table th {
            padding: 4px !important;
        }
        .client-name {
            font-size: 20px;
            font-weight: bold;
        }
        .footer-pix img {
            max-width: 60px !important;
        }
        .print-content {
            display: block !important;
            visibility: visible !important;
        }
    }
    </style>
</head>
<body>
    <?php include '../includes/navbar.php'; ?>
    <div class="container mt-4">
        <?php if (isset($_GET['mensagem'])): ?>
            <div class="alert alert-success no-print"><?php echo htmlspecialchars($_GET['mensagem']); ?></div>
        <?php endif; ?>
        <?php if (isset($_GET['erro'])): ?>
            <div class="alert alert-danger no-print"><?php echo htmlspecialchars($_GET['erro']); ?></div>
        <?php endif; ?>
        <!-- Filtros -->
        <div class="no-print">
            <div class="card mb-4">
                <h4 class="mb-0">Filtros</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="row">
                        <div class="col-md-4">
                            <div class="mb-3">
                                <label for="cliente_id" class="form-label">Cliente</label>
                                <select class="form-select" id="cliente_id" name="cliente_id" required>
                                    <option value="">Selecione um cliente</option>
                                    <?php foreach ($clientes as $c): ?>
                                        <option value="<?php echo $c['id']; ?>" 
                                            <?php echo (isset($filtros['cliente_id']) && $filtros['cliente_id'] == $c['id']) ? 'selected' : ''; ?>>
                                            <?php echo htmlspecialchars($c['nome']); ?>
                                        </option>
                                    <?php endforeach; ?>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="mb-3">
                                <label for="data_inicio" class="form-label">Data Início</label>
                                <input type="text" class="form-control data" id="data_inicio" name="data_inicio" 
                                       value="<?php echo isset($_POST['data_inicio']) ? $_POST['data_inicio'] : ''; ?>">
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="mb-3">
                                <label for="data_fim" class="form-label">Data Fim</label>
                                <input type="text" class="form-control data" id="data_fim" name="data_fim" 
                                       value="<?php echo isset($_POST['data_fim']) ? $_POST['data_fim'] : ''; ?>">
                            </div>
                        </div>
                        <div class="col-md-2">
                            <div class="mb-3">
                                <label class="form-label">&nbsp;</label>
                                <button type="submit" class="btn btn-primary d-block w-100">Gerar</button>
                            </div>
                        </div>
                    </div>
                </form>
            </div>
        </div>

        <?php if (!empty($lancamentos)): ?>
        <!-- Área Imprimível -->
        <div class="print-content">
            <!-- Cabeçalho -->
            <div class="header-container">
                <img src="/sistema_terra/imagens/cabecario.jpg" alt="Cabeçalho Terra Fotolito" class="header-image">
                <p class="header-text">
                    Campinas de Pirajá, nº 24 - Pirajá - Salvador - Ba.<br>
                    Tel / Whts: 71 3242-6120<br>
                    Email: terrafotolitos@hotmail.com
                </p>
            </div>
            <h1 class="mb-4">FATURA</h1>
            <!-- Dados do Cliente -->
            <?php 
            $cliente_atual = array_filter($clientes, function($c) use ($filtros) {
                return $c['id'] == $filtros['cliente_id'];
            });
            $cliente_atual = reset($cliente_atual);

            // Encontrar a primeira e última data dos lançamentos
            $primeira_data = null;
            $ultima_data = null;
            foreach ($lancamentos as $l) {
                $data_atual = strtotime($l['data_lancamento']);
                if ($primeira_data === null || $data_atual < strtotime($primeira_data)) {
                    $primeira_data = $l['data_lancamento'];
                }
                if ($ultima_data === null || $data_atual > strtotime($ultima_data)) {
                    $ultima_data = $l['data_lancamento'];
                }
            }

            // Calcula fatura anterior - usa sempre o valor do cliente atual
            $total_fatura_anterior = isset($cliente_atual['fatura_anterior']) ? $cliente_atual['fatura_anterior'] : 0;
            $total_pagamento_fatura_anterior = 0;

            // Soma apenas os pagamentos da fatura anterior dos lançamentos
            foreach ($lancamentos as $l) {
                $total_pagamento_fatura_anterior += isset($l['pagamento_fatura_anterior']) ? $l['pagamento_fatura_anterior'] : 0;
            }

            // Calcula o saldo da fatura anterior
            $saldo_fatura_anterior = $total_fatura_anterior - $total_pagamento_fatura_anterior;
            ?>
            <div class="mb-4 d-flex justify-content-between align-items-center">
                <div>
                    <strong>Cliente:</strong> <span class="client-name"><?php echo htmlspecialchars($cliente_atual['nome']); ?></span>
                </div>
                <div>
                    <span>Período de <?php echo Database::converteMysqlData($primeira_data); ?> a <?php echo Database::converteMysqlData($ultima_data); ?></span>
                </div>
            </div>
            <div class="table-responsive">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th class="col-item">Itens</th>
                            <th class="col-data">Data</th>
                            <th class="col-servicos">Serviços</th>
                            <th class="col-quant">Quant.</th>
                            <th class="col-produto">Produto</th>
                            <th class="col-valor">Valor</th>
                            <th class="col-entreg">Entreg.</th>
                            <th class="col-pgto">Pgtº</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php 
                        $os = 1;
                        // $total_fatura_anterior e $total_pagamento_fatura_anterior já foram definidos acima!
                        $observacoes_relatorio = [];
                        foreach ($lancamentos as $l): 
                            // Não sobrescrevemos mais o total_fatura_anterior com os lançamentos!
                            if (!empty($l['observacao'])) {
                                $observacoes_relatorio[] = $l['observacao'];
                            }
                            
                            // Só exibe a linha se houver serviços ou valores de entrega/pagamento
                            if (!empty($l['servicos']) || $l['valor_entrega'] > 0 || $l['valor_pagamento'] > 0):
                                if (empty($l['servicos'])):
                                    $data = new DateTime($l['data_lancamento']);
                                    $data_formatada = $data->format('d/m');
                            ?>
                            <tr>
                                <td class="col-item"><?php echo $os++; ?></td>
                                <td class="col-data"><?php echo $data_formatada; ?></td>
                                <td class="col-servicos"></td>
                                <td class="col-quant"></td>
                                <td class="col-produto"></td>
                                <td class="col-valor">R$ 0,00</td>
                                <td class="col-entreg">R$ <?php echo number_format($l['valor_entrega'], 2, ',', '.'); ?></td>
                                <td class="col-pgto">R$ <?php echo number_format($l['valor_pagamento'], 2, ',', '.'); ?></td>
                            </tr>
                            <?php 
                                else:
                                    $primeiro_servico = true;
                                    foreach ($l['servicos'] as $s):
                                        $data = new DateTime($l['data_lancamento']);
                                        $data_formatada = $data->format('d/m');
                            ?>
                            <tr>
                                <td class="col-item"><?php echo $os++; ?></td>
                                <td class="col-data"><?php echo $data_formatada; ?></td>
                                <td class="col-servicos"><?php echo htmlspecialchars($s['descricao']); ?></td>
                                <td class="col-quant"><?php echo $s['quantidade']; ?></td>
                                <td class="col-produto"><?php echo htmlspecialchars($s['produto_nome'] ?? ''); ?></td>
                                <td class="col-valor">R$ <?php echo number_format($s['valor'], 2, ',', '.'); ?></td>
                                <td class="col-entreg">R$ <?php echo number_format($l['valor_entrega'], 2, ',', '.'); ?></td>
                                <td class="col-pgto"><?php echo $primeiro_servico ? 'R$ ' . number_format($l['valor_pagamento'], 2, ',', '.') : ''; ?></td>
                            </tr>
                            <?php 
                                        $primeiro_servico = false;
                                    endforeach;
                                endif;
                            endif;
                        endforeach; 
                        ?>
                    </tbody>
                    <tfoot>
                        <tr>
                            <th colspan="3" style="text-align:right">Totais:</th>
                            <th>
                                <?php
                                $total_quantidade = 0;
                                foreach ($lancamentos as $l) {
                                    if (!empty($l['servicos'])) {
                                        foreach ($l['servicos'] as $s) {
                                            $total_quantidade += $s['quantidade'];
                                        }
                                    }
                                }
                                echo $total_quantidade;
                                ?>
                            </th>
                            <th></th>
                            <th>R$ <?php echo number_format($totais['servicos'], 2, ',', '.'); ?></th>
                            <th>R$ <?php echo number_format($totais['entrega'], 2, ',', '.'); ?></th>
                            <th>R$ <?php echo number_format($totais['pagamento'], 2, ',', '.'); ?></th>
                        </tr>
                    </tfoot>
                </table>
                
                <!-- Seção com Fatura Anterior e Totais -->
                <div class="row mt-4">
                    <div class="col-6">
                        <div class="row">
                            <div class="col-6">
                                <div class="mb-3">
                                    <label class="form-label">Fatura anterior R$</label>
                                    <input type="text" class="form-control" value="R$ <?php echo number_format($total_fatura_anterior, 2, ',', '.'); ?>" readonly>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="mb-3">
                                    <label class="form-label">Pagtº R$</label>
                                    <input type="text" class="form-control" value="R$ <?php echo number_format($total_pagamento_fatura_anterior, 2, ',', '.'); ?>" readonly>
                                </div>
                            </div>
                        </div>
                        <?php if (!empty($observacoes_relatorio)): ?>
                        <div class="row">
                            <div class="col-12">
                                <div class="card bg-light">
                                    <div class="card-body p-2" style="min-height: 60px; border: 1px solid #ced4da; border-radius: 0.375rem;">
                                        <strong>Observações:</strong><br>
                                        <?php echo implode('<br>', array_map('htmlspecialchars', array_unique($observacoes_relatorio))); ?>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <?php else: ?>
                        <div class="row">
                            <div class="col-12">
                                <div class="card bg-light">
                                    <div class="card-body p-2" style="min-height: 60px; border: 1px solid #ced4da; border-radius: 0.375rem;">
                                        <strong>Observações:</strong>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <?php endif; ?>
                    </div>
                    <div class="col-6">
                        <table class="table table-bordered">
                            <tr>
                                <th width="60%">Total Serviços:</th>
                                <td class="text-end">R$ <?php echo number_format($totais['servicos'], 2, ',', '.'); ?></td>
                            </tr>
                            <?php if ($totais['entrega'] > 0): ?>
                            <tr>
                                <th>Total Entrega:</th>
                                <td class="text-end">R$ <?php echo number_format($totais['entrega'], 2, ',', '.'); ?></td>
                            </tr>
                            <?php endif; ?>
                            <tr>
                                <th>Total da fatura:</th>
                                <td class="text-end">R$ <?php echo number_format($totais['servicos'] + $totais['entrega'], 2, ',', '.'); ?></td>
                            </tr>
                            <tr>
                                <th>Total Pago:</th>
                                <td class="text-end">R$ <?php echo number_format($totais['pagamento'] + $total_pagamento_fatura_anterior, 2, ',', '.'); ?></td>
                            </tr>
                            <tr>
                                <th>Saldo da Fatura Anterior:</th>
                                <td class="text-end">R$ <?php echo number_format($saldo_fatura_anterior, 2, ',', '.'); ?></td>
                            </tr>
                            <tr class="table-warning">
                                <th><strong>SALDO DEVEDOR:</strong></th>
                                <td class="text-end"><strong>R$ <?php echo number_format(($totais['servicos'] + $totais['entrega'] - $totais['pagamento']) + $saldo_fatura_anterior, 2, ',', '.'); ?></strong></td>
                            </tr>
                        </table>
                    </div>
                </div>
            </div>
            <?php if (!empty($produtos_utilizados)): ?>
                <div class="mt-4">
                    <h5>Relatório de Produtos Utilizados</h5>
                    <div class="table-responsive">
                        <table class="table table-bordered">
                            <thead>
                                <tr>
                                    <th>Produto</th>
                                    <th>Quantidade Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php foreach ($produtos_utilizados as $produto => $quantidade): ?>
                                    <tr>
                                        <td><?php echo htmlspecialchars($produto); ?></td>
                                        <td><?php echo $quantidade; ?></td>
                                    </tr>
                                <?php endforeach; ?>
                            </tbody>
                        </table>
                    </div>
                </div>
            <?php endif; ?>

            <!-- Rodapé com PIX -->
            <div class="footer-pix">
                <img src="/sistema_terra/imagens/qrcode.png" alt="QR Code PIX">
                <p class="mb-0">PIX: 71 98221-8592 - Erilio Texerira L. Filho</p>
            </div>
            <!-- Botões de Ação -->
            <div class="mt-4 no-print">
                <button onclick="window.print()" class="btn btn-primary">
                    <i class="fas fa-print"></i> Imprimir
                </button>
                <form method="POST" action="" class="d-inline"
      onsubmit="return confirm('Tem certeza que deseja fechar a fatura exibida? Os lançamentos do período serão apagados e o saldo devedor será transferido para a próxima fatura.');">
    <input type="hidden" name="fechar_fatura" value="1">
    <input type="hidden" name="cliente_id" value="<?= htmlspecialchars($filtros['cliente_id'] ?? '') ?>">
    <input type="hidden" name="data_inicio" value="<?= htmlspecialchars($filtros['data_inicio'] ?? '') ?>">
    <input type="hidden" name="data_fim" value="<?= htmlspecialchars($filtros['data_fim'] ?? '') ?>">
    <button type="submit" class="btn btn-danger">
        <i class="fas fa-times"></i> Fechar Fatura
    </button>
</form>
            </div>
        </div>
        <?php endif; ?>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            document.querySelectorAll('.data').forEach(function(input) {
                input.addEventListener('focus', function() {
                    this.type = 'date';
                });
            });
        });
    </script>
</body>
</html>