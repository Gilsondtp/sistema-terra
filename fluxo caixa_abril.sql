-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 03/06/2025 às 02:19
-- Versão do servidor: 10.4.32-MariaDB
-- Versão do PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `bco_caixa`
--

-- --------------------------------------------------------

--
-- Estrutura para tabela `lancamentos`
--
-- Criação: 27/05/2025 às 23:08
-- Última atualização: 03/06/2025 às 00:13
--

CREATE TABLE `lancamentos` (
  `id` int(11) NOT NULL,
  `descricao` varchar(255) NOT NULL,
  `data_lancamento` date NOT NULL,
  `valor` decimal(10,2) NOT NULL,
  `operacao` enum('receita','despesa','pago','recebido','a_receber','transferencia') NOT NULL,
  `usuario` varchar(50) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `lancamentos`
--

INSERT DELAYED IGNORE INTO `lancamentos` (`id`, `descricao`, `data_lancamento`, `valor`, `operacao`, `usuario`, `created_at`, `updated_at`) VALUES
(4, 'Serviços ctp', '2025-04-30', 3085501.00, 'receita', 'sistema', '2025-06-02 23:45:13', '2025-06-02 23:45:13'),
(5, 'pagamentos de serviços', '2025-04-30', 2000.00, 'recebido', 'sistema', '2025-06-02 23:46:04', '2025-06-02 23:46:04'),
(6, 'Salario Antonio Carlos', '2025-04-30', 1200.00, 'despesa', 'sistema', '2025-06-02 23:46:34', '2025-06-03 00:11:38'),
(8, 'combustivel', '2025-03-29', 400.00, 'despesa', 'sistema', '2025-06-02 23:50:01', '2025-06-02 23:50:01'),
(9, 'Atendimento eletronico', '2025-03-29', 600.00, 'despesa', 'sistema', '2025-06-02 23:50:30', '2025-06-03 00:05:44'),
(10, 'Motoboy', '2025-04-29', 160.00, 'despesa', 'sistema', '2025-06-02 23:51:02', '2025-06-02 23:51:02'),
(11, 'Eletronico', '2025-04-29', 350.00, 'despesa', 'sistema', '2025-06-02 23:51:31', '2025-06-02 23:51:31'),
(12, 'Creditos para SR serviços', '2024-10-30', 28540.00, 'transferencia', 'sistema', '2025-06-02 23:52:22', '2025-06-03 00:04:09'),
(13, 'Alimentaçao do eletronico', '2025-02-27', 150.00, 'despesa', 'sistema', '2025-06-02 23:53:42', '2025-06-02 23:53:42'),
(14, 'combustivel', '2025-02-27', 554.00, 'despesa', 'sistema', '2025-06-02 23:54:11', '2025-06-02 23:54:11'),
(15, 'atendimento do eletronico', '2025-02-27', 800.00, 'despesa', 'sistema', '2025-06-02 23:57:22', '2025-06-02 23:57:22'),
(16, 'combustivel - visitas e entregas', '2025-01-29', 180.00, 'despesa', 'sistema', '2025-06-02 23:58:06', '2025-06-02 23:58:06'),
(17, 'combustivel - visitas e entregas', '2024-12-29', 200.00, 'despesa', 'sistema', '2025-06-02 23:58:42', '2025-06-03 00:03:53'),
(18, 'combustivel - visitas e entregas', '2024-10-29', 534.00, 'despesa', 'sistema', '2025-06-02 23:59:45', '2025-06-03 00:04:57'),
(19, 'Motoboy', '2025-01-29', 180.00, 'despesa', 'sistema', '2025-06-03 00:00:30', '2025-06-03 00:00:30'),
(20, 'Motoboy', '2024-12-19', 310.00, 'despesa', 'sistema', '2025-06-03 00:01:00', '2025-06-03 00:04:34'),
(21, 'insumos - metacilicato', '2024-11-24', 110.00, 'despesa', 'sistema', '2025-06-03 00:02:21', '2025-06-03 00:02:21'),
(22, 'Motoboy', '2024-10-30', 300.00, 'despesa', 'sistema', '2025-06-03 00:02:48', '2025-06-03 00:02:48'),
(23, 'Retirada Erilio', '2024-12-29', 3000.00, 'despesa', 'sistema', '2025-06-03 00:03:27', '2025-06-03 00:03:27'),
(24, 'Salario Antonio Carlos', '2024-11-29', 1200.00, 'despesa', 'sistema', '2025-06-03 00:06:18', '2025-06-03 00:06:18'),
(25, 'Salario Gilson', '2024-10-29', 2000.00, 'despesa', 'sistema', '2025-06-03 00:06:48', '2025-06-03 00:06:48'),
(26, 'Salario Antonio Carlos', '2024-10-29', 1.20, 'despesa', 'sistema', '2025-06-03 00:07:13', '2025-06-03 00:07:13'),
(27, 'Salario Gilson', '2024-12-29', 2500.00, 'despesa', 'sistema', '2025-06-03 00:07:57', '2025-06-03 00:07:57'),
(28, 'Salario Gilson', '2025-01-29', 2500.00, 'despesa', 'sistema', '2025-06-03 00:08:25', '2025-06-03 00:08:25'),
(29, 'Salario Gilson', '2025-02-27', 2.50, 'despesa', 'sistema', '2025-06-03 00:08:55', '2025-06-03 00:08:55'),
(30, 'Salario Gilson', '2025-03-29', 2500.00, 'despesa', 'sistema', '2025-06-03 00:09:29', '2025-06-03 00:13:12'),
(31, 'Salario Gilson', '2025-04-29', 2.50, 'despesa', 'sistema', '2025-06-03 00:09:51', '2025-06-03 00:09:51'),
(32, 'Salario Gilson', '2024-11-29', 2.50, 'despesa', 'sistema', '2025-06-03 00:12:44', '2025-06-03 00:12:44');

--
-- Índices para tabelas despejadas
--

--
-- Índices de tabela `lancamentos`
--
ALTER TABLE `lancamentos`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT para tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `lancamentos`
--
ALTER TABLE `lancamentos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=33;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
