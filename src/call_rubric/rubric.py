"""Rule-based grader for outbound voice-agent call transcripts.

Input transcript (JSON):

    {
      "id": "...", "language": "es" | "en",
      "turns": [
        {"speaker": "agent" | "user", "text": "...",
         "barge_in": true,        # user turn: the user spoke over the agent
         "overlap_ms": 1800},     # agent turn: agent kept talking over the user
      ],
      "tool_calls": [{"name": "book_slot", "turn": 7}, {"name": "end_call", "turn": 9}]
    }

Output: a report dict with per-criterion scores (None = not applicable),
flags, an overall score and a pass/fail verdict.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

DEFAULT_CONFIG: Dict[str, Any] = {
    "gatekeeper_max_pitch_turns": 1,
    "forced_booking_lookback_user_turns": 2,
    "max_words_after_barge_in": 30,
    "repeat_similarity": 0.6,
    "overlap_ms_limit": 1500,
    "many_cuts_threshold": 3,
    "nos_to_close": 2,
    "max_pitch_turns_after_nos": 0,
    "weights": {
        "gatekeeper": 1.0,
        "forced_booking": 2.0,
        "interruption": 1.0,
        "close_after_nos": 1.5,
        "tool_syntax": 2.0,
    },
    "critical_flags": [
        "forced_booking", "gatekeeper_booking",
        "no_close_after_two_nos", "tool_syntax_aloud",
    ],
    "min_overall": 0.7,
}


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if path:
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


# ------------------------------------------------------------------ patterns

def _rx(*parts: str) -> "re.Pattern[str]":
    return re.compile("|".join(parts), re.I)


GATEKEEPER = _rx(
    r"soy (?:la|el) (?:asistente|secretaria|recepcionista)",
    r"\b(?:la|su) (?:secretaria|asistente|recepcionista)\b",
    r"el (?:doctor|doctora|dr|dra)\.? no (?:est[aá]|se encuentra)",
    r"est[aá] en (?:consulta|cirug[ií]a|quir[oó]fano)",
    r"de parte de qui[eé]n",
    r"qui[eé]n (?:lo|la) busca",
    r"(?:puedo|puedo yo) (?:dar|tomar|dejar)(?:le)? (?:el |un )?recado",
    r"i(?:'| a)?m (?:his|her|the|dr\.?\s*\w+'s) (?:assistant|receptionist|secretary)",
    r"(?:he|she)(?:'s| is) (?:with a patient|not available|in surgery|in a procedure)",
    r"who(?:'s| is) (?:calling|this)",
    r"may i ask who",
    r"(?:can|may) i take a message",
)
TARGET_REACHED = _rx(
    r"(?:soy|habla|le habla) (?:el|la) (?:doctor|doctora|dr|dra)\b",
    r"\bsoy (?:yo|el m[eé]dico)\b",
    r"this is (?:dr|doctor)\b",
    r"\bspeaking\b",
    r"\byou(?:'ve| have) got (?:him|her)\b",
)
CLOSING = _rx(
    r"hasta luego", r"que tenga (?:un )?(?:excelente|buen|muy buen)",
    r"gracias por su tiempo", r"le dejo (?:mi nombre|el recado)", r"me despido",
    r"thank you for your time", r"goodbye", r"have a (?:great|good|nice) day",
    r"take care", r"i(?:'| wi)ll let you go",
)
YES = _rx(
    r"^\s*s[ií]\b", r"\bs[ií],? (?:claro|est[aá] bien|por favor|adelante)",
    r"\bclaro\b", r"\bde acuerdo\b", r"\bperfecto\b", r"\bva\b", r"\bokay?\b",
    r"\bme parece bien\b", r"\best[aá] bien\b",
    r"\byes\b", r"\bsure\b", r"\bsounds good\b", r"\bthat works\b", r"\bgo ahead\b",
    # picking a slot counts as accepting
    r"\bel (?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado) a las\b",
    r"\b(?:monday|tuesday|wednesday|thursday|friday) (?:at|works)\b",
)
HEDGE = _rx(
    r"\bno s[eé]\b", r"\btal vez\b", r"\bquiz[aá]s?\b", r"d[eé]jame pensarlo",
    r"d[eé]jeme pensarlo", r"estoy (?:muy )?ocupad[oa]", r"\bhmm+\b", r"\beh+m*\b\.{2,}",
    r"\bmaybe\b", r"not sure", r"i(?:'| a)?m busy", r"let me think", r"i guess",
)
NO = _rx(
    r"no,? gracias", r"no me interesa", r"no quiero", r"^\s*no[,.!]?\s*$",
    r"^\s*no[,.]\s", r"ahorita no", r"no tengo inter[eé]s", r"no me llamen",
    r"not interested", r"no,? thanks", r"no,? thank you", r"i(?:'| do)n(?:'|o)?t want",
    r"don(?:'| no)?t call", r"^\s*no[,.!]?\s*$",
)
BOOK_TOOL = re.compile(r"book|agend|reserv|schedul", re.I)
BOOKED_TEXT = _rx(
    r"qued[oó] (?:agendad[oa]|registrad[oa]|reservad[oa])", r"ya (?:agend[eé]|qued[oó])",
    r"you(?:'re| are) (?:all )?(?:booked|set)", r"i(?:'ve| have) booked", r"is booked",
)
END_TOOL = re.compile(r"end_call|hang", re.I)

# Tool syntax read aloud (agent turns only).
LEAK = _rx(
    r"\b[A-Za-z]+(?:_[A-Za-z0-9]+)+\b", r"[{}]", r"```",
    r"\b20\d{2}-\d{2}-?\d{2}", r"\b(?:function|tool_code|default_api)\b\s*[=:(]",
    r"\b[a-z]+[A-Z]\w*\(",
)

_WORD = re.compile(r"\w+", re.U)


def _words(s: str) -> List[str]:
    return _WORD.findall(s.lower())


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(_words(a)), set(_words(b))
    return len(sa & sb) / len(sa | sb) if sa and sb else 0.0


def classify_user(text: str) -> str:
    """'no' | 'hedge' | 'yes' | 'neutral'. Order matters: no > hedge > yes."""
    if NO.search(text):
        return "no"
    if HEDGE.search(text):
        return "hedge"
    if YES.search(text):
        return "yes"
    return "neutral"


# --------------------------------------------------------------------- checks

def _flag(code: str, turn: Optional[int], detail: str) -> Dict[str, Any]:
    return {"code": code, "turn": turn, "detail": detail}


def _booking_turn(t: Dict[str, Any]) -> Optional[int]:
    for c in t.get("tool_calls", []) or []:
        if BOOK_TOOL.search(c.get("name", "")):
            return c.get("turn")
    for i, turn in enumerate(t["turns"]):
        if turn["speaker"] == "agent" and BOOKED_TEXT.search(turn["text"]):
            return i
    return None


def _first_gatekeeper(turns: List[Dict[str, Any]]) -> Optional[int]:
    for i, turn in enumerate(turns):
        if turn["speaker"] == "user" and GATEKEEPER.search(turn["text"]):
            return i
    return None


def _target_reached_after(turns: List[Dict[str, Any]], start: int) -> Optional[int]:
    for i in range(start + 1, len(turns)):
        if turns[i]["speaker"] == "user" and TARGET_REACHED.search(turns[i]["text"]):
            return i
    return None


def check_gatekeeper(t, cfg, booking):
    turns = t["turns"]
    g = _first_gatekeeper(turns)
    if g is None:
        return None, []
    end = _target_reached_after(turns, g)
    window = range(g + 1, end if end is not None else len(turns))
    pitch = [i for i in window
             if turns[i]["speaker"] == "agent" and not CLOSING.search(turns[i]["text"])]
    flags: List[Dict[str, Any]] = []
    over = max(0, len(pitch) - cfg["gatekeeper_max_pitch_turns"])
    score = max(0.0, 1.0 - 0.34 * over)
    if over:
        flags.append(_flag("gatekeeper_chat", pitch[cfg["gatekeeper_max_pitch_turns"]],
                           f"{len(pitch)} non-closing agent turns with a gatekeeper (limit "
                           f"{cfg['gatekeeper_max_pitch_turns']})"))
    if booking is not None and booking > g and (end is None or booking < end):
        flags.append(_flag("gatekeeper_booking", booking, "booked while talking to a gatekeeper"))
        score = 0.0
    return score, flags


def check_forced_booking(t, cfg, booking):
    if booking is None:
        return None, []
    users = [(i, x) for i, x in enumerate(t["turns"][:booking + 1]) if x["speaker"] == "user"]
    recent = users[-cfg["forced_booking_lookback_user_turns"]:]
    classes = [classify_user(x["text"]) for _, x in recent]
    last = classes[-1] if classes else None
    if "yes" in classes and last in ("yes", "neutral"):
        return 1.0, []
    why = "no user turn before the booking" if not classes else \
        f"user turns before booking were {classes}; no clear yes"
    return 0.0, [_flag("forced_booking", booking, why)]


def check_interruption(t, cfg):
    turns = t["turns"]
    flags: List[Dict[str, Any]] = []
    cuts = 0
    ignored = talked = 0
    for i, turn in enumerate(turns):
        if turn["speaker"] == "agent" and turn.get("overlap_ms", 0) >= cfg["overlap_ms_limit"]:
            talked += 1
            flags.append(_flag("talked_over", i, f"agent overlapped the user for {turn['overlap_ms']} ms"))
        if turn["speaker"] == "user" and turn.get("barge_in"):
            cuts += 1
            prev = next((turns[j] for j in range(i - 1, -1, -1) if turns[j]["speaker"] == "agent"), None)
            nxt_i = next((j for j in range(i + 1, len(turns)) if turns[j]["speaker"] == "agent"), None)
            if nxt_i is None:
                continue
            nxt = turns[nxt_i]
            long_ = len(_words(nxt["text"])) > cfg["max_words_after_barge_in"]
            repeat = prev is not None and _jaccard(prev["text"], nxt["text"]) >= cfg["repeat_similarity"]
            if long_ or repeat:
                ignored += 1
                flags.append(_flag("ignored_interruption", nxt_i,
                                   "agent repeated itself after being interrupted" if repeat
                                   else "agent answered an interruption with a long monologue"))
    if cuts >= cfg["many_cuts_threshold"]:
        flags.append(_flag("many_cuts", None, f"agent was cut off {cuts} times"))
    if cuts == 0 and talked == 0:
        return None, flags
    score = max(0.0, 1.0 - 0.5 * ignored - 0.25 * talked - (0.2 if cuts >= cfg["many_cuts_threshold"] else 0))
    return score, flags


def check_close_after_nos(t, cfg):
    turns = t["turns"]
    nos = [i for i, x in enumerate(turns) if x["speaker"] == "user" and classify_user(x["text"]) == "no"]
    n = cfg["nos_to_close"]
    if len(nos) < n:
        return None, []
    after = nos[n - 1]
    ended = any(END_TOOL.search(c.get("name", "")) for c in t.get("tool_calls", []) or [])
    pitch = [i for i in range(after + 1, len(turns))
             if turns[i]["speaker"] == "agent" and not CLOSING.search(turns[i]["text"])]
    extra = len(pitch) - cfg["max_pitch_turns_after_nos"]
    if extra <= 0:
        return 1.0, []
    return max(0.0, 1.0 - 0.34 * extra), [_flag(
        "no_close_after_two_nos", pitch[0],
        f"{len(pitch)} non-closing agent turn(s) after the {n}th clear no"
        + (" (call ended later)" if ended else ""))]


def check_tool_syntax(t, cfg):
    flags = []
    for i, turn in enumerate(t["turns"]):
        if turn["speaker"] == "agent":
            m = LEAK.search(turn["text"])
            if m:
                flags.append(_flag("tool_syntax_aloud", i, f"agent text contains {m.group(0)!r}"))
    return (0.0 if flags else 1.0), flags


# ---------------------------------------------------------------------- grade

def grade(transcript: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or load_config()
    for i, x in enumerate(transcript["turns"]):
        if x.get("speaker") not in ("agent", "user") or "text" not in x:
            raise ValueError(f"turn {i}: needs speaker (agent|user) and text")
    booking = _booking_turn(transcript)
    scores: Dict[str, Optional[float]] = {}
    flags: List[Dict[str, Any]] = []
    for name, (s, f) in {
        "gatekeeper": check_gatekeeper(transcript, cfg, booking),
        "forced_booking": check_forced_booking(transcript, cfg, booking),
        "interruption": check_interruption(transcript, cfg),
        "close_after_nos": check_close_after_nos(transcript, cfg),
        "tool_syntax": check_tool_syntax(transcript, cfg),
    }.items():
        scores[name] = s
        flags += f
    w = cfg["weights"]
    applicable = {k: v for k, v in scores.items() if v is not None}
    total = sum(w[k] for k in applicable)
    overall = round(sum(w[k] * v for k, v in applicable.items()) / total, 3) if total else 1.0
    critical = sorted({f["code"] for f in flags if f["code"] in cfg["critical_flags"]})
    return {
        "id": transcript.get("id"),
        "scores": scores,
        "overall": overall,
        "flags": flags,
        "critical": critical,
        "passed": not critical and overall >= cfg["min_overall"],
    }
