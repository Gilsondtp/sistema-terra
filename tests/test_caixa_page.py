import io
import os
import shutil
import tempfile
import unittest
import zipfile
from datetime import date
from unittest.mock import patch

import database
import hotfolder_monitor


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
        self.assertIn("sistema-terra/templates/faturas.html", nomes)
        self.assertIn("sistema-terra/templates/fatura_detalhe.html", nomes)
        self.assertIn("sistema-terra/iniciar_sistema.bat", nomes)
        self.assertIn("sistema-terra/iniciar_sem_janela.vbs", nomes)
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
        self.assertIn("pyw -3", vbscript)
        self.assertIn("pythonw", vbscript)
        self.assertIn("python ausente", vbscript)

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

    def test_daily_page_auto_refreshes_and_shows_processing_feedback(self):
        client = self.app_module.app.test_client()
        with patch.object(hotfolder_monitor, "executar_ciclo_monitoramento", return_value=[]):
            response = client.get("/lancamento-diario")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Lista atualizada automaticamente", html)
        self.assertIn("/hotfolder/status", html)
        self.assertIn("setInterval(consultarStatus, 5000)", html)
        self.assertIn("operacaoFeedback", html)
        self.assertIn("progress-bar-animated", html)
        self.assertNotIn("Fechamento do Mês / Virada de Mês", html)
        self.assertNotIn("Transfere saldos para a Fatura Anterior", html)
        self.assertIn("Abrir Fechamento Mensal", html)

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
