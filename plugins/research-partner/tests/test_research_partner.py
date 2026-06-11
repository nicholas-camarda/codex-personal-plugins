import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parents[1]


def load_module():
    module_path = ROOT / "scripts" / "research_partner.py"
    spec = importlib.util.spec_from_file_location("research_partner_local", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["research_partner_local"] = module
    spec.loader.exec_module(module)
    return module


RESEARCH_PARTNER = load_module()


class ResearchPartnerLocalTests(unittest.TestCase):
    def test_inventory_smoke_on_minimal_fixture(self) -> None:
        report = RESEARCH_PARTNER.inventory_repo(WORKSPACE_ROOT / "tests" / "fixtures" / "minimal_repo")
        self.assertEqual(report["scope"], "analysis-review-preflight")
        self.assertIn("flow", report)

    def test_run_review_executes_lanes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "review"
            report = RESEARCH_PARTNER.run_review(WORKSPACE_ROOT / "tests" / "fixtures" / "research_repo", output_dir)
        self.assertEqual(report["command"], "run")
        self.assertEqual(report["status"], "ok")
        self.assertEqual(len(report["lane_outputs"]), 6)


if __name__ == "__main__":
    unittest.main()
