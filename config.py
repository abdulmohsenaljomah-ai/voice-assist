"""Configuration for Marcos, the Arabic voice assistant.

Every tunable value lives here so behaviour can be changed without
touching the pipeline code.
"""

import logging
from pathlib import Path

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "marcos.log"
LATENCY_CSV = LOG_DIR / "latency.csv"
LOG_LEVEL = logging.INFO

# ------------------------------------------------------------------
# LLM (local, via Ollama)
# ------------------------------------------------------------------
OLLAMA_MODEL = "deepseek-r1:8b"
LLM_TIMEOUT = 30          # seconds per request
LLM_MAX_RETRIES = 3
HISTORY_TURNS = 6         # user/assistant pairs kept as short-term memory

# ------------------------------------------------------------------
# Speech-to-Text (faster-whisper)
# ------------------------------------------------------------------
WHISPER_MODEL = "small"
WHISPER_DEVICE = "cuda"           # falls back to CPU automatically
WHISPER_COMPUTE_TYPE = "float16"
WHISPER_LANGUAGE = "ar"
SAMPLE_RATE = 16000

# ------------------------------------------------------------------
# Wake word
# ------------------------------------------------------------------
# Whisper is forced to Arabic, so it usually writes the name in Arabic
# script. Accept the common spellings in both scripts.
WAKE_WORDS = ["ماركوس", "ماركس", "مركوس", "marcos", "markos", "marcus"]
WAKE_LISTEN_SECONDS = 2.5         # rolling window while waiting for the wake word

# ------------------------------------------------------------------
# Voice activity detection (end-of-turn)
# ------------------------------------------------------------------
VAD_FRAME_MS = 30                 # analysis frame size
VAD_CALIBRATION_SECONDS = 0.6     # ambient-noise measurement at start-up
VAD_THRESHOLD_MULTIPLIER = 3.0    # speech = energy > noise_floor * multiplier
VAD_MIN_THRESHOLD = 0.004         # never go below this RMS (quiet rooms)
VAD_END_SILENCE_MS = 800          # this much silence after speech ends the turn
VAD_START_TIMEOUT_SECONDS = 5     # give up if the user never starts speaking
VAD_MAX_UTTERANCE_SECONDS = 15    # hard cap on one utterance
VAD_PRE_ROLL_MS = 300             # audio kept from just before speech starts

# ------------------------------------------------------------------
# Text-to-Speech (pyttsx3 / Windows SAPI)
# ------------------------------------------------------------------
TTS_RATE = 165
TTS_VOLUME = 1.0
# Substrings used to pick an Arabic SAPI voice if one is installed
# (e.g. "Microsoft Naayf" / "Microsoft Hoda").
TTS_VOICE_HINTS = ["arabic", "ar-sa", "ar_sa", "naayf", "hoda"]

# ------------------------------------------------------------------
# Tools
# ------------------------------------------------------------------
# The LLM can only open applications from this allowlist.
# Spoken name (Arabic or English) -> Windows executable / URI.
APP_ALLOWLIST = {
    "calculator": "calc.exe",
    "الحاسبة": "calc.exe",
    "notepad": "notepad.exe",
    "المفكرة": "notepad.exe",
    "paint": "mspaint.exe",
    "الرسام": "mspaint.exe",
    "explorer": "explorer.exe",
    "مستكشف الملفات": "explorer.exe",
    "settings": "ms-settings:",
    "الإعدادات": "ms-settings:",
}
SEARCH_URL = "https://www.google.com/search?q={query}"
