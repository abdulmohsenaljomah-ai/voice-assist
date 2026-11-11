"""Marcos – Arabic voice assistant (entry point).

Pipeline per turn:
    mic --VAD--> faster-whisper (STT) --> local LLM via Ollama
        --> [allowlisted tool] --> pyttsx3 (TTS)
Each stage is timed and logged to logs/latency.csv.
"""

from __future__ import annotations

import logging
import sys

import config as cfg
from marcos.metrics import LatencyLog, TurnTimer
from marcos.text import contains_wake_word, normalize_arabic, parse_reply
from marcos.tools import Toolbox


def setup_logging() -> None:
    cfg.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=cfg.LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(cfg.LOG_FILE, encoding="utf-8")],
    )


def command_after_wake_word(transcript: str) -> str:
    """'ماركوس افتح الحاسبة' -> 'افتح الحاسبة' (lets users speak in one breath)."""
    wake = {normalize_arabic(w) for w in cfg.WAKE_WORDS}
    words = transcript.split()
    for i, word in enumerate(words):
        if normalize_arabic(word) in wake:
            return " ".join(words[i + 1:]).strip()
    return ""


class Assistant:
    def __init__(self) -> None:
        # Heavy imports happen here so the pure modules stay testable.
        from marcos.audio import Recorder
        from marcos.llm import LLM
        from marcos.stt import Transcriber
        from marcos.tts import Speaker

        self.log = logging.getLogger("marcos")
        self.speaker = Speaker()
        self.log.info("Loading speech recognition…")
        self.stt = Transcriber()
        self.recorder = Recorder()
        self.llm = LLM()
        self.tools = Toolbox()
        self.latency = LatencyLog(cfg.LATENCY_CSV)

    def handle(self, user_text: str, timer: TurnTimer) -> None:
        with timer.stage("llm"):
            reply = parse_reply(self.llm.ask(user_text))

        if reply.is_tool_call:
            with timer.stage("tool"):
                result = self.tools.run(reply.tool, reply.args)
            self.log.info("🔧 %s(%s) -> %s", reply.tool, reply.args, result.message)
            answer = result.message
        else:
            answer = reply.speech or "عذراً، ما قدرت أجاوب الحين."

        self.llm.remember(user_text, answer)
        with timer.stage("tts"):
            self.speaker.say(answer)

    def run(self) -> None:
        self.recorder.calibrate()
        self.speaker.say("مرحبا، أنا ماركوس جاهز")
        self.log.info("Say 'ماركوس' (Marcos) to start.")
        try:
            while True:
                heard = self.stt.transcribe(
                    self.recorder.record_utterance(start_timeout_s=cfg.WAKE_LISTEN_SECONDS))
                if not heard or not contains_wake_word(heard, cfg.WAKE_WORDS):
                    continue

                command = command_after_wake_word(heard)
                if len(command) < 2:
                    self.speaker.say("نعم؟")
                    audio = self.recorder.record_utterance()
                    timer = TurnTimer()  # latency is measured from end of user speech
                    with timer.stage("stt"):
                        command = self.stt.transcribe(audio)
                else:
                    timer = TurnTimer()

                if len(command) < 2:
                    self.speaker.say("ما سمعت شيئاً")
                    continue
                self.log.info("🎤 %s", command)
                self.handle(command, timer)
                row = self.latency.add(timer)
                self.log.info("⏱️ latency ms: %s", row)
        except KeyboardInterrupt:
            self.log.info("Median latency this session (ms): %s", self.latency.summary())
            self.speaker.say("مع السلامة")


if __name__ == "__main__":
    setup_logging()
    Assistant().run()
