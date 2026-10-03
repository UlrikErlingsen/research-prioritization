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
