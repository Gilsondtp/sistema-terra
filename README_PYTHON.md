# Sistema Terra — Versão em Python + SQLite

Aplicação recriada em **Python (Flask + SQLite)** preservando todas as funções do sistema original em PHP/MySQL e incorporando as novas funcionalidades solicitadas:

## Principais Funcionalidades e Alterações Implementadas

1. **Primeira Tela — `LANC. DIÁRIO` (`/lancamento-diario` ou `/`)**:
   - Exibe a listagem dos serviços monitorados automaticamente pelo Hot Folder e lançados no dia (ou outra data selecionada).
   - **Barra Superior**: Seletor de modo de exibição (*Lançamento Diário (Padrão)*, *Por Cliente*, *Por Produto*, *Por Descrição do Serviço*, *Apenas Não Identificados*), filtro por data/cliente/produto/texto, botão **Criar Lançamento** (abre o modal completo de lançamento), botão **Testar / Simular Hot Folder**, **Atualizar Pasta** e **Imprimir Listagem**.
   - **Destaque em Vermelho para Não Identificados**: Serviços cujo cliente não pôde ser identificado pelo nome do arquivo aparecem destacados em **vermelho** com a opção de **Atribuir Cliente** diretamente na linha ou pelo botão Editar.
   - **Soma nas Colunas**: Rodapé da tabela com a soma total da **Quantidade de Produto (Chapas)** e a soma de **Valores (R$)** da listagem exibida.
   - **Barra Inferior**: Exibe a quantidade total de serviços, a quantidade de **Não Identificados** e o total de chapas/valores.

2. **Monitoramento Automático de Hot Folder (`\\RIPCTP\Manuela\OutPut`)**:
   - Monitora as subpastas associadas a cada chapa/produto (ex: `510x400` &rarr; `GTO`, `660x530` &rarr; `Adast`, `650x550` &rarr; `MO`, `521` &rarr; `521`, `745x605` &rarr; `Speed`, `724` &rarr; `724`, `Solna` &rarr; `Solna`).
   - Reconhece arquivos separados pelo RIP (*Raster Precision Screen*) nas cores **`C`, `M`, `Y`, `K`, `GRAY`, `PANTONE`** e múltiplas páginas numeradas.
   - **Tolerância a falta de espaços, acentos, caixa alta/baixa e erros de grafia**: Identifica o cliente por similaridade (Damerau-Levenshtein), reconhecendo variações como `gilso` ou `glison` para `Gilson`, mesmo quando o nome do arquivo está colado sem espaços (ex: `gilsoncartazc.tif`).

3. **Segunda Alteração — `PRODUTOS / ESTOQUE` (`/produtos`)**:
   - O controle de estoque permanece unificado e aperfeiçoado na própria tela de Produtos (Chapas), exibindo Estoque Inicial, Consumido, Estoque Atual, Valor de Compra, Valor em Estoque, Preço de Venda, Custo das Chapas Consumidas, Status (`OK`, `BAIXO`, `CRÍTICO`), vínculo de subpasta Hot Folder, ajuste rápido de entrada/saída e impressão.

4. **Terceira Alteração — `CAIXA` (`/caixa`)**:
   - Incorporada ao mesmo banco de dados SQLite (`sistema_terra.db`), exibindo lado a lado os **Saldos Devedores dos Clientes e Pagamentos Lançados** e o fluxo de movimentações do Caixa (Receitas, Despesas, Recebidos, Pagos, A Receber, Transferidos).

5. **Telas Preservadas Integralmente**:
   - **Lançamentos (`/lancamentos`)**: Formulário completo com múltiplos serviços, entrega, pagamento/desconto, fatura anterior, pagtº fatura anterior, saldo da fatura anterior, observação e área de registros com filtros.
   - **Clientes (`/clientes`)**: Cadastro, busca, edição e exclusão protegida.
   - **Relatório / Fatura Individual (`/relatorios`)**: Emissão de fatura formatada para impressão, relatório de produtos utilizados no período e botão **Fechar Fatura** (transfere o saldo devedor para `fatura_anterior` do cliente e limpa os lançamentos do período sem devolver o estoque consumido).
   - **Demonstrativo (`/demonstrativo`)**: Resumo geral de todos os clientes por período ou produto, produtos utilizados, alerta de estoque crítico, impressão e **Exportação para Excel (`.xlsx`)**.
   - **Backup Fácil (`/configuracoes`)**: Exportação e importação em 1 clique do banco SQLite (`.db`), `.json` ou `.sql`.

## Como Executar no Windows

Basta dar dois cliques em **`iniciar_sistema.bat`** ou executar no terminal:

```bash
pip install -r requirements.txt
python app.py
```

Depois acesse no navegador: `http://localhost:5000`
