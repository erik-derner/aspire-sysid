"""The HTML report of an interactive session.

The report is written for the user of ASPIRE, in the form of the report of an experiment
(:mod:`aspire_sysid.report.html_report`): self-contained HTML pages, no script that loads
anything, and no language model. A session folder (``aspire session``) receives

* ``report/index.html``: the assignment (``TASK.md`` verbatim), the configuration, one table row
  per identification round, the course of the session (rounds, questions of the agent and answers
  of the user, analysis requests and answers, feedback and task changes, the end), and the files;
* ``report/round<k>.html`` for every evaluated pool version ``k``: the models of the round, as on
  the page of a run of an experiment, the course of the round, and the files.

The session writes the report after every round and analysis exchange and at its end, so that the
user can open the page of a round while the session continues. The report reads ``session.json``
(the session record, with the texts the agent received under ``report``), ``transcript.jsonl``,
``pools/v<k>/`` and ``evaluation/v<k>/``; it needs neither the task folder nor the run record,
which exists only after the end of the session.

A round whose label is *test-informed* (the user had seen results on the test data
before the round started) is marked as such wherever its test errors are shown: the test data may
have influenced the user's feedback, so its test errors are not those of unseen data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import html_report as H

__all__ = ["build_session_report", "round_page_name"]

E = H.E


def round_page_name(pool_version: int) -> str:
    """File name of the page of the round with pool version ``pool_version``."""
    return f"round{int(pool_version)}.html"


def _events(folder: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    tp = folder / "transcript.jsonl"
    if tp.is_file():
        for line in tp.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def _round_record(sess: dict[str, Any], rd: dict[str, Any]) -> dict[str, Any]:
    """The part of a run record that the pages of a run read, for one round of a session."""
    info = sess.get("report") or {}
    return {
        "outcome": rd.get("outcome"),
        "termination_reason": rd.get("termination_message") or "",
        "consumption": {"turns": rd.get("turns"), "cost_usd": rd.get("cost_usd"), "elapsed_s": rd.get("elapsed_s")},
        "task": {"title": info.get("title")},
        "texts": info.get("texts") or {},
        "workspace_manifest": sess.get("workspace_manifest"),
        "extra": {"experiment_run": {"output": info.get("output") or {}, "run_index": rd.get("round")}},
    }


def _load_rounds(folder: Path, sess: dict[str, Any], events: list[dict[str, Any]], report_dir: Path) -> list[tuple[dict[str, Any], H.Run | None]]:
    out = []
    for rd in sess.get("rounds") or []:
        k = rd.get("pool_version")
        run = None
        if isinstance(k, int) and (folder / "evaluation" / f"v{k}" / "evaluation.json").is_file():
            evs = [e for e in events if e.get("round") == rd.get("round") and e.get("exchange") is None
                   and e.get("kind") not in ("user_action", "analysis_answer", "session_end")]
            run = H._load_run(folder, report_dir, version=k, record=_round_record(sess, rd), events=evs, run_id=f"round{k}")
        out.append((rd, run))
    return out


def _round_words(text: str) -> str:
    """The texts shared with the report of an experiment speak of a run; in a session the unit is a round."""
    return (text.replace("the models of this run", "the models of this round").replace("models of this run", "models of this round")
            .replace("since the start of the run", "since the start of the round"))


def _informed_pill(rd: dict[str, Any]) -> str:
    return " <span class='pill bad'>test-informed</span>" if rd.get("test_informed") else ""


def _informed_note(rounds: list[tuple[dict[str, Any], H.Run | None]]) -> str:
    if not any(rd.get("test_informed") for rd, _ in rounds):
        return ""
    return ("<p class='muted small'><b>Test-informed</b>: before this round started, the user had been shown results on the test "
            "data. The user's feedback may therefore depend on the test data, and the test errors of this round are not errors "
            "on unseen data.</p>")


def _rounds_table(rounds: list[tuple[dict[str, Any], H.Run | None]]) -> str:
    first = next((r for _, r in rounds if r is not None), None)
    if first is None:
        return "<p>No round of this session has been evaluated yet.</p>"
    name, unit = first.output
    u = f" ({E(unit)})" if unit not in ("-", "unit not supplied") else ""
    rows = []
    for rd, r in rounds:
        n = rd.get("round")
        if r is None:
            why = H.OUTCOME_TEXT.get(str(rd.get("outcome")), "in progress" if rd.get("outcome") is None else str(rd.get("outcome")))
            rows.append(f"<tr><td>Round {n}{_informed_pill(rd)}</td><td colspan=7 class=muted>no model was evaluated ({E(why)})</td></tr>")
            continue
        s = H._summary(r)
        rec = s["rec"]
        best = s["best"]
        rows.append(
            f"<tr><td><a href='{E(round_page_name(r.pool_version or 0))}'><b>Round {n}</b></a>{_informed_pill(rd)}</td>"
            f"<td class=n>{s['delivered'] if s['delivered'] is not None else '–'}</td>"
            f"<td>{E(rec.label) if rec else '<span class=muted>none</span>'}</td>"
            f"<td class=n>{H.sig(s['rec_train'])}</td><td class=n><b>{H.sig(s['rec_test'])}</b></td>"
            f"<td class=n>{H.sig(s['best_test'])}{f' ({E(best.label)})' if best else ''}</td>"
            f"<td class=n>{s['turns'] if s['turns'] is not None else '–'}</td>"
            f"<td class=n>{s['cost']:.2f}</td></tr>" if isinstance(s["cost"], (int, float)) else
            f"<tr><td>Round {n}</td><td colspan=7 class=muted>no consumption recorded</td></tr>")
    return (
        "<div class=tw><table><thead><tr><th>Round</th><th class=n>Models</th><th>Recommended by the agent</th>"
        f"<th class=n>Its training error of <code>{E(name)}</code>{u}</th><th class=n>Its test error{u}</th>"
        f"<th class=n>Lowest test error in the pool{u}</th><th class=n>Turns</th><th class=n>Cost (USD)</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table></div>"
        f"<p class='muted small'>{H._error_caption(first)} Each round has its own pool of models; a later round starts from the "
        "user's feedback on the previous pool.</p>" + _informed_note(rounds))


_ACTION_TEXT = {"analysis": "User: requested an analysis", "new_round": "User: started a new round with feedback",
                "end": "User: ended the session"}


def _session_course(sess: dict[str, Any], events: list[dict[str, Any]], pages: set[int]) -> str:
    """The steps of the session in order: rounds, questions and answers, analysis exchanges, the
    user's choices, task changes and the end. Each line unfolds to the full text."""
    rows: list[str] = []

    def row(action: str, body: str, cls: str = "harness") -> None:
        rows.append(H._turn("", "", action, "", body, cls=cls))

    for e in events:
        kind = e.get("kind")
        rnd = e.get("round")
        if kind == "round_start" and e.get("exchange") is None and e.get("mode", "round") == "round":
            link = f" (<a href='{E(round_page_name(e.get('pool_version')))}'>models and course of the round</a>)" if e.get("pool_version") in pages else ""
            row(f"Round {rnd} started{link}", "<p class=muted>The agent identifies models; the page of the round lists every "
                "response of the agent.</p>")
        elif kind == "user_question":
            body = H.agent_markdown(e.get("question") or "")
            if e.get("decision"):
                body += f"<p class=muted>Decision affected, as stated by the agent: {E(str(e['decision']))}</p>"
            row(f"Agent: asked the user a question (round {rnd})", body)
        elif kind == "user_answer":
            if e.get("declined"):
                row("User: declined the question", "<p class=muted>The user gave no answer.</p>")
            else:
                row("User: answered the question", f"<div class=say>{E(str(e.get('answer') or ''))}</div>")
        elif kind == "round_end" and e.get("exchange") is None:
            how = H.OUTCOME_TEXT.get(str(e.get("outcome")), str(e.get("outcome")))
            row(f"Round {rnd} ended. {E(how)}.", f"<p>Models evaluated: {E(', '.join(str(x) for x in e.get('evaluated') or []) or 'none')}</p>")
        elif kind == "user_shown_sealed_results":
            row(f"Harness: showed the results of round {e.get('shown_round')} to the user, the test errors included",
                "<p class=muted>From this point on, a further round is labelled test-informed.</p>")
        elif kind == "task_change":
            row(f"User: changed the task from round {e.get('effective_round')} on", f"<div class=say>{E(str(e.get('text') or ''))}</div>")
        elif kind == "task_change_refused":
            row("Harness: did not apply a task change", f"<div class=say>{E(str(e.get('reason') or ''))}</div>")
        elif kind == "user_action":
            text = str(e.get("text") or "")
            row(_ACTION_TEXT.get(str(e.get("action")), f"User: {E(str(e.get('action')))}"),
                f"<div class=say>{E(text)}</div>" if text else "<p class=muted>No text.</p>")
        elif kind == "analysis_answer":
            row(f"Agent: answered analysis request {e.get('index')}", H.agent_markdown(e.get("answer") or ""))
        elif kind == "session_end":
            row("The session ended", f"<div class=say>{E(str(e.get('text') or ''))}</div>")
    if not rows:
        return "<p>The session has not started a round yet.</p>"
    head = "<div class='trow thead'><span class=num></span><span class=num></span><span>Step</span><span class=num></span></div>"
    bar = ("<div class=bar><button type=button data-open='details.turn' data-show='Unfold all steps' data-hide='Fold all steps'>"
           "Unfold all steps</button><span class='muted small'>Select a line to see the full text.</span></div>")
    return bar + f"<div class=turns>{head}{''.join(rows)}</div>"


def _limits(d: Any) -> str:
    d = d or {}
    return f"{d.get('turns', '–')} turns, {H.sig(d.get('seconds'), 6)} s of execution time, {H.sig(d.get('usd'))} USD"


def _files(folder: Path, report_dir: Path, version: int | None = None) -> str:
    rel = lambda p: H._relpath(folder / p, report_dir)  # noqa: E731
    items = []
    if version is not None:
        models = sorted(p.name for p in (folder / "pools" / f"v{version}" / "models").glob("*.json"))
        if models:
            items.append("<li>Model files of this round: " + ", ".join(
                f"<a href='{E(rel(f'pools/v{version}/models/{n}'))}' target=_blank rel=noopener><code>{E(n)}</code></a>" for n in models) + "</li>")
        entries = [("Evaluation report of the harness (Markdown)", f"evaluation/v{version}/evaluation.md"),
                   ("What the agent was told about its models after the round", f"pools/v{version}/agent_results.txt")]
    else:
        entries = [("Session record", "session.json"), ("Run record (written at the end of the session)", "run_record.json")]
    entries += [("Transcript (one JSON object per line)", "transcript.jsonl"),
                ("Working directory of the agent (copied at the end of the session)", "workspace")]
    for name, p in entries:
        if (folder / p).exists():
            items.append(f"<li><a href='{E(rel(p))}' target=_blank rel=noopener>{E(name)}</a> <span class=muted><code>{E(p)}</code></span></li>")
    return "<ul class=files>" + "".join(items) + "</ul>"


def _index(folder: Path, sess: dict[str, Any], events: list[dict[str, Any]], rounds: list[tuple[dict[str, Any], H.Run | None]], report_dir: Path) -> str:
    info = sess.get("report") or {}
    texts = info.get("texts") or {}
    title = str(info.get("title") or sess.get("task_id") or "Session")
    term = sess.get("termination")
    totals = sess.get("totals") or {}
    state = "The session has ended." if term else "The session is in progress."
    use = (f" Consumption{'' if term else ' so far'}: {totals.get('turns')} turns, {float(totals.get('elapsed_s') or 0.0):.0f} s of execution time, "
           f"{float(totals.get('cost_usd') or 0.0):.2f} USD.") if totals.get("turns") is not None else ""
    b = [f"<h1>{E(title)}</h1>", f"<p class=sub>Interactive session <code>{E(folder.name)}</code> · {H._generated()}</p>",
         f"<p>{state}{use}</p>"]
    b.append("<h2>1 Assignment</h2><p class=sub>The task brief <code>TASK.md</code>, as the agent received it at the start of the session.</p>")
    b.append(f"<div class='card doc'>{H.markdown(str(texts.get('brief') or ''))}</div>")
    budget = sess.get("budget") or {}
    start = next((e for e in events if e.get("kind") == "session_start"), {})
    day = str(start.get("timestamp") or start.get("recorded_at") or "")[:10]
    tools = info.get("tools") or []
    b.append("<h2>2 Configuration</h2><div class=card><dl class=kv>"
             f"<dt>Model</dt><dd><code>{E(str(sess.get('model')))}</code>"
             + (f", reasoning effort {E(str(info.get('reasoning_effort')))}" if info.get("reasoning_effort") else "") + "</dd>"
             f"<dt>Tools</dt><dd>{', '.join(f'<code>{E(str(t))}</code>' for t in tools) or '–'}</dd>"
             f"<dt>Limits of a round</dt><dd>{_limits(budget.get('round'))}</dd>"
             f"<dt>Limits of the session</dt><dd>{_limits(budget.get('session'))}</dd>"
             + (f"<dt>Limits of an analysis request</dt><dd>{_limits(budget.get('analysis_exchange'))}</dd>" if budget.get("analysis_exchange") else "")
             + f"<dt>Date</dt><dd>{E(day or '–')}</dd></dl></div>")
    b.append(H.fold("System prompt", f"<div class=say>{E(str(texts.get('system_prompt') or ''))}</div>"))
    if info.get("format_reference"):
        b.append(H.fold("<code>FORMAT.md</code>, the description of the model files", f"<div class=doc>{H.markdown(str(info['format_reference']))}</div>"))
    b.append(H.fold("First message to the agent", f"<div class=say>{E(str(texts.get('first_user_message') or ''))}</div>"))
    b.append("<h2>3 Rounds</h2>" + _round_words(_rounds_table(rounds)))
    pages = {r.pool_version for _, r in rounds if r is not None and r.pool_version is not None}
    b.append("<h2>4 Course of the session</h2>" + _session_course(sess, events, pages))
    b.append("<h2>5 Files</h2>" + _files(folder, report_dir))
    return H.page(title, "".join(b))


def _round_page(folder: Path, sess: dict[str, Any], rd: dict[str, Any], r: H.Run, spec: dict[str, Any], report_dir: Path) -> str:
    title = str((sess.get("report") or {}).get("title") or sess.get("task_id") or "Session")
    b = [f"<h1>{E(title)} – round {rd.get('round')}{_informed_pill(rd)}</h1>", f"<p class=sub>{H._generated()}</p>", f"<p>{H._status_line(r)}</p>"]
    if rd.get("test_informed"):
        b.append("<div class=warnbox><b>Test-informed round.</b> Before this round started, the user had been shown results on the test "
                 "data. The test errors below are therefore not errors on unseen data.</div>")
    if rd.get("feedback"):
        b.append(H.fold("The user's feedback that started this round", f"<div class=say>{E(str(rd['feedback']))}</div>", open_=True))
    b.append("<h2>1 Models</h2>")
    if r.candidates:
        b.append(H._models_table(r))
        rec = r.candidate(r.recommended)
        if rec is not None:
            b.append(f"<div class=card><b>The agent's recommendation: <a href='#model-{E(rec.label)}'>{E(rec.label)}</a>.</b> "
                     f"Its reason: <span class=say style='display:inline'>{H.agent_text(r.reason)}</span></div>")
        else:
            b.append("<div class=card><b>The agent recommended no model.</b>" + (f" Its reason: {H.agent_text(r.reason)}" if r.reason else "") + "</div>")
        b.append("<div class=bar><button type=button data-open='details.more' data-show='Unfold the details of all models' "
                 "data-hide='Fold the details of all models'>Unfold the details of all models</button></div>")
        b += [H._model_card(r, c, spec) for c in r.candidates]
    else:
        b.append("<p>No model was evaluated in this round.</p>")
    b.append("<h2>2 Course of the round</h2>")
    b.append("<p class=sub>The system prompt, <code>TASK.md</code> and <code>FORMAT.md</code> that the agent received are shown on the "
             "<a href='index.html'>page of the session</a>.</p>")
    b.append(H._course(r))
    b.append("<h2>3 Files</h2>" + _files(folder, report_dir, r.pool_version))
    return H.page(f"{title} – round {rd.get('round')}", _round_words("".join(b)), crumb="<a href='index.html'>← Session</a>")


def build_session_report(session_dir: str | Path, out_dir: str | Path | None = None) -> Path:
    """Write the HTML report of the session folder ``session_dir`` into ``out_dir`` (default
    ``<session_dir>/report``) and return the path of ``index.html`` (module docstring).

    Raises :class:`FileNotFoundError` when the folder holds no ``session.json``.
    """
    folder = Path(session_dir)
    sf = folder / "session.json"
    if not sf.is_file():
        raise FileNotFoundError(f"{sf} does not exist: the report is written for the record folder of an interactive session")
    sess = json.loads(sf.read_text(encoding="utf-8"))
    report_dir = Path(out_dir) if out_dir else folder / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    events = _events(folder)
    rounds = _load_rounds(folder, sess, events, report_dir)
    spec = {"columns": (sess.get("report") or {}).get("columns") or []}
    keep = {"index.html"} | {round_page_name(r.pool_version) for _, r in rounds if r is not None and r.pool_version is not None}
    for old in report_dir.glob("*.html"):
        if old.name not in keep:
            old.unlink()
    for rd, r in rounds:
        if r is not None and r.pool_version is not None:
            (report_dir / round_page_name(r.pool_version)).write_text(_round_page(folder, sess, rd, r, spec, report_dir), encoding="utf-8", newline="\n")
    index = report_dir / "index.html"
    index.write_text(_index(folder, sess, events, rounds, report_dir), encoding="utf-8", newline="\n")
    return index
