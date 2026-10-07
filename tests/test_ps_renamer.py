import os
import tempfile
import unittest

import hotfolder_monitor


class PSFileRenamerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="terra-ps-renamer-")
        self.root = self.temp_dir.name
        self.state = {}

    def tearDown(self):
        self.temp_dir.cleanup()

    def scan(self):
        return hotfolder_monitor.normalizar_nomes_arquivos_ps(
            self.root,
            estado_estabilidade=self.state,
        )

    def test_recursively_renames_only_stable_ps_files_and_preserves_content(self):
        dated_folder = os.path.join(self.root, "2026-10-07")
        os.makedirs(dated_folder)
        source = os.path.join(dated_folder, "ENVELOPE PEDACINHODOCEU.ps")
        tiff = os.path.join(dated_folder, "PLATE C M Y K.tif")
        temporary = os.path.join(dated_folder, "~incompleto arquivo.ps")
        plain_ps = os.path.join(dated_folder, "sem_espacos.PS")

        with open(source, "wb") as file:
            file.write(b"postscript content\x00")
        with open(tiff, "wb") as file:
            file.write(b"tiff content")
        with open(temporary, "wb") as file:
            file.write(b"temporary")
        with open(plain_ps, "wb") as file:
            file.write(b"already normalized")

        self.assertEqual(self.scan(), [])  # primeira observação
        self.assertEqual(self.scan(), [])  # primeira leitura estável
        renamed = self.scan()  # segunda leitura estável

        target = os.path.join(dated_folder, "ENVELOPE_PEDACINHODOCEU.ps")
        self.assertEqual(renamed, [(source, target)])
        self.assertFalse(os.path.exists(source))
        with open(target, "rb") as file:
            self.assertEqual(file.read(), b"postscript content\x00")
        self.assertTrue(os.path.exists(tiff))
        self.assertTrue(os.path.exists(temporary))
        self.assertTrue(os.path.exists(plain_ps))

    def test_existing_destination_is_never_overwritten(self):
        source = os.path.join(self.root, "SACOLA HAVAIANAS.ps")
        target = os.path.join(self.root, "SACOLA_HAVAIANAS.ps")
        with open(source, "wb") as file:
            file.write(b"original")
        with open(target, "wb") as file:
            file.write(b"keep this file")

        self.scan()
        self.scan()
        self.assertEqual(self.scan(), [])
        self.assertEqual(self.scan(), [])

        with open(source, "rb") as file:
            self.assertEqual(file.read(), b"original")
        with open(target, "rb") as file:
            self.assertEqual(file.read(), b"keep this file")

    def test_file_change_resets_stability_counter(self):
        source = os.path.join(self.root, "JOB WITH SPACES.ps")
        with open(source, "wb") as file:
            file.write(b"first")

        self.scan()
        with open(source, "wb") as file:
            file.write(b"changed size")
        self.assertEqual(self.scan(), [])  # alteração reinicia a contagem
        self.assertEqual(self.scan(), [])
        renamed = self.scan()

        target = os.path.join(self.root, "JOB_WITH_SPACES.ps")
        self.assertEqual(renamed, [(source, target)])
        with open(target, "rb") as file:
            self.assertEqual(file.read(), b"changed size")


if __name__ == "__main__":
    unittest.main()
