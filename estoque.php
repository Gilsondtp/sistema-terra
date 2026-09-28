<?php
require_once '../config/config.php';
require_once '../config/Database.php';
require_once '../class/Produto.php';
require_once '../class/Lancamento.php';
require_once __DIR__ . '/../includes/header.php';

$database = new Database();
$db = $database->getConnection();
$produto = new Produto($db);
$lancamento = new Lancamento($db);

// Define período padrão (mês atual)
$data_inicio = date('Y-m-01');
$data_fim = date('Y-m-t');

// Busca todos os produtos e consumo do período
$produtos = $produto->listar();
$consumoPeriodo = $lancamento->getProdutosUtilizadosPeriodo($data_inicio, $data_fim);

// Se for o primeiro dia do mês, estoque inicial recebe estoque atual
if (date('d') === '01') {
    foreach ($produtos as $p) {
        $produto->atualizaEstoqueInicial($p['id'], $p['estoque_atual']);
    }
    // Recarregar produtos após atualização
    $produtos = $produto->listar();
}

// Inicializa totais
$total_estoque_inicial = 0;
$total_valor_compra = 0.0;
$total_valor_estoque = 0.0;
$total_valor_venda = 0.0;
$total_consumo = 0;
$total_valor_vendido = 0.0;
$total_estoque_atual = 0;

// Atualiza produtos com consumo do período
foreach ($produtos as &$p) {
    $p['consumo_periodo'] = isset($consumoPeriodo[$p['id']]) ? $consumoPeriodo[$p['id']]['quantidade'] : 0;
    $p['estoque_atual'] = $p['estoque_inicial'] - $p['consumo_periodo'];
    
    // Atualiza totais
    $total_estoque_inicial += $p['estoque_inicial'];
    $total_valor_compra += $p['valor_compra'];
    $total_valor_estoque += ($p['valor_compra'] * $p['estoque_inicial']);
    $total_valor_venda += $p['preco'];
    $total_consumo += $p['consumo_periodo'];
    $total_valor_vendido += ($p['valor_compra'] * $p['consumo_periodo']); // AJUSTE
    $total_estoque_atual += $p['estoque_atual'];
}
unset($p);
?>

<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Estoque - <?php echo SITE_TITLE; ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .table thead th, .table tfoot td {
            background-color: #299e41;
            color: #fff;
            font-weight: bold;
            text-align: center;
        }
        .table tfoot td {
            font-size: 1.1em;
        }
        .btn-print {
            background-color: #007bff;
            color: #fff;
        }
        .btn-print:hover {
            background-color: #0056b3;
            color: #fff;
        }
        .logo-relatorio {
            float: right;
            height: 48px;
        }
        @media print {
            .btn, .navbar, .card-header {
                display: none !important;
            }
            .logo-relatorio {
                float: none;
                display: block;
                margin-left: auto;
                margin-right: auto;
            }
        }
    </style>
</head>
<body>
    <?php include '../includes/navbar.php'; ?>

    <div class="container mt-4">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center print-hidden">
                <h4 class="mb-0">Relatório de Estoque</h4>
                <img src="../imagens/cabecario.jpg" alt="Logo" class="logo-relatorio"/>
            </div>
            <div class="card-body">
                <div class="mb-3 print-hidden">
                    <button class="btn btn-success" onclick="location.reload()">
                        <i class="fas fa-sync-alt"></i> Atualizar Relatório
                    </button>
                    <button class="btn btn-print" onclick="window.print()">
                        <i class="fas fa-print"></i> Imprimir
                    </button>
                </div>
                <div class="table-responsive">
                    <table class="table table-bordered align-middle" id="tabelaEstoque">
                        <thead>
                            <tr>
                                <th>Produto</th>
                                <th>Estoque Inicial</th>
                                <th>Valor de Compra</th>
                                <th>Valor do Estoque</th>
                                <th>Valor de Venda</th>
                                <th>Consumo</th>
                                <th>Custo Chapas</th>
                                <th>Estoque Atual</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($produtos as $p): ?>
                            <tr>
                                <td><?php echo htmlspecialchars($p['nome']); ?></td>
                                <td style="text-align:right"><?php echo $p['estoque_inicial']; ?></td>
                                <td style="text-align:right">R$ <?php echo number_format($p['valor_compra'], 2, ',', '.'); ?></td>
                                <td style="text-align:right">R$ <?php echo number_format($p['valor_compra'] * $p['estoque_inicial'], 2, ',', '.'); ?></td>
                                <td style="text-align:right">R$ <?php echo number_format($p['preco'], 2, ',', '.'); ?></td>
                                <td style="text-align:right"><?php echo $p['consumo_periodo']; ?></td>
                                <td style="text-align:right">R$ <?php echo number_format($p['valor_compra'] * $p['consumo_periodo'], 2, ',', '.'); ?></td>
                                <td style="text-align:right"><?php echo $p['estoque_atual']; ?></td>
                            </tr>
                            <?php endforeach; ?>
                        </tbody>
                        <tfoot>
                            <tr>
                                <td style="text-align:center;">Total</td>
                                <td style="text-align:right;"><?php echo $total_estoque_inicial; ?></td>
                                <td style="text-align:right;">R$ <?php echo number_format($total_valor_compra/count($produtos), 2, ',', '.'); ?></td>
                                <td style="text-align:right;">R$ <?php echo number_format($total_valor_estoque, 2, ',', '.'); ?></td>
                                <td style="text-align:right;">R$ <?php echo number_format($total_valor_venda/count($produtos), 2, ',', '.'); ?></td>
                                <td style="text-align:right;"><?php echo $total_consumo; ?></td>
                                <td style="text-align:right;">R$ <?php echo number_format($total_valor_vendido, 2, ',', '.'); ?></td>
                                <td style="text-align:right;"><?php echo $total_estoque_atual; ?></td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>
    </div>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</body>
</html>