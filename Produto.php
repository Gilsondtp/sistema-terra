<?php
class Produto {
    private $conn;
    private $table_name = "produtos";

    public function __construct($db) {
        $this->conn = $db;
    }

    // Adiciona valor_compra e anotacoes
    public function criar($nome, $estoque_inicial, $data_cadastro, $preco, $valor_compra, $anotacoes = null) {
        try {
            // Verificar se a coluna anotacoes existe
            $checkColumn = $this->conn->query("SHOW COLUMNS FROM {$this->table_name} LIKE 'anotacoes'")->rowCount();
            
            if ($checkColumn > 0) {
                $query = "INSERT INTO " . $this->table_name . " 
                        (nome, estoque_inicial, estoque_atual, data_cadastro, preco, valor_compra, anotacoes) 
                        VALUES 
                        (:nome, :estoque_inicial, :estoque_atual, :data_cadastro, :preco, :valor_compra, :anotacoes)";
            } else {
                // Se a coluna não existir, não a inclua na consulta
                $query = "INSERT INTO " . $this->table_name . " 
                        (nome, estoque_inicial, estoque_atual, data_cadastro, preco, valor_compra) 
                        VALUES 
                        (:nome, :estoque_inicial, :estoque_atual, :data_cadastro, :preco, :valor_compra)";
                error_log("Coluna anotacoes não existe na tabela {$this->table_name}, ignorando este campo");
            }

            $stmt = $this->conn->prepare($query);

            // Usar bindValue em vez de bindParam para todos os parâmetros
            $stmt->bindValue(":nome", $nome, PDO::PARAM_STR);
            $stmt->bindValue(":estoque_inicial", $estoque_inicial, PDO::PARAM_INT);
            $stmt->bindValue(":estoque_atual", $estoque_inicial, PDO::PARAM_INT); // Inicialmente igual ao estoque_inicial
            $stmt->bindValue(":data_cadastro", $data_cadastro, PDO::PARAM_STR);
            $stmt->bindValue(":preco", $preco, PDO::PARAM_STR);
            $stmt->bindValue(":valor_compra", $valor_compra, PDO::PARAM_STR);
            
            // Vincula o parâmetro anotacoes apenas se a coluna existir
            if ($checkColumn > 0) {
                if (is_null($anotacoes)) {
                    $stmt->bindValue(":anotacoes", null, PDO::PARAM_NULL);
                } else {
                    $stmt->bindValue(":anotacoes", $anotacoes, PDO::PARAM_STR);
                }
                error_log("Criando produto, Anotacoes: " . (is_null($anotacoes) ? "NULL" : $anotacoes));
            }

            if($stmt->execute()) {
                return $this->conn->lastInsertId();
            }
            return false;
        } catch(PDOException $e) {
            error_log("Erro ao criar produto: " . $e->getMessage());
            return false;
        }
    }

    public function listar() {
        try {
            // Verificar se a tabela existe
            $checkTable = $this->conn->query("SHOW TABLES LIKE '{$this->table_name}'")->rowCount();
            if ($checkTable == 0) {
                error_log("Tabela {$this->table_name} não existe!");
                return [];
            }
            
            // Verificar se a coluna anotacoes existe
            $checkColumn = $this->conn->query("SHOW COLUMNS FROM {$this->table_name} LIKE 'anotacoes'")->rowCount();
            
            if ($checkColumn > 0) {
                $query = "SELECT id, nome, estoque_inicial, estoque_atual, data_cadastro, preco, valor_compra, anotacoes, 
                        (estoque_inicial - estoque_atual) as estoque_consumido 
                        FROM " . $this->table_name . " ORDER BY nome";
            } else {
                // Se a coluna não existir, não a inclua na consulta
                $query = "SELECT id, nome, estoque_inicial, estoque_atual, data_cadastro, preco, valor_compra, 
                        (estoque_inicial - estoque_atual) as estoque_consumido 
                        FROM " . $this->table_name . " ORDER BY nome";
                error_log("Coluna anotacoes não existe na tabela {$this->table_name}");
            }
            
            $stmt = $this->conn->prepare($query);
            $stmt->execute();
            $produtos = $stmt->fetchAll(PDO::FETCH_ASSOC);
            
            // Debug - verificar se o campo anotacoes está sendo retornado
            if (!empty($produtos)) {
                error_log("Exemplo de produto listado: " . print_r($produtos[0], true));
            } else {
                error_log("Nenhum produto encontrado na tabela {$this->table_name}");
            }
            
            return $produtos;
        } catch(PDOException $e) {
            error_log("Erro ao listar produtos: " . $e->getMessage());
            return [];
        }
    }

    public function buscarPorId($id) {
        try {
            $query = "SELECT * FROM " . $this->table_name . " WHERE id = ?";
            $stmt = $this->conn->prepare($query);
            $stmt->execute([$id]);
            $produto = $stmt->fetch(PDO::FETCH_ASSOC);
            
            // Debug
            error_log("Produto buscado: " . print_r($produto, true));
            
            return $produto;
        } catch(PDOException $e) {
            error_log("Erro ao buscar produto: " . $e->getMessage());
            return false;
        }
    }

    public function atualizar($id, $nome, $estoque_inicial, $data_cadastro, $preco, $valor_compra, $anotacoes = '') {
    try {
        // Debug - verificar os parâmetros recebidos
        error_log("Método atualizar - Parâmetros recebidos:");
        error_log("ID: $id");
        error_log("Nome: $nome");
        error_log("Estoque Inicial: $estoque_inicial");
        error_log("Data Cadastro: $data_cadastro");
        error_log("Preço: $preco");
        error_log("Valor Compra: $valor_compra");
        error_log("Anotações: " . ($anotacoes === '' ? "VAZIO" : $anotacoes));
        
        // Adicionar a coluna anotacoes se não existir
        $this->conn->exec("ALTER TABLE {$this->table_name} ADD COLUMN IF NOT EXISTS anotacoes TEXT NULL");
        
        // Verificar se a coluna anotacoes existe
        $checkColumn = $this->conn->query("SHOW COLUMNS FROM {$this->table_name} LIKE 'anotacoes'")->rowCount();
        
        // Busca os valores atuais
        $stmt = $this->conn->prepare("SELECT estoque_inicial, estoque_atual FROM " . $this->table_name . " WHERE id = :id");
        $stmt->bindParam(":id", $id, PDO::PARAM_INT);
        $stmt->execute();
        $old = $stmt->fetch(PDO::FETCH_ASSOC);

        if ($old) {
            $old_estoque_inicial = (int)$old['estoque_inicial'];
            $old_estoque_atual = (int)$old['estoque_atual'];

            if ($old_estoque_atual >= $old_estoque_inicial) {
                // Não houve consumo, estoque atual segue o estoque inicial
                $novo_estoque_atual = $estoque_inicial;
            } else {
                // Mantenha o consumo já realizado
                $consumo = $old_estoque_inicial - $old_estoque_atual;
                $novo_estoque_atual = $estoque_inicial - $consumo;
                if ($novo_estoque_atual < 0) $novo_estoque_atual = 0;
            }
        } else {
            $novo_estoque_atual = $estoque_inicial;
        }

        // Construir a consulta SQL com base na existência da coluna anotacoes
        if ($checkColumn > 0) {
            $query = "UPDATE " . $this->table_name . " 
                    SET nome = :nome, 
                        estoque_inicial = :estoque_inicial,
                        estoque_atual = :estoque_atual,
                        data_cadastro = :data_cadastro,
                        preco = :preco,
                        valor_compra = :valor_compra,
                        anotacoes = :anotacoes
                    WHERE id = :id";
        } else {
            $query = "UPDATE " . $this->table_name . " 
                    SET nome = :nome, 
                        estoque_inicial = :estoque_inicial,
                        estoque_atual = :estoque_atual,
                        data_cadastro = :data_cadastro,
                        preco = :preco,
                        valor_compra = :valor_compra
                    WHERE id = :id";
            error_log("Coluna anotacoes não existe na tabela {$this->table_name}, ignorando este campo na atualização");
        }

        $stmt = $this->conn->prepare($query);

        // Usar bindValue em vez de bindParam para todos os parâmetros
        $stmt->bindValue(":nome", $nome, PDO::PARAM_STR);
        $stmt->bindValue(":estoque_inicial", $estoque_inicial, PDO::PARAM_INT);
        $stmt->bindValue(":estoque_atual", $novo_estoque_atual, PDO::PARAM_INT);
        $stmt->bindValue(":data_cadastro", $data_cadastro, PDO::PARAM_STR);
        $stmt->bindValue(":preco", $preco, PDO::PARAM_STR);
        $stmt->bindValue(":valor_compra", $valor_compra, PDO::PARAM_STR);
        
        // Debug - verificar o SQL e os parâmetros
        $sql_debug = $query;
        $sql_debug = str_replace(':nome', "'$nome'", $sql_debug);
        $sql_debug = str_replace(':estoque_inicial', "'$estoque_inicial'", $sql_debug);
        $sql_debug = str_replace(':estoque_atual', "'$novo_estoque_atual'", $sql_debug);
        $sql_debug = str_replace(':data_cadastro', "'$data_cadastro'", $sql_debug);
        $sql_debug = str_replace(':preco', "'$preco'", $sql_debug);
        $sql_debug = str_replace(':valor_compra', "'$valor_compra'", $sql_debug);
        if ($checkColumn > 0) {
            $sql_debug = str_replace(':anotacoes', is_null($anotacoes) ? "NULL" : "'$anotacoes'", $sql_debug);
        }
        $sql_debug = str_replace(':id', "'$id'", $sql_debug);
        error_log("SQL que será executado: $sql_debug");
        
        // Vincula o parâmetro anotacoes com o tipo correto apenas se a coluna existir
        if ($checkColumn > 0) {
            if ($anotacoes === '') {
                $stmt->bindValue(":anotacoes", '', PDO::PARAM_STR);
            } else {
                $stmt->bindValue(":anotacoes", $anotacoes, PDO::PARAM_STR);
            }
            error_log("Atualizando produto ID: $id, Anotacoes: " . ($anotacoes === '' ? "VAZIO" : $anotacoes));
        }
        
        $stmt->bindValue(":id", $id, PDO::PARAM_INT);

        return $stmt->execute();
    } catch(PDOException $e) {
        error_log("Erro ao atualizar produto: " . $e->getMessage());
        return false;
    }
}
public function listarEstoqueCritico($limite_percentual = 20) {
    try {
        // Primeiro obtemos o consumo real dos lançamentos
        $sql_consumo = "SELECT 
                        s.produto_id,
                        SUM(s.quantidade) as consumo_real
                    FROM servicos s
                    JOIN lancamentos l ON s.lancamento_id = l.id
                    WHERE s.produto_id IS NOT NULL
                    GROUP BY s.produto_id";
        
        $stmt = $this->conn->prepare($sql_consumo);
        $stmt->execute();
        $consumo_real = $stmt->fetchAll(PDO::FETCH_KEY_PAIR);
        
        // Agora buscamos os produtos com estoque crítico
        $sql = "SELECT 
                    p.id,
                    p.nome,
                    p.estoque_inicial,
                    p.estoque_atual,
                    p.preco,
                    p.valor_compra
                FROM produtos p
                ORDER BY (p.estoque_atual / p.estoque_inicial) ASC";
        
        $stmt = $this->conn->prepare($sql);
        $stmt->execute();
        
        $resultados = [];
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            // Calcula o consumo baseado nos lançamentos (se existir)
            $consumo = $consumo_real[$row['id']] ?? 0;
            $estoque_atual_calculado = $row['estoque_inicial'] - $consumo;

            // CORREÇÃO: evita divisão por zero
            $percentual = ($row['estoque_inicial'] != 0)
                ? ($estoque_atual_calculado / $row['estoque_inicial']) * 100
                : 0;
            
            if ($percentual <= $limite_percentual) {
                $resultados[] = [
                    'id' => $row['id'],
                    'nome' => $row['nome'],
                    'estoque_inicial' => $row['estoque_inicial'],
                    'estoque_atual' => $estoque_atual_calculado,
                    'consumo_real' => $consumo,
                    'percentual' => round($percentual, 2),
                    'status' => ($percentual <= 10) ? 'ESTOQUE CRÍTICO' : 'ESTOQUE BAIXO',
                    'preco' => $row['preco'],
                    'valor_compra' => $row['valor_compra']
                ];
            }
        }
        
        return $resultados;
        
    } catch (PDOException $e) {
        error_log("Erro ao listar estoque crítico: " . $e->getMessage());
        return [];
    }
}
public function sincronizarEstoques() {
    try {
        $this->conn->beginTransaction();
        
        // 1. Obter consumo real de todos os produtos
        $sql_consumo = "SELECT 
                        s.produto_id,
                        SUM(s.quantidade) as consumo_real
                    FROM servicos s
                    WHERE s.produto_id IS NOT NULL
                    GROUP BY s.produto_id";
        
        $stmt = $this->conn->prepare($sql_consumo);
        $stmt->execute();
        $consumo_real = $stmt->fetchAll(PDO::FETCH_KEY_PAIR);
        
        // 2. Atualizar todos os produtos
        $sql_update = "UPDATE produtos p
                    SET p.estoque_consumido = :consumo,
                        p.estoque_atual = p.estoque_inicial - :consumo
                    WHERE p.id = :id";
        
        $stmt = $this->conn->prepare($sql_update);
        
        foreach ($consumo_real as $produto_id => $consumo) {
            $stmt->execute([
                ':consumo' => $consumo,
                ':id' => $produto_id
            ]);
        }
        
        $this->conn->commit();
        return true;
        
    } catch (PDOException $e) {
        $this->conn->rollBack();
        error_log("Erro ao sincronizar estoques: " . $e->getMessage());
        return false;
    }
}
    public function excluir($id) {
        try {
            // Primeiro verifica se há serviços usando este produto
            $query = "SELECT COUNT(*) FROM servicos WHERE produto_id = ?";
            $stmt = $this->conn->prepare($query);
            $stmt->execute([$id]);
            if($stmt->fetchColumn() > 0) {
                return false; // Não pode excluir produto em uso
            }

            $query = "DELETE FROM " . $this->table_name . " WHERE id = ?";
            $stmt = $this->conn->prepare($query);
            return $stmt->execute([$id]);
        } catch(PDOException $e) {
            error_log("Erro ao excluir produto: " . $e->getMessage());
            return false;
        }
    }
	public function atualizaEstoqueInicial($produto_id, $novo_estoque_inicial) {
    $stmt = $this->conn->prepare("UPDATE produtos SET estoque_inicial = :estoque_inicial WHERE id = :id");
    $stmt->bindValue(':estoque_inicial', $novo_estoque_inicial, PDO::PARAM_INT);
    $stmt->bindValue(':id', $produto_id, PDO::PARAM_INT);
    $stmt->execute();
}

    public function atualizarEstoque($id, $quantidade, $tipo = 'saida') {
        try {
            $this->conn->beginTransaction();

            // Busca o produto atual
            $produto = $this->buscarPorId($id);
            if(!$produto) {
                throw new Exception("Produto não encontrado");
            }

            // Calcula novo estoque
            $novo_estoque = $tipo == 'entrada' 
                ? $produto['estoque_atual'] + $quantidade
                : $produto['estoque_atual'] - $quantidade;

            // Atualiza estoque_atual e estoque_consumido
            $query = "UPDATE " . $this->table_name . " 
                    SET estoque_atual = :estoque_atual,
                        estoque_consumido = estoque_consumido " . ($tipo == 'entrada' ? "-" : "+") . " :quantidade
                    WHERE id = :id";

            $stmt = $this->conn->prepare($query);
            $stmt->bindParam(":estoque_atual", $novo_estoque);
            $stmt->bindParam(":quantidade", $quantidade);
            $stmt->bindParam(":id", $id);

            $resultado = $stmt->execute();
            
            if($resultado) {
                $this->conn->commit();
                return true;
            } else {
                $this->conn->rollBack();
                return false;
            }
        } catch(Exception $e) {
            $this->conn->rollBack();
            error_log("Erro ao atualizar estoque: " . $e->getMessage());
            return false;
        }
    }
}