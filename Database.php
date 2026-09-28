<?php
require_once __DIR__ . '/config.php';

class Database {
    private $host = DB_HOST;
    private $db_name = DB_NAME;
    private $username = DB_USER;
    private $password = DB_PASS;
    private $conn;
    
    public function getConnection() {
        $this->conn = null;
        
        try {
            $this->conn = new PDO(
                "mysql:host=" . $this->host . ";dbname=" . $this->db_name,
                $this->username,
                $this->password
            );
            $this->conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            $this->conn->exec("set names utf8mb4");
        } catch(PDOException $e) {
            echo "Erro de conexão: " . $e->getMessage();
        }
        
        return $this->conn;
    }
    
    public static function converteDataMysql($data) {
        if (empty($data)) return null;
        $partes = explode('/', $data);
        if (count($partes) != 3) return null;
        return "{$partes[2]}-{$partes[1]}-{$partes[0]}";
    }
    
    public static function converteMysqlData($data) {
        if (empty($data)) return null;
        return date('d/m/Y', strtotime($data));
    }
    
    public static function formataMoeda($valor) {
        return number_format($valor, 2, ',', '.');
    }
}