"""The task interview: an agent prepares the task definition together with the user.

``aspire session --train <file> [--val <file>] [--test <file> ...]`` starts interactive operation
from data files instead of a task folder. The harness then

1. creates a **task stub** (:func:`aspire_sysid.task.stub.create_task_stub`): a new task folder into which the user's files
   are *copied* under neutral names (``data/train.csv``, ``data/val.csv``, ``test/test_<i>.csv``); the
   originals are not touched, and their names, which may be recording names, are kept only in
   ``interview/stub.json`` of the task folder and are never shown to an agent. The training data are required; validation and test data are optional, and the
   split is the user's: the harness does not divide a file.
2. runs the **interview agent** (:class:`Interview`): the language model of the session with the
   tools of the identification agent (files and commands in a working directory, web access,
   package installation, helper agents), ``ask_user`` and ``check_task``. Its working directory
   holds the training and validation data, a draft ``task.yaml`` with the fields the harness sets,
   the guide and the field reference of ``task.yaml`` and two example task definitions. It never
   holds the test data: they stay in the task folder, which the tool policy protects as for every
   run.
3. **checks** the agent's ``task.yaml`` with the task loader (:meth:`Interview.check`), on the
   agent's request (``check_task``) and after every reply of the agent that ends an exchange. The
   harness overwrites its own fields (identifier, data paths, test entries) before the check, so
   that the agent cannot change which files are sealed.
4. shows the **task brief** ``TASK.md`` rendered from the checked definition to the user, who
   accepts it, asks for changes (a further exchange with the agent), or stops.

The interview is a separate conversation: the identification agent of the session that follows
receives none of it, only the task brief and the data, as for a task folder written by hand. The
interview has its own limits (:data:`INTERVIEW_LIMITS`); its consumption is recorded in
``interview/interview.json`` and is not charged to the session budget, which the task defines.

Records in ``<task folder>/interview/``: ``stub.json`` (the copied files with the original paths
and SHA-256 digests), ``transcript.jsonl`` (every request, response, tool call, question and
answer), ``interview.json`` (outcome, consumption, questions and answers, checks, the user's
verdicts) and ``workspace/`` (the files the agent wrote, without the data).
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import json
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from ..agent.budget import ExecutionClock
from ..agent.config import ToolConfig
from ..agent.events import EventSink, FanoutSink, NullSink
from ..agent.loop import RoundLabels, run_analysis_exchange
from ..agent.prices import PriceTable
from ..agent.probe import EnvironmentProbe
from ..agent.providers import Provider
from ..agent.tools import PipRunner, Tool, ToolContext, ToolOutcome, WebBackends, build_registry
from ..brief.prompts import environment_description
from ..brief.render import render_brief
from ..record import TranscriptWriter
from ..task import TaskError, load_task
from ..task.schema import Limits
from ..task.stub import InterviewError, TaskStub, create_task_stub, default_task_dir, draft_text, load_task_stub, merge_definition
from .ask_user import QuestionRecord, make_ask_user_tool
from .channel import UserChannel

__all__ = [
    "CHECK_TASK",
    "DRAFT_FILE",
    "INTERVIEW_FIRST_MESSAGE",
    "INTERVIEW_HELPER_PROMPT",
    "INTERVIEW_LIMITS",
    "INTERVIEW_PARAGRAPHS",
    "Interview",
    "InterviewError",
    "InterviewResult",
    "TaskStub",
    "create_task_stub",
    "default_task_dir",
    "load_task_stub",
    "merge_definition",
    "render_interview_prompt",
]

DRAFT_FILE = "task.yaml"
"""The task definition in the interview agent's working directory."""

CHECK_TASK = "check_task"
"""Name of the tool with which the interview agent has the harness check ``task.yaml``."""

INTERVIEW_LIMITS = Limits(turns=60, seconds=3600.0, usd=5.0)
"""Limits of one task interview: turns, execution time (the user's waiting time excluded) and cost.
They equal the turns and time of the default round budget and half its cost."""

INTERVIEW_PARAGRAPHS: tuple[str, ...] = (
    "You are an agent that prepares a system identification task together with a user. The user has "
    "supplied data and will answer your questions. Your work is finished when the file task.yaml in the "
    "working directory defines the task completely and the user agrees with it. A second agent will then "
    "identify models of the system; it will receive only what the task definition states and the data in "
    "data/.",
    "How you proceed is your decision. You may read and write files in the working directory, write and "
    "run code, fetch web resources, search the web, install Python packages and start helper agents. "
    "TASK_GUIDE.md explains task.yaml, TASK_REFERENCE.md lists every field, and examples/ holds two "
    "complete task definitions; read them first. Examine the data before you ask, so that you can propose "
    "what the data show, such as the roles of the columns, the sampling period and the ranges, and let the "
    "user confirm or correct it.",
    "Ask the user with ask_user for what the data do not determine: what the system is, what the model "
    "will be used for, which quantity is the output, the units, physical requirements, and any other field "
    "you cannot fill with confidence. Ask one specific question at a time, in plain words. The user may not "
    "know the terms of task.yaml: explain a term when you need it, and ask again when an answer is unclear. "
    "Do not invent information about the system. Write the user's statements about the system in the "
    "user's words; leave out an optional field that the user cannot fill.",
    "task.yaml contains fields that the harness sets: the identifier, the paths of the data files and the "
    "test data. Leave them as they are. Test data, if the user supplied any, are not available to you; do "
    "not try to reach them or any file outside the working directory. Call check_task to have the harness "
    "check task.yaml: it names every error with its field and, when the file is valid, returns the task "
    "brief that the second agent will receive. When the check passes and you have no open question, reply "
    "with a short summary of the task and without a tool request; the user then reads the brief and may "
    "ask for changes. Everything you do is recorded.",
)
"""The system prompt of the interview agent, one paragraph per entry; the environment description of
the harness follows it, as in the prompt of the identification agent."""

INTERVIEW_FIRST_MESSAGE = (
    "The preparation of the task begins. The user supplied {supplied}. The draft of the task definition is "
    "task.yaml in the working directory."
)
"""The first message of the interview; ``{supplied}`` names the kinds of data, never a file name."""

INTERVIEW_HELPER_PROMPT = (
    "You are a helper agent. The main agent prepares a system identification task with a user and has "
    "assigned you the subtask stated in the first message. You work in the same working directory as the "
    "main agent, with the tools described in this request; you cannot start further helper agents and you "
    "cannot ask the user. Your turns and costs count toward the main agent's limits. Do not access any file "
    "outside the working directory. When the subtask is finished, reply with text only, without a tool "
    "request: state what you did, the files you wrote and the results, every number with its unit and the "
    "data it was computed on. That reply ends your work and is returned to the main agent."
)

CHECK_FAILED_MESSAGE = (
    "The harness checked task.yaml after your reply and found errors:\n{errors}\n"
    "Correct them, and ask the user where a correction needs information you do not have. Reply without a "
    "tool request when check_task passes."
)
CHANGE_MESSAGE = (
    "The user read the task brief and asks for changes:\n{text}\n"
    "Change task.yaml accordingly, and ask the user where the request is unclear. Reply without a tool "
    "request when check_task passes."
)


def render_interview_prompt(config: ToolConfig, probe: EnvironmentProbe | None) -> str:
    """The system prompt of the interview agent: :data:`INTERVIEW_PARAGRAPHS` and the environment
    description of the harness (tools, shell, Python version, installed packages)."""
    env = environment_description(config, probe, interactive=True)
    return "\n\n".join(INTERVIEW_PARAGRAPHS) + "\n\n" + env.rstrip() + f"\n- Additional tool of the task preparation: {CHECK_TASK}.\n"


# ---------------------------------------------------------------------------------------------
# the interview


@dataclass
class InterviewResult:
    """Outcome of a task interview. ``outcome`` is ``accepted`` (the user accepted the brief; the task
    folder holds a valid ``task.yaml``), ``stopped`` (the user stopped), ``limit`` (a limit of the
    interview was reached) or ``error``."""

    outcome: str
    task_dir: Path
    turns: int = 0
    cost_usd: float = 0.0
    elapsed_s: float = 0.0
    exchanges: int = 0
    detail: str = ""
    questions: list[dict[str, Any]] = field(default_factory=list)


class _TaskStandIn:
    """What the turn loop needs of a task before one exists: an identifier for the labels of the
    events and the task folder, which the tool policy protects (it holds the test data)."""

    def __init__(self, stub: TaskStub) -> None:
        self.id = stub.task_id
        self.task_dir = stub.task_dir


def _guide_files() -> dict[str, str]:
    """The documents of ``task.yaml`` for the interview agent's working directory: the guide, the
    field reference (Sections 2 to 4 of ``tasks/README.md``) and the two example definitions. They are
    read from the ``tasks`` folder next to the harness; a document that is absent is left out."""
    from ..paths import HARNESS_DIR

    tasks = HARNESS_DIR.parent / "tasks"
    out: dict[str, str] = {}
    guide = tasks / "GUIDE.md"
    if guide.is_file():
        out["TASK_GUIDE.md"] = guide.read_text(encoding="utf-8")
    readme = tasks / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        m = re.search(r"^## 2 .*?(?=^## 5 )", text, flags=re.S | re.M)
        if m:
            out["TASK_REFERENCE.md"] = "# Fields of `task.yaml`: reference\n\n" + m.group(0).rstrip() + "\n"
    for name in ("example-static", "example-dynamic"):
        f = tasks / name / "task.yaml"
        if f.is_file():
            out[f"examples/{name}.yaml"] = f.read_text(encoding="utf-8")
    return out


class Interview:
    """One task interview on the task stub ``stub`` (module docstring, steps 2 to 4)."""

    def __init__(
        self,
        stub: TaskStub,
        provider: Provider,
        config: ToolConfig,
        channel: UserChannel,
        *,
        limits: Limits = INTERVIEW_LIMITS,
        sink: EventSink | None = None,
        probe: EnvironmentProbe | None = None,
        python_executable: str | None = None,
        clock: ExecutionClock | None = None,
        price_table: PriceTable | None = None,
        web: WebBackends | None = None,
        pip_runner: PipRunner | None = None,
        base_env: Mapping[str, str] | None = None,
        workspace_root: str | Path | None = None,
        isolate_environment: bool = False,
        fsync: bool = True,
    ) -> None:
        from ..experiment.workspace import opaque_attempt_folder
        from .session import SessionTracker

        self.stub = stub
        self.provider = provider
        self.config = config
        self.channel = channel
        self.limits = limits
        self._external_sink = sink or NullSink()
        self.probe = probe
        self.python_executable = python_executable
        self.clock = clock or ExecutionClock()
        self.price_table = price_table
        self.web = web
        self.pip_runner = pip_runner
        self.base_env = base_env
        self.isolate_environment = isolate_environment
        self.fsync = fsync
        self.tracker = SessionTracker(limits, self.clock)
        self.workspace_root = Path(workspace_root) if workspace_root is not None else Path(tempfile.gettempdir()) / "aspire-sessions"
        self.workspace = opaque_attempt_folder(self.workspace_root) / "workspace"
        self.record_dir = stub.task_dir / "interview"
        self.questions: list[QuestionRecord] = []
        self.checks: list[dict[str, Any]] = []
        self.verdicts: list[dict[str, Any]] = []
        self.system_prompt = render_interview_prompt(config, probe)
        self.transcript: TranscriptWriter | None = None
        self.sink: EventSink = self._external_sink
        self._seq = 0

    # -- the working directory -----------------------------------------------------------------

    def provision(self) -> None:
        """Write the interview agent's working directory: the training and validation data, the
        draft definition and the documents of ``task.yaml``. The test data are never copied."""
        from ..experiment.workspace import check_workspace_root

        check_workspace_root(self.workspace_root)
        ws = self.workspace
        (ws / "data").mkdir(parents=True, exist_ok=True)
        for rel in filter(None, (self.stub.train, self.stub.val)):
            shutil.copyfile(self.stub.task_dir / rel, ws / rel)
        (ws / DRAFT_FILE).write_text(draft_text(self.stub), encoding="utf-8", newline="\n")
        for rel, text in _guide_files().items():
            p = ws / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8", newline="\n")
        if self.isolate_environment:
            from ..experiment.runner import agent_base_environment

            packages = ws.parent / "packages"
            packages.mkdir(parents=True, exist_ok=True)
            self.base_env, _ = agent_base_environment(packages)

    # -- the check -------------------------------------------------------------------------------

    def check(self, source: str = "harness") -> tuple[bool, str]:
        """Check the agent's ``task.yaml`` (module docstring, step 3). Returns ``(True, brief)`` with
        the task brief of the valid definition, or ``(False, errors)``. A valid definition is the
        ``task.yaml`` of the task folder from then on; an invalid one leaves no file there."""
        target = self.stub.task_dir / "task.yaml"
        ok, text = False, ""
        try:
            draft = (self.workspace / DRAFT_FILE).read_text(encoding="utf-8")
        except OSError as exc:
            text = f"task.yaml cannot be read in the working directory ({exc})"
        else:
            try:
                spec = merge_definition(draft, self.stub)
                target.write_text(
                    f"# Task definition written by the task interview of ASPIRE on {_dt.date.today().isoformat()}; "
                    "interview/ holds its record.\n" + yaml.safe_dump(spec, sort_keys=False, allow_unicode=True, width=100),
                    encoding="utf-8", newline="\n")
                task = load_task(self.stub.task_dir)
                ok, text = True, render_brief(task, interactive=True)
            except InterviewError as exc:
                text = str(exc)
            except TaskError as exc:
                text = str(exc)
            except Exception as exc:  # noqa: BLE001 - a definition the loader cannot read at all
                text = f"the task definition cannot be read ({type(exc).__name__}: {exc})"
        if not ok and target.exists():
            target.unlink()
        self.checks.append({"source": source, "valid": ok, "text": text})
        self._emit("task_check", source=source, valid=ok, text=text)
        return ok, text

    def user_edit(self, text: str) -> tuple[bool, str]:
        """The user's own edit of ``task.yaml`` while the task brief is shown (the web app offers it).

        The user is the owner of the task and may change every field; the text is checked by the task
        loader as it is, without the harness's fields being restored. A valid text becomes the
        ``task.yaml`` of the task folder and replaces the agent's draft in its working directory, so
        that a later change by the agent starts from the user's version; an invalid text changes
        nothing. Returns ``(True, brief)`` or ``(False, errors)``; the check is recorded with the
        source ``user``.
        """
        from ..web.app import check_definition_text

        ok, result = check_definition_text(self.stub.task_dir, text, keep=True)
        if ok:
            try:
                (self.workspace / DRAFT_FILE).write_text(text, encoding="utf-8", newline="\n")
            except OSError:
                pass
        self.checks.append({"source": "user", "valid": ok, "text": result})
        self._emit("task_check", source="user", valid=ok, text=result)
        return ok, result

    def _check_tool(self) -> Tool:
        def handler(ctx: ToolContext, args: Mapping[str, Any]) -> ToolOutcome:
            ok, text = self.check(source="agent")
            if ok:
                return ToolOutcome("task.yaml is valid. The task brief that the second agent will receive:\n\n" + text,
                                   details={"valid": True})
            return ToolOutcome("task.yaml is not valid:\n" + text, is_error=True, details={"valid": False})

        return Tool(
            CHECK_TASK,
            "Have the harness check task.yaml in the working directory. Returns every error with its field, or, for a "
            "valid file, the task brief that the second agent will receive.",
            {"type": "object", "properties": {}, "required": []},
            handler,
            helper_allowed=False,
        )

    # -- events and records ----------------------------------------------------------------------

    def _emit(self, kind: str, **fields: Any) -> None:
        self._seq += 1
        base = {"task": self.stub.task_id, "session": "interview", "round": 0, "pool_version": 0, "agent": "harness",
                "seq": self._seq, "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(), "elapsed_s": self.tracker.elapsed_s}
        base.update(json.loads(json.dumps(fields, default=str)))
        self.sink.emit(kind, **base)

    def _write_record(self, result: InterviewResult) -> None:
        t = self.tracker
        record = {
            "format_version": 1,
            "task_id": self.stub.task_id,
            "model": self.provider.model_id,
            "outcome": result.outcome,
            "detail": result.detail,
            "limits": dataclasses.asdict(self.limits),
            "consumption": {"turns": t.turns, "input_tokens": t.usage.input_tokens, "output_tokens": t.usage.output_tokens,
                            "cost_usd": t.cost_usd, "elapsed_s": t.elapsed_s, "waiting_s": self.clock.waiting_s()},
            "exchanges": result.exchanges,
            "questions": [q.to_dict() for q in self.questions],
            "checks": self.checks,
            "verdicts": self.verdicts,
            "system_prompt": self.system_prompt,
            "data": self.stub.to_dict(),
        }
        (self.record_dir / "interview.json").write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")

    def _archive_workspace(self) -> None:
        """Keep the files the agent wrote (its scripts and notes), without the data."""
        dst = self.record_dir / "workspace"
        if dst.exists() or not self.workspace.is_dir():
            return
        try:
            shutil.copytree(self.workspace, dst, ignore=shutil.ignore_patterns("data", "__pycache__"))
            shutil.rmtree(self.workspace.parent, ignore_errors=True)
        except OSError:
            pass

    # -- the conversation ------------------------------------------------------------------------

    def run(self) -> InterviewResult:
        """Run the interview until the user accepts the task brief or stops, or a limit is reached."""
        self.record_dir.mkdir(parents=True, exist_ok=True)
        bind = getattr(self.channel, "bind_interview", None)
        if callable(bind):
            bind(self)  # a channel that lets the user edit task.yaml directly (the web app)
        self.provision()
        self.transcript = TranscriptWriter(
            self.record_dir / "transcript.jsonl",
            header={"run_id": self.stub.task_id, "session": "interview", "operation": "task interview", "task": self.stub.task_id,
                    "configuration": self.config.name, "model": self.provider.model_id, "vendor": self.provider.vendor},
            fsync=self.fsync,
        )
        self.sink = FanoutSink(self.transcript, self._external_sink)
        self._emit("interview_start", model=self.provider.model_id, limits=dataclasses.asdict(self.limits),
                   data={"train": self.stub.train, "val": self.stub.val, "sealed_files": len(self.stub.tests)})
        registry = build_registry(self.config)
        registry.register(make_ask_user_tool(self.channel, self.questions.append))
        registry.register(self._check_tool())
        stand_in = _TaskStandIn(self.stub)
        message = INTERVIEW_FIRST_MESSAGE.format(supplied=self.stub.supplied_text)
        history: list[Any] = []
        result = InterviewResult("error", self.stub.task_dir)
        n = 0
        try:
            while True:
                hit = self.tracker.limit_reached()
                if hit is not None:
                    result = InterviewResult("limit", self.stub.task_dir, detail=f"the {hit.kind} limit of the interview was reached")
                    break
                n += 1
                rem = self.tracker.remaining()
                self.tracker.open_scope()
                try:
                    r = run_analysis_exchange(
                        self.provider, self.system_prompt, message, self.workspace, stand_in, self.config,  # type: ignore[arg-type]
                        Limits(turns=rem.turns, seconds=rem.seconds, usd=rem.usd), self.sink,
                        labels=RoundLabels(task=self.stub.task_id, session="interview", round=0, exchange=n),
                        clock=self.clock, parent_tracker=self.tracker, price_table=self.price_table, registry=registry,
                        web=self.web, pip_runner=self.pip_runner, python_executable=self.python_executable, history=history,
                        helper_system_prompt=INTERVIEW_HELPER_PROMPT, base_env=self.base_env, pool_version=0,
                    )
                except BaseException:
                    self.tracker.close_scope(None)
                    raise
                self.tracker.close_scope(r.elapsed_s)
                history = list(r.messages)
                if r.outcome != "answered":
                    kind = "limit" if r.limit is not None else "error"
                    detail = (f"the {r.limit.kind} limit of the interview was reached" if r.limit is not None
                              else f"the exchange ended with an error ({r.error})")
                    result = InterviewResult(kind, self.stub.task_dir, detail=detail)
                    break
                ok, text = self.check()
                if not ok:
                    message = CHECK_FAILED_MESSAGE.format(errors=text)
                    continue
                with self.clock.paused():
                    verdict = self.channel.confirm_task(text, r.final_text or "")
                self.verdicts.append({"exchange": n, "verdict": verdict if isinstance(verdict, bool) else "changes",
                                      "text": verdict if isinstance(verdict, str) else ""})
                self._emit("task_verdict", exchange=n, accepted=verdict is True, stopped=verdict is False,
                           text=verdict if isinstance(verdict, str) else "")
                if verdict is True:
                    result = InterviewResult("accepted", self.stub.task_dir)
                    break
                if verdict is False:
                    result = InterviewResult("stopped", self.stub.task_dir, detail="the user stopped before accepting the task brief")
                    break
                message = CHANGE_MESSAGE.format(text="\n".join("> " + line for line in str(verdict).splitlines()))
        finally:
            t = self.tracker
            result.turns, result.cost_usd, result.elapsed_s, result.exchanges = t.turns, t.cost_usd, t.elapsed_s, n
            result.questions = [q.to_dict() for q in self.questions]
            self._emit("interview_end", outcome=result.outcome, detail=result.detail, turns=t.turns, cost_usd=t.cost_usd)
            if self.transcript is not None:
                self.transcript.close(outcome=result.outcome)
            self._write_record(result)
            self._archive_workspace()
        return result
