<?php
require_once 'config/config.php';
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Bem-vindo - <?php echo SITE_TITLE; ?></title>
	<!-- Favicon (ícone na barra do navegador) -->
    <link rel="icon" href="imagens/terra icone.ico" type="image/x-icon">
	<meta name="viewport" content="width=device-width, initial-scale=1">
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="/sistema_terra/assets/custom-navbar.css" rel="stylesheet">
	<style>
        body {
            padding-top: 80px;
        }
        .navbar {
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        }
        .central-links {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-top: 80px;
            gap: 20px;
        }
        .central-links a {
            min-width: 220px;
            font-size: 1.2rem;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg fixed-top" style="background: transparent;">
    <div class="container bg-primary navbar-dark rounded-bottom">
            <a class="navbar-brand fw-bold" href="#">Sistema Terra</a>
            <div class="collapse navbar-collapse justify-content-center">
                <ul class="navbar-nav">
                    <li class="nav-item mx-2">
                        <a class="btn btn-success" href="modules/lancamentos.php">Lançamentos</a>
                    </li>
                    <li class="nav-item mx-2">
                        <a class="btn btn-primary" href="modules/clientes.php">Clientes</a>
                    </li>
                    <li class="nav-item mx-2">
                        <a class="btn btn-info" href="modules/produtos.php">Produtos</a>
                    </li>
                    <li class="nav-item mx-2">
                        <a class="btn btn-primary" href="modules/relatorios.php">Relatórios</a>
                    </li>
                    <li class="nav-item mx-2">
                        <a class="btn btn-purple text-white" style="background-color: #6f42c1;" href="modules/demonstrativo.php">Demonstrativo</a>
                    </li>
                    <li class="nav-item mx-2">
                        <a class="btn btn-warning" href="modules/estoque.php">Estoque</a>
                    </li>
                    <li class="nav-item mx-2">
                        <a class="btn btn-danger" href="modules/caixa.php">Caixa</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    <div class="container">
        <div class="central-links">
            <a class="btn btn-success" href="modules/lancamentos.php">Ir para Lançamentos</a>
            <a class="btn btn-primary" href="modules/clientes.php">Ir para Clientes</a>
            <a class="btn btn-info" href="modules/produtos.php">Ir para Produtos</a>
            <a class="btn btn-primary" href="modules/relatorios.php">Ir para Relatórios</a>
            <a class="btn btn-purple text-white" style="background-color: #6f42c1;" href="modules/demonstrativo.php">Ir para Demonstrativo</a>
            <a class="btn btn-warning" href="modules/estoque.php">Ir para Estoque</a>
           <a class="btn btn-danger" href="caixa/modules/lancamento_caixa.php">Caixa</a>
        </div>
    </div>
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>