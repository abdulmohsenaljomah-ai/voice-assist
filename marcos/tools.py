"""Allowlisted tools the assistant may use.

Security model: the LLM never produces shell commands. It can only
request one of the tools below by name; each tool validates its own
arguments and anything unknown is refused. There is no code path that
passes model output to a shell.
"""

from __future__ import annotations

import datetime as _dt
import os
import urllib.parse
from dataclasses import dataclass
from typing import Callable, Dict

import config as cfg
from marcos.text import normalize_arabic

# The opener is injectable so tests can verify behaviour without
# launching anything. On Windows ``os.startfile`` opens executables,
# URLs and ms-settings: URIs without a shell.
Opener = Callable[[str], None]


def _default_opener(target: str) -> None:
    os.startfile(target)  # type: ignore[attr-defined]  # Windows only


@dataclass
class ToolResult:
    ok: bool
    message: str  # spoken back to the user (Arabic)


_ARABIC_DAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


class Toolbox:
    def __init__(self, opener: Opener | None = None, now: Callable[[], _dt.datetime] | None = None):
        self._open = opener or _default_opener
        self._now = now or _dt.datetime.now
        self._apps = {normalize_arabic(k): v for k, v in cfg.APP_ALLOWLIST.items()}
        self._tools: Dict[str, Callable[..., ToolResult]] = {
            "open_app": self.open_app,
            "open_url": self.open_url,
            "web_search": self.web_search,
            "get_time": self.get_time,
            "get_date": self.get_date,
        }

    # -- registry -------------------------------------------------------
    @property
    def names(self) -> list[str]:
        return sorted(self._tools)

    def run(self, name: str, args: dict) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(False, "هذه الأداة غير متاحة.")
        try:
            return tool(**args)
        except TypeError:
            return ToolResult(False, "طلب الأداة غير مكتمل.")
        except OSError:
            return ToolResult(False, "ما قدرت أنفذ الطلب على الجهاز.")

    # -- tools ----------------------------------------------------------
    def open_app(self, name: str = "") -> ToolResult:
        target = self._apps.get(normalize_arabic(name))
        if target is None:
            return ToolResult(False, "هذا البرنامج غير موجود في القائمة المسموحة.")
        self._open(target)
        return ToolResult(True, "تم فتح البرنامج.")

    def open_url(self, url: str = "") -> ToolResult:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return ToolResult(False, "الرابط غير صالح.")
        self._open(parsed.geturl())
        return ToolResult(True, "تم فتح الرابط.")

    def web_search(self, query: str = "") -> ToolResult:
        query = query.strip()
        if not query:
            return ToolResult(False, "وش تبي أبحث عنه؟")
        self._open(cfg.SEARCH_URL.format(query=urllib.parse.quote_plus(query)))
        return ToolResult(True, f"هذي نتائج البحث عن {query}.")

    def get_time(self) -> ToolResult:
        now = self._now()
        return ToolResult(True, f"الساعة الآن {now:%H:%M}.")

    def get_date(self) -> ToolResult:
        now = self._now()
        return ToolResult(True, f"اليوم {_ARABIC_DAYS[now.weekday()]} {now:%Y-%m-%d}.")
