"""Configuration for the Marco voice assistant.

All hardcoded values that were previously scattered in agent.py are
centralised here so they can be tuned without touching code.
"""

import logging
import os
from pathlib import Path

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

# ------------------------------------------------------------------
# LLM / Ollama
# ------------------------------------------------------------------
OLLAMA_MODEL = "deepseek-r1:8b"
LLM_TIMEOUT = 30  # seconds
LLM_MAX_RETRIES = 3

# ------------------------------------------------------------------
# Speech-to-Text (faster-whisper)
# ------------------------------------------------------------------
WHISPER_MODEL = "small"
WHISPER_DEVICE = "cuda"        # falls back to "cpu" if CUDA unavailable
WHISPER_COMPUTE_TYPE = "float16"
WHISPER_LANGUAGE = "ar"
SAMPLE_RATE = 16000

# ------------------------------------------------------------------
# Audio / Wake-word
# ------------------------------------------------------------------
WAKE_WORD = "marcos"
LISTEN_DURATION_WAKE = 3   # seconds for passive listening
LISTEN_DURATION_COMMAND = 10  # seconds after wake word

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
LOG_LEVEL = logging.INFO
LOG_FILE = PROJECT_ROOT / "logs" / "marco.log"

# ------------------------------------------------------------------
# Command safety
# ------------------------------------------------------------------
# Commands that are completely forbidden and will never execute.
FORBIDDEN_PATTERNS = [
    "shutdown",
    "restart",
    "power off",
    "diskpart",
    "cipher /w",
    "format",
]

# Commands that require explicit user confirmation before execution.
# These are NOT blocked outright — the assistant asks "are you sure?"
CONFIRMATION_REQUIRED_PATTERNS = [
    "del ",
    "rd ",
    "rmdir",
    "deltree",
    "erase",
]

# ------------------------------------------------------------------
# Internal helper
# ------------------------------------------------------------------
def _ensure_log_dir() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

if os.environ.get("MARCO_LOG_DIR"):
    _ensure_log_dir()
