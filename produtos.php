<?php
require_once '../config/config.php';
require_once '../config/Database.php';
require_once '../class/Produto.php';
require_once __DIR__ . '/../includes/header.php'; 

$database = new Database();
$db = $database->getConnection();
$produto = new Produto($db);

$mensagem = '';
$erro = '';

// Processamento do formulário
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['acao'])) {
        switch ($_POST['acao']) {
            case 'criar':
            case 'atualizar':
                $id = isset($_POST['id']) ? $_POST['id'] : null;
                $nome = $_POST['nome'];
                $estoque_inicial = $_POST['estoque_inicial'];
                $data_cadastro = $_POST['data_cadastro'];
                $preco = str_replace(',', '.', str_replace('.', '', $_POST['preco']));
                $valor_compra = str_replace(',', '.', str_replace('.', '', $_POST['valor_compra']));
                $anotacoes = isset($_POST['anotacoes']) ? trim($_POST['anotacoes']) : '';
                
                // Debug
                error_log("POST data: " . print_r($_POST, true));
                error_log("Anotacoes: $anotacoes");

                if (empty($nome)) {
                    $erro = "O nome do produto é obrigatório!";
                } else {
                    if ($id) {
                        // Atualização
                        if ($produto->atualizar($id, $nome, $estoque_inicial, $data_cadastro, $preco, $valor_compra, $anotacoes)) {
                            $mensagem = "Produto atualizado com sucesso!";
                        } else {
                            $erro = "Erro ao atualizar produto.";
                        }
                    } else {
                        // Criação
                        if ($produto->criar($nome, $estoque_inicial, $data_cadastro, $preco, $valor_compra, $anotacoes)) {
                            $mensagem = "Produto cadastrado com sucesso!";
                        } else {
                            $erro = "Erro ao cadastrar produto.";
                        }
                    }
                }
                break;

            case 'excluir':
                $id = $_POST['id'];
                if ($produto->excluir($id)) {
                    $mensagem = "Produto excluído com sucesso!";
                } else {
                    $erro = "Não é possível excluir um produto que está em uso.";
                }
                break;
        }
    }
}

// Busca todos os produtos para listar
$produtos = $produto->listar();
?>

<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cadastro de Produtos - <?php echo SITE_TITLE; ?></title>
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
        .status-ok {
            color: green;
            font-weight: bold;
        }
        .status-low {
            color: red;
            font-weight: bold;
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

        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h4 class="mb-0">Cadastro de Produtos</h4>
                <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#produtoModal">
                    <i class="fas fa-plus"></i> Novo Produto
                </button>
            </div>
            <div class="card-body">
                <table id="tabelaProdutos" class="table table-striped">
                    <thead>
                        <tr>
                            <th>Nome</th>
                            <th>Estoque Inicial</th>
                            <th>Estoque Atual</th>
                            <th>Consumido</th>
                            <th>Data Cadastro</th>
                            <th>Preço</th>
                            <th>Valor Compra</th>
                            <th>Status</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
<?php foreach ($produtos as $p): ?>
    <tr>
        <td><?php echo htmlspecialchars($p['nome']); ?></td>
        <td><?php echo $p['estoque_inicial']; ?></td>
        <td><?php echo $p['estoque_atual']; ?></td>
        <td><?php echo $p['estoque_consumido']; ?></td>
        <td><?php echo date('d/m/Y', strtotime($p['data_cadastro'])); ?></td>
        <td>R$ <?php echo number_format($p['preco'], 2, ',', '.'); ?></td>
        <td>
            R$
            <?php
                echo isset($p['valor_compra']) && $p['valor_compra'] !== null
                    ? number_format($p['valor_compra'], 2, ',', '.')
                    : '0,00';
            ?>
        </td>
        <td>
            <?php 
            $status = $p['estoque_atual'] <= ($p['estoque_inicial'] * 0.2) ? 
                '<span class="status-low">BAIXO</span>' : 
                '<span class="status-ok">OK</span>';
            echo $status;
            ?>
        </td>
        <td>
            <?php 
            // Garantir que o campo anotacoes esteja presente no array
            $produto_json = $p;
            if (!isset($produto_json['anotacoes'])) {
                $produto_json['anotacoes'] = null;
            }
            ?>
            <button type="button" class="btn btn-sm btn-warning" 
                    onclick="editarProduto(<?php echo htmlspecialchars(json_encode($produto_json)); ?>)">
                <i class="fas fa-edit"></i>
            </button>
            <button type="button" class="btn btn-sm btn-danger" 
                    onclick="confirmarExclusao(<?php echo $p['id']; ?>)">
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

    <!-- Modal de Produto -->
    <div class="modal fade" id="produtoModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <form id="formProduto" method="POST" onsubmit="logFormData(event)">
                    <div class="modal-header">
                        <h5 class="modal-title" id="modalTitle">Novo Produto</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" name="acao" value="criar">
                        <input type="hidden" name="id" id="id">
                        
                        <div class="mb-3">
                            <label for="nome" class="form-label">Nome</label>
                            <input type="text" class="form-control" id="nome" name="nome" required>
                        </div>
                        
                        <div class="mb-3">
                            <label for="estoque_inicial" class="form-label">Estoque Inicial</label>
                            <input type="number" class="form-control" id="estoque_inicial" name="estoque_inicial" value="0" min="0">
                        </div>
                        
                        <div class="mb-3">
                            <label for="data_cadastro" class="form-label">Data de Cadastro</label>
                            <input type="date" class="form-control" id="data_cadastro" name="data_cadastro" 
                                   value="<?php echo date('Y-m-d'); ?>" required>
                        </div>
                        
                        <div class="mb-3">
                            <label for="preco" class="form-label">Preço Unitário</label>
                            <div class="input-group">
                                <span class="input-group-text">R$</span>
                                <input type="text" class="form-control" id="preco" name="preco" value="0,00" required>
                            </div>
                        </div>

                        <div class="mb-3">
                            <label for="valor_compra" class="form-label">Valor Compra</label>
                            <div class="input-group">
                                <span class="input-group-text">R$</span>
                                <input type="text" class="form-control" id="valor_compra" name="valor_compra" value="0,00" required>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <label for="anotacoes" class="form-label">Anotações</label>
                            <textarea class="form-control" id="anotacoes" name="anotacoes" rows="3"></textarea>
                        </div>
                        
                        <script>
                            // Debug - verificar se o campo está presente no formulário
                            console.log('Campo anotacoes no formulário:', document.getElementById('anotacoes'));
                        </script>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                        <button type="submit" class="btn btn-primary">Salvar</button>
                    </div>
                </form>
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
                        Tem certeza que deseja excluir este produto?
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
        // Função para logar os dados do formulário antes do envio
        function logFormData(event) {
            // Não impede o envio do formulário
            const formData = new FormData(document.getElementById('formProduto'));
            console.log('Dados do formulário a serem enviados:');
            for (let pair of formData.entries()) {
                console.log(pair[0] + ': ' + pair[1]);
            }
            // Verificar especificamente o campo anotacoes
            console.log('Campo anotacoes:', document.getElementById('anotacoes').value);
        }
        
        $(document).ready(function() {
            // Inicializa DataTable
            $('#tabelaProdutos').DataTable({
                language: {
                    url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/pt-BR.json'
                }
            });

            // Máscara para valor monetário
            $('#preco, #valor_compra').mask('#.##0,00', {reverse: true});

            // Remove mensagens após 3 segundos
            setTimeout(function() {
                $('.toast-message').fadeOut('slow');
            }, 3000);
        });

        function editarProduto(produto) {
            document.getElementById('id').value = produto.id;
            document.getElementById('nome').value = produto.nome;
            document.getElementById('estoque_inicial').value = produto.estoque_inicial;
            document.getElementById('data_cadastro').value = produto.data_cadastro;
            document.getElementById('preco').value = formatarMoeda(produto.preco);
            document.getElementById('valor_compra').value = formatarMoeda(produto.valor_compra);
            
            // Debug
            console.log('Produto completo:', produto);
            console.log('Anotacoes:', produto.anotacoes);
            
            // Garantir que o valor seja definido mesmo que seja null ou undefined
            document.getElementById('anotacoes').value = produto.anotacoes || '';
            
            document.querySelector('[name="acao"]').value = 'atualizar';
            document.getElementById('modalTitle').textContent = 'Editar Produto';
            
            new bootstrap.Modal(document.getElementById('produtoModal')).show();
        }

        function confirmarExclusao(id) {
            document.getElementById('excluir_id').value = id;
            new bootstrap.Modal(document.getElementById('confirmacaoModal')).show();
        }

        function formatarMoeda(valor) {
            return Number(valor).toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }

        // Limpa o formulário quando o modal é fechado
        document.getElementById('produtoModal').addEventListener('hidden.bs.modal', function () {
            document.getElementById('formProduto').reset();
            document.getElementById('id').value = '';
            document.querySelector('[name="acao"]').value = 'criar';
            document.getElementById('modalTitle').textContent = 'Novo Produto';
            document.getElementById('data_cadastro').value = new Date().toISOString().split('T')[0];
            document.getElementById('preco').value = '0,00';
            document.getElementById('valor_compra').value = '0,00';
            document.getElementById('anotacoes').value = '';
        });
    </script>
</body>
</html>