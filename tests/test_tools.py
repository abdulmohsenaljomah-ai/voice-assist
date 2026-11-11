import datetime as dt
import unittest

from marcos.tools import Toolbox


class ToolboxTests(unittest.TestCase):
    def setUp(self):
        self.opened = []
        self.tools = Toolbox(opener=self.opened.append,
                             now=lambda: dt.datetime(2026, 11, 12, 9, 5))

    def test_open_allowlisted_app_in_arabic(self):
        self.assertTrue(self.tools.run("open_app", {"name": "الحاسبة"}).ok)
        self.assertEqual(self.opened, ["calc.exe"])

    def test_unknown_app_is_refused(self):
        result = self.tools.run("open_app", {"name": "cmd.exe /c del *"})
        self.assertFalse(result.ok)
        self.assertEqual(self.opened, [])

    def test_unknown_tool_is_refused(self):
        self.assertFalse(self.tools.run("run_shell", {"cmd": "format c:"}).ok)
        self.assertEqual(self.opened, [])

    def test_bad_arguments_do_not_crash(self):
        self.assertFalse(self.tools.run("open_app", {"path": "x"}).ok)

    def test_url_scheme_validation(self):
        self.assertFalse(self.tools.run("open_url", {"url": "file:///C:/Windows/System32"}).ok)
        self.assertFalse(self.tools.run("open_url", {"url": "javascript:alert(1)"}).ok)
        self.assertTrue(self.tools.run("open_url", {"url": "https://example.com"}).ok)
        self.assertEqual(self.opened, ["https://example.com"])

    def test_search_is_url_encoded(self):
        self.tools.run("web_search", {"query": "أسعار الذهب & الفضة"})
        self.assertTrue(self.opened[0].startswith("https://www.google.com/search?q="))
        self.assertNotIn(" ", self.opened[0])
        self.assertNotIn("&", self.opened[0].split("q=", 1)[1])

    def test_time_and_date(self):
        self.assertIn("09:05", self.tools.run("get_time", {}).message)
        self.assertIn("الخميس", self.tools.run("get_date", {}).message)


if __name__ == "__main__":
    unittest.main()
