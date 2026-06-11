import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parents[1]


def load_module():
    module_path = ROOT / "scripts" / "documentation_wizard.py"
    spec = importlib.util.spec_from_file_location("documentation_wizard_local", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["documentation_wizard_local"] = module
    spec.loader.exec_module(module)
    return module


DOCUMENTATION_WIZARD = load_module()


class DocumentationWizardLocalTests(unittest.TestCase):
    def test_report_smoke_on_generic_fixture(self) -> None:
        report = DOCUMENTATION_WIZARD.build_report(WORKSPACE_ROOT / "tests" / "fixtures" / "generic_python_repo")
        self.assertEqual(report["scope"], "documentation-drift-audit")
        self.assertIsInstance(report["findings"], list)

    def test_iter_files_prunes_non_public_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "docs" / "guide.md").parent.mkdir(parents=True)
            (root / "docs" / "guide.md").write_text("public\n", encoding="utf-8")
            (root / "docs" / "archive" / "old.md").parent.mkdir(parents=True)
            (root / "docs" / "archive" / "old.md").write_text("archived\n", encoding="utf-8")
            files = DOCUMENTATION_WIZARD.iter_files(root, {".md"})
        self.assertEqual([path.relative_to(root).as_posix() for path in files], ["docs/guide.md"])


if __name__ == "__main__":
    unittest.main()
