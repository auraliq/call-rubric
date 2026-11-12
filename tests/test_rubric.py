import json
import unittest

import _path  # noqa: F401
from call_rubric import (NullJudge, JudgeVerdict, build_judge_prompt, combine,
                         grade, load_config)
from call_rubric.rubric import classify_user

DIR = _path.ROOT / "data" / "transcripts"
DOCS = [json.loads(p.read_text("utf-8")) for p in sorted(DIR.glob("*.json"))]


def codes(report):
    return sorted({f["code"] for f in report["flags"]})


class Corpus(unittest.TestCase):
    def test_corpus_size_and_languages(self):
        self.assertGreaterEqual(len(DOCS), 15)
        self.assertEqual({d["language"] for d in DOCS}, {"es", "en"})

    def test_each_transcript_raises_exactly_the_expected_flags(self):
        for d in DOCS:
            self.assertEqual(codes(grade(d)), d["expect"]["flags"], d["id"])

    def test_pass_fail(self):
        for d in DOCS:
            r = grade(d)
            has_critical = any(c in load_config()["critical_flags"] for c in d["expect"]["flags"])
            if has_critical:
                self.assertFalse(r["passed"], d["id"])
            if not d["expect"]["flags"]:
                self.assertTrue(r["passed"], d["id"])
                self.assertEqual(r["overall"], 1.0, d["id"])

    def test_every_check_is_exercised_both_ways(self):
        seen = set()
        for d in DOCS:
            seen |= set(codes(grade(d)))
        self.assertEqual(seen, {
            "gatekeeper_chat", "gatekeeper_booking", "forced_booking",
            "ignored_interruption", "talked_over", "many_cuts",
            "no_close_after_two_nos", "tool_syntax_aloud"})


class Units(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify_user("No, gracias"), "no")
        self.assertEqual(classify_user("No sé, tal vez"), "hedge")
        self.assertEqual(classify_user("Sí, claro"), "yes")
        self.assertEqual(classify_user("El jueves a las 4"), "yes")
        self.assertEqual(classify_user("Not interested"), "no")
        self.assertEqual(classify_user("Maybe, I'm busy"), "hedge")
        self.assertEqual(classify_user("Dígame"), "neutral")

    def test_not_applicable_is_none_and_excluded(self):
        r = grade({"turns": [{"speaker": "agent", "text": "Hola, buenas tardes."},
                             {"speaker": "user", "text": "Dígame."}]})
        self.assertIsNone(r["scores"]["gatekeeper"])
        self.assertEqual(r["scores"]["tool_syntax"], 1.0)
        self.assertEqual(r["overall"], 1.0)

    def test_config_override_changes_threshold(self):
        d = next(x for x in DOCS if x["id"] == "es_many_cuts")
        cfg = load_config()
        cfg["many_cuts_threshold"] = 4
        self.assertNotIn("many_cuts", codes(grade(d, cfg)))

    def test_bad_turn_rejected(self):
        with self.assertRaises(ValueError):
            grade({"turns": [{"speaker": "bot", "text": "x"}]})

    def test_load_config_example_file(self):
        cfg = load_config(str(_path.ROOT / "config.example.json"))
        self.assertEqual(cfg["nos_to_close"], 2)


class JudgeHook(unittest.TestCase):
    class Fake:
        def judge(self, transcript, report):
            return JudgeVerdict({"forced_booking": 0.0, "interruption": None}, "fake")

    def test_prompt_contains_transcript_and_no_network(self):
        d = DOCS[0]
        p = build_judge_prompt(d, grade(d))
        self.assertIn("Transcript:", p)
        self.assertIn(d["turns"][0]["text"], p)

    def test_combine_min_and_disagreement(self):
        d = next(x for x in DOCS if x["id"] == "es_clean_booking")
        rep = grade(d)
        out = combine(rep, self.Fake().judge(d, rep))
        self.assertEqual(out["scores"]["forced_booking"], 0.0)
        self.assertEqual(out["judge_disagreements"], ["forced_booking"])
        self.assertEqual(rep["scores"]["forced_booking"], 1.0)  # input untouched

    def test_null_judge(self):
        d = DOCS[0]
        rep = grade(d)
        self.assertEqual(combine(rep, NullJudge().judge(d, rep))["scores"], rep["scores"])


if __name__ == "__main__":
    unittest.main()
