import tempfile
import unittest
from unittest import mock
from pathlib import Path

from marcos.audio import EndpointDetector
from marcos.llm import LLM
from marcos.metrics import LatencyLog, TurnTimer


class EndpointDetectorTests(unittest.TestCase):
    def make(self, **kw):
        return EndpointDetector(threshold=0.01, frame_ms=30, end_silence_ms=300,
                                start_timeout_s=1, max_utterance_s=2, **kw)

    def test_ends_after_silence_following_speech(self):
        d = self.make()
        for _ in range(10):
            self.assertFalse(d.push(0.05))      # speaking
        ended = [d.push(0.0) for _ in range(10)]  # 300 ms of silence
        self.assertTrue(d.heard_speech)
        self.assertEqual(ended.index(True), 9)

    def test_short_pause_does_not_end_turn(self):
        d = self.make()
        for level in [0.05] * 5 + [0.0] * 5 + [0.05] * 5:
            self.assertFalse(d.push(level))

    def test_start_timeout_without_speech(self):
        d = self.make()
        results = [d.push(0.0) for _ in range(34)]
        self.assertTrue(results[-1])
        self.assertFalse(d.heard_speech)

    def test_max_utterance_cap(self):
        d = self.make()
        results = [d.push(0.05) for _ in range(67)]
        self.assertTrue(results[-1])


class LLMMemoryTests(unittest.TestCase):
    def test_history_is_sent_and_bounded(self):
        calls = []

        def fake_chat(model, messages):
            calls.append(messages)
            return {"message": {"content": "تمام"}}

        llm = LLM(chat_fn=fake_chat)
        for i in range(20):
            llm.ask(f"سؤال {i}")
            llm.remember(f"سؤال {i}", "تمام")
        last = calls[-1]
        self.assertEqual(last[0]["role"], "system")
        self.assertLessEqual(len(last), 1 + llm.history.maxlen + 1)
        self.assertEqual(last[-2]["content"], "تمام")

    def test_retries_then_empty(self):
        attempts = []

        def failing(model, messages):
            attempts.append(1)
            raise ConnectionError("ollama down")

        import config
        llm = LLM(chat_fn=failing)
        with mock.patch("marcos.llm.time.sleep"), self.assertLogs("marcos.llm", "WARNING"):
            self.assertEqual(llm.ask("hi"), "")
        self.assertEqual(len(attempts), config.LLM_MAX_RETRIES)


class LatencyTests(unittest.TestCase):
    def test_rows_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = LatencyLog(Path(tmp) / "latency.csv")
            for _ in range(3):
                t = TurnTimer()
                with t.stage("llm"):
                    pass
                log.add(t)
            text = (Path(tmp) / "latency.csv").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("stt,llm,tool,tts,total"))
            self.assertEqual(len(text.strip().splitlines()), 4)
            self.assertIn("total", log.summary())


if __name__ == "__main__":
    unittest.main()
