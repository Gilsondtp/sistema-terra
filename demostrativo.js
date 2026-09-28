document.addEventListener('DOMContentLoaded', function() {
    // Manter os listeners existentes
    document.querySelectorAll('[onclick*="exportarDados"]').forEach(btn => {
        btn.addEventListener('click', exportarDados);
    });
    
    document.querySelectorAll('[onclick*="importarDados"]').forEach(btn => {
        btn.addEventListener('click', importarDados);
    });
    
    // Adicionar listeners para os novos botões (se existirem)
    if(document.getElementById('btnExportar')) {
        document.getElementById('btnExportar').addEventListener('click', exportarDados);
    }
    
    if(document.getElementById('btnImportar')) {
        document.getElementById('btnImportar').addEventListener('click', importarDados);
    }
});

function exportarDados() {
    if(confirm('Deseja exportar os dados para um arquivo SQL?')) {
        fetch('/sistema_terra/api/exportar_dados.php')
            .then(response => {
                if(!response.ok) throw new Error('Erro na exportação');
                return response.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `backup_${new Date().toISOString().slice(0,10)}.sql`;
                a.click();
                window.URL.revokeObjectURL(url);
                alert('Exportação concluída com sucesso!');
            })
            .catch(error => {
                console.error('Erro:', error);
                alert('Falha na exportação: ' + error.message);
            });
    }
}

function importarDados() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.sql,.txt';
    
    input.onchange = e => {
        const file = e.target.files[0];
        if(file && confirm(`Importar o arquivo ${file.name}?`)) {
            const formData = new FormData();
            formData.append('sql_file', file);
            
            fetch('/sistema_terra/api/importar_dados.php', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if(data.success) {
                    alert('Importação realizada com sucesso!');
                    location.reload();
                } else {
                    throw new Error(data.message || 'Erro desconhecido');
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                alert('Falha na importação: ' + error.message);
            });
        }
    };
    
    input.click();
}