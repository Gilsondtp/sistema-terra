<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo isset($page_title) ? $page_title : SITE_TITLE; ?></title>
	<!-- Favicon (ícone na barra do navegador) -->
<link rel="icon" href="/sistema_terra/imagens/terra icone.ico" type="image/x-icon">
    <link rel="icon" href="imagens/terra icone.ico" type="image/x-icon">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="<?php echo BASE_URL; ?>/assets/css/style.css" rel="stylesheet">
	<link href="<?php echo BASE_URL; ?>/assets/custom-navbar.css" rel="stylesheet">
</head>
<body>
    <div class="toast" id="toast"></div>
    <div class="container">