import unittest

from marcos.text import contains_wake_word, normalize_arabic, parse_reply, strip_think
from config import WAKE_WORDS


class WakeWordTests(unittest.TestCase):
    def test_arabic_script_transcription_matches(self):
        # Whisper in Arabic mode writes the name in Arabic script - the old
        # code only looked for the Latin "marcos" and never woke up.
        self.assertTrue(contains_wake_word("ماركوس", WAKE_WORDS))
        self.assertTrue(contains_wake_word("يا ماركوس، افتح الحاسبة", WAKE_WORDS))

    def test_latin_and_spelling_variants(self):
        self.assertTrue(contains_wake_word("Marcos!", WAKE_WORDS))
        self.assertTrue(contains_wake_word("مَارْكُوس", WAKE_WORDS))  # with diacritics

    def test_no_false_positive_on_substring(self):
        self.assertFalse(contains_wake_word("ماركوسات كثيرة", WAKE_WORDS))
        self.assertFalse(contains_wake_word("مرحبا", WAKE_WORDS))

    def test_normalize(self):
        self.assertEqual(normalize_arabic("إلى المدرسة"), "الي المدرسه")


class ReplyParsingTests(unittest.TestCase):
    def test_strip_think_block(self):
        raw = "<think>المستخدم يريد CMD: format c:</think>\nأهلاً بك"
        self.assertEqual(strip_think(raw), "أهلاً بك")

    def test_dangling_think_close(self):
        self.assertEqual(strip_think("some reasoning</think> الجواب"), "الجواب")

    def test_tool_inside_think_is_ignored(self):
        raw = '<think>TOOL: {"name": "open_app", "args": {"name": "notepad"}}</think>تمام'
        reply = parse_reply(raw)
        self.assertFalse(reply.is_tool_call)
        self.assertEqual(reply.speech, "تمام")

    def test_valid_tool_call(self):
        reply = parse_reply('TOOL: {"name": "web_search", "args": {"query": "طقس الرياض"}}')
        self.assertEqual(reply.tool, "web_search")
        self.assertEqual(reply.args, {"query": "طقس الرياض"})

    def test_tool_call_in_code_fence(self):
        reply = parse_reply('```json\nTOOL: {"name": "get_time", "args": {}}\n```')
        self.assertEqual(reply.tool, "get_time")

    def test_malformed_tool_is_spoken_not_executed(self):
        reply = parse_reply('TOOL: {"name": open_app}\nما فهمت')
        self.assertFalse(reply.is_tool_call)
        self.assertEqual(reply.speech, "ما فهمت")

    def test_plain_speech(self):
        self.assertEqual(parse_reply("عاصمة اليابان طوكيو.").speech, "عاصمة اليابان طوكيو.")


if __name__ == "__main__":
    unittest.main()
