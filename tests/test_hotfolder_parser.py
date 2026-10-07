import unittest

import hotfolder_monitor


class HotFolderParserTests(unittest.TestCase):
    def test_rip_suffix_color_and_page_are_removed_but_service_is_preserved(self):
        filename = "GilbertoSantinho7x10JooeKtiaA4x1psY1.tif"
        base, color, page = hotfolder_monitor.extrair_cor_e_base(filename)
        self.assertEqual(color, "Y")
        self.assertEqual(page, "1")

        client = {"id": 1, "nome": "Gilberto", "apelidos": ""}
        parsed = hotfolder_monitor.identificar_cliente_e_servico(base, [client])
        self.assertEqual(parsed["cliente_nome"], "Gilberto")
        self.assertEqual(parsed["descricao_servico"], "Santinho 7x10 Jooe Ktia A 4x1")

    def test_lowercase_cmyk_plates_group_using_sibling_files(self):
        siblings = [
            "gilsoncartazc.tif",
            "gilsoncartazm.tif",
            "gilsoncartazy.tif",
            "gilsoncartazk.tif",
        ]
        results = [hotfolder_monitor.extrair_cor_e_base(name, siblings) for name in siblings]
        self.assertEqual({result[0] for result in results}, {"gilsoncartaz"})
        self.assertEqual({result[1] for result in results}, {"C", "M", "Y", "K"})

    def test_terminal_letters_in_service_words_are_not_removed_without_evidence(self):
        for word in ("Dynamic", "Party", "Maverick"):
            with self.subTest(word=word):
                filename = f"Gilson{word}.tif"
                base, color, _ = hotfolder_monitor.extrair_cor_e_base(filename)
                self.assertEqual(base, f"Gilson{word}")
                self.assertEqual(color, "UNICA")

    def test_spaced_or_source_extension_color_codes_remain_supported(self):
        cases = {
            "gilson cartaz c.tif": ("gilson cartaz", "C"),
            "gilsoncartazpsm1.tif": ("gilsoncartaz", "M"),
            "gilsoncartazpsY1.tif": ("gilsoncartaz", "Y"),
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                base, color, _ = hotfolder_monitor.extrair_cor_e_base(filename)
                self.assertEqual((base, color), expected)

    def test_confirmed_rip_collapsed_name_keeps_underscores_as_separators(self):
        client = {"id": 20, "nome": "Terra Fotolito", "apelidos": "terrafotolito"}
        self.assertEqual(
            hotfolder_monitor.formatar_descricao_servico("ARQUIVOSENVIADO Stestenome 5"),
            "ARQUIVOS_ENVIADOS_teste_nome5",
        )
        filenames = (
            "terra_ARQUIVOS_ENVIADOS_teste_nome5.tif",
            "terra_ARQUIVOSENVIADOStestenome5.tif",
        )

        for filename in filenames:
            with self.subTest(filename=filename):
                base, _, _ = hotfolder_monitor.extrair_cor_e_base(filename)
                parsed = hotfolder_monitor.identificar_cliente_e_servico(base, [client])
                self.assertEqual(parsed["cliente_id"], 20)
                self.assertEqual(
                    parsed["descricao_servico"],
                    "ARQUIVOS_ENVIADOS_teste_nome5",
                )


if __name__ == "__main__":
    unittest.main()
