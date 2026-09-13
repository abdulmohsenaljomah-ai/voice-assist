"""Safe command execution for the Marco voice assistant.

Commands emitted by the LLM are classified into three risk levels:

  SAFE            – executed immediately without prompting the user.
  CONFIRM_REQUIRED – the assistant asks the user to say "نعم" before running.
  FORBIDDEN        – never executed; the assistant says it's not allowed.

Security model: **shell=True is never used.**  All commands are parsed
with ``shlex.split()`` and executed with ``shell=False``, so shell
metacharacters such as ``&``, ``|``, ``>``, ``<``, ``&&``, ``||`` and
command chaining cannot be exploited to inject additional commands.
"""

import shlex
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from config import FORBIDDEN_PATTERNS, CONFIRMATION_REQUIRED_PATTERNS


# Shell metacharacters that must never appear in an otherwise-safe command.
# If any of these are present the command is rejected outright.
SHELL_METACHARACTERS = ("&", "|", ">", "<", ";", "`", "$", "(", ")", "{", "}")


class RiskLevel(Enum):
    SAFE = "safe"
    CONFIRM_REQUIRED = "confirm_required"
    FORBIDDEN = "forbidden"
    INVALID = "invalid"          # malformed / injection attempt


@dataclass
class ExecutionResult:
    """Outcome of attempting to run a command."""
    risk: RiskLevel
    executed: bool
    message: str


def _classify(cmd: str) -> RiskLevel:
    """Return the risk level for *cmd* (checked lowercased)."""
    lowered = cmd.lower()

    for pat in FORBIDDEN_PATTERNS:
        if pat in lowered:
            return RiskLevel.FORBIDDEN

    for pat in CONFIRMATION_REQUIRED_PATTERNS:
        if pat in lowered:
            return RiskLevel.CONFIRM_REQUIRED

    return RiskLevel.SAFE


def _contains_metacharacters(cmd: str) -> bool:
    """Return True if *cmd* contains any shell metacharacter."""
    return any(ch in cmd for ch in SHELL_METACHARACTERS)


def _sanitize(cmd: str) -> Optional[List[str]]:
    """Split *cmd* into args for ``subprocess.run`` (no shell).

    Returns ``None`` if the command contains shell metacharacters or
    cannot be cleanly parsed by ``shlex.split``.
    """
    if _contains_metacharacters(cmd):
        return None

    try:
        return shlex.split(cmd)
    except ValueError:
        return None


def execute(cmd: str, skip_confirmation: bool = False) -> ExecutionResult:
    """Execute *cmd* respecting safety rules.

    Parameters
    ----------
    cmd :
        Raw command string from the LLM (without the leading ``CMD:``).
    skip_confirmation :
        Internally set to ``True`` when the user has already confirmed.
    """
    # Reject anything that looks like an injection attempt first.
    if _contains_metacharacters(cmd):
        return ExecutionResult(
            risk=RiskLevel.INVALID,
            executed=False,
            message="تم رفض الأمر بسبب أحرف غير مسموح بها.",
        )

    risk = _classify(cmd)

    if risk == RiskLevel.FORBIDDEN:
        return ExecutionResult(
            risk=risk,
            executed=False,
            message="هذا الأمر محظور ولا يمكن تنفيذه.",
        )

    if risk == RiskLevel.CONFIRM_REQUIRED and not skip_confirmation:
        # The caller (agent.py) will ask for voice confirmation;
        # this function returns *without executing* and signals
        # the caller to re-invoke with ``skip_confirmation=True``.
        return ExecutionResult(
            risk=risk,
            executed=False,
            message="تأكيد مطلوب: هل أنت متأكد؟",
        )

    # ---- Actually run the command ----
    # shell=False everywhere — no exceptions.  The LLM output is parsed
    # into a list of arguments via shlex, and any metacharacters were
    # already rejected above.
    args = _sanitize(cmd)
    if args is None:
        return ExecutionResult(
            risk=RiskLevel.INVALID,
            executed=False,
            message="تم رفض الأمر بسبب صيغة غير صالحة.",
        )

    try:
        subprocess.Popen(args, shell=False)

        return ExecutionResult(
            risk=risk,
            executed=True,
            message="تم التنفيذ.",
        )

    except FileNotFoundError:
        return ExecutionResult(
            risk=risk,
            executed=False,
            message="الأمر غير موجود على الجهاز.",
        )
    except OSError:
        return ExecutionResult(
            risk=risk,
            executed=False,
            message="خطأ في تشغيل الأمر.",
        )
    except Exception:
        return ExecutionResult(
            risk=risk,
            executed=False,
            message="ما قدرت أطّلع الأمر.",
        )
