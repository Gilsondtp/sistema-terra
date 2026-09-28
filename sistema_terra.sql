-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 29/05/2025 às 22:03
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
-- Banco de dados: `sistema_terra`
--
CREATE DATABASE IF NOT EXISTS `sistema_terra` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `sistema_terra`;

-- --------------------------------------------------------

--
-- Estrutura para tabela `clientes`
--

DROP TABLE IF EXISTS `clientes`;
CREATE TABLE `clientes` (
  `id` int(11) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `telefone` varchar(20) DEFAULT NULL,
  `rua_bairro` varchar(200) DEFAULT NULL,
  `cidade` varchar(100) DEFAULT NULL,
  `data_cadastro` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `clientes`
--

INSERT INTO `clientes` (`id`, `nome`, `telefone`, `rua_bairro`, `cidade`, `data_cadastro`) VALUES
(3, 'Falcao', '', 'https://maps.app.goo.gl/wG8hLytG5b4kCffj9', 'Lauro de Freitas', '2025-05-29 13:53:59'),
(4, 'Manuela', '', 'Estrada de Camp. Pirajá', 'Salvador', '2025-05-29 14:05:02'),
(5, 'Exxograf', '', 'https://maps.app.goo.gl/PqJaJR7jc2eckmZz8', 'Calçada - Salvador', '2025-05-29 14:25:23'),
(6, 'Noel', '', 'https://maps.app.goo.gl/ct91WVKM3m4AyDP77', 'Pirajá - Salvador', '2025-05-29 14:26:40'),
(7, 'Vangraf', '', '', 'Feira de Santana', '2025-05-29 14:28:09'),
(8, 'Jacograf', '', 'centro', 'Lauro de Freitas', '2025-05-29 14:28:38'),
(9, 'Norte Grafica', '', 'https://maps.app.goo.gl/TRECAohPscLdREFN6', 'Lauro de Freitas', '2025-05-29 14:29:37'),
(10, 'Gold', '', '', 'Feira de Santana', '2025-05-29 14:30:10'),
(11, 'CADS', '', 'AV.MACHADO DE ASSIS N 85- ALTO DO ALENCAR', 'Juazeiro - Ba', '2025-05-29 14:31:29'),
(12, 'IPLAST', '', '', '', '2025-05-29 14:32:52'),
(13, 'Aqui Grafica', '', 'https://maps.app.goo.gl/d4dkrEdUqDS2bSRH6', 'Lauro de Freitas', '2025-05-29 14:34:13'),
(14, 'Flavia', '', '', 'Salvador', '2025-05-29 14:35:02'),
(15, 'Demerval', '', 'Marechal Rondom', 'Salvador', '2025-05-29 14:35:31'),
(16, 'Jaelson', '', 'Bomfim', 'salvador', '2025-05-29 14:36:04'),
(17, 'Sou Grafica', '', '', 'Salvador', '2025-05-29 14:37:05'),
(18, 'Ribas', '', 'via expressa', 'Salvador', '2025-05-29 14:37:28'),
(19, 'Perdas', '', '-----', '------', '2025-05-29 14:44:56'),
(20, 'Terra Fotolito', '(71) 32426-120', 'Av. Estados Unidos, Edf. Wildberg, nº 18, sala 335', 'salvador', '2025-05-29 14:45:27');

-- --------------------------------------------------------

--
-- Estrutura para tabela `lancamentos`
--

DROP TABLE IF EXISTS `lancamentos`;
CREATE TABLE `lancamentos` (
  `id` int(11) NOT NULL,
  `cliente_id` int(11) NOT NULL,
  `data_lancamento` date NOT NULL,
  `valor_entrega` decimal(10,2) DEFAULT 0.00,
  `valor_pagamento` decimal(10,2) DEFAULT 0.00,
  `data_registro` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `lancamentos`
--

INSERT INTO `lancamentos` (`id`, `cliente_id`, `data_lancamento`, `valor_entrega`, `valor_pagamento`, `data_registro`) VALUES
(1, 20, '2025-05-29', 0.00, 0.00, '2025-05-29 14:48:19');

-- --------------------------------------------------------

--
-- Estrutura para tabela `lancamentos_caixa`
--

DROP TABLE IF EXISTS `lancamentos_caixa`;
CREATE TABLE `lancamentos_caixa` (
  `id` int(11) NOT NULL,
  `descricao` varchar(255) NOT NULL,
  `data` date NOT NULL,
  `valor` decimal(10,2) NOT NULL,
  `operacao` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `produtos`
--

DROP TABLE IF EXISTS `produtos`;
CREATE TABLE `produtos` (
  `id` int(11) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `estoque_inicial` int(11) DEFAULT 0,
  `estoque_atual` int(11) DEFAULT 0,
  `estoque_consumido` int(11) DEFAULT 0,
  `data_cadastro` date DEFAULT NULL,
  `preco` decimal(10,2) DEFAULT 0.00,
  `valor_compra` decimal(10,2) DEFAULT 0.00
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `produtos`
--

INSERT INTO `produtos` (`id`, `nome`, `estoque_inicial`, `estoque_atual`, `estoque_consumido`, `data_cadastro`, `preco`, `valor_compra`) VALUES
(3, 'Adast', 26, 26, 0, '2025-05-29', 40.00, 13.54),
(4, 'MO', 471, 471, 0, '2025-05-29', 40.00, 14.24),
(5, 'GTO', 454, 454, 0, '2025-05-29', 30.00, 8.83),
(6, 'Speed', 278, 278, 0, '2025-05-29', 50.00, 18.30),
(7, '521', 287, 286, 1, '2025-05-29', 30.00, 9.28),
(8, '724', 3, 3, 0, '2025-05-29', 50.00, 20.01),
(9, 'Solna', 432, 432, 0, '2025-05-29', 40.00, 12.20);

-- --------------------------------------------------------

--
-- Estrutura para tabela `servicos`
--

DROP TABLE IF EXISTS `servicos`;
CREATE TABLE `servicos` (
  `id` int(11) NOT NULL,
  `lancamento_id` int(11) NOT NULL,
  `produto_id` int(11) DEFAULT NULL,
  `descricao` text DEFAULT NULL,
  `quantidade` int(11) DEFAULT 1,
  `valor` decimal(10,2) DEFAULT 0.00
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `servicos`
--

INSERT INTO `servicos` (`id`, `lancamento_id`, `produto_id`, `descricao`, `quantidade`, `valor`) VALUES
(1, 1, 7, 'teste', 1, 30.00);

--
-- Índices para tabelas despejadas
--

--
-- Índices de tabela `clientes`
--
ALTER TABLE `clientes`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_cliente_nome` (`nome`);

--
-- Índices de tabela `lancamentos`
--
ALTER TABLE `lancamentos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_lancamento_data` (`data_lancamento`),
  ADD KEY `idx_lancamento_cliente` (`cliente_id`);

--
-- Índices de tabela `lancamentos_caixa`
--
ALTER TABLE `lancamentos_caixa`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_caixa_data` (`data`),
  ADD KEY `idx_caixa_operacao` (`operacao`);

--
-- Índices de tabela `produtos`
--
ALTER TABLE `produtos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_produto_nome` (`nome`);

--
-- Índices de tabela `servicos`
--
ALTER TABLE `servicos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_servico_lancamento` (`lancamento_id`),
  ADD KEY `idx_servico_produto` (`produto_id`);

--
-- AUTO_INCREMENT para tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `clientes`
--
ALTER TABLE `clientes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=21;

--
-- AUTO_INCREMENT de tabela `lancamentos`
--
ALTER TABLE `lancamentos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de tabela `lancamentos_caixa`
--
ALTER TABLE `lancamentos_caixa`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `produtos`
--
ALTER TABLE `produtos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT de tabela `servicos`
--
ALTER TABLE `servicos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- Restrições para tabelas despejadas
--

--
-- Restrições para tabelas `lancamentos`
--
ALTER TABLE `lancamentos`
  ADD CONSTRAINT `lancamentos_ibfk_1` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`) ON UPDATE CASCADE;

--
-- Restrições para tabelas `servicos`
--
ALTER TABLE `servicos`
  ADD CONSTRAINT `servicos_ibfk_1` FOREIGN KEY (`lancamento_id`) REFERENCES `lancamentos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `servicos_ibfk_2` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`) ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
