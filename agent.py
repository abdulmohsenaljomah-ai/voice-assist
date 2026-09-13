import pyttsx3
import ollama
import subprocess
import sounddevice as sd
from faster_whisper import WhisperModel

engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    clean = text.split("</think>")[-1].strip()
    print(f"🔊 ماركوس: {clean}")
    engine.say(clean)
    engine.runAndWait()

print("⏳ جاري تحميل Whisper...")
whisper = WhisperModel("small", device="cuda", compute_type="float16")
print("✅ Whisper جاهز!")

def listen(duration=3):
    sample_rate = 16000
    audio = sd.rec(int(duration * sample_rate),
                   samplerate=sample_rate,
                   channels=1, dtype="float32")
    sd.wait()
    audio_np = audio.flatten()
    segments, _ = whisper.transcribe(audio_np, language="ar")
    text = " ".join([s.text for s in segments])
    print(f"📝 سمعت: {text}")
    return text.strip().lower()

DANGEROUS = ["اغلق الجهاز", "اعد التشغيل", "احذف", "format"]

def ask_ollama(prompt):
    system = """أنت وكيل ذكاء اصطناعي اسمك ماركوس تتحكم بجهاز Windows.
عندما يطلب المستخدم شيئاً، رد بطريقتين فقط:
١. إذا الطلب يحتاج تنفيذ على الجهاز: رد هكذا بالضبط في سطر واحد: CMD: الأمر
مثال: CMD: start calc
مثال: CMD: start https://youtube.com
مثال: CMD: start notepad
٢. إذا سؤال أو محادثة: رد بالعربية مباشرة بدون CMD
مهم جداً: رد بإيجاز، جملة أو جملتين فقط، لا تفكر بصوت عالٍ"""

    response = ollama.chat(
        model="deepseek-r1:8b",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
    )
    return response['message']['content']

def process_response(response, original_command):
    clean = response.split("</think>")[-1].strip()

    if any(x in original_command for x in DANGEROUS):
        speak("هذا أمر خطير، هل أنت متأكد؟ قل نعم للتأكيد")
        confirm = listen(duration=3)
        if "نعم" not in confirm:
            speak("تم الإلغاء")
            return

    if "CMD:" in clean:
        cmd = clean.split("CMD:")[1].strip().split("\n")[0]
        try:
            subprocess.Popen(cmd, shell=True)
            speak("تم")
        except:
            speak("ما قدرت أنفذ")
    else:
        speak(clean)

speak("مرحبا، أنا ماركوس جاهز")
print("✅ قل 'Marcos' لتفعيل ماركوس")

while True:
    print("👂 منتظر Marcos...")
    trigger = listen(duration=3)

    if "marcos" not in trigger:
        continue

    speak("نعم؟")
    print("🎤 تكلم! عندك 10 ثواني")
    command = listen(duration=10)

    if not command or len(command) < 3:
        speak("ما سمعت شيئاً")
        continue

    print(f"🎤 قلت: {command}")
    response = ask_ollama(command)
    print(f"🤖 الرد: {response}")
    process_response(response, command)