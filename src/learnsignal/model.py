"""Exact finite-state Bayesian decision analysis with explicit study likelihoods.

Every calculation is polynomial in the table size (options x scenarios x study results), so there is no size limit
locally; a public demo caps record counts through limits.py.
"""
from collections import defaultdict

import numpy as np
import pandas as pd

from learnsignal import limits, portable as io

REF = {"anyOf": [io.ID, {"type": "null"}]}
STATE = io.obj({"id": io.ID, "label": io.text(150), "probability": io.number(0, 1, True), "note": io.text(1000, True), "source_id": REF})
ACTION = io.obj({"id": io.ID, "label": io.text(150)})
PAYOFF = io.obj({"action_id": io.ID, "state_id": io.ID, "value": io.number(-1e12, 1e12, True), "note": io.text(1000, True), "source_id": REF})
STUDY = io.obj({"id": io.ID, "label": io.text(150), "cost": io.number(0, 1e12, True), "description": io.text(1000), "source_id": REF})
SIGNAL = io.obj({"study_id": io.ID, "state_id": io.ID, "outcome": io.text(100), "probability": io.number(0, 1, True)})
QUESTION = io.obj({"id": io.ID, "label": io.text(250)})
PARTITION = io.obj({"question_id": io.ID, "state_id": io.ID, "answer": io.text(150)})
SCHEMA = io.obj({"schema_version": {"const": "1.0"}, "brief": io.text(2500),
                 "context": io.array(io.obj({"unit": io.text(50), "horizon": io.text(200)}), 1, 1),
                 "states": io.array(STATE, minimum=2), "actions": io.array(ACTION, minimum=2), "payoffs": io.array(PAYOFF),
                 "studies": io.array(STUDY), "signals": io.array(SIGNAL),
                 "questions": io.array(QUESTION), "partitions": io.array(PARTITION), "sources": io.array(io.SOURCE)})
DEMO_COUNTS = {"states": "Future scenarios", "actions": "Decision options", "payoffs": "Payoffs", "studies": "Research studies",
               "signals": "Study results", "questions": "Questions", "partitions": "Answers", "sources": "Sources"}
TITLES = {"context": "One common payoff unit and horizon · higher payoff is better",
          "states": "Mutually exclusive, exhaustive future states · probabilities must sum to one",
          "actions": "Available decisions · include a feasible fallback",
          "payoffs": "Payoff for each decision in each state · same unit, net of action costs",
          "studies": "Candidate studies · cost in the same unit as payoffs",
          "signals": "Study likelihoods · P(result | true state), not P(state | result)",
          "questions": "Uncertainties we could learn perfectly", "partitions": "The answer to each uncertainty in every state",
          "sources": "Evidence or justification for inputs"}
REFERENCES = [("Howard (1966). Information value theory.", "https://doi.org/10.1109/TSSC.1966.300074"),
              ("Canessa et al. (2015). When do we need more data? A primer on calculating the value of information for applied ecologists.",
               "https://doi.org/10.1111/2041-210X.12423"),
              ("Runge et al. (2023). A Simplified Method for Value of Information Using Constructed Scales.",
               "https://doi.org/10.1287/deca.2023.0474")]
METHOD = ("For each action a, expected payoff is Σs p(s)u(a,s). Current value is the largest expected payoff. "
          "Perfect-information value is Σs p(s)max_a u(a,s); EVPI is its improvement over current value. "
          "For a study with conditional result likelihoods L(y|s), value with information is Σy max_a Σs p(s)L(y|s)u(a,s). "
          "EVSI subtracts current value; net research value also subtracts study cost. Posterior probabilities use Bayes' rule. "
          "A question's value is the expected improvement if its partition of the state space were learned perfectly. "
          "These are exact finite-table calculations. Runge et al. motivates early research framing; this app implements expected-value calculations, not their constructed-scale method.")
LIMITS = ["Probabilities, payoffs and study likelihoods are supplied assumptions or estimates. The app does not estimate them from the AI's confidence or validate them as facts.",
          "States must cover the possibilities relevant to this decision without overlap. A state can encode several correlated uncertainties jointly.",
          "Higher payoff is always preferred. Monetary calculations assume risk-neutral expected value. With utility units, research costs must also be expressed consistently in utility units.",
          "EVPI is an upper bound on information value under this model. A specific study normally resolves only part of the uncertainty.",
          "Each study is evaluated alone, before the decision. Net values cannot be added across studies; sequential testing, delays and study-induced outcome changes are not modeled.",
          "Perfect answers to different questions can overlap in value. Their values are not additive or automatic research budgets.",
          "Learn prioritizes evidence collection. Experiment Signal analyzes experiment outcomes; Gate Signal handles the broader investment decision."]
AI_RULES = ("Build a finite decision model only from the information supplied. States must be mutually exclusive and exhaustive. "
            "Unknown prior probabilities, payoffs, study costs and result likelihoods MUST be null. Do not fabricate them or replace them with 1–5 ratings. "
            "Payoffs are net outcomes including action costs, excluding research cost; larger is better and all entries use one unit and horizon. "
            "Propose studies with explicit possible results. A signal probability means P(result | state), never the reverse. "
            "Keep all result labels consistent within a study and include a row for every state × result. Include all action × state payoff rows. "
            "Questions and partitions describe what a perfectly observed uncertainty would reveal about the states. Give every question an answer in every state.")
REVIEW_GUIDANCE = "Check state coverage, probability totals, the payoff unit and horizon, net action costs, and the evidence behind each study's conditional likelihoods. Keep unsupported values unknown."


def probability_total(values, label):
    known = sum(v for v in values if v is not None)
    if known > 1 + 1e-9 or (all(v is not None for v in values) and abs(known - 1) > 1e-9):
        raise io.DataProblem(label + " must sum to 1. No automatic renormalization is applied.")


def validate(data):
    if isinstance(data, dict):
        for kind, title in DEMO_COUNTS.items():
            if isinstance(data.get(kind), list):
                limits.check(kind, len(data[kind]), f"{title} has too many rows")
    d = io.validate_schema(data, SCHEMA)
    states, actions, studies, questions, sources = [io.unique(d[k]) for k in ["states", "actions", "studies", "questions", "sources"]]
    probability_total([s["probability"] for s in d["states"]], "State probabilities")
    for kind in ["states", "payoffs", "studies"]:
        for row in d[kind]:
            if row["source_id"] and row["source_id"] not in sources:
                raise io.DataProblem("An input refers to a missing source.")
    for kind, fields, maps in [("payoffs", ["action_id", "state_id"], [actions, states]),
                               ("signals", ["study_id", "state_id", "outcome"], [studies, states, None]),
                               ("partitions", ["question_id", "state_id"], [questions, states])]:
        seen = set()
        for row in d[kind]:
            key = tuple(row[f] for f in fields)
            if key in seen or any(m is not None and row[f] not in m for f, m in zip(fields, maps)):
                raise io.DataProblem(f"{kind}: duplicate combination or missing referenced record.")
            seen.add(key)
    outcomes, cells = defaultdict(set), defaultdict(list)
    for r in d["signals"]:
        outcomes[r["study_id"]].add(r["outcome"])
        cells[(r["study_id"], r["state_id"])].append(r["probability"])
    for study in d["studies"]:
        limits.check("results_per_study", len(outcomes[study["id"]]), f"{study['id']} has too many possible results")
        for state in states:
            values = cells.get((study["id"], state))
            if values:
                values = values + [None] * (len(outcomes[study["id"]]) - len(values))
                probability_total(values, f"Likelihoods for {study['id']} in state {state}")
    return d


def starter(brief):
    states = [{"id": "S1", "label": "Higher demand", "probability": None, "note": "Define your actual state space.", "source_id": None},
              {"id": "S2", "label": "Lower demand", "probability": None, "note": "Define your actual state space.", "source_id": None}]
    actions = [{"id": "A1", "label": "Proceed"}, {"id": "A2", "label": "Hold"}]
    return {"schema_version": "1.0", "brief": brief, "context": [{"unit": "NOK", "horizon": "Specify a common outcome horizon"}],
            "states": states, "actions": actions, "payoffs": [{"action_id": a["id"], "state_id": s["id"], "value": None, "note": "", "source_id": None} for a in actions for s in states],
            "studies": [], "signals": [], "questions": [], "partitions": [], "sources": []}


def demo():
    d = starter("FICTIONAL DEMO: decide whether to launch a restaurant lunch service, pilot it, or hold; compare research before committing.")
    d["context"] = [{"unit": "NOK", "horizon": "Incremental contribution over the next 12 months"}]
    d["sources"] = [{"id": "N1", "title": "Fictional planning assumptions", "url": None, "note": "Invented numerical teaching example; no actual demand or study data."}]
    d["states"][0].update(probability=0.4, source_id="N1", note="Illustrative prior")
    d["states"][1].update(probability=0.6, source_id="N1", note="Illustrative prior")
    d["actions"] = [{"id": "A1", "label": "Full launch"}, {"id": "A2", "label": "Small pilot"}, {"id": "A3", "label": "Hold"}]
    vals = [[140000, -60000], [50000, -10000], [0, 0]]
    d["payoffs"] = [{"action_id": a["id"], "state_id": s["id"], "value": vals[i][j], "note": "Assumed contribution net of action costs.", "source_id": "N1"} for i,a in enumerate(d["actions"]) for j,s in enumerate(d["states"])]
    d["studies"] = [{"id": "T1", "label": "Structured demand test", "cost": 8000, "description": "Illustrative informative test; sensitivity and specificity both assumed to be 80%.", "source_id": "N1"},
                    {"id": "T2", "label": "Small exploratory survey", "cost": 3000, "description": "Illustrative weak test; sensitivity and specificity assumed to be 55%.", "source_id": "N1"}]
    d["signals"] = [{"study_id": tid, "state_id": state, "outcome": result, "probability": p} for tid, high in [("T1",.8),("T2",.55)] for state, positive in [("S1",high),("S2",1-high)] for result,p in [("positive",positive),("negative",1-positive)]]
    d["questions"] = [{"id": "Q1", "label": "Would demand be higher or lower?"}]
    d["partitions"] = [{"question_id": "Q1", "state_id": s["id"], "answer": s["label"]} for s in d["states"]]
    return io.accept(io.project("learn", validate(d), "FICTIONAL DEMO — assumed probabilities, payoffs and study accuracy"), "Fictional reviewer", "Verified example arithmetic, not empirical assumptions.")


def readiness(d):
    missing = []
    for state in d["states"]:
        if state["probability"] is None:
            missing.append("Prior probability for " + state["id"])
    payoffs = {(p["action_id"], p["state_id"]): p["value"] for p in d["payoffs"]}
    for a in d["actions"]:
        for s in d["states"]:
            if payoffs.get((a["id"], s["id"])) is None:
                missing.append("Payoff for " + a["id"] + " / " + s["id"])
    return missing


def analyze(d):
    d = validate(d)
    missing = readiness(d)
    if missing:
        raise io.DataProblem("Complete these inputs before calculating: " + "; ".join(missing[:12]))
    states, actions = d["states"], d["actions"]
    prior = np.array([s["probability"] for s in states])
    pay = {(x["action_id"],x["state_id"]):x["value"] for x in d["payoffs"]}
    utility = np.array([[pay[(a["id"],s["id"])] for s in states] for a in actions], dtype=float)
    ev = utility @ prior
    current, perfect = float(ev.max()), float(utility.max(axis=0) @ prior)
    tol = max(1e-8, np.abs(utility).max() * 1e-12)
    def best(values):
        top = float(np.max(values))
        return " / ".join(a["label"] for a, v in zip(actions, values) if abs(v - top) <= tol)
    action_table = pd.DataFrame([{"action": a["label"], "expected_payoff": float(ev[i]), "expected_opportunity_loss": max(0.0, perfect-float(ev[i]))} for i,a in enumerate(actions)])
    studies, policies, posteriors = [], [], []
    by_study = defaultdict(list)
    for r in d["signals"]:
        by_study[r["study_id"]].append(r)
    for study in d["studies"]:
        rows = by_study[study["id"]]
        outcomes = sorted({r["outcome"] for r in rows})
        lookup = {(r["state_id"], r["outcome"]): r["probability"] for r in rows}
        complete = bool(outcomes) and all(lookup.get((s["id"],o)) is not None for s in states for o in outcomes)
        if not complete or study["cost"] is None:
            studies.append({"study": study["label"], "status": "Missing likelihoods or cost", "evsi": None, "cost": study["cost"], "net_value": None})
            continue
        likelihood = np.array([[lookup[(s["id"], o)] for s in states] for o in outcomes])  # results x states
        joint = likelihood * prior                                                          # p(s) L(y|s)
        probability = joint.sum(axis=1)
        weighted = joint @ utility.T                                                        # results x actions
        informed = float(weighted.max(axis=1).sum())
        for i, outcome in enumerate(outcomes):
            p_y = float(probability[i])
            policies.append({"study": study["label"], "result": outcome, "result_probability": p_y,
                             "preferred_action": best(weighted[i] / p_y) if p_y > 0 else "Impossible under this model",
                             "conditional_payoff": float(weighted[i].max()/p_y) if p_y > 0 else None})
            for s, mass in zip(states, joint[i]):
                posteriors.append({"study": study["label"], "result": outcome, "state": s["label"], "posterior_probability": float(mass/p_y) if p_y > 0 else None})
        evsi = max(0.0, informed-current)
        studies.append({"study": study["label"], "status": "Complete", "evsi": evsi, "cost": study["cost"], "net_value": evsi-study["cost"]})
    questions = []
    by_question = defaultdict(dict)
    for r in d["partitions"]:
        by_question[r["question_id"]][r["state_id"]] = r["answer"]
    weighted_states = utility * prior                                                       # actions x states
    for question in d["questions"]:
        answers = by_question[question["id"]]
        if set(answers) != {s["id"] for s in states}:
            questions.append({"question": question["label"], "perfect_answer_value": None, "status": "Answer missing for a state"})
            continue
        codes = pd.factorize(pd.Series([answers[s["id"]] for s in states]))[0]
        grouped = np.zeros((utility.shape[0], codes.max() + 1))
        np.add.at(grouped.T, codes, weighted_states.T)                                      # sum the states sharing an answer
        value = float(grouped.max(axis=0).sum())
        questions.append({"question": question["label"], "perfect_answer_value": max(0.0,value-current), "status": "Complete"})
    return {"current_value": current, "perfect_value": perfect, "evpi": max(0.0,perfect-current), "preferred": best(ev),
            "actions": action_table, "studies": pd.DataFrame(studies, columns=["study","status","evsi","cost","net_value"]),
            "policies": pd.DataFrame(policies, columns=["study","result","result_probability","preferred_action","conditional_payoff"]),
            "posteriors": pd.DataFrame(posteriors, columns=["study","result","state","posterior_probability"]),
            "questions": pd.DataFrame(questions, columns=["question","perfect_answer_value","status"])}


def sensitivity(d, state_id):
    """Vary one prior from 0 to 1 on a 0.025 grid; the other states keep their relative probabilities."""
    d = validate(d)
    original = next(s["probability"] for s in d["states"] if s["id"] == state_id)
    if original is None or original >= 1:
        raise io.DataProblem("Sensitivity needs a selected state below probability 1 and a defined distribution across the other states.")
    missing = readiness(d)
    if missing:
        raise io.DataProblem("Complete these inputs before calculating: " + "; ".join(missing[:12]))
    states, actions = d["states"], d["actions"]
    pay = {(x["action_id"], x["state_id"]): x["value"] for x in d["payoffs"]}
    utility = np.array([[pay[(a["id"], s["id"])] for s in states] for a in actions], dtype=float)
    base = np.array([s["probability"] for s in states], dtype=float)
    selected = np.array([s["id"] == state_id for s in states])
    tol = max(1e-8, np.abs(utility).max() * 1e-12)
    rows = []
    for probability in np.linspace(0, 1, 41):
        prior = np.where(selected, probability, base / (1 - original) * (1 - probability))
        ev = utility @ prior
        current = float(ev.max())
        preferred = " / ".join(a["label"] for a, v in zip(actions, ev) if abs(v - current) <= tol)
        rows.append({"state_probability": probability, "current_value": current,
                     "evpi": max(0.0, float(utility.max(axis=0) @ prior) - current), "preferred_action": preferred})
    return pd.DataFrame(rows)


def printable(p):
    sections = [("Inputs", pd.DataFrame(p["data"]["states"])), ("Payoff table", pd.DataFrame(p["data"]["payoffs"]))]
    sections += [("Study designs", pd.DataFrame(p["data"]["studies"])), ("Assumed conditional likelihoods", pd.DataFrame(p["data"]["signals"]))]
    if io.reviewed(p) and not readiness(p["data"]):
        result = analyze(p["data"])
        sections += [("Decision value", pd.DataFrame([{k:v for k,v in result.items() if not isinstance(v,pd.DataFrame)}]))]
        sections += [(k.title(), v) for k,v in result.items() if isinstance(v,pd.DataFrame)]
    else:
        sections.append(("Calculation status", "<p>Review the draft and complete missing model inputs before calculating.</p>"))
    return io.report("Learn Signal · research decision brief", p, sections, REFERENCES, LIMITS)
