<?php
require_once '../config/config.php';
require_once '../config/Database.php';
require_once '../class/Cliente.php';
require_once '../class/Produto.php';
require_once '../class/Lancamento.php';
require_once __DIR__ . '/../includes/header.php'; 

$database = new Database();
$db = $database->getConnection();

$cliente = new Cliente($db);
$produto = new Produto($db);
$lancamento = new Lancamento($db);

// Define período padrão (mês atual)
$data_inicio = date('Y-m-01'); // Primeiro dia do mês
$data_fim = date('Y-m-t'); // Último dia do mês

// Processa filtros de data e produto
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!empty($_POST['data_inicio'])) {
        $data_inicio = Database::converteDataMysql($_POST['data_inicio']);
    }
    if (!empty($_POST['data_fim'])) {
        $data_fim = Database::converteDataMysql($_POST['data_fim']);
    }
    
    // Filtro de produto
    $produto_filtro = !empty($_POST['produto_id']) ? $_POST['produto_id'] : null;
}

// Busca lançamentos do período
$filtros = [
    'data_inicio' => $data_inicio,
    'data_fim' => $data_fim
];

// Adiciona filtro de produto se selecionado
if (!empty($produto_filtro)) {
    $filtros['produto_id'] = $produto_filtro;
}

$lancamentos = $lancamento->listar($filtros);

// Busca todos os clientes cadastrados
$lista_clientes = $cliente->listar();

// Inicializa dados dos clientes
$dados_clientes = [];

// Se não houver filtro de produto, inicializa todos os clientes
if (empty($produto_filtro)) {
    foreach ($lista_clientes as $c) {
        $dados_clientes[$c['id']] = [
            'nome' => $c['nome'],
            'servicos' => 0,
            'entregas' => 0,
            'pagamentos' => 0
        ];
    }
}
// Quando há filtro de produto, inicializamos apenas os clientes que aparecem nos lançamentos filtrados

$totais_gerais = [
    'servicos' => 0,
    'entregas' => 0,
    'pagamentos' => 0,
    'saldo' => 0
];

// Preenche dados dos clientes com lançamentos (inclui clientes novos)
foreach ($lancamentos as $l) {
    // Verifica se o cliente usou o produto filtrado (quando há filtro)
    $cliente_usou_produto = false;
    
    if (!empty($produto_filtro)) {
        foreach ($l['servicos'] as $s) {
            if (isset($s['produto_id']) && $s['produto_id'] == $produto_filtro) {
                $cliente_usou_produto = true;
                break;
            }
        }
    } else {
        // Se não há filtro de produto, considera todos os clientes
        $cliente_usou_produto = true;
    }
    
    // Só processa os clientes que usaram o produto filtrado
    if ($cliente_usou_produto) {
        // Se o cliente foi cadastrado após a montagem de $lista_clientes, adiciona na hora:
        if (!isset($dados_clientes[$l['cliente_id']])) {
            $dados_clientes[$l['cliente_id']] = [
                'nome' => $l['cliente_nome'],
                'servicos' => 0,
                'entregas' => 0,
                'pagamentos' => 0
            ];
        }

        // Soma serviços
        foreach ($l['servicos'] as $s) {
            $dados_clientes[$l['cliente_id']]['servicos'] += $s['valor'];
            $totais_gerais['servicos'] += $s['valor'];
        }

        // Soma entregas e pagamentos
        $dados_clientes[$l['cliente_id']]['entregas'] += $l['valor_entrega'];
        $dados_clientes[$l['cliente_id']]['pagamentos'] += $l['valor_pagamento'];

        $totais_gerais['entregas'] += $l['valor_entrega'];
        $totais_gerais['pagamentos'] += $l['valor_pagamento'];
    }
}

// Calcula saldos e ordena por nome do cliente
foreach ($dados_clientes as &$cliente) {
    $cliente['saldo'] = $cliente['servicos'] + $cliente['entregas'] - $cliente['pagamentos'];
}
unset($cliente);
uasort($dados_clientes, function($a, $b) {
    return strcmp($a['nome'], $b['nome']);
});

$totais_gerais['saldo'] = $totais_gerais['servicos'] + $totais_gerais['entregas'] - $totais_gerais['pagamentos'];

// Processa uso de produtos
$produtos_utilizados = [];
foreach ($lancamentos as $l) {
    foreach ($l['servicos'] as $s) {
        if (!empty($s['produto_nome'])) {
            if (!isset($produtos_utilizados[$s['produto_nome']])) {
                $produtos_utilizados[$s['produto_nome']] = [
                    'quantidade' => 0,
                    'valor_total' => 0
                ];
            }
            $produtos_utilizados[$s['produto_nome']]['quantidade'] += $s['quantidade'];
            $produtos_utilizados[$s['produto_nome']]['valor_total'] += $s['valor'];
        }
    }
}
ksort($produtos_utilizados);

// Análise de estoque
$produtos = $produto->listar();
$estoque_critico = [];
foreach ($produtos as $p) {
    $percentual = ($p['estoque_inicial'] != 0) ? ($p['estoque_atual'] / $p['estoque_inicial']) * 100 : 0;

if ($percentual <= 20) {
    $estoque_critico[] = [
        'nome' => $p['nome'],
        'estoque_inicial' => $p['estoque_inicial'],
        'estoque_atual' => $p['estoque_atual'],
        'consumido' => $p['estoque_inicial'] - $p['estoque_atual'],
        'percentual' => round($percentual),
        'status' => ($percentual <= 10) ? 'ESTOQUE CRÍTICO' : 'ESTOQUE BAIXO'
    ];
}
}
// 3. ESTOQUE CRÍTICO - NOVA SEÇÃO (ADICIONE ESTE BLOCO)
$estoque_critico = $produto->listarEstoqueCritico(20); // 20% é o limite padrão
?>

<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Demonstrativo Financeiro - <?php echo SITE_TITLE; ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        @media print {
            .no-print {
                display: none !important;
            }
            .container {
                width: 100% !important;
                max-width: none !important;
            }
            .card {
                border: none !important;
            }
            .card-header {
                background-color: transparent !important;
            }
        }
        .status-low {
            color: #dc3545;
            font-weight: bold;
        }
        .card {
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <?php include '../includes/navbar.php'; ?>

    <div class="container mt-4">
        <!-- Filtros -->
        <div class="card mb-4 no-print">
            <div class="card-header">
                <h4 class="mb-0">Filtros</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="mb-3">
                                <label for="data_inicio" class="form-label">Data Início</label>
                                <input type="text" class="form-control data" id="data_inicio" name="data_inicio" 
                                       value="<?php echo Database::converteMysqlData($data_inicio); ?>" required>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="mb-3">
                                <label for="data_fim" class="form-label">Data Fim</label>
                                <input type="text" class="form-control data" id="data_fim" name="data_fim" 
                                       value="<?php echo Database::converteMysqlData($data_fim); ?>" required>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="mb-3">
                                <label for="produto_id" class="form-label">Filtrar por Produto</label>
                                <select class="form-select" id="produto_id" name="produto_id">
                                    <option value="">Todos os produtos</option>
                                    <?php foreach ($produto->listar() as $p): ?>
                                        <option value="<?php echo $p['id']; ?>" <?php echo (isset($produto_filtro) && $produto_filtro == $p['id']) ? 'selected' : ''; ?>>
                                            <?php echo htmlspecialchars($p['nome']); ?>
                                        </option>
                                    <?php endforeach; ?>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="mb-3">
                                <label class="form-label">&nbsp;</label>
                                <button type="submit" class="btn btn-primary d-block w-100">Gerar</button>
                            </div>
                        </div>
                    </div>
                </form>
            </div>
        </div>

        <!-- Cabeçalho do Demonstrativo -->
        <h2 class="mb-4">
            Demonstrativo Financeiro - 
            <?php echo Database::converteMysqlData($data_inicio); ?> a 
            <?php echo Database::converteMysqlData($data_fim); ?>
        </h2>

        <!-- Resumo por Cliente -->
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">Resumo por Cliente</h4>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-striped" id="tabelaClientes">
                        <thead>
                            <tr>
                                <th>Cliente</th>
                                <th>Serviços</th>
                                <th>Entregas</th>
                                <th>Pagamentos</th>
                                <th>Saldo</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($dados_clientes as $cliente): ?>
                                <tr>
                                    <td><?php echo htmlspecialchars($cliente['nome']); ?></td>
                                    <td>R$ <?php echo number_format($cliente['servicos'], 2, ',', '.'); ?></td>
                                    <td>R$ <?php echo number_format($cliente['entregas'], 2, ',', '.'); ?></td>
                                    <td>R$ <?php echo number_format($cliente['pagamentos'], 2, ',', '.'); ?></td>
                                    <td>R$ <?php echo number_format($cliente['saldo'], 2, ',', '.'); ?></td>
                                </tr>
                            <?php endforeach; ?>
                        </tbody>
                        <tfoot>
                            <tr>
                                <th>TOTAL</th>
                                <th>R$ <?php echo number_format($totais_gerais['servicos'], 2, ',', '.'); ?></th>
                                <th>R$ <?php echo number_format($totais_gerais['entregas'], 2, ',', '.'); ?></th>
                                <th>R$ <?php echo number_format($totais_gerais['pagamentos'], 2, ',', '.'); ?></th>
                                <th>R$ <?php echo number_format($totais_gerais['saldo'], 2, ',', '.'); ?></th>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>

        <!-- Produtos Utilizados -->
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">Produtos Utilizados no Período</h4>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-striped" id="tabelaProdutos">
                        <thead>
                            <tr>
                                <th>Produto</th>
                                <th>Quantidade</th>
                                <th>Valor Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($produtos_utilizados as $nome => $dados): ?>
                                <tr>
                                    <td><?php echo htmlspecialchars($nome); ?></td>
                                    <td><?php echo $dados['quantidade']; ?></td>
                                    <td>R$ <?php echo number_format($dados['valor_total'], 2, ',', '.'); ?></td>
                                </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Estoque Crítico -->
        <?php if (!empty($estoque_critico)): ?>
<div class="card border-danger mt-4">
    <div class="card-header bg-danger text-white">
        <h5 class="mb-0">Alerta de Estoque Crítico</h5>
    </div>
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-sm table-hover">
                <thead>
                    <tr>
                        <th>Produto</th>
                        <th class="text-end">Estoque Inicial</th>
                        <th class="text-end">Consumo Real</th>
                        <th class="text-end">Estoque Atual</th>
                        <th class="text-end">% Disponível</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($estoque_critico as $item): ?>
                    <tr class="<?= ($item['percentual'] <= 10) ? 'table-danger' : 'table-warning' ?>">
                        <td><?= htmlspecialchars($item['nome']) ?></td>
                        <td class="text-end"><?= $item['estoque_inicial'] ?></td>
                        <td class="text-end"><?= $item['consumo_real'] ?></td>
                        <td class="text-end"><?= $item['estoque_atual'] ?></td>
                        <td class="text-end"><?= $item['percentual'] ?>%</td>
                        <td><?= $item['status'] ?></td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    </div>
</div>
<?php endif; ?>

        <!-- Botões de Ação -->
        <div class="mt-4 no-print">
            <button onclick="window.print()" class="btn btn-primary">
                <i class="fas fa-print"></i> Imprimir
            </button>
            <button onclick="exportarExcel()" class="btn btn-success">
                <i class="fas fa-file-excel"></i> Exportar Excel
            </button>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.4.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery.mask/1.14.16/jquery.mask.min.js"></script>

    <script>
        $(document).ready(function() {
            // DataTables apenas para ordenação (sem paginação, info ou busca)
            $('#tabelaClientes').DataTable({
                paging: false,
                info: false,
                searching: false,
                ordering: true,
                language: {
                    url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/pt-BR.json'
                }
            });
            $('#tabelaProdutos').DataTable({
                paging: false,
                info: false,
                searching: false,
                ordering: true,
                language: {
                    url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/pt-BR.json'
                }
            });
            $('#tabelaEstoque').DataTable({
                paging: false,
                info: false,
                searching: false,
                ordering: true,
                language: {
                    url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/pt-BR.json'
                }
            });

            // Máscaras
            $('.data').mask('00/00/0000');
        });

        function exportarExcel() {
            // Implementar exportação para Excel se necessário
            alert('Função de exportação para Excel será implementada em breve!');
        }
    </script>
</body>
</html>