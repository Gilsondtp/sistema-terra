ddocument.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('lancamentoCaixaForm'); // Atualizado
    const valorInput = document.getElementById('valor');
    IMask(valorInput, {
        mask: 'R$ num',
        blocks: {
            num: {
                mask: Number,
                thousandsSeparator: '.',
                radix: ',',
                scale: 2,
                padFractionalZeros: true,
            }
        }
    });

    // Form submission
    const form = document.getElementById('lancamentoForm');
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        formData.append('action', 'create');
        
        try {
            const response = await fetch('', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('Lançamento salvo com sucesso!');
                window.location.reload();
            } else {
                alert('Erro ao salvar lançamento.');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Erro ao processar requisição.');
        }
    });

    // Delete entry
    document.querySelectorAll('.excluir-lancamento').forEach(button => {
        button.addEventListener('click', async function() {
            if (!confirm('Deseja realmente excluir este lançamento?')) return;
            
            const id = this.dataset.id;
            const formData = new FormData();
            formData.append('action', 'delete');
            formData.append('id', id);
            
            try {
                const response = await fetch('', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    window.location.reload();
                } else {
                    alert('Erro ao excluir lançamento.');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Erro ao processar requisição.');
            }
        });
    });

    // Clear all entries
    document.getElementById('limparTodos').addEventListener('click', async function() {
        if (!confirm('Deseja realmente limpar todos os lançamentos?')) return;
        
        const formData = new FormData();
        formData.append('action', 'deleteAll');
        
        try {
            