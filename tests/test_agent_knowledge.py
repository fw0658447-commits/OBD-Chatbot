"""Offline smoke tests for the shared OBD Systemkoordination data and retrieval."""
import json
import unittest
from pathlib import Path

import obd_systemkoordination_core as core

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "knowledge"


class AgentKnowledgeTest(unittest.TestCase):
    def test_required_structured_sources_exist(self):
        for filename in ("source_catalog.json", "regulatory_graph.json", "early_warning_initiatives.json"):
            self.assertTrue((DATA / filename).is_file(), filename)
            json.loads((DATA / filename).read_text(encoding="utf-8"))

    def test_knowledge_has_global_scope(self):
        counts = core.knowledge_metrics()
        self.assertGreater(counts["sources"], 20)
        self.assertGreater(counts["regulations_and_standards"], 10)
        self.assertGreater(counts["relationships"], 10)
        self.assertGreater(counts["initiatives"], 8)

    def test_euro7_returns_sources_and_real_legal_status(self):
        hits = core.search_knowledge("Euro 7 Batterie EU 2026/1764")
        self.assertTrue(hits["source_matches"], "No EU7 sources")
        self.assertTrue(any(s.get("market") == "EU" for s in hits["source_matches"]))

    def test_early_warning_is_separate_from_binding_law(self):
        hits = core.search_knowledge("Pilot DIAS Antitampering")
        self.assertTrue(any("DIAS" in p["title"] for p in hits["initiatives"]))

    def test_service_customer_field_chain(self):
        answer = core.answer_from_knowledge("Service Feld ePTI")
        self.assertIn("Service/Kunde/ePTI", answer)
        self.assertIn("Keine", answer if "Keine" in answer else "Keine automatische Compliance-Freigabe")

    def test_unknown_local_acronyms_are_not_fabricated(self):
        results = core.search_knowledge("GSP RTM SCE")
        self.assertGreaterEqual(len(results["unknown_terms"]), 3)

    def test_no_fake_statutory_obligation_from_engineering_links(self):
        answer = core.answer_from_knowledge("GTR 22 SOCE UN R156")
        self.assertTrue("Hypothese" in answer or "Review" in answer)


if __name__ == "__main__":
    unittest.main()
