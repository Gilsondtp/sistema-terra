<?php
define('SITE_TITLE', 'Sistema Terra');
define('DB_HOST', 'localhost');
define('DB_NAME', 'sistema_terra');
define('DB_USER', 'root');
define('DB_PASS', '');
define('BASE_URL', 'http://localhost:8080/sistema_terra');
define('IMG_PATH', '/sistema_terra/imagens/');

// Configuração de fuso horário
date_default_timezone_set('America/Sao_Paulo');

// Configuração de exibição de erros
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);