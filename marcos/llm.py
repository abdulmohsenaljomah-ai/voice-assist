"""Local LLM client (Ollama) with short-term conversation memory."""

from __future__ import annotations

import collections
import logging
import time
from typing import Callable, Deque, Dict, List, Optional

import config as cfg

log = logging.getLogger("marcos.llm")

SYSTEM_PROMPT = """أنت ماركوس، مساعد صوتي ذكي يعمل على جهاز Windows ويتكلم العربية.
ردودك تُقرأ بصوت عالٍ، فاجعلها قصيرة: جملة أو جملتين، بدون رموز أو قوائم.

إذا احتاج الطلب تنفيذ شيء على الجهاز، رد بسطر واحد فقط بهذا الشكل بالضبط:
TOOL: {"name": "<اسم الأداة>", "args": {...}}

الأدوات المتاحة:
- open_app: {"name": "<اسم البرنامج>"}  البرامج المسموحة: {apps}
- open_url: {"url": "https://..."}
- web_search: {"query": "<نص البحث>"}
- get_time: {}
- get_date: {}

أمثلة:
المستخدم: افتح الحاسبة
TOOL: {"name": "open_app", "args": {"name": "الحاسبة"}}
المستخدم: ابحث عن أسعار الذهب اليوم
TOOL: {"name": "web_search", "args": {"query": "أسعار الذهب اليوم"}}
المستخدم: وش عاصمة اليابان؟
عاصمة اليابان طوكيو.

لا تخترع أدوات أو أوامر غير الموجودة في القائمة."""

ChatFn = Callable[..., dict]


class LLM:
    def __init__(self, chat_fn: Optional[ChatFn] = None, model: str = cfg.OLLAMA_MODEL) -> None:
        if chat_fn is None:
            import ollama

            client = ollama.Client(timeout=cfg.LLM_TIMEOUT)
            chat_fn = client.chat
        self._chat = chat_fn
        self.model = model
        apps = "، ".join(sorted(cfg.APP_ALLOWLIST))
        self.system_prompt = SYSTEM_PROMPT.replace("{apps}", apps)
        self.history: Deque[Dict[str, str]] = collections.deque(maxlen=cfg.HISTORY_TURNS * 2)

    def messages_for(self, user_text: str) -> List[Dict[str, str]]:
        return [{"role": "system", "content": self.system_prompt},
                *self.history,
                {"role": "user", "content": user_text}]

    def ask(self, user_text: str) -> str:
        """Return the raw model reply (may contain <think> blocks)."""
        messages = self.messages_for(user_text)
        for attempt in range(1, cfg.LLM_MAX_RETRIES + 1):
            try:
                reply = self._chat(model=self.model, messages=messages)["message"]["content"]
                return reply
            except Exception as exc:  # noqa: BLE001 - network / model errors
                log.warning("Ollama attempt %d/%d failed: %s", attempt, cfg.LLM_MAX_RETRIES, exc)
                if attempt < cfg.LLM_MAX_RETRIES:
                    time.sleep(attempt)  # simple linear back-off
        return ""

    def remember(self, user_text: str, assistant_text: str) -> None:
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})
