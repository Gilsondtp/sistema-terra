-- Inserção de clientes
INSERT INTO clientes (id, nome, telefone, bairro, cidade) VALUES
(1743276350377, 'Manuela', '1111111', 'campinas', 'Salvador'),
(1743276379884, 'Noel', '33333', 'brasil gas', 'Salvador'),
(1743677836650, 'Exxograf', '0', 'Calçada', 'salvador'),
(1743677853034, 'Ribas', '0', 'via expressa', 'salvador'),
(1743677866538, 'Marinho', '71', 'Calçada', 'salvador'),
(1743677891354, 'Jaelson', '0', 'MARES', 'salvador'),
(1743677924673, 'Falcao', '0', 'caji', 'Lauro de Freitas'),
(1743677941737, 'Gold', '0', 'centro', 'Feira'),
(1743677964009, 'Aqui Grafica', '0', 'centro', 'Lauro de Freitas'),
(1743677983057, 'Flavia', '0', 'centro', 'Lauro de Freitas'),
(1743678007921, 'Terra Fotolito', '0', 'comercio', 'salvador'),
(1743678059361, 'Impact', '0', 'centro', 'ALAGOINHAS'),
(1743678130065, 'Nordeste', '0', 'sao cristovao', 'salvador'),
(1743678146513, 'Gilberto', '0', 's caqetano', 'salvador'),
(1743678186761, 'Demerval', '0', 'M rondon', 'salvador'),
(1744291173401, 'CADS', '0', 'Travessa Machado de Assis, 85 - Alto do AlencarCEP.: 48.905-481', 'Juazeiro'),
(1744658096686, 'Jacograf', '0', NULL, 'Lauro de Freitas'),
(1744736239998, 'Sou Grafica', '0', NULL, 'Lauro de Freitas'),
(1744737208499, 'PBA - embalagens', '0', NULL, 'Salvador'),
(1745431287421, 'IPLAST', '0', NULL, 'Sergipé'),
(1746639128178, 'Norte Gráfica', '0', NULL, 'Lauro de Freitas'),
(1746639630480, 'Perdas', '0', NULL, 'Salvador'),
(1746714853997, 'Vangraf', '0', NULL, 'Feira de Santana'),
(1746715737858, 'Fonte Viva', '0', 'av Apolonio Sales , 1059', 'Pauo Afonso'),
(1747156733922, 'Vilacy', '0', NULL, 'Lauro de Freitas');

-- Atualização dos clientes com ruaBairro
UPDATE clientes SET ruaBairro = 'centro' WHERE id IN (1744658096686, 1744736239998, 1744737208499, 1745431287421, 1746639128178, 1746639630480, 1746714853997, 1747156733922);
UPDATE clientes SET ruaBairro = 'Caji' WHERE id = 1746639128178;
UPDATE clientes SET ruaBairro = 'campinas' WHERE id = 1746639630480;

-- Inserção de produtos
INSERT INTO produtos (id, nome, estoqueInicial, estoqueAtual, dataCadastro, preco, estoqueConsumido) VALUES
(1746030506469, '521', 368, 308, '2025-04-28', 30.00, 60),
(1746707169166, '724', 41, 3, '2025-05-01', 45.00, 38),
(1747320375156, 'Adast', 393, 94, '2025-04-28', 40.00, 299),
(1746707214790, 'GTO', 537, 505, '2025-04-28', 30.00, 32),
(1746707252622, 'MO', 661, 514, '2025-04-28', 40.00, 147),
(1745972260907, 'Solna', 430, 422, '2025-04-26', 40.00, 8),
(1747319123012, 'Speed', 300, 300, '2025-05-05', 45.00, 0);

-- Inserção de lançamentos (apenas alguns exemplos devido ao volume)
INSERT INTO lancamentos (id, clienteId, clienteNome, data, valorEntrega, valorPagamento) VALUES
(1746638639028, 1743678186761, 'Demerval', '2025-05-02', 0, 0),
(1746638681691, 1743677964009, 'Aqui Grafica', '2025-05-02', 0, 0),
(1746638711243, 1743677964009, 'Aqui Grafica', '2025-05-05', 0, 0),
(1746638765355, 1743677853034, 'Ribas', '2025-05-02', 0, 0),
(1746638794971, 1743677983057, 'Flavia', '2025-05-05', 0, 0);

-- Inserção de serviços (apenas alguns exemplos devido ao volume)
INSERT INTO servicos (lancamentoId, descricao, quantidade, produtoId, produtoNome, valor) VALUES
(1746638639028, 'folder CBFD 25', 4, 1746030506469, '521', 120),
(1746638639028, 'Plano de panfletos', 4, 1746030506469, '521', 120),
(1746638681691, 'encarte guarda roupa F4', 4, 1746030515494, 'Adast', 160),
(1746638711243, 'Encarte guarda roupa f2', 4, 1746030515494, 'Adast', 160),
(1746638765355, 'Encarte mães', 4, 1746030515494, 'Adast', 160);