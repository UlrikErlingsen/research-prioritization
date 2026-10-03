from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from learnsignal import __version__, model, portable as io
from learnsignal.ui import signal_theme as sig
from learnsignal.ui.keys import NS, k
from learnsignal.ui.workspace import Workspace


def calculation(w):
    if not io.reviewed(w.p):
        st.info("Review the inputs on Edit & review before calculating decision or research values.")
        return None
    missing = model.readiness(w.d)
    if missing:
        st.warning("Missing inputs: " + "; ".join(missing[:12]))
        return None
    return model.analyze(w.d)


def render() -> None:
    """Draw the whole app on the current page. Never calls st.set_page_config or st.navigation."""
    sig.apply(NS)
    w = Workspace(model)
    sig.sidebar_brand(NS, "Find the uncertainty that could change your decision.")
    pages = ["Overview", "1 · Add your data", "2 · Edit & review", "3 · Decision & research value", "4 · Results & sensitivity", "5 · Export", "Research & limits"]
    with st.sidebar:
        page = st.radio("Navigate", pages, label_visibility="collapsed", key=k("page"))
        st.caption("EXCEL · CSV · MANUAL · OPTIONAL AI")
        if st.button("Reset fictional demo", key=k("reset")):
            w.reset()
            st.rerun()
    sig.masthead(NS, ["Value of information", "Explicit assumptions", "Exact finite model"])
    w.status()
    try:
        if page == pages[0]:
            sig.hero(NS, eyebrow="RESEARCH PRIORITIZATION", title="Know what to learn.", em="Before you pay to learn it.",
                     body="Find which uncertainties could change your choice, then compare the decision value of proposed studies with their cost.",
                     pills=["Decision tables", "Bayesian updating", "Research value"])
            w.welcome()
            sig.cards([("01 / FRAME", "Define a real choice", "List feasible actions, mutually exclusive states and the net payoff for each combination."),
                       ("02 / CHALLENGE", "Expose the assumptions", "Keep priors and study accuracy explicit. AI can structure your inputs; missing numbers stay unknown."),
                       ("03 / LEARN", "Compare better-informed choices", "See the value of perfect information, realistic study results, and research costs side by side.")])
            cols = st.columns(4)
            for c,label,value in zip(cols,["Available actions","Future states","Candidate studies","Missing core inputs"],[len(w.d["actions"]),len(w.d["states"]),len(w.d["studies"]),len(model.readiness(w.d))]):
                c.metric(label,value)
            st.write("The fictional lunch-service example shows that a cheaper study can change a decision yet cost more than the expected improvement it provides.")
        elif page == pages[1]:
            sig.header("UPLOAD, ENTER OR USE AI", "Your data, your way.", "Bring a decision spreadsheet, enter your assumptions, or ask your AI to help structure the case.")
            w.inputs()
        elif page == pages[2]:
            sig.header("PROBABILITIES → PAYOFFS → STUDY DESIGN", "Make the model explicit.", "Studies use conditional likelihoods: the probability of each result if a state were true.")
            w.edit(model.TITLES)
        elif page == pages[3]:
            sig.header("CHOICE → INFORMATION → COST", "What could better information be worth?")
            result = calculation(w)
            if result is not None:
                unit = w.d["context"][0]["unit"]
                st.text("Payoff unit: " + unit + " · Horizon: " + w.d["context"][0]["horizon"])
                c1,c2,c3 = st.columns(3)
                c1.metric("Best expected payoff now", f"{result['current_value']:,.1f}")
                c2.metric("With perfect information", f"{result['perfect_value']:,.1f}")
                c3.metric("Perfect-information value · EVPI", f"{result['evpi']:,.1f}")
                st.text("Preferred action under current assumptions: " + result["preferred"])
                st.dataframe(result["actions"].round(3), hide_index=True, width="stretch")
                st.subheader("Compare candidate studies")
                if result["studies"].empty:
                    st.info("Add studies and their result likelihoods to compare research value.")
                else:
                    frame = result["studies"].dropna(subset=["net_value"])
                    if not frame.empty:
                        fig = go.Figure()
                        for col,label,color in [("evsi","Expected information value",sig.colorway(NS)[0]),("cost","Study cost",sig.colorway(NS)[1]),("net_value","Value after study cost",sig.colorway(NS)[2])]:
                            fig.add_bar(x=[escape(x) for x in frame.study],y=frame[col],name=label,marker_color=color)
                        fig.update_layout(barmode="group", height=380, yaxis_title=escape(unit), legend={"orientation":"h","y":1.15})
                        fig.update_yaxes(zeroline=True, rangemode="tozero")
                        sig.chart(NS,fig,key=k("study_chart"))
                    st.dataframe(result["studies"].round(3),hide_index=True,width="stretch")
                sig.note("info", "**EVPI is a ceiling under this model.** A study's expected information value depends on how often its results change the choice. A positive value after cost is conditional on your inputs and does not authorize spending.")
                st.subheader("Which uncertainty would be useful to resolve?")
                st.dataframe(result["questions"].round(3),hide_index=True,width="stretch")
                st.caption("Each question assumes its answer could be learned perfectly. Values may overlap and must not be added together.")
        elif page == pages[4]:
            sig.header("RESULT → POSTERIOR → CHOICE", "What would you do after each study result?")
            result = calculation(w)
            if result is not None:
                st.dataframe(result["policies"].round(4),hide_index=True,width="stretch")
                with st.expander("Posterior state probabilities"):
                    st.dataframe(result["posteriors"].round(5),hide_index=True,width="stretch")
                st.subheader("How sensitive is the decision to a prior?")
                names = {s["id"]:s["label"] for s in w.d["states"]}
                sid = st.selectbox("State to vary",list(names),format_func=names.get,key=k("vary_state"))
                frame = model.sensitivity(w.d,sid)
                fig = go.Figure()
                for col,label in [("current_value","Best expected payoff now"),("evpi","Perfect-information value")]:
                    fig.add_scatter(x=frame.state_probability,y=frame[col],mode="lines",name=label)
                fig.update_layout(height=370,xaxis_title="Probability of selected state",yaxis_title=escape(w.d["context"][0]["unit"]),legend={"orientation":"h","y":1.15})
                sig.chart(NS,fig,key=k("sensitivity"))
                st.caption("The remaining states retain their relative probabilities. This is a one-dimensional assumption check, not a confidence interval.")
                transitions = frame[frame.preferred_action.ne(frame.preferred_action.shift())]
                st.dataframe(transitions.round(4),hide_index=True,width="stretch")
                st.caption("Rows mark changes found on a 0.025 probability grid; exact switch points may lie between rows.")
        elif page == pages[5]:
            tables = {k:pd.DataFrame(w.d[k]) for k in model.TITLES}
            if io.reviewed(w.p) and not model.readiness(w.d):
                tables.update({"result_"+k:v for k,v in model.analyze(w.d).items() if isinstance(v,pd.DataFrame)})
            w.export(model.printable(w.p),tables)
        else:
            w.research()
    except io.DataProblem as exc:
        st.error(str(exc))
    sig.footer(NS, __version__, "Research value conditional on the decision model")
