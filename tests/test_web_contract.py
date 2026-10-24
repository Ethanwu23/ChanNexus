import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
APP_SOURCE = ROOT / "web" / "chanlun_chart" / "cl_app" / "__init__.py"
CONTRACT_FILE = ROOT / "tests" / "fixtures" / "web_routes_v1.json"


def extract_routes(source: str) -> list[str]:
    """静态提取Flask路由，避免契约测试连接数据库和行情服务。"""
    tree = ast.parse(source)
    routes = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "route"
                and decorator.args
                and isinstance(decorator.args[0], ast.Constant)
            ):
                continue
            methods = ["GET"]
            for keyword in decorator.keywords:
                if keyword.arg != "methods" or not isinstance(
                    keyword.value, (ast.List, ast.Tuple)
                ):
                    continue
                methods = [
                    item.value
                    for item in keyword.value.elts
                    if isinstance(item, ast.Constant)
                ]
            routes.append(
                f"{','.join(sorted(methods))} "
                f"{decorator.args[0].value} {node.name}"
            )
    return sorted(routes)


def returned_dictionary_keys(source: str, function_name: str) -> set[str]:
    """提取目标函数直接返回或通过局部变量返回的字典键。"""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != function_name:
            continue
        dictionaries = []
        named_dictionaries = {}
        for child in ast.walk(node):
            if isinstance(child, ast.Assign) and isinstance(child.value, ast.Dict):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        named_dictionaries[target.id] = child.value
            if isinstance(child, ast.Return):
                if isinstance(child.value, ast.Dict):
                    dictionaries.append(child.value)
                elif isinstance(child.value, ast.Name):
                    dictionary = named_dictionaries.get(child.value.id)
                    if dictionary is not None:
                        dictionaries.append(dictionary)
        keys = set()
        for dictionary in dictionaries:
            keys.update(
                key.value
                for key in dictionary.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            )
        return keys
    raise AssertionError(f"没有找到函数: {function_name}")


class WebContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP_SOURCE.read_text(encoding="utf-8")
        cls.contract = json.loads(CONTRACT_FILE.read_text(encoding="utf-8"))

    def test_flask_routes_match_baseline_v1(self):
        self.assertEqual(
            extract_routes(self.source),
            sorted(self.contract["routes"]),
        )

    def test_key_chart_response_fields_match_baseline_v1(self):
        function_by_path = {
            "/tv/config": "tv_config",
            "/tv/history": "tv_history",
        }
        for path, function_name in function_by_path.items():
            with self.subTest(path=path):
                actual = returned_dictionary_keys(self.source, function_name)
                expected = set(self.contract["key_response_fields"][path])
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
