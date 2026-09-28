<?php
class Cliente {
    private $conn;
    private $table_name = "clientes";

    public function __construct($db) {
        $this->conn = $db;
    }

    public function criar($nome, $telefone, $rua_bairro, $cidade, $fatura_anterior = 0) {
        try {
            $query = "INSERT INTO " . $this->table_name . " 
                    (nome, telefone, rua_bairro, cidade, fatura_anterior) 
                    VALUES 
                    (:nome, :telefone, :rua_bairro, :cidade, :fatura_anterior)";

            $stmt = $this->conn->prepare($query);

            $stmt->bindParam(":nome", $nome);
            $stmt->bindParam(":telefone", $telefone);
            $stmt->bindParam(":rua_bairro", $rua_bairro);
            $stmt->bindParam(":cidade", $cidade);
            $stmt->bindParam(":fatura_anterior", $fatura_anterior);

            if($stmt->execute()) {
                return $this->conn->lastInsertId();
            }
            return false;
        } catch(PDOException $e) {
            error_log("Erro ao criar cliente: " . $e->getMessage());
            return false;
        }
    }

    public function listar() {
        try {
            $query = "SELECT * FROM " . $this->table_name . " ORDER BY nome";
            $stmt = $this->conn->prepare($query);
            $stmt->execute();
            return $stmt->fetchAll(PDO::FETCH_ASSOC);
        } catch(PDOException $e) {
            error_log("Erro ao listar clientes: " . $e->getMessage());
            return [];
        }
    }

    public function buscarPorId($id) {
        try {
            $query = "SELECT * FROM " . $this->table_name . " WHERE id = ?";
            $stmt = $this->conn->prepare($query);
            $stmt->execute([$id]);
            return $stmt->fetch(PDO::FETCH_ASSOC);
        } catch(PDOException $e) {
            error_log("Erro ao buscar cliente: " . $e->getMessage());
            return false;
        }
    }

    public function atualizar($id, $nome, $telefone, $rua_bairro, $cidade, $fatura_anterior = null) {
        try {
            if ($fatura_anterior === null) {
                $query = "UPDATE " . $this->table_name . " 
                        SET nome = :nome, 
                            telefone = :telefone, 
                            rua_bairro = :rua_bairro, 
                            cidade = :cidade 
                        WHERE id = :id";
            } else {
                $query = "UPDATE " . $this->table_name . " 
                        SET nome = :nome, 
                            telefone = :telefone, 
                            rua_bairro = :rua_bairro, 
                            cidade = :cidade,
                            fatura_anterior = :fatura_anterior 
                        WHERE id = :id";
            }

            $stmt = $this->conn->prepare($query);

            $stmt->bindParam(":nome", $nome);
            $stmt->bindParam(":telefone", $telefone);
            $stmt->bindParam(":rua_bairro", $rua_bairro);
            $stmt->bindParam(":cidade", $cidade);
            $stmt->bindParam(":id", $id);
            if ($fatura_anterior !== null) {
                $stmt->bindParam(":fatura_anterior", $fatura_anterior);
            }

            return $stmt->execute();
        } catch(PDOException $e) {
            error_log("Erro ao atualizar cliente: " . $e->getMessage());
            return false;
        }
    }

    public function atualizarFaturaAnterior($id, $valor) {
        try {
            $query = "UPDATE " . $this->table_name . " 
                    SET fatura_anterior = :fatura_anterior 
                    WHERE id = :id";

            $stmt = $this->conn->prepare($query);
            $stmt->bindParam(":fatura_anterior", $valor);
            $stmt->bindParam(":id", $id);
            return $stmt->execute();
        } catch(PDOException $e) {
            error_log("Erro ao atualizar fatura anterior: " . $e->getMessage());
            return false;
        }
    }

    public function excluir($id) {
        try {
            // Primeiro verifica se há lançamentos para este cliente
            $query = "SELECT COUNT(*) FROM lancamentos WHERE cliente_id = ?";
            $stmt = $this->conn->prepare($query);
            $stmt->execute([$id]);
            if($stmt->fetchColumn() > 0) {
                return false; // Não pode excluir cliente com lançamentos
            }

            $query = "DELETE FROM " . $this->table_name . " WHERE id = ?";
            $stmt = $this->conn->prepare($query);
            return $stmt->execute([$id]);
        } catch(PDOException $e) {
            error_log("Erro ao excluir cliente: " . $e->getMessage());
            return false;
        }
    }

    public function buscar($termo) {
        try {
            $query = "SELECT * FROM " . $this->table_name . " 
                    WHERE nome LIKE :termo 
                    OR rua_bairro LIKE :termo 
                    OR cidade LIKE :termo 
                    ORDER BY nome";

            $termo = "%{$termo}%";
            $stmt = $this->conn->prepare($query);
            $stmt->bindParam(":termo", $termo);
            $stmt->execute();

            return $stmt->fetchAll(PDO::FETCH_ASSOC);
        } catch(PDOException $e) {
            error_log("Erro ao buscar clientes: " . $e->getMessage());
            return [];
        }
    }
}