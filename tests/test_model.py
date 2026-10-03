from copy import deepcopy

import numpy as np
import pytest

from learnsignal import model as m, portable as io


def test_hand_calculated_two_state_decision_tree():
    r = m.analyze(m.demo()["data"])
    assert r["current_value"] == pytest.approx(20000)
    assert r["perfect_value"] == pytest.approx(56000)
    assert r["evpi"] == pytest.approx(36000)
    studies = r["studies"].set_index("study")
    assert studies.loc["Structured demand test","evsi"] == pytest.approx(17600)
    assert studies.loc["Structured demand test","net_value"] == pytest.approx(9600)
    # Positive: launch contributes 14,600. Negative: pilot contributes 5,700,
    # slightly better than launch's 5,400. Information gain is 20,300 - 20,000.
    assert studies.loc["Small exploratory survey","evsi"] == pytest.approx(300)
    assert studies.loc["Small exploratory survey","net_value"] == pytest.approx(-2700)
    policies = r["policies"].set_index(["study","result"])
    assert policies.loc[("Structured demand test","positive"),"result_probability"] == pytest.approx(.44)
    assert policies.loc[("Structured demand test","negative"),"preferred_action"] == "Hold"
    post = r["posteriors"].query("study == 'Structured demand test' and result == 'positive'")
    assert post.posterior_probability.sum() == pytest.approx(1)
    assert post.iloc[0].posterior_probability == pytest.approx(.32/.44)


def test_perfect_test_equals_evpi_and_noninformative_result_has_zero_value():
    d = m.demo()["data"]
    for row in d["signals"]:
        if row["study_id"] == "T1":
            row["probability"] = float((row["state_id"] == "S1") == (row["outcome"] == "positive"))
        else:
            row["probability"] = .5
    r = m.analyze(d)
    assert r["studies"].iloc[0].evsi == pytest.approx(r["evpi"])
    assert r["studies"].iloc[1].evsi == pytest.approx(0)


def test_impossible_result_does_not_divide_by_zero():
    d = m.demo()["data"]
    for row in d["signals"]:
        row["probability"] = float(row["outcome"] == "positive")
    r = m.analyze(d)
    impossible = r["policies"].query("result == 'negative'")
    assert impossible.conditional_payoff.isna().all()
    assert (r["studies"].evsi == 0).all()


def test_question_partition_values_are_bounded_and_nonadditive():
    d = m.demo()["data"]
    assert m.analyze(d)["questions"].iloc[0].perfect_answer_value == pytest.approx(36000)
    for row in d["partitions"]:
        row["answer"] = "Same answer"
    assert m.analyze(d)["questions"].iloc[0].perfect_answer_value == pytest.approx(0)


def test_missing_inputs_never_become_zero_or_equal_priors():
    d = m.validate(m.starter("Our decision"))
    assert len(m.readiness(d)) == 6
    with pytest.raises(io.DataProblem,match="Complete"):
        m.analyze(d)
    d = m.demo()["data"]
    d["signals"][0]["probability"] = None
    r = m.analyze(d)
    assert r["studies"].iloc[0].status.startswith("Missing")
    assert np.isnan(r["studies"].iloc[0].evsi)


@pytest.mark.parametrize("mutate",[
    lambda d:d["states"][0].update(probability=.5),
    lambda d:d["states"][0].update(probability=-1),
    lambda d:d["payoffs"][0].update(value=float("nan")),
    lambda d:d["payoffs"][0].update(action_id="missing"),
    lambda d:d["signals"][0].update(probability=.9),
    lambda d:d["signals"].append(deepcopy(d["signals"][0])),
    lambda d:d["partitions"][0].update(question_id="missing"),
    lambda d:d["studies"][0].update(cost=-1),
    lambda d:d["payoffs"][0].update(source_id="missing"),
])
def test_invalid_models_rejected(mutate):
    d=m.demo()["data"]
    mutate(d)
    with pytest.raises(io.DataProblem):
        m.validate(d)


def test_random_models_obey_information_bounds_and_posterior_totals():
    rng=np.random.default_rng(841)
    for _ in range(20):
        d=m.demo()["data"]
        p=float(rng.uniform(.01,.99))
        d["states"][0]["probability"],d["states"][1]["probability"]=p,1-p
        for row in d["payoffs"]:
            row["value"]=float(rng.normal(0,100))
        for study in d["studies"]:
            for state in d["states"]:
                q=float(rng.random())
                for row in d["signals"]:
                    if row["study_id"]==study["id"] and row["state_id"]==state["id"]:
                        row["probability"]=q if row["outcome"]=="positive" else 1-q
        r=m.analyze(d)
        assert r["evpi"]>=0
        assert (r["studies"].evsi>=-1e-8).all()
        assert (r["studies"].evsi<=r["evpi"]+1e-8).all()
        assert np.allclose(r["posteriors"].groupby(["study","result"]).posterior_probability.sum(),1)


def test_sensitivity_endpoints_have_no_state_uncertainty():
    frame=m.sensitivity(m.demo()["data"],"S1")
    assert frame.iloc[0].evpi == pytest.approx(0)
    assert frame.iloc[-1].evpi == pytest.approx(0)
    assert frame.iloc[0].preferred_action == "Hold"
    assert frame.iloc[-1].preferred_action == "Full launch"


def test_export_unreviewed_draft_does_not_include_calculated_values():
    p=m.demo()
    assert "17600" in m.printable(p)
    p["review"]=None
    assert "17600" not in m.printable(p)
    assert "Review the draft" in m.printable(p)
    assert io.restore(io.json_bytes(p),"learn",m.validate)==p


def test_textbook_oil_drilling_example_evpi_and_evsi():
    """The classic oil-drilling decision used to teach decision analysis (as in Hillier and Lieberman's
    decision-analysis chapter of Introduction to Operations Research), worked by hand below.

    Land may hold oil (prior 0.25) or be dry (0.75). Drilling pays 700 if oil and -100 if dry; selling the land pays
    90 either way (thousands of dollars). A seismic survey costing 30 reads favourable with probability 0.6 if oil
    and 0.2 if dry.

    Without information: drill = 0.25*700 + 0.75*(-100) = 100 > sell = 90, so drill, worth 100.
    Perfect information: 0.25*700 + 0.75*90 = 242.5, so EVPI = 142.5.
    Survey: P(favourable) = 0.25*0.6 + 0.75*0.2 = 0.3, P(oil | favourable) = 0.15/0.3 = 0.5, drill is worth
    0.5*700 - 0.5*100 = 300. P(oil | unfavourable) = 0.1/0.7 = 1/7, drill is worth 100 - 600/7 = 14.29 < 90, so sell.
    With the survey: 0.3*300 + 0.7*90 = 153, so EVSI = 53 and the net value after its cost of 30 is 23.
    """
    d = m.starter("Textbook oil-drilling decision")
    d["context"] = [{"unit": "thousand USD", "horizon": "One drilling decision"}]
    d["states"] = [{"id": "OIL", "label": "Oil", "probability": .25, "note": "", "source_id": None},
                   {"id": "DRY", "label": "Dry", "probability": .75, "note": "", "source_id": None}]
    d["actions"] = [{"id": "DRILL", "label": "Drill"}, {"id": "SELL", "label": "Sell the land"}]
    values = {("DRILL", "OIL"): 700, ("DRILL", "DRY"): -100, ("SELL", "OIL"): 90, ("SELL", "DRY"): 90}
    d["payoffs"] = [{"action_id": a, "state_id": s, "value": v, "note": "", "source_id": None} for (a, s), v in values.items()]
    d["studies"] = [{"id": "SURVEY", "label": "Seismic survey", "cost": 30, "description": "Detailed seismic survey",
                     "source_id": None}]
    likelihood = {"OIL": .6, "DRY": .2}
    d["signals"] = [{"study_id": "SURVEY", "state_id": s, "outcome": outcome, "probability": p if outcome == "favourable" else 1 - p}
                    for s, p in likelihood.items() for outcome in ["favourable", "unfavourable"]]
    d["questions"] = [{"id": "Q", "label": "Is there oil?"}]
    d["partitions"] = [{"question_id": "Q", "state_id": s, "answer": s} for s in ["OIL", "DRY"]]
    r = m.analyze(m.validate(d))
    assert r["preferred"] == "Drill"
    assert r["current_value"] == pytest.approx(100)
    assert r["perfect_value"] == pytest.approx(242.5)
    assert r["evpi"] == pytest.approx(142.5)
    assert r["questions"].iloc[0].perfect_answer_value == pytest.approx(142.5)
    study = r["studies"].iloc[0]
    assert study.evsi == pytest.approx(53)
    assert study.net_value == pytest.approx(23)
    policies = r["policies"].set_index("result")
    assert policies.loc["favourable", "result_probability"] == pytest.approx(.3)
    assert policies.loc["favourable", "preferred_action"] == "Drill"
    assert policies.loc["favourable", "conditional_payoff"] == pytest.approx(300)
    assert policies.loc["unfavourable", "preferred_action"] == "Sell the land"
    assert policies.loc["unfavourable", "conditional_payoff"] == pytest.approx(90)
    post = r["posteriors"].set_index(["result", "state"]).posterior_probability
    assert post[("favourable", "Oil")] == pytest.approx(.5)
    assert post[("unfavourable", "Oil")] == pytest.approx(1 / 7)


def large_model(states, actions, studies, results, seed=7):
    """A valid random model of any size; the first study is perfectly accurate (it reveals the state's result group)."""
    rng = np.random.default_rng(seed)
    d = m.starter("Large generated decision")
    prior = rng.dirichlet(np.ones(states))
    prior[-1] = 1 - prior[:-1].sum()
    d["states"] = [{"id": f"S{i}", "label": f"State {i}", "probability": float(p), "note": "", "source_id": None}
                   for i, p in enumerate(prior)]
    d["actions"] = [{"id": f"A{j}", "label": f"Action {j}"} for j in range(actions)]
    d["payoffs"] = [{"action_id": a["id"], "state_id": s["id"], "value": float(rng.normal(0, 100)), "note": "",
                     "source_id": None} for a in d["actions"] for s in d["states"]]
    d["studies"] = [{"id": f"T{t}", "label": f"Study {t}", "cost": 1.0, "description": "Generated", "source_id": None}
                    for t in range(studies)]
    for t in range(studies):
        for i, s in enumerate(d["states"]):
            if t == 0:
                probs = np.eye(results)[i % results]
            else:
                probs = rng.dirichlet(np.ones(results))
                probs[-1] = 1 - probs[:-1].sum()
            d["signals"] += [{"study_id": f"T{t}", "state_id": s["id"], "outcome": f"r{y}", "probability": float(p)}
                             for y, p in enumerate(probs)]
    return d


def test_local_mode_accepts_models_beyond_the_demo_caps(monkeypatch):
    from learnsignal import limits

    monkeypatch.delenv("SIGNAL_PUBLIC", raising=False)
    d = large_model(states=40, actions=15, studies=14, results=12)
    assert len(d["states"]) > limits.DEMO["states"] and len(d["actions"]) > limits.DEMO["actions"]
    assert len(d["signals"]) > limits.DEMO["signals"]
    r = m.analyze(m.validate(d))
    assert len(r["studies"]) == 14
    assert (r["studies"].evsi >= -1e-8).all() and (r["studies"].evsi <= r["evpi"] + 1e-8).all()
    assert np.allclose(r["posteriors"].groupby(["study", "result"]).posterior_probability.sum().dropna(), 1)
    assert len(m.sensitivity(d, "S0")) == 41


def test_public_demo_caps_model_size(monkeypatch):
    monkeypatch.setenv("SIGNAL_PUBLIC", "1")
    d = large_model(states=40, actions=3, studies=1, results=2)
    with pytest.raises(io.DataProblem, match="public demo"):
        m.validate(d)
    d = large_model(states=4, actions=3, studies=1, results=11)
    with pytest.raises(io.DataProblem, match="too many possible results.*public demo"):
        m.validate(d)
    assert m.analyze(m.demo()["data"])["evpi"] == pytest.approx(36000)


def test_a_thousand_states_is_exact_and_fast():
    """Calculations scale with options x states x results, not combinatorially."""
    import time

    d = large_model(states=1_000, actions=20, studies=5, results=4, seed=11)
    started = time.perf_counter()
    r = m.analyze(d)
    assert time.perf_counter() - started < 60
    prior = np.array([s["probability"] for s in d["states"]])
    pay = {(p["action_id"], p["state_id"]): p["value"] for p in d["payoffs"]}
    u = np.array([[pay[(a["id"], s["id"])] for s in d["states"]] for a in d["actions"]])
    assert r["evpi"] == pytest.approx(float(u.max(axis=0) @ prior - (u @ prior).max()))
    assert (r["studies"].evsi <= r["evpi"] + 1e-6).all()
