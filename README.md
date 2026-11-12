# call-rubric

A rule-based grader for transcripts of outbound AI voice-agent calls. Give it a JSON transcript, get back scores, flags and a pass/fail. Python 3.9+, no dependencies.

Español: califica transcripciones de llamadas en frío de agentes de voz (cinco revisiones: gatekeeper, cita forzada, interrupciones, cierre tras dos "no", sintaxis de herramientas leída en voz alta). Las 24 transcripciones de ejemplo son inventadas, en español e inglés.

## Why this exists

Reading transcripts by hand does not scale past a few dozen calls, and the failures that hurt are specific and repeatable. In real outbound campaigns the same five kept showing up: the agent chatted with a receptionist instead of hanging up; it booked a meeting after a hedge ("maybe, I'm busy") that was never a yes; it ignored or repeated itself after being interrupted; it kept pitching after two clear refusals; and it read tool calls out loud. Each one burns money or burns the contact. This grader turns them into code with explicit thresholds, so every call in a batch gets the same checks, and a human only reads the flagged ones. No real transcripts are included here: all 24 examples are synthetic.

## Use

```bash
python3 -B -m unittest discover -s tests
PYTHONPATH=src python3 -B -m call_rubric grade data/transcripts          # table
PYTHONPATH=src python3 -B -m call_rubric grade data/transcripts/es_forced_booking.json --json
PYTHONPATH=src python3 -B -m call_rubric grade data/transcripts --config config.example.json
```

The command exits with status 1 if any transcript fails, so it can gate a CI job.

Output (excerpt):

```
id                               overall  pass  flags
en_clean_booking                    1.00  yes   -
en_forced_booking                   0.50  NO    forced_booking
es_gatekeeper_booked                0.80  NO    gatekeeper_booking,gatekeeper_chat
es_two_nos_ignored                  0.71  NO    no_close_after_two_nos
es_tool_leak                        0.00  NO    tool_syntax_aloud
```

From Python:

```python
from call_rubric import grade
report = grade(transcript_dict)   # {"scores": {...}, "overall": 0.5, "flags": [...], "passed": False}
```

## Transcript format

```json
{
  "id": "example", "language": "en",
  "turns": [
    {"speaker": "agent", "text": "..."},
    {"speaker": "user",  "text": "...", "barge_in": true},
    {"speaker": "agent", "text": "...", "overlap_ms": 2600}
  ],
  "tool_calls": [{"name": "book_slot", "turn": 6}, {"name": "end_call", "turn": 8}]
}
```

`barge_in` (user spoke over the agent) and `overlap_ms` (agent kept talking over the user) are optional and usually come from your telephony or VAD events. `tool_calls` is optional; without it a booking is detected from agent phrases like "you're booked".

## The five checks

| Check | Raises | Rule (defaults in `config.example.json`) |
|---|---|---|
| Gatekeeper | `gatekeeper_chat`, `gatekeeper_booking` | After a receptionist or assistant answers, the agent may say its name and firm once and close. More than 1 non-closing agent turn is a warning; booking while the gatekeeper is on the line is critical. Ends when the target says they are on the phone. |
| Forced booking | `forced_booking` | A booking needs a clear yes (or a picked slot) in the last 2 user turns, and the last one must not be a hedge or a no. Critical. |
| Interruption | `ignored_interruption`, `talked_over`, `many_cuts` | After a barge-in the next agent turn must not repeat the previous one (word overlap at least 0.6) nor exceed 30 words. Overlap of 1,500 ms or more is talking over. Three cuts or more is flagged for review. |
| Close after two no's | `no_close_after_two_nos` | After the 2nd clear refusal (one turn = one refusal), every agent turn must be a closing. Critical. |
| Tool syntax aloud | `tool_syntax_aloud` | Agent text with snake_case names, braces, code fences or ISO dates. Critical. |

Each check gives a score from 0 to 1, or `null` when it does not apply (no booking, no gatekeeper). The overall score is the weighted mean of the applicable ones. A call passes if it has no critical flag and the overall is at least 0.7. Weights, thresholds and the list of critical flags are all in the config.

## Optional LLM judge

`call_rubric.judge` defines the interface only: `Judge.judge(transcript, report) -> JudgeVerdict`, `build_judge_prompt()` for a ready prompt, and `combine(report, verdict, mode="min"|"mean")`. In `min` mode a judge can only make a grade stricter, and a gap above 0.5 is listed under `judge_disagreements` for a human to look at. The package makes no API calls and the tests never use a network. See `examples/with_judge.py`.

## Limits

- Pattern-based. Spanish and English phrase lists live in `src/call_rubric/rubric.py`; other languages need their own patterns. A sarcastic "sure" counts as a yes; that is what the judge hook is for.
- Gatekeeper detection needs the receptionist to say something recognizable ("I'm his assistant", "who's calling"). A silent handoff is invisible.
- "One refusal = one user turn": "No, no, thanks" counts once.
- Thresholds were chosen for short cold calls; tune them against your own labeled calls before trusting a pass rate.
- The transcripts are invented and clean. Real speech-to-text is messier, expect more misses.

## License

MIT, see `LICENSE`. Author: Ricardo Delgado ([auraliq.io/ricardo](https://www.auraliq.io/ricardo), [LinkedIn](https://www.linkedin.com/in/ricardo-delgado-0626642a7)).
