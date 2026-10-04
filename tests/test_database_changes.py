import os
import shutil
import sqlite3
import tempfile
import unittest

import database


class DatabaseChangeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="terra-db-test-")
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        self.backup_dir = os.path.join(self.temp_dir.name, "backups")
        os.makedirs(self.backup_dir)
        shutil.copy2(os.path.join(database.BASE_DIR, "sistema_terra.db"), self.db_path)
        self.original_db_path = database.DB_PATH
        self.original_backup_dir = database.BACKUP_DIR
        database.DB_PATH = self.db_path
        database.BACKUP_DIR = self.backup_dir
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        database.BACKUP_DIR = self.original_backup_dir
        self.temp_dir.cleanup()

    def test_cnpj_is_persisted_formatted_and_searchable(self):
        with sqlite3.connect(self.db_path) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(clientes)")}
        self.assertIn("cnpj", columns)

        client_id = database.criar_cliente(
            "Cliente CNPJ Teste", "", "", "", 0, "", "12.345.678/0001-95"
        )
        client = database.buscar_cliente(client_id)
        self.assertEqual(client["cnpj"], "12345678000195")
        self.assertEqual(database.formatar_cnpj(client["cnpj"]), "12.345.678/0001-95")
        self.assertEqual(database.listar_clientes("12.345.678/0001-95")[0]["id"], client_id)

        database.atualizar_cliente(
            client_id, "Cliente CNPJ Teste", "", "", "", 0, "", "98.765.432/0001-10"
        )
        self.assertEqual(database.buscar_cliente(client_id)["cnpj"], "98765432000110")

    def test_month_close_preserves_cash_transactions(self):
        with sqlite3.connect(self.db_path) as conn:
            before = conn.execute(
                "SELECT COUNT(*), ROUND(COALESCE(SUM(valor), 0), 2) FROM lancamentos_caixa"
            ).fetchone()

        ok, message = database.realizar_virada_mes("2026-09-30", "limpar_tudo")
        self.assertTrue(ok, message)

        with sqlite3.connect(self.db_path) as conn:
            after = conn.execute(
                "SELECT COUNT(*), ROUND(COALESCE(SUM(valor), 0), 2) FROM lancamentos_caixa"
            ).fetchone()
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
