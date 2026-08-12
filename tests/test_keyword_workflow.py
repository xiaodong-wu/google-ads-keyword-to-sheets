import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import keyword_workflow as workflow  # noqa: E402


class CsvPreparationTests(unittest.TestCase):
    def test_detailed_export_preserves_metrics_and_google_ads_metadata(self):
        csv_text = """Currency,USD
Keyword,Avg. monthly searches,Three month change,YoY change,Competition,Competition (indexed value),Top of page bid (low range),Top of page bid (high range)
watch,100000,10%,20%,High,90,1.10,4.50
watch wholesale,1200,5%,12%,Medium,55,2.20,6.80
watch price supplier,900,1%,2%,Low,20,0.80,2.10
custom watch,700,-2%,4%,High,78,1.90,5.40
rolex custom watch,500,3%,8%,High,88,2.50,7.20
luxury watch,450,2%,6%,Medium,45,1.50,4.20
WATCH WHOLESALE,1100,4%,11%,Medium,53,2.10,6.60
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            ads_csv = temp_path / "ideas.csv"
            detailed_csv = temp_path / "watch-filtered.csv"
            prepared_json = temp_path / "prepared.json"
            irrelevant_file = temp_path / "irrelevant.txt"
            ads_csv.write_text(csv_text, encoding="utf-8-sig")
            irrelevant_file.write_text("luxury watch\n", encoding="utf-8")

            exit_code = workflow.main(
                [
                    "prepare",
                    "--ads-csv",
                    str(ads_csv),
                    "--seed",
                    "watch",
                    "--irrelevant-keyword-file",
                    str(irrelevant_file),
                    "--detail-output",
                    str(detailed_csv),
                    "--output",
                    str(prepared_json),
                ]
            )
            output_rows = workflow.read_csv_rows(detailed_csv)
            prepared = json.loads(prepared_json.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(output_rows[0], ["Currency", "USD"])
        self.assertEqual(
            output_rows[1],
            [
                "Keyword",
                "Avg. monthly searches",
                "Three month change",
                "YoY change",
                "Competition",
                "Competition (indexed value)",
                "Top of page bid (low range)",
                "Top of page bid (high range)",
            ],
        )
        self.assertEqual(
            output_rows[2:],
            [
                ["watch wholesale", "1200", "5%", "12%", "Medium", "55", "2.20", "6.80"],
                ["custom watch", "700", "-2%", "4%", "High", "78", "1.90", "5.40"],
            ],
        )
        self.assertEqual(prepared["new_keywords"], ["watch wholesale", "custom watch"])
        self.assertEqual(prepared["stats"]["detail_row_count"], 2)
        self.assertEqual(prepared["stats"]["detail_column_count"], 8)
        self.assertEqual(prepared["stats"]["seed_excluded"], 1)
        self.assertEqual(prepared["stats"]["blocked_phrase_excluded"], 1)
        self.assertEqual(prepared["stats"]["confirmed_brand_excluded"], 1)
        self.assertEqual(prepared["stats"]["irrelevant_keyword_excluded"], 1)
        self.assertEqual(prepared["stats"]["duplicate_export_excluded"], 1)

    def test_detailed_export_cannot_overwrite_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ads_csv = Path(temp_dir) / "ideas.csv"
            irrelevant_file = Path(temp_dir) / "irrelevant.txt"
            ads_csv.write_text(
                "Keyword,Avg. monthly searches\nwatch wholesale,100\n",
                encoding="utf-8",
            )
            irrelevant_file.write_text("", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                exit_code = workflow.main(
                    [
                        "prepare",
                        "--ads-csv",
                        str(ads_csv),
                        "--seed",
                        "watch",
                        "--irrelevant-keyword-file",
                        str(irrelevant_file),
                        "--detail-output",
                        str(ads_csv),
                    ]
                )

        self.assertEqual(exit_code, 2)

    def test_detailed_export_does_not_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            ads_csv = temp_path / "ideas.csv"
            detailed_csv = temp_path / "existing.csv"
            irrelevant_file = temp_path / "irrelevant.txt"
            ads_csv.write_text(
                "Keyword,Avg. monthly searches\nwatch wholesale,100\n",
                encoding="utf-8",
            )
            detailed_csv.write_text("user data\n", encoding="utf-8")
            irrelevant_file.write_text("", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                exit_code = workflow.main(
                    [
                        "prepare",
                        "--ads-csv",
                        str(ads_csv),
                        "--seed",
                        "watch",
                        "--irrelevant-keyword-file",
                        str(irrelevant_file),
                        "--detail-output",
                        str(detailed_csv),
                    ]
                )
            retained_text = detailed_csv.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 2)
        self.assertEqual(retained_text, "user data\n")

    def test_chinese_header_bom_preamble_and_exclusions(self):
        csv_text = """关键字提示
货币,USD
关键字,平均每月搜索量
protein powder,100
PROTEIN   POWDER,90
维生素,80
,70
whey protein supplier,60
WHEY  PROTEIN SUPPLIER,50
collagen powder supplier,40
pea protein wholesale,30
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            ads_csv = temp_path / "ideas.csv"
            existing = temp_path / "existing.json"
            ads_csv.write_text(csv_text, encoding="utf-8-sig")
            existing.write_text(
                json.dumps(["核心关键字", "collagen powder supplier"]),
                encoding="utf-8",
            )

            exported, csv_stats = workflow.parse_ads_csv(ads_csv)
            result = workflow.prepare_keyword_ideas(
                exported,
                seed="protein powder",
                existing_keywords=workflow.load_existing_keywords(existing),
                chunk_size=1,
            )

        self.assertEqual(
            result["new_keywords"],
            ["whey protein supplier", "pea protein wholesale"],
        )
        self.assertEqual(csv_stats["header_row"], 3)
        self.assertEqual(csv_stats["empty_excluded"], 1)
        self.assertEqual(result["stats"]["parsed_count"], 7)
        self.assertEqual(result["stats"]["seed_excluded"], 2)
        self.assertEqual(result["stats"]["non_english_excluded"], 1)
        self.assertEqual(result["stats"]["duplicate_export_excluded"], 1)
        self.assertEqual(result["stats"]["existing_excluded"], 1)
        self.assertEqual(
            result["chunks"],
            [["whey protein supplier"], ["pea protein wholesale"]],
        )

    def test_english_header_utf16_tab_delimited_and_nested_existing_values(self):
        csv_text = (
            "Report\tGoogle Ads\n"
            "Keyword\tAvg. monthly searches\n"
            "Alpha tool supplier\t100\n"
            "Beta tool supplier\t80\n"
            "Gamma tool manufacturer\t60\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            ads_csv = temp_path / "ideas.csv"
            existing = temp_path / "existing.json"
            ads_csv.write_bytes(csv_text.encode("utf-16"))
            existing.write_text(
                json.dumps({"values": [["核心关键字"], ["Beta tool supplier"]]}),
                encoding="utf-8",
            )

            exported, stats = workflow.parse_ads_csv(ads_csv)
            result = workflow.prepare_keyword_ideas(
                exported,
                seed="Alpha tool supplier",
                existing_keywords=workflow.load_existing_keywords(existing),
                chunk_size=2,
            )

        self.assertEqual(stats["keyword_column"], 1)
        self.assertEqual(result["new_keywords"], ["Gamma tool manufacturer"])
        self.assertEqual(result["stats"]["new_count"], 1)

    def test_missing_keyword_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.csv"
            path.write_text("Name,Volume\nalpha,10\n", encoding="utf-8")
            with self.assertRaises(workflow.KeywordWorkflowError):
                workflow.parse_ads_csv(path)

    def test_filters_new_low_value_phrases_brands_and_imprecise_keywords(self):
        exported = [
            "watch wholesale",
            "WATCH WHOLESALE",
            "watch price",
            "watch cost",
            "old watch",
            "watch near me",
            "watch for me",
            "gold watch",
            "metal watch",
            "nearly indestructible watch",
            "watch repair supplier",
            "custom watch",
            "luxury watch",
            "rolex watch supplier",
            "amazon watch",
            "free watch",
            "watch sale",
        ]

        result = workflow.prepare_keyword_ideas(
            exported,
            seed="watch",
            existing_keywords=[],
            irrelevant_keywords=["luxury watch"],
        )

        self.assertEqual(
            result["new_keywords"],
            [
                "watch wholesale",
                "gold watch",
                "metal watch",
                "nearly indestructible watch",
                "watch repair supplier",
                "custom watch",
                "free watch",
                "watch sale",
            ],
        )
        self.assertEqual(result["stats"]["duplicate_export_excluded"], 1)
        self.assertEqual(result["stats"]["blocked_phrase_excluded"], 5)
        self.assertEqual(result["stats"]["confirmed_brand_excluded"], 2)
        self.assertEqual(result["stats"]["irrelevant_keyword_excluded"], 1)

    def test_imprecise_filter_uses_exact_full_keyword_matching(self):
        result = workflow.prepare_keyword_ideas(
            ["watch-parts", "custom watch parts", "luxury watch"],
            seed="watch",
            existing_keywords=[],
            irrelevant_keywords=["watch parts"],
        )

        self.assertEqual(result["new_keywords"], ["custom watch parts", "luxury watch"])
        self.assertEqual(result["stats"]["irrelevant_keyword_excluded"], 1)

    def test_non_english_requires_localized_blocked_list(self):
        with self.assertRaises(workflow.KeywordWorkflowError):
            workflow.prepare_keyword_ideas(
                ["relojes al por mayor"],
                seed="relojes",
                existing_keywords=[],
                language="Spanish",
            )

        result = workflow.prepare_keyword_ideas(
            [
                "relojes al por mayor",
                "relojes precio",
                "rolex relojes al por mayor",
                "relojes elegantes",
            ],
            seed="relojes",
            existing_keywords=[],
            language="Spanish",
            blocked_phrases=["precio"],
            confirmed_brands=[],
            irrelevant_keywords=["relojes elegantes"],
        )

        self.assertEqual(result["new_keywords"], ["relojes al por mayor"])
        self.assertEqual(result["stats"]["blocked_phrase_excluded"], 1)
        self.assertEqual(result["stats"]["confirmed_brand_excluded"], 1)
        self.assertEqual(result["stats"]["irrelevant_keyword_excluded"], 1)

    def test_unsegmented_language_uses_localized_phrase_containment(self):
        result = workflow.prepare_keyword_ideas(
            ["手表批发", "手表附近", "劳力士手表批发", "普通手表"],
            seed="手表",
            existing_keywords=[],
            language="Chinese",
            blocked_phrases=["附近"],
            confirmed_brands=["劳力士"],
            irrelevant_keywords=["普通手表"],
        )

        self.assertEqual(result["new_keywords"], ["手表批发"])
        self.assertEqual(result["stats"]["blocked_phrase_excluded"], 1)
        self.assertEqual(result["stats"]["confirmed_brand_excluded"], 1)
        self.assertEqual(result["stats"]["irrelevant_keyword_excluded"], 1)

    def test_parser_and_workflow_defaults(self):
        args = workflow.build_parser().parse_args(
            [
                "prepare",
                "--ads-csv",
                "ideas.csv",
                "--seed",
                "watch",
                "--irrelevant-keyword-file",
                "irrelevant.txt",
            ]
        )
        self.assertEqual(args.language, "English")
        self.assertEqual(workflow.DEFAULT_LANGUAGE, "English")
        self.assertEqual(workflow.DEFAULT_LOCATION, "All locations")


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
        self.assertRegex(skill_text, r"no\s+active website/site filter")
        self.assertNotIn("Build the website seed", skill_text)
        self.assertNotIn("fill the website-filter field with the website seed", skill_text)
        self.assertIn("The supplied domain is a destination-tab selector only.", readme_text)

    def test_language_location_and_filter_contract(self):
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        policy_text = (SKILL_ROOT / "references/keyword-filter-policy.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Default `language` to `English`", skill_text)
        self.assertIn("`location` to `All locations`", skill_text)
        self.assertIn("Set targeting language to the requested language.", skill_text)
        self.assertIn("does not require a", skill_text)
        self.assertRegex(skill_text, r"`me` does not match\s+`metal`")
        self.assertIn("Do not require wholesale", policy_text)
        self.assertIn("--irrelevant-keyword-file", policy_text)
        self.assertIn("confirmed-brands.txt", policy_text)
        self.assertIn("refuses a non-English run", policy_text)

    def test_domain_selects_sheets_and_missing_domain_selects_detailed_export(self):
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        export_contract = (SKILL_ROOT / "references/detail-export-contract.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Do not default a missing domain.", skill_text)
        self.assertIn("When `domain` is present", skill_text)
        self.assertIn("When `domain` is absent", skill_text)
        self.assertIn("do not access Google Drive or Google Sheets", skill_text)
        self.assertIn("--detail-output <durable-workspace-path.csv>", skill_text)
        self.assertIn("Preserve the complete source header", export_contract)
        self.assertIn("average monthly searches", export_contract)
        self.assertIn("low-range top-of-page bid", export_contract)
        self.assertIn("Every detail cell exactly matches", export_contract)

    def test_user_facing_skill_copy_is_english(self):
        for relative_path in ("SKILL.md", "README.md", "agents/openai.yaml"):
            with self.subTest(relative_path=relative_path):
                text = (SKILL_ROOT / relative_path).read_text(encoding="utf-8")
                self.assertNotRegex(text, r"[\u3400-\u9fff]")


if __name__ == "__main__":
    unittest.main()
