import io
import os
import shutil
import tempfile
import unittest
import zipfile
from datetime import date
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

import database
import hotfolder_monitor
import wait_for_server


class CaixaPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="terra-caixa-page-test-")
        cls.db_path = os.path.join(cls.temp_dir.name, "test.db")
        cls.backup_dir = os.path.join(cls.temp_dir.name, "backups")
        os.makedirs(cls.backup_dir)
        shutil.copy2(os.path.join(database.BASE_DIR, "sistema_terra.db"), cls.db_path)
        cls.original_db_path = database.DB_PATH
        cls.original_backup_dir = database.BACKUP_DIR
        database.DB_PATH = cls.db_path
        database.BACKUP_DIR = cls.backup_dir
        with patch.object(hotfolder_monitor.HotFolderWatcherThread, "start", lambda self: None):
            import app as app_module
        cls.app_module = app_module
        cls.app_module.app.config["TESTING"] = True

    @classmethod
    def tearDownClass(cls):
        database.DB_PATH = cls.original_db_path
        database.BACKUP_DIR = cls.original_backup_dir
        cls.temp_dir.cleanup()

    def test_default_period_is_current_month_and_cash_rows_are_concise(self):
        class OctoberDate(date):
            @classmethod
            def today(cls):
                return cls(2026, 10, 6)

        today = OctoberDate.today()
        start = today.replace(day=1).isoformat()
        end = today.isoformat()
        client = self.app_module.app.test_client()

        with patch.object(self.app_module, "date", OctoberDate):
            response = client.get("/caixa")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        self.assertIn(f'name="data_inicio" value="{start}"', html)
        self.assertIn(f'name="data_fim" value="{end}"', html)
        self.assertIn("Pagtº Cliente: Gold", html)
        self.assertNotIn("Pagtº Cliente: Norte Grafica", html)
        self.assertNotIn("(Lanç. #", html)
        self.assertNotIn("Auto Lançamento", html)
        self.assertIn("Automático", html)
        self.assertIn("Manual", html)

    def test_explicit_empty_dates_can_still_show_full_history(self):
        response = self.app_module.app.test_client().get(
            "/caixa?data_inicio=&data_fim="
        )
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('name="data_inicio" value=""', html)
        self.assertIn('name="data_fim" value=""', html)
        self.assertIn("Pagtº Cliente: Norte Grafica", html)

    def test_project_zip_is_accessible_and_excludes_legacy_code_and_user_data(self):
        client = self.app_module.app.test_client()
        page = client.get("/configuracoes")
        self.assertEqual(page.status_code, 200)
        html = page.get_data(as_text=True)
        download_link = html.index('href="/download-projeto-zip"')
        navbar_collapse = html.index('id="mainNavbar"')
        self.assertLess(download_link, navbar_collapse)
        self.assertIn('Baixar Projeto Completo em Python (.zip)', html)

        response = client.get("/download-projeto-zip")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response.headers.get("Content-Disposition", ""))
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            nomes = archive.namelist()
            batch_zip = archive.read("sistema-terra/iniciar_sistema.bat")
            stop_batch_zip = archive.read("sistema-terra/parar_sistema.bat")
            vbs_zip = archive.read("sistema-terra/iniciar_sem_janela.vbs")
        self.assertIn("sistema-terra/.gitattributes", nomes)
        self.assertEqual(batch_zip.count(b"\n"), batch_zip.count(b"\r\n"))
        self.assertEqual(stop_batch_zip.count(b"\n"), stop_batch_zip.count(b"\r\n"))
        self.assertEqual(vbs_zip.count(b"\n"), vbs_zip.count(b"\r\n"))
        self.assertIn("sistema-terra/templates/faturas.html", nomes)
        self.assertIn("sistema-terra/templates/fatura_detalhe.html", nomes)
        self.assertIn("sistema-terra/iniciar_sistema.bat", nomes)
        self.assertIn("sistema-terra/iniciar_sem_janela.vbs", nomes)
        self.assertIn("sistema-terra/wait_for_server.py", nomes)
        self.assertFalse([nome for nome in nomes if nome.lower().endswith((".php", ".db", ".sqlite", ".sqlite3", ".sql"))])
        self.assertFalse(any(nome.startswith("sistema-terra/tests/") for nome in nomes))

    def test_windows_launchers_resolve_pythonw_and_explain_missing_runtime(self):
        with open(os.path.join(database.BASE_DIR, "iniciar_sistema.bat"), encoding="utf-8") as launcher:
            batch = launcher.read().lower()
        with open(os.path.join(database.BASE_DIR, "iniciar_sem_janela.vbs"), encoding="utf-8") as launcher:
            vbscript = launcher.read().lower()

        self.assertIn("py -3 -c", batch)
        self.assertIn("sys.executable", batch)
        self.assertIn("pythonw.exe", batch)
        self.assertIn("python 3 nao foi encontrado", batch)
        self.assertIn("wait_for_server.py", batch)
        self.assertNotIn("timeout /t 2", batch)
        self.assertIn("sistema_terra.log", batch)
        self.assertIn("pyw -3", vbscript)
        self.assertIn("pythonw", vbscript)
        self.assertIn("wait_for_server.py", vbscript)
        self.assertIn("healthz", vbscript)
        self.assertIn("import flask, watchdog, openpyxl", vbscript)
        self.assertIn("iniciar_sistema.bat", vbscript)
        self.assertIn("python ausente", vbscript)

    def test_health_endpoint_identifies_the_running_application(self):
        response = self.app_module.app.test_client().get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"service": "sistema-terra", "status": "ok"})

    def test_startup_waiter_only_accepts_the_sistema_terra_health_response(self):
        with patch.object(wait_for_server.http.client, "HTTPConnection") as connection_class, \
             patch.dict(os.environ, {"PORT": "5000"}), \
             patch("sys.stdout", io.StringIO()):
            response = connection_class.return_value.getresponse.return_value
            response.status = 200
            response.read.return_value = b'{"service":"sistema-terra","status":"ok"}'
            result = wait_for_server.wait_for_server()

        self.assertEqual(result, 0)
        connection_class.assert_called_once_with("127.0.0.1", 5000, timeout=2)
        connection_class.return_value.request.assert_called_once_with(
            "GET", "/healthz", headers={"Connection": "close"}
        )
        connection_class.return_value.close.assert_called_once_with()

    def test_invoice_reopening_reason_is_optional_in_the_ui(self):
        with open(os.path.join(database.BASE_DIR, "templates", "fatura_detalhe.html"), encoding="utf-8") as template:
            html = template.read()
        self.assertIn("Motivo da reabertura (opcional)", html)
        self.assertNotIn('name="motivo" required', html)

    def test_ps_source_is_configured_separately_from_tiff_hotfolder(self):
        response = self.app_module.app.test_client().get("/configuracoes")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('name="ps_entrada_path"', html)
        self.assertIn('name="ps_renomeador_ativo"', html)
        self.assertIn('value="\\\\Ripctp\\rip (d:) (z)"', html)
        self.assertIn('name="hotfolder_network_path"', html)
        self.assertIn('value="\\\\RIPCTP\\Manuela\\OutPut"', html)

    def test_report_supports_date_ranges_without_changing_monthly_invoice_logic(self):
        client = self.app_module.app.test_client()
        cliente = {"id": 1, "nome": "Cliente Teste", "fatura_anterior": 0.0}
        query = {
            "cliente_id": "1",
            "tipo_periodo": "intervalo",
            "data_inicio": "2026-10-05",
            "data_fim": "2026-10-18",
        }

        lancamento = {
            "data_lancamento": "2026-10-06",
            "observacao": "",
            "servicos": [{"valor": 100.0, "quantidade": 1, "produto_nome": "Chapa teste"}],
            "valor_entrega": 10.0,
            "valor_pagamento": 20.0,
            "pagamento_fatura_anterior": 5.0,
        }
        with patch.object(database, "listar_clientes", return_value=[cliente]), \
             patch.object(database, "buscar_cliente", return_value=cliente), \
             patch.object(database, "listar_lancamentos", return_value=[lancamento]) as listar, \
             patch.object(database, "obter_fatura_periodo") as obter_fatura, \
             patch.object(database, "limites_periodo_fatura") as limites_mensais:
            response = client.get("/relatorios", query_string=query)

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('value="2026-10-05"', html)
        self.assertIn('value="2026-10-18"', html)
        self.assertIn("RELATÓRIO DE LANÇAMENTOS", html)
        self.assertIn("Esta consulta não altera nem fecha faturas mensais", html)
        self.assertNotIn("Arquivar fatura do mês", html)
        self.assertNotIn("abrirModalNovoLancamento(", html)
        self.assertNotIn("abrirModalEditarLancamento", html)
        self.assertNotIn("Ações</th>", html)
        self.assertIn("R$ 110,00", html)  # Serviços + entrega
        self.assertIn("R$ 25,00", html)   # Pagamento do período + fatura anterior
        self.assertIn("R$ 5,00", html)    # Pagamento antigo fica identificado à parte
        self.assertIn("R$ 90,00", html)   # Pagamento antigo não reduz saldo dos serviços
        listar.assert_called_once_with(
            {"cliente_id": 1, "data_inicio": "2026-10-05", "data_fim": "2026-10-18"}
        )
        obter_fatura.assert_not_called()
        limites_mensais.assert_not_called()

    def test_monthly_report_still_uses_only_open_rows_and_month_boundaries(self):
        client = self.app_module.app.test_client()
        cliente = {"id": 1, "nome": "Cliente Teste", "fatura_anterior": 0.0}
        with patch.object(database, "listar_clientes", return_value=[cliente]), \
             patch.object(database, "buscar_cliente", return_value=cliente), \
             patch.object(database, "obter_fatura_periodo", return_value=None) as obter_fatura, \
             patch.object(database, "listar_lancamentos", return_value=[]) as listar, \
             patch.object(database, "obter_saldo_abertura_fatura", return_value=0.0), \
             patch.object(database, "limites_periodo_fatura", return_value=("2026-09-01", "2026-09-30")) as limites:
            response = client.get(
                "/relatorios",
                query_string={"cliente_id": "1", "tipo_periodo": "mensal", "periodo": "2026-09"},
            )

        self.assertEqual(response.status_code, 200)
        obter_fatura.assert_called_once_with(1, "2026-09")
        limites.assert_called_once_with("2026-09")
        listar.assert_called_once_with(
            {
                "cliente_id": 1,
                "data_inicio": "2026-09-01",
                "data_fim": "2026-09-30",
                "somente_abertos": True,
            }
        )

    def _lancamento_teste_relatorio(self, fatura_id=None, fatura_status=None):
        return {
            "id": 501,
            "cliente_id": 1,
            "cliente_nome": "Cliente Teste",
            "cliente_nome_original": "",
            "identificado": 1,
            "origem": "manual",
            "data_lancamento": "2026-10-06",
            "valor_entrega": 10.0,
            "valor_pagamento": 20.0,
            "fatura_anterior": 0.0,
            "pagamento_fatura_anterior": 0.0,
            "saldo_fatura_anterior": 0.0,
            "fatura_id": fatura_id,
            "fatura_periodo": "2026-10" if fatura_id else None,
            "fatura_status": fatura_status,
            "observacao": "Observação de teste",
            "servicos": [
                {
                    "id": 901,
                    "descricao": "Serviço de teste",
                    "quantidade": 2,
                    "produto_id": 3,
                    "produto_nome": "Chapa teste",
                    "valor": 100.0,
                }
            ],
        }

    def test_open_monthly_report_embeds_new_and_edit_launch_actions(self):
        client = self.app_module.app.test_client()
        cliente = {"id": 1, "nome": "Cliente Teste", "fatura_anterior": 0.0}
        lancamento = self._lancamento_teste_relatorio()
        with patch.object(database, "listar_clientes", return_value=[cliente]), \
             patch.object(database, "buscar_cliente", return_value=cliente), \
             patch.object(database, "obter_fatura_periodo", return_value=None), \
             patch.object(database, "listar_lancamentos", return_value=[lancamento]), \
             patch.object(database, "obter_saldo_abertura_fatura", return_value=0.0), \
             patch.object(database, "limites_periodo_fatura", return_value=("2026-10-01", "2026-10-31")), \
             patch.object(database, "listar_produtos", return_value=[]):
            response = client.get(
                "/relatorios",
                query_string={"cliente_id": "1", "tipo_periodo": "mensal", "periodo": "2026-10"},
            )

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Novo lançamento", html)
        self.assertIn("abrirModalNovoLancamento(", html)
        self.assertIn("Ações</th>", html)
        self.assertIn("abrirModalEditarLancamento(", html)
        self.assertIn("confirmarExclusaoLancamentoRelatorio(501, 901)", html)
        self.assertIn('id="modalLancamento"', html)
        self.assertIn('id="modalExcluirLancamentoRelatorio"', html)
        self.assertIn('class="text-center no-print"', html)
        self.assertNotIn("/lancamentos", html)

    def test_reopened_report_allows_edits_and_keeps_correction_reason_optional(self):
        client = self.app_module.app.test_client()
        cliente = {"id": 1, "nome": "Cliente Teste", "fatura_anterior": 0.0}
        fatura = {"id": 82, "status": "reaberta", "saldo_abertura": 0.0}
        lancamento = self._lancamento_teste_relatorio(82, "reaberta")
        with patch.object(database, "listar_clientes", return_value=[cliente]), \
             patch.object(database, "buscar_cliente", return_value=cliente), \
             patch.object(database, "obter_fatura_periodo", return_value=fatura), \
             patch.object(database, "listar_lancamentos", return_value=[lancamento]), \
             patch.object(database, "listar_produtos", return_value=[]):
            response = client.get(
                "/relatorios",
                query_string={"cliente_id": "1", "tipo_periodo": "mensal", "periodo": "2026-10"},
            )

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("abrirModalEditarLancamento(", html)
        self.assertIn('id="modal_motivo_correcao"', html)
        self.assertIn("A alteração será registrada na auditoria mesmo sem motivo", html)
        self.assertNotIn('name="motivo_correcao" required', html)

    def test_closed_report_hides_mutation_controls(self):
        client = self.app_module.app.test_client()
        cliente = {"id": 1, "nome": "Cliente Teste", "fatura_anterior": 0.0}
        fatura = {"id": 83, "status": "fechada", "saldo_abertura": 0.0}
        lancamento = self._lancamento_teste_relatorio(83, "fechada")
        with patch.object(database, "listar_clientes", return_value=[cliente]), \
             patch.object(database, "buscar_cliente", return_value=cliente), \
             patch.object(database, "obter_fatura_periodo", return_value=fatura), \
             patch.object(database, "listar_lancamentos", return_value=[lancamento]), \
             patch.object(database, "listar_produtos", return_value=[]):
            response = client.get(
                "/relatorios",
                query_string={"cliente_id": "1", "tipo_periodo": "mensal", "periodo": "2026-10"},
            )

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertNotIn("abrirModalNovoLancamento(", html)
        self.assertNotIn("abrirModalEditarLancamento(", html)
        self.assertNotIn("confirmarExclusaoLancamentoRelatorio(", html)
        self.assertNotIn("Ações</th>", html)
        self.assertNotIn('id="modalLancamento"', html)

    def test_legacy_launch_screen_redirects_to_the_report(self):
        response = self.app_module.app.test_client().get(
            "/lancamentos?cliente_id=1&data_inicio=2026-09-01&data_fim=2026-09-30"
        )
        self.assertEqual(response.status_code, 302)
        parsed = urlparse(response.headers["Location"])
        self.assertEqual(parsed.path, "/relatorios")
        self.assertEqual(
            parse_qs(parsed.query),
            {
                "cliente_id": ["1"],
                "tipo_periodo": ["intervalo"],
                "data_inicio": ["2026-09-01"],
                "data_fim": ["2026-09-30"],
            },
        )

    def test_daily_page_auto_refreshes_and_shows_processing_feedback(self):
        client = self.app_module.app.test_client()
        with patch.object(hotfolder_monitor, "executar_ciclo_monitoramento") as scanner:
            response = client.get("/lancamento-diario")
        self.assertEqual(response.status_code, 200)
        scanner.assert_not_called()
        html = response.get_data(as_text=True)
        self.assertIn("Lista atualizada automaticamente", html)
        self.assertIn("/hotfolder/status", html)
        self.assertIn("setInterval(consultarStatus, 5000)", html)
        self.assertIn("operacaoFeedback", html)
        self.assertIn("progress-bar-animated", html)
        self.assertNotIn("Fechamento do Mês / Virada de Mês", html)
        self.assertNotIn("Transfere saldos para a Fatura Anterior", html)
        self.assertIn("Abrir Fechamento Mensal", html)
        self.assertNotIn("abrirModalEditarLancamento", html)
        self.assertNotIn("confirmarExclusaoLancamento", html)
        self.assertNotIn("modalLancamento", html)
        self.assertNotIn("Criar Lançamento", html)

    def test_manual_hotfolder_scan_still_runs_on_demand(self):
        client = self.app_module.app.test_client()
        with patch.object(hotfolder_monitor, "executar_ciclo_monitoramento", return_value=[]) as scanner:
            response = client.post(
                "/hotfolder/escanear",
                data={"redirect_to": "/lancamento-diario?data=2026-10-23"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/lancamento-diario?data=2026-10-23")
        scanner.assert_called_once_with()

    def test_hotfolder_status_endpoint_reports_watcher_activity(self):
        client = self.app_module.app.test_client()
        with patch.object(self.app_module.watcher_thread, "total_detected", 7), \
             patch.object(self.app_module.watcher_thread, "last_scan", "14:32:10"):
            response = client.get("/hotfolder/status")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total_detected"], 7)
        self.assertEqual(payload["last_scan"], "14:32:10")
        self.assertIsInstance(payload["active"], bool)


if __name__ == "__main__":
    unittest.main()
