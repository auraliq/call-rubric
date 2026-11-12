"""Optional LLM-judge hook. Interface only: this package never calls an API.

Implement ``Judge.judge`` with whatever client you use and pass the instance to
``combine``. The rule-based report stays the source of truth for hard flags;
the judge refines the soft judgment (tone, whether a "yes" was really a yes).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Protocol

CRITERIA = {
    "gatekeeper": "Did the agent give its name and firm once and end the call when a receptionist answered?",
    "forced_booking": "Was a booking made only after the person clearly accepted?",
    "interruption": "Did the agent yield and respond briefly when interrupted, without repeating itself?",
    "close_after_nos": "After two clear refusals, did the agent close politely instead of pitching again?",
    "tool_syntax": "Did the agent avoid reading code, tool names or timestamps aloud?",
}


@dataclass
class JudgeVerdict:
    scores: Dict[str, float] = field(default_factory=dict)  # criterion -> 0..1
    notes: str = ""


class Judge(Protocol):
    def judge(self, transcript: Dict[str, Any], report: Dict[str, Any]) -> JudgeVerdict: ...


class NullJudge:
    """Default: no opinion."""

    def judge(self, transcript, report) -> JudgeVerdict:
        return JudgeVerdict()


def build_judge_prompt(transcript: Dict[str, Any], report: Dict[str, Any]) -> str:
    """A ready-to-send prompt. You choose the model and the client."""
    lines = [f"{t['speaker'].upper()}: {t['text']}" for t in transcript["turns"]]
    crit = "\n".join(f"- {k}: {v}" for k, v in CRITERIA.items())
    return (
        "You grade a transcript of an outbound call made by an AI voice agent.\n"
        "Score each criterion from 0 (clear failure) to 1 (clear success); "
        "use null if it does not apply.\n"
        f"Criteria:\n{crit}\n\n"
        f"A rule-based grader already produced this report:\n{json.dumps(report['scores'])}\n"
        f"Flags: {json.dumps([f['code'] for f in report['flags']])}\n\n"
        "Transcript:\n" + "\n".join(lines) + "\n\n"
        'Answer with JSON only: {"scores": {"<criterion>": <0..1 or null>}, "notes": "<one sentence>"}'
    )


def combine(report: Dict[str, Any], verdict: JudgeVerdict, mode: str = "min",
            disagreement: float = 0.5) -> Dict[str, Any]:
    """Merge a judge verdict into a rule report (returns a new dict).

    mode "min": keep the lower score per criterion (a judge can only make the
    grade stricter). mode "mean": average. A gap above ``disagreement`` adds a
    ``judge_disagrees`` note so a human looks at it.
    """
    out = json.loads(json.dumps(report))
    out["judge_notes"] = verdict.notes
    out["judge_disagreements"] = []
    for k, jv in verdict.scores.items():
        rv = out["scores"].get(k)
        if jv is None or rv is None:
            continue
        if abs(jv - rv) > disagreement:
            out["judge_disagreements"].append(k)
        out["scores"][k] = min(rv, jv) if mode == "min" else round((rv + jv) / 2, 3)
    return out
