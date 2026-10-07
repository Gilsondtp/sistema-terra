import os
import shutil
import tempfile
import unittest
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

    def test_ps_source_is_configured_separately_from_tiff_hotfolder(self):
        response = self.app_module.app.test_client().get("/configuracoes")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('name="ps_entrada_path"', html)
        self.assertIn('name="ps_renomeador_ativo"', html)
        self.assertIn('value="\\\\Ripctp\\rip (d:) (z)"', html)
        self.assertIn('name="hotfolder_network_path"', html)
        self.assertIn('value="\\\\RIPCTP\\Manuela\\OutPut"', html)


if __name__ == "__main__":
    unittest.main()
