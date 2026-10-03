"""Friendly decision/outcome spreadsheet layout."""
from . import model, portable as io

TABLE_NAMES = {"context": "Scope", "states": "Future scenarios", "actions": "Decision options", "payoffs": "Payoffs", "studies": "Research studies", "signals": "Study results", "questions": "Questions", "partitions": "Answers", "sources": "Sources"}
LABELS = {"label": "Name", "probability": "Probability (0 to 1)", "value": "Net payoff", "action_id": "Decision reference", "state_id": "Scenario reference", "study_id": "Study reference", "question_id": "Question reference", "outcome": "Study result", "cost": "Research cost", "horizon": "Time horizon", "unit": "Payoff unit"}
INTRO = "Start with your decision options and possible future scenarios. Enter the payoff for every option in every scenario, using the same unit and time period."
QUICK = {"decisions": {"title": "Decision outcomes", "aliases": ["decisions", "payoffs", "outcomes", "decision table"], "fields": {
    "decision": ("Decision option", "text", ["decision", "action", "option", "alternative"]),
    "scenario": ("Future scenario", "text", ["scenario", "state", "outcome"]),
    "probability": ("Scenario probability", "optional_probability", ["probability", "chance", "likelihood", "prior"]),
    "payoff": ("Net payoff", "optional_number", ["payoff", "value", "profit", "contribution"]),
    "note": ("Assumption or evidence note", "optional_text", ["note", "notes", "evidence"]),
}}}
HELP = "Repeat each future scenario for every decision option. Its probability must agree across rows; the probabilities of the distinct scenarios must total 1. Use 0.4 or 40%, not 40. Leave unknown values blank. Research study costs and possible test results can be added in Edit & review or the complete workbook."
EXAMPLES = {"decisions": [
    {"decision": a, "scenario": s, "probability": p, "payoff": v, "note": "Fictional planning assumption"}
    for a, high, low in [("Launch", 140000, -60000), ("Pilot", 50000, -10000), ("Hold", 0, 0)]
    for s, p, v in [("Higher demand", .4, high), ("Lower demand", .6, low)]
]}


def build(brief, tables, settings, source):
    d = model.starter(brief)
    rows = tables["decisions"]
    actions = list(dict.fromkeys(r["decision"] for r in rows))
    states = list(dict.fromkeys(r["scenario"] for r in rows))
    aids = {s: f"A{i}" for i, s in enumerate(actions, 1)}
    sids = {s: f"S{i}" for i, s in enumerate(states, 1)}
    d["context"] = [{"unit": settings["unit"], "horizon": settings["horizon"]}]
    d["sources"] = [{"id": "FILE1", "title": source[:300], "url": None, "note": "User-supplied decision table. Probabilities and payoffs are assumptions or estimates to review."}]
    d["actions"] = [{"id": aids[s], "label": s} for s in actions]
    d["states"] = []
    for label in states:
        values = [r["probability"] for r in rows if r["scenario"] == label and r["probability"] is not None]
        if values and max(values) - min(values) > 1e-9:
            raise io.DataProblem(f"The scenario '{label}' has different probabilities in different rows. Use one probability for that scenario.")
        d["states"].append({"id": sids[label], "label": label, "probability": values[0] if values else None, "source_id": "FILE1", "note": "Probability supplied in the decision table."})
    d["payoffs"] = [{"action_id": aids[r["decision"]], "state_id": sids[r["scenario"]], "value": r["payoff"], "note": r["note"], "source_id": "FILE1"} for r in rows]
    if len(actions) < 2 or len(states) < 2:
        raise io.DataProblem("Include at least two decision options and two possible future scenarios.")
    return model.validate(d)
