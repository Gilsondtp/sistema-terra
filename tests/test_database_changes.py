import os
import shutil
import sqlite3
import tempfile
import unittest

import database
import hotfolder_monitor


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

    def test_nordeste_september_balance_correction_updates_october_snapshots(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE clientes SET fatura_anterior = 10192.50 WHERE id = 23")
            conn.execute(
                """
                UPDATE lancamentos
                SET fatura_anterior = 10192.50,
                    saldo_fatura_anterior = 10192.50 - COALESCE(pagamento_fatura_anterior, 0)
                WHERE cliente_id = 23
                """
            )

        hotfolder_monitor.limpar_e_corrigir_registros_monitorados()

        with sqlite3.connect(self.db_path) as conn:
            saldo_cliente = conn.execute(
                "SELECT fatura_anterior FROM clientes WHERE id = 23"
            ).fetchone()[0]
            snapshots = conn.execute(
                "SELECT DISTINCT fatura_anterior, saldo_fatura_anterior FROM lancamentos WHERE cliente_id = 23"
            ).fetchall()
            count = conn.execute("SELECT COUNT(*) FROM lancamentos WHERE cliente_id = 23").fetchone()[0]
        self.assertEqual(saldo_cliente, 8852.50)
        self.assertEqual([tuple(row) for row in snapshots], [(8852.50, 8852.50)])
        self.assertEqual(count, 4)

    def test_nordeste_autocorrection_waits_until_september_rows_are_closed(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE clientes SET fatura_anterior = 10192.50 WHERE id = 23")
            conn.execute(
                """
                INSERT INTO lancamentos
                    (cliente_id, cliente_nome_original, identificado, origem, data_lancamento,
                     fatura_anterior, saldo_fatura_anterior)
                VALUES (23, 'Nordeste', 1, 'manual', '2026-09-30', 10192.50, 10192.50)
                """
            )

        hotfolder_monitor.limpar_e_corrigir_registros_monitorados()

        with sqlite3.connect(self.db_path) as conn:
            saldo_cliente = conn.execute(
                "SELECT fatura_anterior FROM clientes WHERE id = 23"
            ).fetchone()[0]
        self.assertEqual(saldo_cliente, 10192.50)

    def test_individual_invoice_close_transfers_verified_saldo_and_refreshes_remaining_rows(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE clientes SET fatura_anterior = 4310.00 WHERE id = 23")
            cursor = conn.execute(
                """
                INSERT INTO lancamentos
                    (cliente_id, cliente_nome_original, identificado, origem, data_lancamento,
                     valor_entrega, valor_pagamento, fatura_anterior,
                     pagamento_fatura_anterior, saldo_fatura_anterior, observacao)
                VALUES (23, 'Nordeste', 1, 'manual', '2026-09-30',
                        130.00, 0.00, 4310.00, 1430.00, 2880.00, 'Fechamento setembro')
                """
            )
            lancamento_id = cursor.lastrowid
            conn.execute(
                """
                INSERT INTO servicos
                    (lancamento_id, produto_id, descricao, quantidade, valor,
                     cores_detectadas, arquivos_origem, pasta_origem)
                VALUES (?, NULL, 'Serviços de setembro', 1, 5842.50, '', '[]', '')
                """,
                (lancamento_id,),
            )

        ok, saldo = database.fechar_fatura_cliente(23, "2026-09-01", "2026-09-30")
        self.assertTrue(ok, saldo)
        self.assertEqual(saldo, 8852.50)

        with sqlite3.connect(self.db_path) as conn:
            balance = conn.execute(
                "SELECT fatura_anterior FROM clientes WHERE id = 23"
            ).fetchone()[0]
            old_september = conn.execute(
                "SELECT COUNT(*) FROM lancamentos WHERE cliente_id = 23 AND data_lancamento = '2026-09-30'"
            ).fetchone()[0]
            remaining_snapshots = conn.execute(
                "SELECT DISTINCT fatura_anterior, saldo_fatura_anterior FROM lancamentos WHERE cliente_id = 23"
            ).fetchall()
        self.assertEqual(balance, 8852.50)
        self.assertEqual(old_september, 0)
        self.assertEqual([tuple(row) for row in remaining_snapshots], [(8852.50, 8852.50)])

    def test_month_close_transfers_balance_and_preserves_october_data_and_cash(self):
        with sqlite3.connect(self.db_path) as conn:
            cash_before = conn.execute(
                "SELECT COUNT(*), ROUND(COALESCE(SUM(valor), 0), 2) FROM lancamentos_caixa"
            ).fetchone()
            october_count = conn.execute("SELECT COUNT(*) FROM lancamentos").fetchone()[0]
            nordeste_before = conn.execute(
                "SELECT fatura_anterior FROM clientes WHERE id = 23"
            ).fetchone()[0]
        self.assertEqual(october_count, 67)
        self.assertEqual(nordeste_before, 8852.50)

        ok, message = database.realizar_virada_mes("2026-09-30", "somente_hotfolder_mes_atual")
        self.assertTrue(ok, message)
        with sqlite3.connect(self.db_path) as conn:
            after_september = conn.execute(
                "SELECT fatura_anterior FROM clientes WHERE id = 23"
            ).fetchone()[0]
            october_count_after_september = conn.execute("SELECT COUNT(*) FROM lancamentos").fetchone()[0]
        self.assertEqual(after_september, 8852.50)
        self.assertEqual(october_count_after_september, 67)

        ok, message = database.realizar_virada_mes("2026-10-31", "manter_apos_corte")
        self.assertTrue(ok, message)
        with sqlite3.connect(self.db_path) as conn:
            november_opening = conn.execute(
                "SELECT fatura_anterior FROM clientes WHERE id = 23"
            ).fetchone()[0]
            launches_after_october = conn.execute("SELECT COUNT(*) FROM lancamentos").fetchone()[0]
            cash_after = conn.execute(
                "SELECT COUNT(*), ROUND(COALESCE(SUM(valor), 0), 2) FROM lancamentos_caixa"
            ).fetchone()
        self.assertEqual(november_opening, 10372.50)  # 8.852,50 + 1.520,00 de serviços em outubro
        self.assertEqual(launches_after_october, 0)
        self.assertEqual(cash_after, cash_before)

    def test_hotfolder_only_close_is_blocked_by_post_cut_manual_records(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO lancamentos
                    (cliente_id, cliente_nome_original, identificado, origem, data_lancamento,
                     valor_entrega, valor_pagamento, fatura_anterior,
                     pagamento_fatura_anterior, saldo_fatura_anterior, observacao)
                VALUES (23, 'Nordeste', 1, 'manual', '2026-10-10',
                        0, 0, 8852.50, 0, 8852.50, 'Lançamento manual de teste')
                """
            )
            launches_before = conn.execute("SELECT COUNT(*) FROM lancamentos").fetchone()[0]

        ok, message = database.realizar_virada_mes("2026-09-30", "somente_hotfolder_mes_atual")
        self.assertFalse(ok)
        self.assertIn("lançamento(s) manual(is) posterior(es)", message)
        self.assertIn("Nenhum dado foi alterado", message)
        self.assertEqual(os.listdir(self.backup_dir), [])

        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM lancamentos").fetchone()[0], launches_before)
            self.assertEqual(
                conn.execute("SELECT fatura_anterior FROM clientes WHERE id = 23").fetchone()[0],
                8852.50,
            )

    def test_destructive_close_is_blocked_when_new_month_records_exist(self):
        with sqlite3.connect(self.db_path) as conn:
            balance_before = conn.execute(
                "SELECT fatura_anterior FROM clientes WHERE id = 23"
            ).fetchone()[0]
            launches_before = conn.execute("SELECT COUNT(*) FROM lancamentos").fetchone()[0]
            cash_before = conn.execute(
                "SELECT COUNT(*), ROUND(COALESCE(SUM(valor), 0), 2) FROM lancamentos_caixa"
            ).fetchone()

        ok, message = database.realizar_virada_mes("2026-09-30", "limpar_tudo")
        self.assertFalse(ok)
        self.assertIn("Virada cancelada", message)
        self.assertIn("Nenhum dado foi alterado", message)
        self.assertEqual(os.listdir(self.backup_dir), [])

        with sqlite3.connect(self.db_path) as conn:
            balance_after = conn.execute(
                "SELECT fatura_anterior FROM clientes WHERE id = 23"
            ).fetchone()[0]
            launches_after = conn.execute("SELECT COUNT(*) FROM lancamentos").fetchone()[0]
            cash_after = conn.execute(
                "SELECT COUNT(*), ROUND(COALESCE(SUM(valor), 0), 2) FROM lancamentos_caixa"
            ).fetchone()
        self.assertEqual(balance_after, balance_before)
        self.assertEqual(launches_after, launches_before)
        self.assertEqual(cash_after, cash_before)


if __name__ == "__main__":
    unittest.main()
