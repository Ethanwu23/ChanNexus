import contextlib
import importlib.util
import io
import unittest
from pathlib import Path


def load_entry_module():
    path = Path(__file__).parents[1] / "web" / "chanlun_chart" / "app.py"
    spec = importlib.util.spec_from_file_location("chanlun_web_entry", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WebEntryTests(unittest.TestCase):
    def test_missing_dependency_has_install_command_and_no_create_app_nameerror(self):
        module = load_entry_module()
        error = ModuleNotFoundError("No module named 'pinyin'", name="pinyin")
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            module._print_startup_error(error)
        message = output.getvalue()
        self.assertIn("[DEPENDENCY_ERROR]", message)
        self.assertIn("pip install pinyin", message)
        self.assertNotIn("NameError: name 'create_app'", message)

    def test_syntax_error_is_classified(self):
        module = load_entry_module()
        error = SyntaxError("bad syntax", ("broken.py", 3, 1, "bad"))
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            module._print_startup_error(error)
        self.assertIn("[SYNTAX_ERROR]", output.getvalue())


if __name__ == "__main__":
    unittest.main()
