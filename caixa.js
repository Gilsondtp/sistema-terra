let lancamentos = [];

function atualizarResumo() {
    let receitas = 0, despesas = 0, pagos = 0, recebidos = 0, aReceber = 0, transferidos = 0;

    lancamentos.forEach(l => {
        let valor = parseFloat(l.valor.replace(/[^\d,.-]/g, '').replace('.', '').replace(',', '.')) || 0;
        switch(l.operacao) {
            case 'receita': receitas += valor; break;
            case 'despesa': despesas += valor; break;
            case 'pago': pagos += valor; break;
            case 'recebido': recebidos += valor; break;
            case 'a_receber': aReceber += valor; break;
            case 'transferido': transferidos += valor; break;
        }
    });

    $('#total-receitas').text(`R$ ${receitas.toFixed(2).replace('.', ',')}`);
    $('#total-despesas').text(`R$ ${despesas.toFixed(2).replace('.', ',')}`);
    $('#total-pagos').text(`R$ ${pagos.toFixed(2).replace('.', ',')}`);
    $('#total-recebidos').text(`R$ ${recebidos.toFixed(2).replace('.', ',')}`);
    $('#total-a-receber').text(`R$ ${aReceber.toFixed(2).replace('.', ',')}`);
    $('#total-transferidos').text(`R$ ${transferidos.toFixed(2).replace('.', ',')}`);
    $('#total-geral').text(`R$ ${(receitas - despesas).toFixed(2).replace('.', ',')}`);
}

function formatarMoeda(valor) {
    return parseFloat(valor).toLocaleString('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    });
}

function prepararParaImpressao() {
    // Cria um clone da área de impressão
    let printContent = $('#print-area').clone();
    
    // Remove elementos não necessários
    printContent.find('.no-print').remove();
    
    // Abre nova janela para impressão
    let printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <html>
            <head>
                <title>Relatório de Caixa</title>
                <style>
                    body { font-family: Arial; margin: 20px; }
                    table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                    .resumo { margin-top: 30px; }
                    .total-geral { font-weight: bold; margin-top: 15px; }
                </style>
            </head>
            <body>
                <h2>Relatório de Caixa - Sistema Terra</h2>
                <p>Emitido em: ${new Date().toLocaleString('pt-BR')}</p>
                ${printContent.html()}
            </body>
        </html>
    `);
    
    printWindow.document.close();
    printWindow.focus();
    
    // Espera o conteúdo carregar antes de imprimir
    setTimeout(() => {
        printWindow.print();
        printWindow.close();
    }, 500);
}

let tabela;

$(document).ready(function() {
    // Inicializa DataTable
    tabela = $('#tabela-lancamentos').DataTable({
        language: { 
            url: "//cdn.datatables.net/plug-ins/1.13.4/i18n/pt-BR.json" 
        },
        dom: 't',
        ordering: true,
        pageLength: 10,
        lengthMenu: [10, 25, 50, 100],
        columnDefs: [
            {
                targets: 4, // Coluna de ações
                className: 'no-print'
            }
        ]
    });

    // Configura o calendário
    $('#data').datepicker({
        format: 'dd/mm/yyyy',
        todayHighlight: true,
        autoclose: true,
        language: 'pt-BR'
    });
    
    $('#icone-calendario').on('click', function() {
        $('#data').datepicker('show');
    });

    // Configura o botão de impressão
    $(document).on('click', '.btn-print', prepararParaImpressao);

    // Formulário de lançamento
    $("#form-caixa").on("submit", function(e) {
        e.preventDefault();
        let descricao = $("#descricao").val().trim();
        let data = $("#data").val();
        let valor = $("#valor").val();
        let operacao = $("#operacao").val();

        if(descricao && data && valor && operacao) {
            // Formata o valor para consistência
            const valorFormatado = formatarMoeda(parseFloat(valor.replace(/[^\d,.-]/g, '').replace('.', '').replace(',', '.')));
            
            // Adiciona na tabela DataTable
            tabela.row.add([
                descricao,
                data,
                valorFormatado,
                obterDescricaoOperacao(operacao),
                '<button class="btn btn-danger btn-sm btn-excluir"><i class="fas fa-trash"></i></button>'
            ]).draw(false);

            // Adiciona no array para cálculo do resumo
            lancamentos.push({
                descricao, 
                data, 
                valor: valorFormatado, 
                operacao
            });

            atualizarResumo();
            this.reset();
        }
    });

    // Excluir lançamento
    $('#tabela-lancamentos').on('click', '.btn-excluir', function() {
        let row = tabela.row($(this).parents('tr'));
        let idx = row.index();
        
        if (confirm('Deseja realmente excluir este lançamento?')) {
            row.remove().draw();
            lancamentos.splice(idx, 1);
            atualizarResumo();
        }
    });
});

function obterDescricaoOperacao(codigo) {
    const operacoes = {
        'receita': 'Receita',
        'despesa': 'Despesa',
        'pago': 'Pago',
        'recebido': 'Recebido',
        'a_receber': 'A Receber',
        'transferido': 'Transferido'
    };
    return operacoes[codigo] || codigo;
}