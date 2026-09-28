<?php
require_once '../config/config.php';
require_once '../config/Database.php';
require_once '../class/Cliente.php';
require_once __DIR__ . '/../includes/header.php'; 

$database = new Database();
$db = $database->getConnection();
$cliente = new Cliente($db);

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
                $telefone = $_POST['telefone'];
                $rua_bairro = $_POST['rua_bairro'];
                $cidade = $_POST['cidade'];

                if (empty($nome)) {
                    $erro = "O nome do cliente é obrigatório!";
                } else {
                    if ($id) {
                        // Atualização
                        if ($cliente->atualizar($id, $nome, $telefone, $rua_bairro, $cidade)) {
                            $mensagem = "Cliente atualizado com sucesso!";
                        } else {
                            $erro = "Erro ao atualizar cliente.";
                        }
                    } else {
                        // Criação
                        if ($cliente->criar($nome, $telefone, $rua_bairro, $cidade)) {
                            $mensagem = "Cliente cadastrado com sucesso!";
                        } else {
                            $erro = "Erro ao cadastrar cliente.";
                        }
                    }
                }
                break;

            case 'excluir':
                $id = $_POST['id'];
                if ($cliente->excluir($id)) {
                    $mensagem = "Cliente excluído com sucesso!";
                } else {
                    $erro = "Não é possível excluir um cliente que possui lançamentos.";
                }
                break;
        }
    }
}

// Busca todos os clientes para listar
$clientes = $cliente->listar();
?>

<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cadastro de Clientes - <?php echo SITE_TITLE; ?></title>
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
                <h4 class="mb-0">Cadastro de Clientes</h4>
                <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#clienteModal">
                    <i class="fas fa-plus"></i> Novo Cliente
                </button>
            </div>
            <div class="card-body">
                <table id="tabelaClientes" class="table table-striped">
                    <thead>
                        <tr>
                            <th>Nome</th>
                            <th>Telefone</th>
                            <th>Endereço</th>
                            <th>Cidade</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($clientes as $c): ?>
                            <tr>
                                <td><?php echo htmlspecialchars($c['nome']); ?></td>
                                <td><?php echo htmlspecialchars($c['telefone']); ?></td>
                                <td><?php echo htmlspecialchars($c['rua_bairro']); ?></td>
                                <td><?php echo htmlspecialchars($c['cidade']); ?></td>
                                <td>
                                    <button type="button" class="btn btn-sm btn-warning" 
                                            onclick="editarCliente(<?php echo htmlspecialchars(json_encode($c)); ?>)">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button type="button" class="btn btn-sm btn-danger" 
                                            onclick="confirmarExclusao(<?php echo $c['id']; ?>)">
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

    <!-- Modal de Cliente -->
    <div class="modal fade" id="clienteModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <form id="formCliente" method="POST">
                    <div class="modal-header">
                        <h5 class="modal-title" id="modalTitle">Novo Cliente</h5>
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
                            <label for="telefone" class="form-label">Telefone</label>
                            <input type="text" class="form-control" id="telefone" name="telefone">
                        </div>
                        
                        <div class="mb-3">
                            <label for="rua_bairro" class="form-label">Endereço</label>
                            <input type="text" class="form-control" id="rua_bairro" name="rua_bairro">
                        </div>
                        
                        <div class="mb-3">
                            <label for="cidade" class="form-label">Cidade</label>
                            <input type="text" class="form-control" id="cidade" name="cidade">
                        </div>
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
                        Tem certeza que deseja excluir este cliente?
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
        $(document).ready(function() {
            // Inicializa DataTable
            $('#tabelaClientes').DataTable({
                language: {
                    url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/pt-BR.json'
                }
            });

            // Máscara para telefone
            $('#telefone').mask('(00) 00000-0000');

            // Remove mensagens após 3 segundos
            setTimeout(function() {
                $('.toast-message').fadeOut('slow');
            }, 3000);
        });

        function editarCliente(cliente) {
            document.getElementById('id').value = cliente.id;
            document.getElementById('nome').value = cliente.nome;
            document.getElementById('telefone').value = cliente.telefone;
            document.getElementById('rua_bairro').value = cliente.rua_bairro;
            document.getElementById('cidade').value = cliente.cidade;
            
            document.querySelector('[name="acao"]').value = 'atualizar';
            document.getElementById('modalTitle').textContent = 'Editar Cliente';
            
            new bootstrap.Modal(document.getElementById('clienteModal')).show();
        }

        function confirmarExclusao(id) {
            document.getElementById('excluir_id').value = id;
            new bootstrap.Modal(document.getElementById('confirmacaoModal')).show();
        }

        // Limpa o formulário quando o modal é fechado
        document.getElementById('clienteModal').addEventListener('hidden.bs.modal', function () {
            document.getElementById('formCliente').reset();
            document.getElementById('id').value = '';
            document.querySelector('[name="acao"]').value = 'criar';
            document.getElementById('modalTitle').textContent = 'Novo Cliente';
        });
    </script>
</body>
</html>