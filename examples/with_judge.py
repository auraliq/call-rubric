"""Shows where an LLM judge plugs in. Run: python3 examples/with_judge.py

The judge here is a stub; replace ``judge`` with a call to your own model client,
parse its JSON answer into a JudgeVerdict. This repo never makes network calls.
"""
import json
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))
from call_rubric import JudgeVerdict, build_judge_prompt, combine, grade  # noqa: E402


class StubJudge:
    def judge(self, transcript, report):
        prompt = build_judge_prompt(transcript, report)  # send this to your model
        _ = prompt
        return JudgeVerdict({"forced_booking": 0.2}, "stub: the 'yes' sounded reluctant")


doc = json.loads((root / "data/transcripts/es_hedge_then_yes.json").read_text("utf-8"))
rule = grade(doc)
final = combine(rule, StubJudge().judge(doc, rule), mode="min")
print("rules:", rule["scores"]["forced_booking"], "| after judge:", final["scores"]["forced_booking"])
print("disagreements:", final["judge_disagreements"])
