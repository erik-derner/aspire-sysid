"""The scripted agent of a dry run: the whole grid without a language model and without cost.


The scripted agent of one run lists the working directory, reads the brief, writes the example
model files of the task (:func:`aspire_sysid.model.example_model_files`: one candidate with one
fitted, one fixed and one tied parameter, which passes the file and expression checks), runs the
checking script, and sends the completion message ``DONE``. Every step goes through the real turn
loop, tools, checks, evaluation, records and exports; only the language model is replaced.

The scripted provider carries the experiment's model identifier, so that the price schedule and
the records are those of a real run; its usage is fixed (a few thousand tokens per turn) and the
record marks the vendor as ``scripted`` and the run as a dry run. Dry-run records are never
aggregated with real runs (:mod:`aspire_sysid.experiment.aggregate`).
"""

from __future__ import annotations

from ..agent.providers import ScriptedProvider, ScriptStep, ToolCall, Usage
from ..model import example_model_files
from ..task.schema import TaskSpec

__all__ = ["DRY_RUN_USAGE", "dry_run_script", "dry_run_provider"]

DRY_RUN_USAGE = Usage(input_tokens=2000, output_tokens=500)
"""Usage recorded for every scripted turn of a dry run (fixed; not a measurement)."""


def _call(name: str, **arguments: object) -> ToolCall:
    return ToolCall(id="", name=name, arguments=dict(arguments))


def dry_run_script(task: TaskSpec, pause_s: float = 0.0) -> list[ScriptStep]:
    """The scripted responses of one dry run on ``task`` (module docstring).  

    With ``pause_s`` > 0 the agent first runs a shell command that waits that long (used to
    interrupt a run in the middle in tests and pre-flights).
    """
    files = example_model_files(task)
    pause = [ScriptStep(text="I wait.", tool_calls=[_call("run_shell", command=f'python -c "import time; time.sleep({float(pause_s)})"')],
                        usage=DRY_RUN_USAGE)] if pause_s > 0 else []
    return pause + [
        ScriptStep(text="I list the working directory.", tool_calls=[_call("list_files")], usage=DRY_RUN_USAGE),
        ScriptStep(text="I read the task brief.", tool_calls=[_call("read_file", path="TASK.md")], usage=DRY_RUN_USAGE),
        ScriptStep(
            text="I write the candidate file and the pool file.",
            tool_calls=[_call("write_file", path=p, content=t) for p, t in files.items()],
            usage=DRY_RUN_USAGE,
        ),
        ScriptStep(text="I run the checking script.", tool_calls=[_call("run_shell", command="python check_submission.py")], usage=DRY_RUN_USAGE),
        ScriptStep(text="The checks pass.\nDONE", usage=DRY_RUN_USAGE),
    ]


def dry_run_provider(task: TaskSpec, model_id: str, *, pause_s: float = 0.0) -> ScriptedProvider:
    """A :class:`ScriptedProvider` with :func:`dry_run_script` under the experiment's model identifier.  """
    return ScriptedProvider(dry_run_script(task, pause_s), model_id=model_id)
