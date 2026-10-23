import json
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

    def test_cash_auto_descriptions_are_shortened_and_manual_rows_are_marked_by_origin(self):
        with sqlite3.connect(self.db_path) as conn:
            stored_auto_description = conn.execute(
                "SELECT descricao FROM lancamentos_caixa WHERE origem = 'lancamento_cliente' LIMIT 1"
            ).fetchone()[0]
        self.assertNotIn("(Lanç. #", stored_auto_description)

        existing_auto = next(
            row for row in database.listar_lancamentos_caixa()
            if row["origem"] == "lancamento_cliente"
        )
        self.assertTrue(existing_auto["descricao"].startswith("Pagtº Cliente: "))
        self.assertNotIn("(Lanç. #", existing_auto["descricao"])

        manual_id = database.criar_lancamento_caixa(
            "Compra de insumos", "2026-10-06", "45,00", "despesa"
        )
        manual = next(row for row in database.listar_lancamentos_caixa() if row["id"] == manual_id)
        self.assertEqual(manual["descricao"], "Compra de insumos")
        self.assertEqual(manual["origem"], "manual")

        lancamento_id = database.criar_lancamento(
            {
                "cliente_id": 37,
                "data_lancamento": "2026-10-06",
                "valor_pagamento": "10,00",
                "pagamento_fatura_anterior": "0,00",
                "servicos": [],
            }
        )
        automatico = next(
            row for row in database.listar_lancamentos_caixa()
            if row["lancamento_id"] == lancamento_id
        )
        self.assertEqual(automatico["descricao"], "Pagtº Cliente: Edson")
        self.assertEqual(automatico["origem"], "lancamento_cliente")

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

    def test_open_hotfolder_group_reprocesses_when_rip_page_index_is_corrected(self):
        cliente_id = next(
            cliente["id"] for cliente in database.listar_clientes()
            if cliente["nome"].strip().upper() == "ITAPLAST"
        )
        produto_id = database.criar_produto(
            "Chapa Teste RIP", 100, "2026-10-01", 45.00, 20.00, pasta_hotfolder="P724_TEST"
        )
        output_dir = os.path.join(self.temp_dir.name, "output", "P724_TEST")
        source_dir = os.path.join(self.temp_dir.name, "rip")
        os.makedirs(output_dir)
        os.makedirs(source_dir)
        names = [
            "ItaplastGIULIASAFIRAcmpsC.TIF",
            "ItaplastGIULIASAFIRAcmpsC [1].TIF",
            "ItaplastGIULIASAFIRAcmpsM.TIF",
            "ItaplastGIULIASAFIRAcmpsM [1].TIF",
        ]
        for name in names:
            with open(os.path.join(output_dir, name), "wb") as file:
                file.write(b"test TIFF")
        with open(os.path.join(source_dir, "Itaplast_GIULIA_SAFIRA_cm.ps"), "wb") as file:
            file.write(b"test PostScript")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO lancamentos
                    (cliente_id, cliente_nome_original, identificado, origem, data_lancamento,
                     valor_entrega, valor_pagamento, fatura_anterior,
                     pagamento_fatura_anterior, saldo_fatura_anterior, observacao)
                VALUES (?, 'Itaplast', 1, 'hotfolder', '2026-10-23', 0, 0, 0, 0, 0,
                        'Auto Hot Folder (724)')
                """,
                (cliente_id,),
            )
            lancamento_id = cursor.lastrowid
            cursor = conn.execute(
                """
                INSERT INTO servicos
                    (lancamento_id, produto_id, descricao, quantidade, valor,
                     cores_detectadas, arquivos_origem, pasta_origem)
                VALUES (?, ?, 'GIULIA SAFIRA', 2, 90, 'C, M', ?, '724')
                """,
                (lancamento_id, produto_id, json.dumps(names)),
            )
            servico_id = cursor.lastrowid
            conn.execute(
                "UPDATE produtos SET estoque_atual = 98, estoque_consumido = 2 WHERE id = ?",
                (produto_id,),
            )
            for name in names:
                color = "C" if "psC" in name else "M"
                page = "1" if "[1]" in name else ""
                path = os.path.abspath(os.path.join(output_dir, name))
                conn.execute(
                    """
                    INSERT INTO arquivos_monitorados
                        (caminho_completo, nome_arquivo, pasta_produto, chave_agrupamento,
                         cor_detectada, pagina_detectada, lancamento_id, servico_id,
                         data_lancamento, ignorado)
                    VALUES (?, ?, 'P724_TEST', 'old-key', ?, ?, ?, ?, '2026-10-23', 0)
                    """,
                    (path, name, color, page, lancamento_id, servico_id),
                )

        hotfolder_monitor.limpar_e_corrigir_registros_monitorados()
        with sqlite3.connect(self.db_path) as conn:
            self.assertIsNone(
                conn.execute("SELECT 1 FROM lancamentos WHERE id = ?", (lancamento_id,)).fetchone()
            )
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM arquivos_monitorados WHERE lancamento_id = ?", (lancamento_id,)).fetchone()[0],
                0,
            )

        index = hotfolder_monitor.construir_indice_nomes_postscript(source_dir)
        for name in sorted(names):
            hotfolder_monitor.processar_arquivo_hotfolder(
                os.path.join(output_dir, name),
                "P724_TEST",
                data_ref="2026-10-23",
                arquivos_irmaos=names,
                indice_nomes_ps=index,
            )

        with sqlite3.connect(self.db_path) as conn:
            service = conn.execute(
                """
                SELECT s.quantidade, s.valor, s.descricao, s.cores_detectadas, l.id
                FROM servicos s JOIN lancamentos l ON l.id = s.lancamento_id
                WHERE s.produto_id = ? AND l.cliente_id = ? AND l.data_lancamento = '2026-10-23'
                ORDER BY l.id DESC LIMIT 1
                """,
                (produto_id, cliente_id),
            ).fetchone()
            stock = conn.execute(
                "SELECT estoque_atual, estoque_consumido FROM produtos WHERE id = ?", (produto_id,)
            ).fetchone()
            pages = {
                row[0]
                for row in conn.execute(
                    "SELECT pagina_detectada FROM arquivos_monitorados WHERE servico_id = (SELECT id FROM servicos WHERE lancamento_id = ?)",
                    (service[4],),
                )
            }
        self.assertEqual(service[0], 4)
        self.assertEqual(service[1], 180.0)
        self.assertEqual(service[2], "GIULIA SAFIRA")
        self.assertEqual(set(service[3].split(", ")), {"C", "P2-C", "M", "P2-M"})
        self.assertEqual(tuple(stock), (96, 4))
        self.assertEqual(pages, {"", "2"})

    def test_open_hotfolder_description_is_repaired_from_matching_postscript_name(self):
        cliente_id = next(
            cliente["id"] for cliente in database.listar_clientes()
            if cliente["nome"].strip().upper() == "ITAPLAST"
        )
        output_dir = os.path.join(self.temp_dir.name, "output", "PTEST_DESC")
        source_dir = os.path.join(self.temp_dir.name, "rip-source")
        os.makedirs(output_dir)
        os.makedirs(source_dir)
        output_name = "ItaplastDOMQUIXOTEPps.TIF"
        output_path = os.path.abspath(os.path.join(output_dir, output_name))
        with open(output_path, "wb") as file:
            file.write(b"test TIFF")
        with open(os.path.join(source_dir, "Itaplast_DOM_QUIXOTE_p.ps"), "wb") as file:
            file.write(b"test PostScript")
        database.set_config({"ps_entrada_path": source_dir})

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO lancamentos
                    (cliente_id, cliente_nome_original, identificado, origem, data_lancamento,
                     valor_entrega, valor_pagamento, fatura_anterior,
                     pagamento_fatura_anterior, saldo_fatura_anterior, observacao)
                VALUES (?, 'Itaplast', 1, 'hotfolder', '2026-10-23', 0, 0, 0, 0, 0,
                        'Auto Hot Folder (PTEST_DESC)')
                """,
                (cliente_id,),
            )
            lancamento_id = cursor.lastrowid
            cursor = conn.execute(
                """
                INSERT INTO servicos
                    (lancamento_id, produto_id, descricao, quantidade, valor,
                     cores_detectadas, arquivos_origem, pasta_origem)
                VALUES (?, NULL, 'DOMQUIXOT Ep', 1, 45, 'UNICA', ?, 'PTEST_DESC')
                """,
                (lancamento_id, json.dumps([output_name])),
            )
            servico_id = cursor.lastrowid
            conn.execute(
                """
                INSERT INTO arquivos_monitorados
                    (caminho_completo, nome_arquivo, pasta_produto, chave_agrupamento,
                     cor_detectada, pagina_detectada, lancamento_id, servico_id,
                     data_lancamento, ignorado)
                VALUES (?, ?, 'PTEST_DESC', 'old-description-key', 'UNICA', '', ?, ?, '2026-10-23', 0)
                """,
                (output_path, output_name, lancamento_id, servico_id),
            )

        hotfolder_monitor.limpar_e_corrigir_registros_monitorados()

        with sqlite3.connect(self.db_path) as conn:
            service = conn.execute(
                "SELECT descricao, quantidade, valor FROM servicos WHERE id = ?", (servico_id,)
            ).fetchone()
        self.assertEqual(tuple(service), ("DOM QUIXOTE", 1, 45.0))

    def test_known_compact_hotfolder_description_is_corrected_without_changing_amounts(self):
        with sqlite3.connect(self.db_path) as conn:
            client = conn.execute("SELECT id FROM clientes WHERE id = 20").fetchone()
            self.assertIsNotNone(client)
            cursor = conn.execute(
                """
                INSERT INTO lancamentos
                    (cliente_id, cliente_nome_original, identificado, origem, data_lancamento,
                     valor_entrega, valor_pagamento, fatura_anterior, pagamento_fatura_anterior,
                     saldo_fatura_anterior, observacao)
                VALUES (?, 'terra', 1, 'hotfolder', '2026-10-07', 0, 0, 0, 0, 0, 'teste parser')
                """,
                (client[0],),
            )
            lancamento_id = cursor.lastrowid
            cursor = conn.execute(
                """
                INSERT INTO servicos
                    (lancamento_id, produto_id, descricao, quantidade, valor,
                     cores_detectadas, arquivos_origem, pasta_origem)
                VALUES (?, NULL, 'ARQUIVOSENVIADO Stestenome 5', 7, 123.45,
                        'C, M, Y, K', '[]', '510x400')
                """,
                (lancamento_id,),
            )
            servico_id = cursor.lastrowid
            conn.commit()

        hotfolder_monitor.limpar_e_corrigir_registros_monitorados()

        with sqlite3.connect(self.db_path) as conn:
            servico = conn.execute(
                "SELECT descricao, quantidade, valor FROM servicos WHERE id = ?",
                (servico_id,),
            ).fetchone()
        self.assertEqual(tuple(servico), ("ARQUIVOS_ENVIADOS_teste_nome5", 7, 123.45))

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

    def test_individual_invoice_close_archives_details_and_refreshes_open_month_rows(self):
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
                "SELECT id, fatura_id FROM lancamentos WHERE cliente_id = 23 AND data_lancamento = '2026-09-30'"
            ).fetchone()
            fatura = conn.execute(
                "SELECT periodo, status, saldo_abertura, total_servicos, saldo_fechamento FROM faturas_cliente WHERE cliente_id = 23 AND periodo = '2026-09'"
            ).fetchone()
            september_service = conn.execute(
                "SELECT descricao, valor FROM servicos WHERE lancamento_id = ?",
                (lancamento_id,),
            ).fetchone()
            remaining_snapshots = conn.execute(
                "SELECT DISTINCT fatura_anterior, saldo_fatura_anterior FROM lancamentos WHERE cliente_id = 23 AND fatura_id IS NULL"
            ).fetchall()
        self.assertEqual(balance, 8852.50)
        self.assertIsNotNone(old_september)
        self.assertIsNotNone(old_september[1])
        self.assertEqual(tuple(fatura), ("2026-09", "fechada", 4310.0, 5842.5, 8852.5))
        self.assertEqual(tuple(september_service), ("Serviços de setembro", 5842.5))
        self.assertEqual([tuple(row) for row in remaining_snapshots], [(8852.5, 8852.5)])

    def test_archive_preserves_stock_cash_services_and_hotfolder_links(self):
        produto = database.listar_produtos()[0]
        stock_before = int(produto["estoque_atual"] or 0)
        with sqlite3.connect(self.db_path) as conn:
            cash_before = conn.execute(
                "SELECT COUNT(*), ROUND(COALESCE(SUM(valor), 0), 2) FROM lancamentos_caixa"
            ).fetchone()
            conn.execute("UPDATE clientes SET fatura_anterior = 0 WHERE id = 23")

        lancamento_id = database.criar_lancamento(
            {
                "cliente_id": 23,
                "data_lancamento": "2026-08-12",
                "fatura_anterior": 0,
                "servicos": [{
                    "descricao": "Chapa de teste", "quantidade": 1,
                    "produto_id": produto["id"], "valor": 12.50,
                }],
            }
        )
        stock_after_launch = database.buscar_produto(produto["id"])["estoque_atual"]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO arquivos_monitorados
                    (caminho_completo, nome_arquivo, pasta_produto, chave_agrupamento,
                     cor_detectada, lancamento_id, servico_id, data_lancamento, ignorado)
                SELECT '/tmp/arquivo-teste-arquivado.ps', 'arquivo-teste-arquivado.ps', 'teste',
                       'teste-arquivado', 'C', ?, id, '2026-08-12', 0
                FROM servicos WHERE lancamento_id = ? LIMIT 1
                """,
                (lancamento_id, lancamento_id),
            )

        ok, saldo = database.fechar_fatura_cliente(23, "2026-08-01", "2026-08-31")
        self.assertTrue(ok, saldo)
        self.assertEqual(database.buscar_produto(produto["id"])["estoque_atual"], stock_after_launch)
        hotfolder_monitor.limpar_e_corrigir_registros_monitorados()

        with sqlite3.connect(self.db_path) as conn:
            archived = conn.execute(
                "SELECT fatura_id FROM lancamentos WHERE id = ?", (lancamento_id,)
            ).fetchone()
            service = conn.execute(
                "SELECT id, descricao, quantidade, valor FROM servicos WHERE lancamento_id = ?",
                (lancamento_id,),
            ).fetchone()
            monitor = conn.execute(
                "SELECT lancamento_id, servico_id, ignorado FROM arquivos_monitorados WHERE caminho_completo = '/tmp/arquivo-teste-arquivado.ps'"
            ).fetchone()
            cash_after = conn.execute(
                "SELECT COUNT(*), ROUND(COALESCE(SUM(valor), 0), 2) FROM lancamentos_caixa"
            ).fetchone()
        self.assertIsNotNone(archived)
        self.assertIsNotNone(archived[0])
        self.assertEqual(tuple(service[1:]), ("Chapa de teste", 1, 12.5))
        self.assertEqual(tuple(monitor), (lancamento_id, service[0], 1))
        self.assertEqual(tuple(cash_after), tuple(cash_before))
        self.assertNotEqual(stock_before, stock_after_launch)
        payload = database.exportar_backup_json()
        self.assertIn("faturas_cliente", payload["tabelas"])
        self.assertIn("faturas_auditoria", payload["tabelas"])

    def test_reopened_invoice_audits_correction_and_recalculates_later_and_open_periods(self):
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
            setembro_id = cursor.lastrowid
            conn.execute(
                """
                INSERT INTO servicos
                    (lancamento_id, produto_id, descricao, quantidade, valor,
                     cores_detectadas, arquivos_origem, pasta_origem)
                VALUES (?, NULL, 'Serviços de setembro', 1, 5842.50, '', '[]', '')
                """,
                (setembro_id,),
            )

        novembro_id = database.criar_lancamento(
            {
                "cliente_id": 23,
                "data_lancamento": "2026-11-05",
                "servicos": [{"descricao": "Serviço de novembro", "quantidade": 1, "valor": 100.00}],
            }
        )
        self.assertTrue(database.fechar_fatura_cliente(23, "2026-09-01", "2026-09-30")[0])
        ok, saldo_outubro = database.fechar_fatura_cliente(23, "2026-10-01", "2026-10-31")
        self.assertTrue(ok, saldo_outubro)
        self.assertEqual(saldo_outubro, 10372.50)

        fatura_setembro = database.obter_fatura_periodo(23, "2026-09")
        fatura_outubro = database.obter_fatura_periodo(23, "2026-10")
        self.assertEqual(fatura_setembro["status"], "fechada")
        self.assertEqual(fatura_outubro["saldo_abertura"], 8852.50)

        ok, mensagem = database.reabrir_fatura_cliente(fatura_setembro["id"], "Corrigir valor do serviço")
        self.assertTrue(ok, mensagem)
        lancamento = database.buscar_lancamento(setembro_id)
        dados = {
            "cliente_id": 23,
            "cliente_nome_original": lancamento["cliente_nome_original"],
            "data_lancamento": lancamento["data_lancamento"],
            "valor_entrega": lancamento["valor_entrega"],
            "valor_pagamento": lancamento["valor_pagamento"],
            "fatura_anterior": lancamento["fatura_anterior"],
            "pagamento_fatura_anterior": lancamento["pagamento_fatura_anterior"],
            "observacao": lancamento["observacao"],
            "motivo_correcao": "Valor confirmado na revisão",
            "servicos": [{"descricao": "Serviços de setembro", "quantidade": 1, "valor": 6000.00}],
        }
        self.assertTrue(database.atualizar_lancamento(setembro_id, dados))
        ok, novo_saldo_setembro = database.fechar_fatura_reaberta(
            fatura_setembro["id"], "Correção concluída"
        )
        self.assertTrue(ok, novo_saldo_setembro)
        self.assertEqual(novo_saldo_setembro, 9010.00)

        with sqlite3.connect(self.db_path) as conn:
            outubro = conn.execute(
                "SELECT saldo_abertura, saldo_fechamento FROM faturas_cliente WHERE id = ?",
                (fatura_outubro["id"],),
            ).fetchone()
            novembro = conn.execute(
                "SELECT fatura_anterior, fatura_id FROM lancamentos WHERE id = ?", (novembro_id,)
            ).fetchone()
            saldo_cliente = conn.execute(
                "SELECT fatura_anterior FROM clientes WHERE id = 23"
            ).fetchone()[0]
            eventos_setembro = {
                row[0] for row in conn.execute(
                    "SELECT acao FROM faturas_auditoria WHERE fatura_id = ?",
                    (fatura_setembro["id"],),
                )
            }
            evento_propagacao = conn.execute(
                "SELECT COUNT(*) FROM faturas_auditoria WHERE fatura_id = ? AND acao = 'recalculo_saldo'",
                (fatura_outubro["id"],),
            ).fetchone()[0]
        self.assertEqual(tuple(outubro), (9010.00, 10530.00))
        self.assertEqual(novembro[0], 10530.00)
        self.assertIsNone(novembro[1])
        self.assertEqual(saldo_cliente, 10530.00)
        self.assertTrue({"reabertura", "edicao_lancamento", "refechamento"}.issubset(eventos_setembro))
        self.assertGreaterEqual(evento_propagacao, 2)

    def test_closed_invoice_blocks_edit_until_reopened_and_requires_month_range(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE clientes SET fatura_anterior = 0 WHERE id = 23")
            cursor = conn.execute(
                """
                INSERT INTO lancamentos
                    (cliente_id, cliente_nome_original, identificado, origem, data_lancamento,
                     valor_entrega, valor_pagamento, observacao)
                VALUES (23, 'Nordeste', 1, 'manual', '2026-09-15', 0, 0, 'Teste fechamento')
                """
            )
            lancamento_id = cursor.lastrowid
        ok, mensagem = database.fechar_fatura_cliente(23, "2026-09-01", "2026-09-15")
        self.assertFalse(ok)
        self.assertIn("mês civil completo", mensagem)

        ok, saldo = database.fechar_fatura_cliente(23, "2026-09-01", "2026-09-30")
        self.assertTrue(ok, saldo)
        dados = {
            "cliente_id": 23,
            "data_lancamento": "2026-09-15",
            "valor_entrega": 0,
            "valor_pagamento": 0,
            "fatura_anterior": 0,
            "pagamento_fatura_anterior": 0,
            "servicos": [],
        }
        with self.assertRaisesRegex(ValueError, "Reabra-a"):
            database.atualizar_lancamento(lancamento_id, dados)
        with self.assertRaisesRegex(ValueError, "mês já foi arquivado"):
            database.criar_lancamento(dados)

    def test_reopening_invoice_does_not_require_a_reason_and_is_still_audited(self):
        lancamento_id = database.criar_lancamento(
            {
                "cliente_id": 23,
                "data_lancamento": "2027-01-10",
                "servicos": [
                    {"descricao": "Lançamento de teste", "quantidade": 1, "valor": 25.00}
                ],
            }
        )
        self.assertTrue(lancamento_id)
        ok, resultado = database.fechar_fatura_cliente(23, "2027-01-01", "2027-01-31")
        self.assertTrue(ok, resultado)
        fatura = database.obter_fatura_periodo(23, "2027-01")

        ok, mensagem = database.reabrir_fatura_cliente(fatura["id"], "")
        self.assertTrue(ok, mensagem)
        evento = next(
            evento for evento in database.listar_auditoria_fatura(fatura["id"])
            if evento["acao"] == "reabertura"
        )
        self.assertEqual(evento["motivo"], "")
        self.assertTrue(evento["created_at"])

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
            archived_october = conn.execute(
                "SELECT COUNT(*) FROM lancamentos WHERE fatura_id IN (SELECT id FROM faturas_cliente WHERE periodo = '2026-10')"
            ).fetchone()[0]
        self.assertEqual(november_opening, 10372.50)  # 8.852,50 + 1.520,00 de serviços em outubro
        self.assertEqual(launches_after_october, 67)
        self.assertEqual(archived_october, 62)  # Cinco não identificados continuam sem fatura de cliente.
        self.assertEqual(cash_after, cash_before)

    def test_month_close_preserves_manual_post_cut_records_instead_of_blocking(self):
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
        self.assertTrue(ok, message)
        self.assertIn("preservados no histórico", message)
        self.assertTrue(os.listdir(self.backup_dir))

        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM lancamentos").fetchone()[0], launches_before)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM lancamentos WHERE observacao = 'Lançamento manual de teste'").fetchone()[0],
                1,
            )
            self.assertEqual(
                conn.execute("SELECT fatura_anterior FROM clientes WHERE id = 23").fetchone()[0],
                8852.50,
            )

    def test_legacy_clear_all_mode_archives_without_deleting_current_month_or_cash(self):
        with sqlite3.connect(self.db_path) as conn:
            balance_before = conn.execute(
                "SELECT fatura_anterior FROM clientes WHERE id = 23"
            ).fetchone()[0]
            launches_before = conn.execute("SELECT COUNT(*) FROM lancamentos").fetchone()[0]
            cash_before = conn.execute(
                "SELECT COUNT(*), ROUND(COALESCE(SUM(valor), 0), 2) FROM lancamentos_caixa"
            ).fetchone()

        ok, message = database.realizar_virada_mes("2026-09-30", "limpar_tudo")
        self.assertTrue(ok, message)
        self.assertIn("preservados no histórico", message)
        self.assertTrue(os.listdir(self.backup_dir))

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
