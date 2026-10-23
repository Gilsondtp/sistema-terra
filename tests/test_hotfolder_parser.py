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

    def test_rip_bracketed_outputs_count_as_next_page_when_unindexed_sibling_exists(self):
        siblings = (
            "ItaplastGIULIASAFIRAcmpsC.TIF",
            "ItaplastGIULIASAFIRAcmpsC [1].TIF",
            "ItaplastGIULIASAFIRAcmpsM.TIF",
            "ItaplastGIULIASAFIRAcmpsM [1].TIF",
        )
        parsed = {
            name: hotfolder_monitor.extrair_cor_e_base(name, siblings)
            for name in siblings
        }

        self.assertEqual(parsed[siblings[0]], ("ItaplastGIULIASAFIRAcm", "C", None))
        self.assertEqual(parsed[siblings[1]], ("ItaplastGIULIASAFIRAcm", "C", "2"))
        self.assertEqual(parsed[siblings[2]], ("ItaplastGIULIASAFIRAcm", "M", None))
        self.assertEqual(parsed[siblings[3]], ("ItaplastGIULIASAFIRAcm", "M", "2"))
        self.assertEqual(
            {(color, int(page or 1)) for _, color, page in parsed.values()},
            {("C", 1), ("C", 2), ("M", 1), ("M", 2)},
        )
        self.assertEqual(
            hotfolder_monitor.extrair_cor_e_base(siblings[1], [siblings[1]]),
            ("ItaplastGIULIASAFIRAcm", "C", "1"),
        )

    def test_postscript_names_restore_lost_word_boundaries_and_drop_color_selection(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory(prefix="terra-ps-index-") as source_dir:
            source_names = (
                "Itaplast_DOM_QUIXOTE_p.ps",
                "Itaplast_GIULIA_SAFIRA_cm.ps",
                "Itaplast_TOCA_DO_JEANS_m_p.ps",
            )
            for name in source_names:
                open(os.path.join(source_dir, name), "wb").close()

            index = hotfolder_monitor.construir_indice_nomes_postscript(source_dir)
            files = {
                "ItaplastDOMQUIXOTEPps.TIF": "DOM QUIXOTE",
                "ItaplastGIULIASAFIRAcmpsC.TIF": "GIULIA SAFIRA",
                "ItaplastTOCADOJEANSmpps.TIF": "TOCA DO JEANS",
            }
            client = {"id": 12, "nome": "ITAPLAST", "apelidos": "itaplast"}

            for output_name, expected_service in files.items():
                with self.subTest(output_name=output_name):
                    base, _, _ = hotfolder_monitor.extrair_cor_e_base(output_name)
                    restored, matched = hotfolder_monitor.restaurar_base_nome_postscript(base, index)
                    parsed = hotfolder_monitor.identificar_cliente_e_servico(restored, [client])
                    self.assertTrue(matched)
                    self.assertEqual(parsed["cliente_id"], 12)
                    self.assertEqual(parsed["descricao_servico"], expected_service)

    def test_ambiguous_postscript_names_are_not_guessed(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory(prefix="terra-ps-ambiguous-") as source_dir:
            for name in ("Itaplast_JOB_ONE_c.ps", "ItaplastJOBONEc.ps"):
                open(os.path.join(source_dir, name), "wb").close()
            index = hotfolder_monitor.construir_indice_nomes_postscript(source_dir)
            self.assertNotIn("itaplastjobonec", index)

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
