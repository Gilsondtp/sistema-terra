<?php
class Lancamento {
    private $conn;
    private $table_name = "lancamentos";

    public function __construct($db) {
        $this->conn = $db;
    }

    public function criar($dados) {
        $this->conn->beginTransaction();
        try {
            $query = "INSERT INTO " . $this->table_name . "
                     (cliente_id, data_lancamento, valor_entrega, valor_pagamento, fatura_anterior, pagamento_fatura_anterior, saldo_fatura_anterior, observacao)
                     VALUES
                     (:cliente_id, :data_lancamento, :valor_entrega, :valor_pagamento, :fatura_anterior, :pagamento_fatura_anterior, :saldo_fatura_anterior, :observacao)";
            $stmt = $this->conn->prepare($query);

            $valor_entrega = str_replace(['.', ','], ['', '.'], $dados['valor_entrega']);
            $valor_pagamento = str_replace(['.', ','], ['', '.'], $dados['valor_pagamento']);
            $fatura_anterior = str_replace(['.', ','], ['', '.'], $dados['fatura_anterior']);
            $pagamento_fatura_anterior = str_replace(['.', ','], ['', '.'], $dados['pagamento_fatura_anterior']);
            $saldo_fatura_anterior = $fatura_anterior - $pagamento_fatura_anterior;
            $observacao = isset($dados['observacao']) ? $dados['observacao'] : '';

            $stmt->bindParam(':cliente_id', $dados['cliente_id']);
            $stmt->bindParam(':data_lancamento', $dados['data_lancamento']);
            $stmt->bindParam(':valor_entrega', $valor_entrega);
            $stmt->bindParam(':valor_pagamento', $valor_pagamento);
            $stmt->bindParam(':fatura_anterior', $fatura_anterior);
            $stmt->bindParam(':pagamento_fatura_anterior', $pagamento_fatura_anterior);
            $stmt->bindParam(':saldo_fatura_anterior', $saldo_fatura_anterior);
            $stmt->bindParam(':observacao', $observacao);

            if(!$stmt->execute()) {
                throw new Exception("Erro ao criar lançamento principal");
            }
            $lancamento_id = $this->conn->lastInsertId();

            if (isset($dados['servicos']) && !empty($dados['servicos'])) {
                $query = "INSERT INTO servicos
                         (lancamento_id, produto_id, descricao, quantidade, valor)
                         VALUES
                         (:lancamento_id, :produto_id, :descricao, :quantidade, :valor)";
                $stmt = $this->conn->prepare($query);

                foreach ($dados['servicos'] as $servico) {
                    $produto_id = (isset($servico['produto_id']) && $servico['produto_id'] !== "" && is_numeric($servico['produto_id'])) ? (int)$servico['produto_id'] : null;
                    $valor = str_replace(['.', ','], ['', '.'], $servico['valor']);

                    $stmt->bindValue(':lancamento_id', $lancamento_id);
                    if (is_null($produto_id)) {
                        $stmt->bindValue(':produto_id', null, PDO::PARAM_NULL);
                    } else {
                        $stmt->bindValue(':produto_id', $produto_id, PDO::PARAM_INT);
                    }
                    $stmt->bindValue(':descricao', $servico['descricao']);
                    $stmt->bindValue(':quantidade', $servico['quantidade']);
                    $stmt->bindValue(':valor', $valor);

                    if(!$stmt->execute()) {
                        throw new Exception("Erro ao inserir serviço");
                    }

                    if (!is_null($produto_id)) {
                        $queryEstoque = "UPDATE produtos SET
                                         estoque_atual = estoque_atual - :quantidade,
                                         estoque_consumido = estoque_consumido + :quantidade
                                         WHERE id = :produto_id";
                        $stmt_estoque = $this->conn->prepare($queryEstoque);
                        $stmt_estoque->bindValue(':quantidade', $servico['quantidade']);
                        $stmt_estoque->bindValue(':produto_id', $produto_id, PDO::PARAM_INT);
                        if(!$stmt_estoque->execute()) {
                            throw new Exception("Erro ao atualizar estoque");
                        }
                    }
                }
            }
            $this->conn->commit();
            return $lancamento_id;
        } catch (Exception $e) {
            $this->conn->rollBack();
            error_log("ERRO (criar lançamento): " . $e->getMessage());
            return false;
        }
    }

    public function atualizar($id, $dados) {
        $this->conn->beginTransaction();
        try {
            $query = "UPDATE " . $this->table_name . " SET
                     cliente_id = :cliente_id,
                     data_lancamento = :data_lancamento,
                     valor_entrega = :valor_entrega,
                     valor_pagamento = :valor_pagamento,
                     fatura_anterior = :fatura_anterior,
                     pagamento_fatura_anterior = :pagamento_fatura_anterior,
                     saldo_fatura_anterior = :saldo_fatura_anterior,
                     observacao = :observacao
                     WHERE id = :id";
            $stmt = $this->conn->prepare($query);

            $valor_entrega = str_replace(['.', ','], ['', '.'], $dados['valor_entrega']);
            $valor_pagamento = str_replace(['.', ','], ['', '.'], $dados['valor_pagamento']);
            $fatura_anterior = str_replace(['.', ','], ['', '.'], $dados['fatura_anterior']);
            $pagamento_fatura_anterior = str_replace(['.', ','], ['', '.'], $dados['pagamento_fatura_anterior']);
            $saldo_fatura_anterior = $fatura_anterior - $pagamento_fatura_anterior;
            $observacao = isset($dados['observacao']) ? $dados['observacao'] : '';

            $stmt->bindParam(':id', $id);
            $stmt->bindParam(':cliente_id', $dados['cliente_id']);
            $stmt->bindParam(':data_lancamento', $dados['data_lancamento']);
            $stmt->bindParam(':valor_entrega', $valor_entrega);
            $stmt->bindParam(':valor_pagamento', $valor_pagamento);
            $stmt->bindParam(':fatura_anterior', $fatura_anterior);
            $stmt->bindParam(':pagamento_fatura_anterior', $pagamento_fatura_anterior);
            $stmt->bindParam(':saldo_fatura_anterior', $saldo_fatura_anterior);
            $stmt->bindParam(':observacao', $observacao);

            if(!$stmt->execute()) {
                throw new Exception("Erro ao atualizar lançamento principal");
            }

            $servicos_antigos = $this->listarServicos($id);
            foreach ($servicos_antigos as $servico) {
                if (!empty($servico['produto_id'])) {
                    $stmtEstoque = $this->conn->prepare("
                        UPDATE produtos SET
                        estoque_atual = estoque_atual + :qtd,
                        estoque_consumido = estoque_consumido - :qtd
                        WHERE id = :produto_id
                    ");
                    $stmtEstoque->bindValue(':qtd', $servico['quantidade']);
                    $stmtEstoque->bindValue(':produto_id', $servico['produto_id']);
                    $stmtEstoque->execute();
                }
            }

            $this->excluirServicos($id);

            if (!empty($dados['servicos'])) {
                $query = "INSERT INTO servicos
                         (lancamento_id, produto_id, descricao, quantidade, valor)
                         VALUES
                         (:lancamento_id, :produto_id, :descricao, :quantidade, :valor)";
                $stmt = $this->conn->prepare($query);

                foreach ($dados['servicos'] as $servico) {
                    $produto_id = (isset($servico['produto_id']) && $servico['produto_id'] !== "" && is_numeric($servico['produto_id'])) ? (int)$servico['produto_id'] : null;
                    $valor = str_replace(['.', ','], ['', '.'], $servico['valor']);

                    $stmt->bindValue(':lancamento_id', $id);
                    if (is_null($produto_id)) {
                        $stmt->bindValue(':produto_id', null, PDO::PARAM_NULL);
                    } else {
                        $stmt->bindValue(':produto_id', $produto_id, PDO::PARAM_INT);
                    }
                    $stmt->bindValue(':descricao', $servico['descricao']);
                    $stmt->bindValue(':quantidade', $servico['quantidade']);
                    $stmt->bindValue(':valor', $valor);

                    if(!$stmt->execute()) {
                        throw new Exception("Erro ao inserir serviço");
                    }

                    if (!is_null($produto_id)) {
                        $queryEstoque = "UPDATE produtos SET
                                         estoque_atual = estoque_atual - :quantidade,
                                         estoque_consumido = estoque_consumido + :quantidade
                                         WHERE id = :produto_id";
                        $stmt_estoque = $this->conn->prepare($queryEstoque);
                        $stmt_estoque->bindValue(':quantidade', $servico['quantidade']);
                        $stmt_estoque->bindValue(':produto_id', $produto_id, PDO::PARAM_INT);
                        if(!$stmt_estoque->execute()) {
                            throw new Exception("Erro ao atualizar estoque");
                        }
                    }
                }
            }
            $this->conn->commit();
            return true;
        } catch (Exception $e) {
            $this->conn->rollBack();
            error_log("ERRO (atualizar lançamento): " . $e->getMessage());
            return false;
        }
    }

    public function listar($filtros = array()) {
    try {
        $conditions = array();
        $params = array();

        $query = "SELECT l.*, c.nome as cliente_nome
                FROM " . $this->table_name . " l
                JOIN clientes c ON l.cliente_id = c.id";

        if (!empty($filtros['cliente_id'])) {
            $conditions[] = "l.cliente_id = :cliente_id";
            $params[':cliente_id'] = $filtros['cliente_id'];
        }
        if (!empty($filtros['data_inicio'])) {
            $conditions[] = "l.data_lancamento >= :data_inicio";
            $params[':data_inicio'] = $filtros['data_inicio'];
        }
        if (!empty($filtros['data_fim'])) {
            $conditions[] = "l.data_lancamento <= :data_fim";
            $params[':data_fim'] = $filtros['data_fim'];
        }
        if (!empty($filtros['texto_servico'])) {
            $conditions[] = "EXISTS (
                SELECT 1 FROM servicos s 
                WHERE s.lancamento_id = l.id 
                AND s.descricao LIKE :texto_servico
            )";
            $params[':texto_servico'] = '%' . $filtros['texto_servico'] . '%';
        }
        if (!empty($filtros['produto_id'])) {
            $conditions[] = "EXISTS (
                SELECT 1 FROM servicos s 
                WHERE s.lancamento_id = l.id 
                AND s.produto_id = :produto_id
            )";
            $params[':produto_id'] = $filtros['produto_id'];
        }
        if (!empty($conditions)) {
            $query .= " WHERE " . implode(" AND ", $conditions);
        }
        $query .= " ORDER BY l.data_lancamento ASC, l.id ASC";

        $stmt = $this->conn->prepare($query);
        foreach ($params as $key => $value) {
            $stmt->bindValue($key, $value);
        }
        $stmt->execute();

        $lancamentos = $stmt->fetchAll(PDO::FETCH_ASSOC);

        foreach ($lancamentos as &$lancamento) {
            $lancamento['servicos'] = $this->listarServicos($lancamento['id']);
        }
        return $lancamentos;
    } catch (Exception $e) {
        error_log("Erro ao listar lançamentos: " . $e->getMessage());
        return false;
    }
}
public function apagarPorCliente($cliente_id, $data_inicio = null, $data_fim = null) {
    try {
        // Monta condições (com filtro opcional de período)
        $conditions = "l.cliente_id = :cliente_id";
        $params = [':cliente_id' => $cliente_id];
        if (!empty($data_inicio)) {
            $conditions .= " AND l.data_lancamento >= :data_inicio";
            $params[':data_inicio'] = $data_inicio;
        }
        if (!empty($data_fim)) {
            $conditions .= " AND l.data_lancamento <= :data_fim";
            $params[':data_fim'] = $data_fim;
        }

        // Apaga serviços relacionados
        // ATENÇÃO: o estoque NÃO é estornado aqui propositalmente.
        // Os produtos foram efetivamente consumidos/vendidos e não devem
        // voltar ao estoque, para que o saldo do mês seguinte não seja
        // inflado com quantidades já vendidas.
        $sql = "DELETE s FROM servicos s
                JOIN lancamentos l ON s.lancamento_id = l.id
                WHERE $conditions";
        $stmt = $this->conn->prepare($sql);
        foreach ($params as $key => $value) {
            $stmt->bindValue($key, $value);
        }
        $stmt->execute();

        // Apaga os lançamentos
        $sql = "DELETE l FROM lancamentos l WHERE $conditions";
        $stmt = $this->conn->prepare($sql);
        foreach ($params as $key => $value) {
            $stmt->bindValue($key, $value);
        }
        $stmt->execute();

        return true;
    } catch (Exception $e) {
        error_log("ERRO (apagar lançamentos do cliente {$cliente_id}): " . $e->getMessage());
        return false;
    }
}

/**
 * Fecha a fatura de um cliente: calcula o saldo devedor (incluindo o saldo
 * da fatura anterior), transfere esse saldo para o campo fatura_anterior do
 * cliente e apaga os lançamentos do período.
 *
 * Tudo é executado dentro de uma transação com lock no registro do cliente,
 * garantindo que o saldo nunca seja transferido sem apagar os lançamentos
 * (ou vice-versa) e evitando dupla transferência em acessos simultâneos.
 *
 * @param int         $cliente_id  ID do cliente
 * @param string|null $data_inicio Início do período (opcional, formato MySQL)
 * @param string|null $data_fim    Fim do período (opcional, formato MySQL)
 * @return float|false Saldo devedor transferido, ou false em caso de erro
 */
public function fecharFatura($cliente_id, $data_inicio = null, $data_fim = null) {
    $this->conn->beginTransaction();
    try {
        // Busca a fatura anterior do cliente com lock (evita fechamento duplo simultâneo)
        $stmt = $this->conn->prepare("SELECT fatura_anterior FROM clientes WHERE id = ? FOR UPDATE");
        $stmt->execute([$cliente_id]);
        $cliente = $stmt->fetch(PDO::FETCH_ASSOC);
        if (!$cliente) {
            throw new Exception("Cliente não encontrado.");
        }
        $fatura_anterior = (float)$cliente['fatura_anterior'];

        // Busca os lançamentos do período (mesmo filtro exibido na tela)
        $filtros = ['cliente_id' => $cliente_id];
        if (!empty($data_inicio)) {
            $filtros['data_inicio'] = $data_inicio;
        }
        if (!empty($data_fim)) {
            $filtros['data_fim'] = $data_fim;
        }
        $lancamentos = $this->listar($filtros);
        if ($lancamentos === false) {
            throw new Exception("Erro ao consultar os lançamentos do cliente.");
        }
        if (empty($lancamentos)) {
            throw new Exception("Nenhum lançamento encontrado para o cliente no período.");
        }

        // Calcula os totais
        $total_servicos = 0;
        $total_entrega = 0;
        $total_pagamento = 0;
        $total_pagamento_fatura_anterior = 0;
        foreach ($lancamentos as $l) {
            foreach ($l['servicos'] as $s) {
                $total_servicos += (float)$s['valor'];
            }
            $total_entrega += (float)$l['valor_entrega'];
            $total_pagamento += (float)$l['valor_pagamento'];
            $total_pagamento_fatura_anterior += (float)$l['pagamento_fatura_anterior'];
        }

        // Saldo da fatura anterior + saldo do período = novo saldo devedor
        $saldo_fatura_anterior = $fatura_anterior - $total_pagamento_fatura_anterior;
        $saldo_devedor = ($total_servicos + $total_entrega - $total_pagamento) + $saldo_fatura_anterior;

        // Transfere o saldo devedor para a fatura anterior do cliente
        $stmt = $this->conn->prepare("UPDATE clientes SET fatura_anterior = ? WHERE id = ?");
        $stmt->execute([$saldo_devedor, $cliente_id]);

        // Apaga os lançamentos do período (sem estornar estoque — ver apagarPorCliente)
        if (!$this->apagarPorCliente($cliente_id, $data_inicio, $data_fim)) {
            throw new Exception("Erro ao apagar os lançamentos do cliente.");
        }

        $this->conn->commit();
        return $saldo_devedor;
    } catch (Exception $e) {
        if ($this->conn->inTransaction()) {
            $this->conn->rollBack();
        }
        error_log("ERRO (fechar fatura do cliente {$cliente_id}): " . $e->getMessage());
        return false;
    }
}
    private function listarServicos($lancamento_id) {
        $query = "SELECT s.*, p.nome as produto_nome
                 FROM servicos s
                 LEFT JOIN produtos p ON s.produto_id = p.id
                 WHERE s.lancamento_id = :lancamento_id";
        $stmt = $this->conn->prepare($query);
        $stmt->bindParam(':lancamento_id', $lancamento_id);
        $stmt->execute();
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    }

    private function excluirServicos($lancamento_id) {
        $query = "DELETE FROM servicos WHERE lancamento_id = :lancamento_id";
        $stmt = $this->conn->prepare($query);
        $stmt->bindParam(':lancamento_id', $lancamento_id);
        return $stmt->execute();
    }
	 public function getProdutosUtilizadosPeriodo($data_inicio, $data_fim) {
    try {
        $sql = "SELECT 
                    s.produto_id as id,
                    p.nome,
                    SUM(s.quantidade) as quantidade,
                    SUM(s.valor) as valor_total
                FROM servicos s
                JOIN lancamentos l ON s.lancamento_id = l.id
                JOIN produtos p ON s.produto_id = p.id
                WHERE l.data_lancamento BETWEEN :data_inicio AND :data_fim
                AND s.produto_id IS NOT NULL
                GROUP BY s.produto_id";
        
        $stmt = $this->conn->prepare($sql);
        $stmt->execute([
            ':data_inicio' => $data_inicio,
            ':data_fim' => $data_fim
        ]);
        
        $result = [];
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            $result[$row['id']] = [
                'nome' => $row['nome'],
                'quantidade' => (int)$row['quantidade'],
                'valor_total' => (float)$row['valor_total']
            ];
        }
        return $result;
        
    } catch (PDOException $e) {
        error_log("Erro ao buscar produtos utilizados: " . $e->getMessage());
        return [];
    }
}
    public function excluir($id) {
        $this->conn->beginTransaction();
        try {
            $stmt = $this->conn->prepare("SELECT id FROM " . $this->table_name . " WHERE id = ?");
            $stmt->execute([$id]);
            if (!$stmt->fetch()) {
                throw new Exception("Lançamento não encontrado");
            }

            $servicos = $this->listarServicos($id);

            if (!$this->excluirServicos($id)) {
                throw new Exception("Falha ao excluir serviços do lançamento");
            }

            foreach ($servicos as $servico) {
                if (!empty($servico['produto_id'])) {
                    $stmt = $this->conn->prepare("
                        UPDATE produtos SET
                        estoque_atual = estoque_atual + ?,
                        estoque_consumido = estoque_consumido - ?
                        WHERE id = ?
                    ");
                    $stmt->execute([
                        $servico['quantidade'],
                        $servico['quantidade'],
                        $servico['produto_id']
                    ]);
                }
            }

            $stmt = $this->conn->prepare("DELETE FROM " . $this->table_name . " WHERE id = ?");
            $stmt->execute([$id]);
            if ($stmt->rowCount() === 0) {
                throw new Exception("Nenhum lançamento foi excluído");
            }
            $this->conn->commit();
            return true;
        } catch (Exception $e) {
            $this->conn->rollBack();
            error_log("ERRO (excluir lançamento ID {$id}): " . $e->getMessage());
            return false;
        }
    }
}