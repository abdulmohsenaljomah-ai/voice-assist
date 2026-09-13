"""ماركوس – Arabic voice assistant for Windows (development edition).

Target environment: Windows PC with NVIDIA GPU + local Ollama.
This file is the main entry point.  See README.md for setup instructions.
"""

import logging
import sys
import time

import ollama
import pyttsx3
import sounddevice as sd
from faster_whisper import WhisperModel

import config as cfg
from command_executor import execute, ExecutionResult, RiskLevel

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(
    level=cfg.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
# Optional: also write to file if logs directory exists
try:
    cfg._ensure_log_dir()
    logging.getLogger().addHandler(logging.FileHandler(cfg.LOG_FILE))
except Exception:
    pass

log = logging.getLogger("marco")

# ------------------------------------------------------------------
# TTS
# ------------------------------------------------------------------
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)


def speak(text: str) -> None:
    """Speak *text* aloud and also print it."""
    clean = text.split("```")[-1].strip()
    log.info(f"🔊 ماركوس: {clean}")
    engine.say(clean)
    engine.runAndWait()


# ------------------------------------------------------------------
# STT (Whisper)
# ------------------------------------------------------------------
print("⏳ جاري تحميل Whisper...")
try:
    whisper = WhisperModel(
        cfg.WHISPER_MODEL,
        device=cfg.WHISPER_DEVICE,
        compute_type=cfg.WHISPER_COMPUTE_TYPE,
    )
except Exception as e:
    log.error(f"Failed to initialise Whisper on CUDA: {e}")
    log.info("Falling back to CPU.")
    try:
        whisper = WhisperModel(
            cfg.WHISPER_MODEL,
            device="cpu",
            compute_type="int8",
        )
    except Exception as e2:
        log.critical(f"Whisper could not be loaded at all: {e2}")
        speak("لم أتمكن من تشغيل نظام التعرف على الكلام")
        sys.exit(1)

print("✅ Whisper جاهز!")


def listen(duration: int = cfg.LISTEN_DURATION_WAKE) -> str:
    """Record *duration* seconds of audio and return lowercased AR text."""
    try:
        audio = sd.rec(
            int(duration * cfg.SAMPLE_RATE),
            samplerate=cfg.SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        audio_np = audio.flatten()
        segments, _ = whisper.transcribe(audio_np, language=cfg.WHISPER_LANGUAGE)
        text = " ".join([s.text for s in segments])
        log.info(f"📝 سمعت: {text}")
        return text.strip().lower()
    except Exception as e:
        log.error(f"Error in listen(): {e}")
        return ""


# ------------------------------------------------------------------
# LLM (Ollama)
# ------------------------------------------------------------------
SYSTEM_PROMPT = """أنت وكيل ذكاء اصطناعي اسمك ماركوس تتحكم بجهاز Windows.
عندما يطلب المستخدم شيئاً، رد بطريقتين فقط:
١. إذا الطلب يحتاج تنفيذ على الجهاز: رد هكذا بالضبط في سطر واحد: CMD: الأمر
مثال: CMD: start calc
مثال: CMD: start https://youtube.com
مثال: CMD: start notepad
٢. إذا سؤال أو محادثة: رد بالعربية مباشرة بدون CMD
مهم جداً: رد بإيجاز، جملة أو جملتين فقط، لا تفكر بصوت عالٍ"""


def ask_ollama(prompt: str) -> str:
    """Send *prompt* to the local Ollama LLM and return the reply."""
    for attempt in range(cfg.LLM_MAX_RETRIES):
        try:
            response = ollama.chat(
                model=cfg.OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                timeout=cfg.LLM_TIMEOUT,
            )
            return response['message']['content']
        except Exception as e:
            log.warning(f"Ollama attempt {attempt + 1}/{cfg.LLM_MAX_RETRIES} failed: {e}")
            if attempt < cfg.LLM_MAX_RETRIES - 1:
                time.sleep(1)
            else:
                log.error("All Ollama retries exhausted.")
                return "عذراً، الخدمة غير متاحة الآن."


# ------------------------------------------------------------------
# Response processing
# ------------------------------------------------------------------
def process_response(response: str) -> None:
    """Parse LLM *response* and either speak it or execute a command."""
    clean = response.split("```")[-1].strip()

    if "CMD:" in clean:
        cmd = clean.split("CMD:")[1].strip().split("\n")[0]
        log.info(f"🔧 استلام أمر: {cmd}")

        result: ExecutionResult = execute(cmd)

        if result.risk == RiskLevel.FORBIDDEN or result.risk == RiskLevel.INVALID:
            speak(result.message)
            return

        if result.risk == RiskLevel.CONFIRM_REQUIRED and not result.executed:
            # Ask for voice confirmation
            speak(result.message)
            confirm = listen(duration=3)
            if "نعم" not in confirm:
                speak("تم الإلغاء")
                return
            # Re-execute with confirmation granted
            result = execute(cmd, skip_confirmation=True)

        speak(result.message)
    else:
        speak(clean)


# ------------------------------------------------------------------
# Main loop
# ------------------------------------------------------------------
speak("مرحبا، أنا ماركوس جاهز")
print("✅ قل 'Marcos' لتفعيل ماركوس")

while True:
    print("👂 منتظر Marcos...")
    trigger = listen(duration=cfg.LISTEN_DURATION_WAKE)

    if cfg.WAKE_WORD not in trigger:
        continue

    speak("نعم؟")
    print("🎤 تكلم! عندك 10 ثواني")
    command = listen(duration=cfg.LISTEN_DURATION_COMMAND)

    if not command or len(command) < 3:
        speak("ما سمعت شيئاً")
        continue

    print(f"🎤 قلت: {command}")
    response = ask_ollama(command)
    print(f"🤖 الرد: {response}")
    process_response(response)
