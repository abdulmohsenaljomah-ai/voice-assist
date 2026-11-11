"""Microphone capture with energy-based voice activity detection (VAD).

Instead of recording a fixed 10 seconds, the recorder waits for speech,
keeps a short pre-roll so the first syllable is not clipped, and ends
the turn after a configurable stretch of silence. The decision logic
(:class:`EndpointDetector`) is pure and unit-tested; :class:`Recorder`
just feeds it frames from the microphone.
"""

from __future__ import annotations

import collections
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

import config as cfg

log = logging.getLogger("marcos.audio")


def rms(frame: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(frame, dtype=np.float64)))) if frame.size else 0.0


@dataclass
class EndpointDetector:
    """Frame-by-frame turn detector.

    Feed frames with :meth:`push`; it returns ``True`` once the turn is
    over (speech followed by enough silence, start timeout, or max
    length). ``heard_speech`` tells you whether anything was said.
    """
    threshold: float
    frame_ms: int = cfg.VAD_FRAME_MS
    end_silence_ms: int = cfg.VAD_END_SILENCE_MS
    start_timeout_s: float = cfg.VAD_START_TIMEOUT_SECONDS
    max_utterance_s: float = cfg.VAD_MAX_UTTERANCE_SECONDS

    def __post_init__(self) -> None:
        self.heard_speech = False
        self._elapsed_ms = 0
        self._speech_ms = 0
        self._silence_ms = 0

    def push(self, frame_rms: float) -> bool:
        self._elapsed_ms += self.frame_ms
        if frame_rms >= self.threshold:
            self.heard_speech = True
            self._silence_ms = 0
        elif self.heard_speech:
            self._silence_ms += self.frame_ms
        if self.heard_speech:
            self._speech_ms += self.frame_ms

        if not self.heard_speech:
            return self._elapsed_ms >= self.start_timeout_s * 1000
        if self._silence_ms >= self.end_silence_ms:
            return True
        return self._speech_ms >= self.max_utterance_s * 1000


class Recorder:
    """Captures one utterance at a time from the default microphone."""

    def __init__(self, sample_rate: int = cfg.SAMPLE_RATE):
        import sounddevice as sd  # imported lazily so tests don't need audio drivers

        self._sd = sd
        self.sample_rate = sample_rate
        self.frame_len = int(sample_rate * cfg.VAD_FRAME_MS / 1000)
        self.threshold = cfg.VAD_MIN_THRESHOLD

    def calibrate(self) -> float:
        """Measure ambient noise and set the speech threshold from it."""
        audio = self._sd.rec(int(cfg.VAD_CALIBRATION_SECONDS * self.sample_rate),
                             samplerate=self.sample_rate, channels=1, dtype="float32")
        self._sd.wait()
        noise = rms(audio.flatten())
        self.threshold = max(cfg.VAD_MIN_THRESHOLD, noise * cfg.VAD_THRESHOLD_MULTIPLIER)
        log.info("VAD calibrated: noise=%.5f threshold=%.5f", noise, self.threshold)
        return self.threshold

    def record_utterance(self, start_timeout_s: Optional[float] = None) -> np.ndarray:
        """Block until the user finishes speaking; return mono float32 audio
        (empty array if nobody spoke before the timeout)."""
        detector = EndpointDetector(
            threshold=self.threshold,
            start_timeout_s=start_timeout_s or cfg.VAD_START_TIMEOUT_SECONDS,
        )
        pre_roll = collections.deque(maxlen=max(1, cfg.VAD_PRE_ROLL_MS // cfg.VAD_FRAME_MS))
        captured: list[np.ndarray] = []

        with self._sd.InputStream(samplerate=self.sample_rate, channels=1,
                                  dtype="float32", blocksize=self.frame_len) as stream:
            while True:
                frame, _overflow = stream.read(self.frame_len)
                frame = frame.flatten()
                was_speaking = detector.heard_speech
                done = detector.push(rms(frame))
                if detector.heard_speech:
                    if not was_speaking:
                        captured.extend(pre_roll)
                    captured.append(frame)
                else:
                    pre_roll.append(frame)
                if done:
                    break

        if not detector.heard_speech:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(captured)
