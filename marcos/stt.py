"""Speech-to-text with faster-whisper (GPU first, CPU fallback)."""

from __future__ import annotations

import logging

import numpy as np

import config as cfg

log = logging.getLogger("marcos.stt")


class Transcriber:
    def __init__(self) -> None:
        from faster_whisper import WhisperModel

        try:
            self._model = WhisperModel(cfg.WHISPER_MODEL, device=cfg.WHISPER_DEVICE,
                                       compute_type=cfg.WHISPER_COMPUTE_TYPE)
            # CUDA problems often surface only on first use, so warm up now.
            self._warm_up()
            self.device = cfg.WHISPER_DEVICE
        except Exception as exc:  # noqa: BLE001 - any CUDA/cuDNN failure
            log.warning("Whisper on %s failed (%s); falling back to CPU int8.", cfg.WHISPER_DEVICE, exc)
            self._model = WhisperModel(cfg.WHISPER_MODEL, device="cpu", compute_type="int8")
            self._warm_up()
            self.device = "cpu"
        log.info("Whisper '%s' ready on %s", cfg.WHISPER_MODEL, self.device)

    def _warm_up(self) -> None:
        self.transcribe(np.zeros(cfg.SAMPLE_RATE // 2, dtype=np.float32))

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        segments, _info = self._model.transcribe(
            audio,
            language=cfg.WHISPER_LANGUAGE,
            beam_size=1,            # greedy decoding: noticeably lower latency
            vad_filter=True,        # drop residual silence inside the clip
            condition_on_previous_text=False,
        )
        return " ".join(s.text for s in segments).strip()
