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

$mensagem = '';
$erro = '';

// Lista de clientes e produtos para os selects
$clientes = $cliente->listar();
$produtos = $produto->listar();

// Processamento do formulário
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        if (isset($_POST['acao'])) {
            switch ($_POST['acao']) {
                case 'criar':
                case 'atualizar':
                    $dados = [
                        'cliente_id' => $_POST['cliente_id'],
                        'data_lancamento' => Database::converteDataMysql($_POST['data_lancamento']),
                        'valor_entrega' => $_POST['valor_entrega'],
                        'valor_pagamento' => $_POST['valor_pagamento'],
                        'fatura_anterior' => isset($_POST['fatura_anterior']) ? $_POST['fatura_anterior'] : '0,00',
                        'pagamento_fatura_anterior' => isset($_POST['pagamento_fatura_anterior']) ? $_POST['pagamento_fatura_anterior'] : '0,00',
                        'observacao' => isset($_POST['observacao']) ? $_POST['observacao'] : '',
                        'servicos' => []
                    ];

                    // Processa os serviços (opcional)
                    if (isset($_POST['servico_descricao']) && is_array($_POST['servico_descricao'])) {
                        foreach ($_POST['servico_descricao'] as $key => $descricao) {
                            if (!empty($descricao)) {
                                $produto_id = $_POST['servico_produto'][$key];
                                // Se não selecionou produto, define como NULL
                                if ($produto_id === "" || strtolower($produto_id) === "null") {
                                    $produto_id = null;
                                }
                                $dados['servicos'][] = [
                                    'descricao' => $descricao,
                                    'quantidade' => $_POST['servico_quantidade'][$key],
                                    'produto_id' => $produto_id,
                                    'valor' => $_POST['servico_valor'][$key]
                                ];
                            }
                        }
                    }

                    if ($_POST['acao'] === 'criar') {
                        if ($lancamento->criar($dados)) {
                            $mensagem = "Lançamento registrado com sucesso!";
                        }
                    } else {
                        if ($lancamento->atualizar($_POST['id'], $dados)) {
                            $mensagem = "Lançamento atualizado com sucesso!";
                        }
                    }
                    break;

                case 'excluir':
                    if ($lancamento->excluir($_POST['id'])) {
                        $mensagem = "Lançamento excluído com sucesso!";
                    }
                    break;
            }
        }
    } catch (Exception $e) {
        $erro = "Erro: " . $e->getMessage();
    }
}

$filtros = [];

if (isset($_GET['data_inicio'])) {
    $filtros['data_inicio'] = Database::converteDataMysql($_GET['data_inicio']);
}

if (isset($_GET['data_fim'])) {
    $filtros['data_fim'] = Database::converteDataMysql($_GET['data_fim']);
}

if (isset($_GET['cliente_id'])) {
    $filtros['cliente_id'] = $_GET['cliente_id'];
}

// ADICIONE ESTA LINHA - Filtro por texto no serviço
if (isset($_GET['texto_servico']) && !empty($_GET['texto_servico'])) {
    $filtros['texto_servico'] = $_GET['texto_servico'];
}

$lancamentos = $lancamento->listar($filtros);
?>

<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lançamentos - <?php echo SITE_TITLE; ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        .toast-message {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
        }
        .servico-item {
            background-color: #f8f9fa;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
        }
        .servico-total {
            font-weight: bold;
            font-size: 1.1em;
        }
        .remove-servico {
            color: #dc3545;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <?php include '../includes/navbar.php'; ?>

    <div class="container mt-4">
        <?php if ($mensagem): ?>
            <div class="alert alert-success alert-dismissible fade show toast-message" role="alert">
                <?php echo $mensagem; ?>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        <?php endif; ?>

        <?php if ($erro): ?>
            <div class="alert alert-danger alert-dismissible fade show toast-message" role="alert">
                <?php echo $erro; ?>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        <?php endif; ?>

        <!-- Formulário de Lançamento -->
        <div class="card mb-4">
            <div class="card-header">
                <h4 class="mb-0">Novo Lançamento</h4>
            </div>
            <div class="card-body">
                <form id="formLancamento" method="POST">
                    <input type="hidden" name="acao" value="criar">
                    <input type="hidden" name="id" id="lancamento_id">

                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="cliente_id" class="form-label">Cliente</label>
                                <select class="form-select" id="cliente_id" name="cliente_id" required>
                                    <option value="">Selecione um cliente</option>
                                    <?php foreach ($clientes as $c): ?>
                                        <option value="<?php echo $c['id']; ?>">
                                            <?php echo htmlspecialchars($c['nome']); ?>
                                        </option>
                                    <?php endforeach; ?>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="data_lancamento" class="form-label">Data</label>
                                <input type="text" class="form-control data" id="data_lancamento" 
                                       name="data_lancamento" value="<?php echo date('d/m/Y'); ?>" required>
                            </div>
                        </div>
                    </div>

                    <div id="servicos_container">
                        <!-- Serviços serão adicionados aqui -->
                    </div>

                    <div class="mb-3">
                        <button type="button" class="btn btn-success" onclick="adicionarServico()">
                            <i class="fas fa-plus"></i> Adicionar Serviço
                        </button>
                    </div>

                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="valor_entrega" class="form-label">Valor de Entrega</label>
                                <div class="input-group">
                                    <span class="input-group-text">R$</span>
                                    <input type="text" class="form-control money" id="valor_entrega" 
                                           name="valor_entrega" value="0,00">
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="valor_pagamento" class="form-label">Pagamento/Desconto</label>
                                <div class="input-group">
                                    <span class="input-group-text">R$</span>
                                    <input type="text" class="form-control money" id="valor_pagamento" 
                                           name="valor_pagamento" value="0,00">
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="row">
                        <div class="col-md-4">
                            <div class="mb-3">
                                <label for="fatura_anterior" class="form-label">Fatura anterior R$</label>
                                <div class="input-group">
                                    <span class="input-group-text">R$</span>
                                    <input type="text" class="form-control money" id="fatura_anterior" 
                                           name="fatura_anterior" value="0,00" oninput="calcularSaldoFaturaAnterior()">
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="mb-3">
                                <label for="pagamento_fatura_anterior" class="form-label">Pagtº R$</label>
                                <div class="input-group">
                                    <span class="input-group-text">R$</span>
                                    <input type="text" class="form-control money" id="pagamento_fatura_anterior" 
                                           name="pagamento_fatura_anterior" value="0,00" oninput="calcularSaldoFaturaAnterior()">
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="mb-3">
                                <label for="saldo_fatura_anterior" class="form-label">Saldo da Fatura anterior R$</label>
                                <div class="input-group">
                                    <span class="input-group-text">R$</span>
                                    <input type="text" class="form-control money" id="saldo_fatura_anterior" 
                                           name="saldo_fatura_anterior" value="0,00" readonly>
                                </div>
                            </div>
                        </div>
                    </div>


                    <div class="row align-items-end">
                        <div class="col-md-3">
                            <div class="mb-3">
                                <button type="submit" class="btn btn-primary">Salvar Lançamento</button>
                                <button type="button" class="btn btn-secondary" onclick="novoLancamento()">Novo</button>
                            </div>
                        </div>
                        <div class="col-md-9">
                            <div class="mb-3">
                                <label for="observacao" class="form-label">Observação</label>
                                <input type="text" class="form-control" id="observacao" name="observacao" placeholder="Digite uma observação para este lançamento">
                            </div>
                        </div>
                    </div>
                </form>
            </div>
        </div>

        <!-- Lista de Lançamentos -->
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">Lançamentos Registrados</h4>
            </div>
            <div class="card-body">
                <!-- Filtros -->
                <form class="mb-4" method="GET">
    <div class="row">
        <div class="col-md-2">
            <div class="mb-3">
                <label for="filtro_data_inicio" class="form-label">Data Início</label>
                <input type="text" class="form-control data" id="filtro_data_inicio" 
                       name="data_inicio" value="<?php echo isset($_GET['data_inicio']) ? htmlspecialchars($_GET['data_inicio']) : ''; ?>">
            </div>
        </div>
        <div class="col-md-2">
            <div class="mb-3">
                <label for="filtro_data_fim" class="form-label">Data Fim</label>
                <input type="text" class="form-control data" id="filtro_data_fim" 
                       name="data_fim" value="<?php echo isset($_GET['data_fim']) ? htmlspecialchars($_GET['data_fim']) : ''; ?>">
            </div>
        </div>
        <div class="col-md-3">
            <div class="mb-3">
                <label for="filtro_cliente" class="form-label">Cliente</label>
                <select class="form-select" id="filtro_cliente" name="cliente_id">
                    <option value="">Todos os clientes</option>
                    <?php foreach ($clientes as $c): ?>
                        <option value="<?php echo $c['id']; ?>" 
                            <?php echo (isset($_GET['cliente_id']) && $_GET['cliente_id'] == $c['id']) ? 'selected' : ''; ?>>
                            <?php echo htmlspecialchars($c['nome']); ?>
                        </option>
                    <?php endforeach; ?>
                </select>
            </div>
        </div>
        <div class="col-md-3">
            <div class="mb-3">
                <label for="filtro_texto_servico" class="form-label">Buscar no Serviço</label>
                <input type="text" class="form-control" id="filtro_texto_servico" 
                       name="texto_servico" placeholder="Digite parte do serviço"
                       value="<?php echo isset($_GET['texto_servico']) ? htmlspecialchars($_GET['texto_servico']) : ''; ?>">
            </div>
        </div>
        <div class="col-md-2">
            <div class="mb-3">
                <label class="form-label">&nbsp;</label>
                <button type="submit" class="btn btn-primary d-block w-100">Filtrar</button>
            </div>
        </div>
    </div>
</form>

                <table id="tabelaLancamentos" class="table table-striped">
                    <thead>
                        <tr>
                            <th>Data</th>
                            <th>Cliente</th>
                            <th>Serviços</th>
                            <th>Valor Total</th>
                            <th>Entrega</th>
                            <th>Pagamento</th>
                            <th>Saldo</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($lancamentos as $l): ?>
                            <?php
                            $total_servicos = 0;
                            foreach ($l['servicos'] as $s) {
                                $total_servicos += $s['valor'];
                            }
                            $saldo = $total_servicos + $l['valor_entrega'] - $l['valor_pagamento'];
                            ?>
                            <tr>
                                <td><?php echo Database::converteMysqlData($l['data_lancamento']); ?></td>
                                <td><?php echo htmlspecialchars($l['cliente_nome']); ?></td>
                                <td><?php echo count($l['servicos']); ?> serviço(s)</td>
                                <td>R$ <?php echo number_format($total_servicos, 2, ',', '.'); ?></td>
                                <td>R$ <?php echo number_format($l['valor_entrega'], 2, ',', '.'); ?></td>
                                <td>R$ <?php echo number_format($l['valor_pagamento'], 2, ',', '.'); ?></td>
                                <td>R$ <?php echo number_format($saldo, 2, ',', '.'); ?></td>
                                <td>
                                    <button type="button" class="btn btn-sm btn-warning" 
                                            onclick='editarLancamento(<?php echo json_encode($l); ?>)'>
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button type="button" class="btn btn-sm btn-danger" 
                                            onclick="confirmarExclusao(<?php echo $l['id']; ?>)">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Modal de Confirmação de Exclusão -->
    <div class="modal fade" id="confirmacaoModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <form method="POST">
                    <input type="hidden" name="acao" value="excluir">
                    <input type="hidden" name="id" id="excluir_id">
                    <div class="modal-header">
                        <h5 class="modal-title">Confirmar Exclusão</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        Tem certeza que deseja excluir este lançamento?
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                        <button type="submit" class="btn btn-danger">Excluir</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.4.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery.mask/1.14.16/jquery.mask.min.js"></script>

    <script>
let servicoCount = 0;
const produtos = <?php echo json_encode($produtos); ?>;
const clientes = <?php echo json_encode($clientes); ?>;

function calcularSaldoFaturaAnterior() {
    const faturaAnterior = parseFloat($('#fatura_anterior').val().replace('.', '').replace(',', '.')) || 0;
    const pagamentoFaturaAnterior = parseFloat($('#pagamento_fatura_anterior').val().replace('.', '').replace(',', '.')) || 0;
    const saldo = faturaAnterior - pagamentoFaturaAnterior;
    $('#saldo_fatura_anterior').val(saldo.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
}

$(document).ready(function() {
    // Inicializa DataTable
    $('#tabelaLancamentos').DataTable({
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/pt-BR.json'
        },
        order: [[0, 'desc']]
    });

    // Máscaras
    $('.data').mask('00/00/0000');
    $('.money').mask('#.##0,00', {reverse: true});

    // Remove mensagens após 3 segundos
    setTimeout(function() {
        $('.toast-message').fadeOut('slow');
    }, 3000);

    // Adiciona um serviço automaticamente ao abrir a tela (opcional, não obrigatório)
    if ($('#servicos_container').children().length === 0) {
        adicionarServico();
    }
    // Evento para detectar alterações manuais no valor
    $(document).on('keyup', 'input[name="servico_valor[]"]', function() {
        $(this).data('manually-changed', true);
    });

    // Evento para resetar a flag quando trocar de produto
    $(document).on('change', 'select[name="servico_produto[]"]', function() {
        const valorInput = $(this).closest('.servico-item').find('input[name="servico_valor[]"]');
        valorInput.data('manually-changed', false);
    });
    
    // Evento quando seleciona um cliente para preencher fatura anterior
    $('#cliente_id').on('change', function() {
        console.log('Clientes array:', clientes);
        const clienteId = $(this).val();
        console.log('Cliente selecionado ID:', clienteId);
        if (clienteId) {
            const cliente = clientes.find(c => c.id == clienteId);
            console.log('Cliente encontrado:', cliente);
            if (cliente) {
                console.log('Fatura anterior do cliente:', cliente.fatura_anterior);
                $('#fatura_anterior').val(formatarMoeda(cliente.fatura_anterior || 0));
                $('#pagamento_fatura_anterior').val(formatarMoeda(0));
                calcularSaldoFaturaAnterior();
            }
        }
    });
    
    // Tooltip removido conforme solicitação do cliente
});

function adicionarServico() {
    servicoCount++;
    const html = `
        <div class="servico-item" id="servico_${servicoCount}">
            <div class="row">
                <div class="col-md-4">
                    <div class="mb-3">
                        <label class="form-label">Descrição</label>
                        <input type="text" class="form-control" name="servico_descricao[]">
                    </div>
                </div>
                <div class="col-md-2">
                    <div class="mb-3">
                        <label class="form-label">Quantidade</label>
                        <input type="number" class="form-control" name="servico_quantidade[]" 
                               value="1" min="0" onchange="calcularValor(${servicoCount})">
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="mb-3">
                        <label class="form-label">Produto (Opcional)</label>
                        <select class="form-select" name="servico_produto[]" onchange="atualizarProduto(${servicoCount})">
                            <option value="">Sem produto (valor manual)</option>
                            ${produtos.map(p => `
                                <option value="${p.id}" data-preco="${p.preco}">
                                    ${p.nome} - R$ ${formatarMoeda(p.preco)}
                                </option>
                            `).join('')}
                        </select>
                    </div>
                </div>
                <div class="col-md-2">
                    <div class="mb-3">
                        <label class="form-label">Valor</label>
                        <div class="input-group">
                            <span class="input-group-text">R$</span>
                            <input type="text" class="form-control money" name="servico_valor[]" 
                                   value="0,00" onchange="marcarValorManual(${servicoCount})">
                        </div>
                    </div>
                </div>
                <div class="col-md-1">
                    <div class="mb-3">
                        <label class="form-label">&nbsp;</label>
                        <button type="button" class="btn btn-danger" onclick="removerServico(${servicoCount})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    $('#servicos_container').append(html);
    $(`#servico_${servicoCount} .money`).mask('#.##0,00', {reverse: true});
}

function removerServico(id) {
    $(`#servico_${id}`).remove();
}

function calcularValor(servicoId) {
    const container = $(`#servico_${servicoId}`);
    const select = container.find('select[name="servico_produto[]"]');
    const quantidade = container.find('input[name="servico_quantidade[]"]').val();
    const valorInput = container.find('input[name="servico_valor[]"]');

    if (select.val()) {
        const preco = select.find(':selected').data('preco');
        const valor = preco * quantidade;
        // Só sugere valor se não foi mudado manualmente
        if (!valorInput.data('manually-changed')) {
            valorInput.val(valor.toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }));
        }
    }
}

function atualizarProduto(servicoId) {
    const container = $(`#servico_${servicoId}`);
    const select = container.find('select[name="servico_produto[]"]');
    const valorInput = container.find('input[name="servico_valor[]"]');
    const quantidadeInput = container.find('input[name="servico_quantidade[]"]');

    if (select.val()) {
        const preco = select.find(':selected').data('preco');
        const quantidade = quantidadeInput.val();
        const valor = preco * quantidade;
        if (!valorInput.data('manually-changed')) {
            valorInput.val(valor.toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }));
        }
    }
}

function marcarValorManual(servicoId) {
    const container = $(`#servico_${servicoId}`);
    const valorInput = container.find('input[name="servico_valor[]"]');
    valorInput.data('manually-changed', true);
}

function editarLancamento(lancamento) {
    // Limpa serviços existentes
    $('#servicos_container').empty();
    servicoCount = 0;

    // Preenche dados básicos
    $('#lancamento_id').val(lancamento.id);
    $('#cliente_id').val(lancamento.cliente_id);
    $('#data_lancamento').val(formatarData(lancamento.data_lancamento));
    $('#valor_entrega').val(formatarMoeda(lancamento.valor_entrega));
    $('#valor_pagamento').val(formatarMoeda(lancamento.valor_pagamento));
    $('#fatura_anterior').val(formatarMoeda(lancamento.fatura_anterior ?? 0));
    $('#pagamento_fatura_anterior').val(formatarMoeda(lancamento.pagamento_fatura_anterior ?? 0));
    $('#saldo_fatura_anterior').val(formatarMoeda(lancamento.saldo_fatura_anterior ?? 0));
    $('#observacao').val(lancamento.observacao ?? '');
    
    // Adiciona serviços
    lancamento.servicos.forEach(servico => {
        adicionarServico();
        const container = $(`#servico_${servicoCount}`);
        container.find('input[name="servico_descricao[]"]').val(servico.descricao);
        container.find('input[name="servico_quantidade[]"]').val(servico.quantidade);
        // Garante que valor null ou vazio não cause erro
        container.find('select[name="servico_produto[]"]').val(servico.produto_id ? servico.produto_id : "");
        container.find('input[name="servico_valor[]"]').val(formatarMoeda(servico.valor));
        // Marca o valor como alterado manualmente para evitar sobrescrita
        container.find('input[name="servico_valor[]"]').data('manually-changed', true);
    });

    $('[name="acao"]').val('atualizar');
    window.scrollTo(0, 0);
}

function confirmarExclusao(id) {
    $('#excluir_id').val(id);
    new bootstrap.Modal(document.getElementById('confirmacaoModal')).show();
}

function novoLancamento() {
    $('#formLancamento')[0].reset();
    $('#lancamento_id').val('');
    $('[name="acao"]').val('criar');
    $('#servicos_container').empty();
    servicoCount = 0;
    adicionarServico();
    $('#data_lancamento').val(new Date().toLocaleDateString('pt-BR'));
    $('#fatura_anterior').val('0,00');
    $('#pagamento_fatura_anterior').val('0,00');
    $('#saldo_fatura_anterior').val('0,00');
    $('#observacao').val('');
}

function formatarData(data) {
    if (!data) return '';
    if (data.includes('/')) return data; // já está dd/mm/yyyy
    const [ano, mes, dia] = data.split('-');
    return `${dia}/${mes}/${ano}`;
}

function formatarMoeda(valor) {
    if (typeof valor === 'string') valor = parseFloat(valor.replace(',', '.'));
    if (isNaN(valor)) valor = 0;
    return valor.toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}
</script>
</body>
</html>