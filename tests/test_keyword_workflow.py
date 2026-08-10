import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import keyword_workflow as workflow  # noqa: E402


class CsvPreparationTests(unittest.TestCase):
    def test_chinese_header_bom_preamble_and_exclusions(self):
        csv_text = """关键字提示
货币,USD
关键字,平均每月搜索量
protein powder,100
PROTEIN   POWDER,90
维生素,80
,70
whey protein,60
WHEY  PROTEIN,50
collagen powder,40
pea protein,30
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            ads_csv = temp_path / "ideas.csv"
            existing = temp_path / "existing.json"
            ads_csv.write_text(csv_text, encoding="utf-8-sig")
            existing.write_text(json.dumps(["核心关键字", "collagen powder"]), encoding="utf-8")

            exported, csv_stats = workflow.parse_ads_csv(ads_csv)
            result = workflow.prepare_keyword_ideas(
                exported,
                seed="protein powder",
                existing_keywords=workflow.load_existing_keywords(existing),
                chunk_size=1,
            )

        self.assertEqual(result["new_keywords"], ["whey protein", "pea protein"])
        self.assertEqual(csv_stats["header_row"], 3)
        self.assertEqual(csv_stats["empty_excluded"], 1)
        self.assertEqual(result["stats"]["parsed_count"], 7)
        self.assertEqual(result["stats"]["seed_excluded"], 2)
        self.assertEqual(result["stats"]["non_english_excluded"], 1)
        self.assertEqual(result["stats"]["duplicate_export_excluded"], 1)
        self.assertEqual(result["stats"]["existing_excluded"], 1)
        self.assertEqual(result["chunks"], [["whey protein"], ["pea protein"]])

    def test_english_header_utf16_tab_delimited_and_nested_existing_values(self):
        csv_text = "Report\tGoogle Ads\nKeyword\tAvg. monthly searches\nAlpha tool\t100\nBeta tool\t80\nGamma tool\t60\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            ads_csv = temp_path / "ideas.csv"
            existing = temp_path / "existing.json"
            ads_csv.write_bytes(csv_text.encode("utf-16"))
            existing.write_text(
                json.dumps({"values": [["核心关键字"], ["Beta tool"]]}),
                encoding="utf-8",
            )

            exported, stats = workflow.parse_ads_csv(ads_csv)
            result = workflow.prepare_keyword_ideas(
                exported,
                seed="Alpha tool",
                existing_keywords=workflow.load_existing_keywords(existing),
                chunk_size=2,
            )

        self.assertEqual(stats["keyword_column"], 1)
        self.assertEqual(result["new_keywords"], ["Gamma tool"])
        self.assertEqual(result["stats"]["new_count"], 1)

    def test_missing_keyword_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.csv"
            path.write_text("Name,Volume\nalpha,10\n", encoding="utf-8")
            with self.assertRaises(workflow.KeywordWorkflowError):
                workflow.parse_ads_csv(path)


class SheetPlanningTests(unittest.TestCase):
    def test_domain_normalization(self):
        self.assertEqual(
            workflow.normalize_domain(" HTTPS://WWW.NutricDMO.com/products/?x=1 "),
            "www.nutricdmo.com",
        )
        self.assertEqual(workflow.normalize_domain("www.nutricdmo.com"), "www.nutricdmo.com")

    def test_domain_rejects_credentials_ports_and_bare_names(self):
        for value in (
            "https://user:pass@example.com",
            "https://example.com:8443",
            "localhost",
        ):
            with self.subTest(value=value):
                with self.assertRaises(workflow.KeywordWorkflowError):
                    workflow.normalize_domain(value)

    def test_header_contract(self):
        workflow.validate_headers(list(workflow.REQUIRED_HEADERS))
        bad_headers = list(workflow.REQUIRED_HEADERS)
        bad_headers[1] = "国家"
        with self.assertRaises(workflow.KeywordWorkflowError):
            workflow.validate_headers(bad_headers)

    def test_latest_complete_template_and_last_keyword_rows(self):
        rows = [
            ["first", "美国", "客户", "https://example.com/a", "secret"],
            ["second", "美国", "客户", "", "secret"],
            ["third", "美国", "客户", "https://example.com/c", "secret"],
            ["", "", "", "", ""],
        ]
        self.assertEqual(workflow.find_latest_template_row(rows, first_sheet_row=2), 4)
        self.assertEqual(workflow.find_last_keyword_row(rows, first_sheet_row=2), 4)

    def test_chunk_ranges_and_row_expansion(self):
        self.assertEqual(
            workflow.destination_chunks(start_row=71, item_count=1201, chunk_size=500),
            [(71, 570), (571, 1070), (1071, 1271)],
        )
        self.assertEqual(workflow.rows_to_append(1000, 1271), 271)
        self.assertEqual(workflow.rows_to_append(1500, 1271), 0)

    def test_english_filter_allows_latin_and_rejects_other_scripts(self):
        self.assertTrue(workflow.is_english_keyword("private-label whey protein 2.0"))
        self.assertTrue(workflow.is_english_keyword("café protein"))
        self.assertFalse(workflow.is_english_keyword("乳清 protein"))
        self.assertFalse(workflow.is_english_keyword("протеин"))


class SkillInstructionContractTests(unittest.TestCase):
    def test_domain_is_sheet_only_and_ads_website_filter_stays_empty(self):
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        readme_text = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn(
            "Use the domain only to normalize and select the destination Sheet tab.",
            skill_text,
        )
        self.assertIn(
            "Clear the optional website-filter field if it contains any value and leave it empty.",
            skill_text,
        )
        self.assertIn("no active website/site filter", skill_text)
        self.assertNotIn("Build the website seed", skill_text)
        self.assertNotIn("fill the website-filter field with the website seed", skill_text)
        self.assertIn("The supplied domain is a destination-tab selector only.", readme_text)


if __name__ == "__main__":
    unittest.main()
