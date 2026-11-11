"""Text-to-speech via pyttsx3 (Windows SAPI), preferring an Arabic voice."""

from __future__ import annotations

import logging

import config as cfg

log = logging.getLogger("marcos.tts")


class Speaker:
    def __init__(self) -> None:
        import pyttsx3

        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", cfg.TTS_RATE)
        self._engine.setProperty("volume", cfg.TTS_VOLUME)
        voice = self._pick_arabic_voice()
        if voice:
            self._engine.setProperty("voice", voice.id)
            log.info("Using TTS voice: %s", voice.name)
        else:
            log.warning("No Arabic SAPI voice found; install one from Windows "
                        "Settings > Time & language > Speech for better output.")

    def _pick_arabic_voice(self):
        for voice in self._engine.getProperty("voices"):
            label = f"{voice.id} {voice.name} {getattr(voice, 'languages', '')}".lower()
            if any(hint in label for hint in cfg.TTS_VOICE_HINTS):
                return voice
        return None

    def say(self, text: str) -> None:
        if not text:
            return
        log.info("🔊 %s", text)
        self._engine.say(text)
        self._engine.runAndWait()
