-- Cria o banco de dados se não existir
CREATE DATABASE IF NOT EXISTS sistema_terra;

-- Seleciona o banco de dados
USE sistema_terra;

-- Desativa verificação de chaves estrangeiras temporariamente
-- Isso é crucial para permitir o DROP TABLE em qualquer ordem
SET FOREIGN_KEY_CHECKS = 0;

-- Exclui tabelas se existirem para garantir estrutura limpa
-- Importante: A ordem de DROP deve ser o inverso da criação
-- As tabelas filhas devem ser dropadas antes das tabelas pai
DROP TABLE IF EXISTS servicos;
DROP TABLE IF EXISTS lancamentos;
DROP TABLE IF EXISTS produtos;
DROP TABLE IF EXISTS clientes;
DROP TABLE IF EXISTS lancamentos_caixa; -- Adicionado, caso exista no seu ambiente anterior

--
---

-- CRIAÇÃO DAS TABELAS - ORDEM CORRETA DE DEPENDÊNCIA

-- 1. Tabela clientes (não depende de nenhuma outra)
CREATE TABLE clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    telefone VARCHAR(20) DEFAULT NULL,
    rua_bairro VARCHAR(200) DEFAULT NULL,
    cidade VARCHAR(100) DEFAULT NULL,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Tabela produtos (não depende de nenhuma outra)
CREATE TABLE produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    estoque_inicial INT DEFAULT 0,
    estoque_atual INT DEFAULT 0,
    estoque_consumido INT DEFAULT 0,
    data_cadastro DATE,
    preco DECIMAL(10,2) DEFAULT 0.00,
    valor_compra DECIMAL(10,2) DEFAULT 0.00
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Tabela lancamentos (depende de clientes)
CREATE TABLE lancamentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT NOT NULL,
    data_lancamento DATE NOT NULL,
    valor_entrega DECIMAL(10,2) DEFAULT 0.00,
    valor_pagamento DECIMAL(10,2) DEFAULT 0.00,
    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Tabela servicos (depende de lancamentos e produtos)
CREATE TABLE servicos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lancamento_id INT NOT NULL,
    produto_id INT DEFAULT NULL,
    descricao TEXT,
    quantidade INT DEFAULT 1,
    valor DECIMAL(10,2) DEFAULT 0.00,
    FOREIGN KEY (lancamento_id) REFERENCES lancamentos(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Tabela lancamentos_caixa (não depende de outras)
CREATE TABLE lancamentos_caixa (
    id INT AUTO_INCREMENT PRIMARY KEY,
    descricao VARCHAR(255) NOT NULL,
    data DATE NOT NULL,
    valor DECIMAL(10,2) NOT NULL,
    operacao VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Reativa verificação de chaves estrangeiras
SET FOREIGN_KEY_CHECKS = 1;

---

## Criação de Índices e Inserção de Dados (mantidos na ordem original)

A partir daqui, o restante do seu script pode permanecer na ordem original, pois os índices e as inserções de dados dependem apenas da existência das tabelas, não da ordem de criação entre si.

```sql
-- Índices para performance em buscas por data e operação
CREATE INDEX idx_caixa_data ON lancamentos_caixa(data);
CREATE INDEX idx_caixa_operacao ON lancamentos_caixa(operacao);

-- Cria índices para melhor performance
CREATE INDEX idx_cliente_nome ON clientes(nome);
CREATE INDEX idx_produto_nome ON produtos(nome);
CREATE INDEX idx_lancamento_data ON lancamentos(data_lancamento);
CREATE INDEX idx_lancamento_cliente ON lancamentos(cliente_id);
CREATE INDEX idx_servico_lancamento ON servicos(lancamento_id);
CREATE INDEX idx_servico_produto ON servicos(produto_id);

-- Insere alguns dados de exemplo
INSERT INTO clientes (nome, telefone, rua_bairro, cidade) VALUES
('Cliente Teste', '(71) 99999-9999', 'Rua Teste, 123', 'Salvador'),
('Empresa ABC', '(71) 98888-8888', 'Av. Principal, 456', 'Salvador');

INSERT INTO produtos (nome, estoque_inicial, estoque_atual, data_cadastro, preco, valor_compra) VALUES
('Produto A', 100, 100, CURDATE(), 50.00, 30.00),
('Produto B', 200, 200, CURDATE(), 75.50, 55.00);

-- Confirma as alterações
COMMIT;

-- Verifica se as tabelas foram criadas
SHOW TABLES;

-- Exibe a estrutura de cada tabela
DESCRIBE clientes;
DESCRIBE produtos;
DESCRIBE lancamentos;
DESCRIBE servicos;
DESCRIBE lancamentos_caixa; -- Corrigido de 'caixa' para 'lancamentos_caixa'