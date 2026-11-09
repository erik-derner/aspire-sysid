"""Task specification, schema version 1: the data structures of a loaded task.

Data, roles, static and dynamic formulations, NARX, required and
optional task information, formal and natural-language requirements, evaluation settings
and budgets. The folder
format is documented in ``tasks/README.md``.

The loader (:mod:`aspire_sysid.task.loader`) builds a :class:`TaskSpec` from ``task.yaml``.
The sealed part of a task (test trajectories and reference expression) is held in a
:class:`SealedPart`, whose file locations are private attributes resolved and opened only by
:mod:`aspire_sysid.evaluate.sealed`.

Expression keys (the names under which a candidate stores its expressions)
are fixed per formulation by :func:`required_expression_keys`:

========== ===================================== ==========================================
formulation expression keys                         meaning
========== ===================================== ==========================================
static      ``<output>``                            ``ŷ = f(u; p, c)``, equation (1)
continuous  ``d<state>`` for every declared state   ``dx/dt = g_c(x, u; p, c)``, equation (2)
discrete    ``<state>_next`` for every state        ``x[k+1] = g_d(x[k], u[k]; p, c)``, (3)
narx        ``<output>_next``                       the regression of ``y[k+1]`` on the output,
                                                    its declared delays and the inputs; the
                                                    shift equations are supplied by the task
========== ===================================== ==========================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
"""The schema version implemented here."""

FORMULATIONS = ("static", "continuous", "discrete", "narx")
"""Formulations: static, continuous-time, discrete-time and NARX."""

ROLES = ("input", "state", "output", "state_derivative")
"""Column roles."""

EVALUATION_MODES = ("algebraic", "one_step", "simulation")
"""Evaluation modes."""

SCORING_RULES = ("all_samples", "after_initialization")
"""Index-set rules for the scoring interval ``I``.

``all_samples``: every sample of the dataset (static tasks). ``after_initialization``: in every
trajectory of ``N`` samples, the samples ``initialization, …, N − 1`` (0-based), that is, every
sample after the initialization samples (dynamic tasks).
"""

INTEGRATORS = ("rk4",)
"""Integration methods the harness implements (default: classical fourth-order
Runge–Kutta). Another method requires an implementation in ``aspire_sysid.evaluate`` first."""

INPUT_HOLDS = ("zero_order",)
"""Treatment of the recorded inputs between samples (default: zero-order hold)."""

REQUIREMENT_TYPES = (
    "symmetry",
    "monotonicity",
    "parity",
    "exact_value",
    "inequality",
    "curvature",
    "limit",
    "equation",
    "relation_at_points",
)
"""The nine types of formal requirement."""

VERIFICATIONS = ("symbolic", "sampling", "symbolic_then_sampling")
"""Verification procedures of a formal requirement."""

DEFAULT_FUNCTIONS = (
    "sin",
    "cos",
    "tan",
    "asin",
    "acos",
    "atan",
    "atan2",
    "sinh",
    "cosh",
    "tanh",
    "exp",
    "log",
    "sqrt",
    "Abs",
    "sign",
    "Min",
    "Max",
    "Piecewise",
)
"""Default permitted functions, spelled as in SymPy.

Arithmetic operators (``+ - * / **``), relational operators (``< <= > >= Eq Ne``) inside
``Piecewise`` conditions and the logical operators ``&``, ``|``, ``~`` are permitted by default;
π and e are fixed constants, written ``pi`` and ``E``."""

SEALED_FOLDERS = ("test", "reference")
"""Folders of a task that hold sealed data: the test data and the reference.

This is the single definition of their names. ``aspire_sysid.evaluate.sealed`` resolves and opens
files in them; the task loader uses the names only to reject agent-visible paths that point into
them, without opening anything there."""

UNIT_NOT_SUPPLIED = "not supplied"
"""The unit string of a quantity whose unit the task does not state (``unit: not supplied`` in
``task.yaml``). Every column and failure limit of a blind variant carries it; the
brief renders it verbatim, so that the agent reads that the unit is not supplied. The
unit ``-`` keeps its meaning: dimensionless, or not supplied as the column description states."""

RESERVED_NAMES = ("pi", "E")
"""Names of the fixed mathematical constants π and e."""

DEFAULT_ROUND_BUDGET = (60, 3600.0, 10.0)
"""Default round limits: turns, seconds, US dollars."""


class TaskError(ValueError):
    """A task specification violates schema version 1.

    ``errors`` lists every violation found, each as one sentence naming the field.
    """

    def __init__(self, errors: list[str], task_dir: Path | None = None):
        self.errors = list(errors)
        self.task_dir = task_dir
        where = f" in {task_dir}" if task_dir is not None else ""
        msg = f"{len(self.errors)} error(s){where}:\n" + "\n".join(f"  - {e}" for e in self.errors)
        super().__init__(msg)


@dataclass(frozen=True)
class Source:
    """Who stated a piece of task information and when."""

    stated_by: str
    date: str
    note: str | None = None


@dataclass(frozen=True)
class Column:
    """One column of the data table.

    ``range`` is a declared interval ``[lower, upper]`` that contains every training sample;
    the loader verifies the containment. ``derivative_of`` names the state whose sampled time
    derivative the column holds (role ``state_derivative`` only).
    """

    name: str
    roles: tuple[str, ...]
    unit: str
    description: str
    symbol: str | None = None
    range: tuple[float, float] | None = None
    derivative_of: str | None = None


@dataclass(frozen=True)
class Delay:
    """A delayed variable of a NARX task: ``name[k] = variable[k − lag]``."""

    name: str
    variable: str
    lag: int


@dataclass(frozen=True)
class Dynamics:
    """Dynamic settings; absent for a static task.

    ``measurement`` is the expression of the measurement equation ``y = h(x, u)`` over the states and inputs.
    ``shift_equations`` maps each delayed variable to the expression of its next value (NARX
    only), for example ``{"y_d2": "y_d1"}`` for ``y_d2[k+1] = y_d1[k]``.
    """

    sampling_period: float
    states: tuple[str, ...]
    inputs: tuple[str, ...]
    measurement: str
    input_hold: str = "zero_order"
    integrator: str = "rk4"
    substeps: int = 1
    delays: tuple[Delay, ...] = ()
    shift_equations: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FailureLimit:
    """A numerical failure limit for one simulated state or output."""

    variable: str
    lower: float
    upper: float
    unit: str
    justification: str


@dataclass(frozen=True)
class Evaluation:
    """Evaluation settings.

    ``time_limit_s`` is the evaluation time limit of a candidate;
    ``symbolic_time_limit_s`` bounds each symbolic verification attempt of a requirement or a
    reference comparison, after which the attempt counts as inconclusive; ``None``
    means that the task declares no such limit. ``horizon`` (simulation mode only; ``None``: not
    used) is the number of simulated samples after the initialization samples over which the
    harness evaluates the training and validation data: every trajectory of these data is cut
    into consecutive segments of that length, each started from the measured state, so that the
    training and validation errors are simulation errors over the same horizon as the errors on
    test trajectories of that length (:func:`aspire_sysid.evaluate.data.segments`). The test
    files are evaluated as they are. The horizon is a setting of the harness's evaluation and is
    not part of the public view of the task.
    """

    mode: str
    initialization: int
    scoring: str
    failure_limits: tuple[FailureLimit, ...]
    time_limit_s: float
    symbolic_time_limit_s: float | None = None
    horizon: int | None = None

    def scoring_indices(self, n_samples: int) -> range:
        """The 0-based scoring interval ``I`` of one trajectory with ``n_samples`` samples.

 For ``after_initialization`` the interval is ``initialization, …,
        n_samples − 1``; for ``all_samples`` it is ``0, …, n_samples − 1``.
        """
        start = 0 if self.scoring == "all_samples" else self.initialization
        return range(min(start, n_samples), n_samples)


@dataclass(frozen=True)
class DataSpec:
    """Agent-visible data of a task.

    ``train_path`` and ``val_path`` are absolute paths inside the task folder. ``source_names``
    maps ``train`` and ``val`` to the original recording names (for the user only; never shown
    to the agent).
    """

    train_path: Path
    val_path: Path | None
    trajectory_column: str | None
    noise: str | None
    preprocessing: str | None
    source_names: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class Constant:
    """A given constant."""

    name: str
    value: float
    unit: str
    source: str


@dataclass(frozen=True)
class AddedFunction:
    """A function added to the default list, with its interpretation."""

    name: str
    arguments: tuple[str, ...]
    definition: str
    domain: str


@dataclass(frozen=True)
class Tolerance:
    """Tolerance of a formal requirement, with its unit."""

    value: float
    unit: str


@dataclass(frozen=True)
class Requirement:
    """A formal requirement of one of the nine types.

    Common fields: ``id``, ``type``, ``target`` (an expression key, or the output column name
    for the model output), ``variables`` (the arguments the requirement ranges over), ``domain``
    (``{"box": {variable: (lower, upper)}}`` or ``{"points": [{variable: value}, …]}``),
    ``tolerance``, ``verification``, ``exclude_on_violation`` (default true) with
    ``exception`` (the source of the explicit user instruction when false), ``source`` and an
    optional ``statement`` in words.

    Type-specific fields are kept in ``params``:

    - ``symmetry``: ``transform`` (variable → expression) and ``factor`` (1 or −1):
      ``f(T(v)) = factor · f(v)``;
    - ``monotonicity``: ``variable``, ``direction`` (``increasing`` or ``decreasing``);
    - ``parity``: ``parity`` (``even`` or ``odd``) under the joint sign flip of ``variables``;
    - ``exact_value``: ``value``, the target value at every point of ``domain.points``;
    - ``inequality``: ``relation``, a relation over the target name and the variables;
    - ``curvature``: ``variable``, ``sign`` (``convex`` or ``concave``);
    - ``limit``: ``variable``, ``approach`` (a number, ``oo`` or ``-oo``), ``value``;
    - ``equation``: ``equals``, the expression the target must equal on the domain;
    - ``relation_at_points``: ``relation`` over ``at1, at2, …``, the target values at the
      points of ``domain.points`` in their order.
    """

    id: str
    type: str
    target: str
    variables: tuple[str, ...]
    domain: dict[str, Any]
    tolerance: Tolerance
    verification: str
    exclude_on_violation: bool
    source: Source
    params: dict[str, Any]
    statement: str | None = None
    exception: Source | None = None


@dataclass(frozen=True)
class NLRequirement:
    """A requirement stated in natural language, kept verbatim."""

    id: str
    text: str
    source: Source


@dataclass(frozen=True)
class ContextFile:
    """A supporting file with the user's note; ``path`` is absolute."""

    path: Path
    note: str


@dataclass(frozen=True)
class DiscussionQuestion:
    """A discussion question of the task."""

    id: str
    text: str


@dataclass(frozen=True)
class Limits:
    """Limits on turns, elapsed execution time and cost."""

    turns: int
    seconds: float
    usd: float


@dataclass(frozen=True)
class Budget:
    """Round, session and analysis-exchange limits.

    ``analysis_exchange`` is ``None`` when the task declares no analysis exchanges.
    """

    round: Limits
    session: Limits
    analysis_exchange: Limits | None


@dataclass(frozen=True)
class SealedTestEntry:
    """One sealed test trajectory. Its file is resolved only by ``aspire_sysid.evaluate``."""

    trajectory: str
    source_name: str | None
    _file: str = field(repr=False)


@dataclass(frozen=True)
class SealedReferenceEntry:
    """The sealed reference expression. Its file is resolved only by ``aspire_sysid.evaluate``."""

    domain: dict[str, Any]
    _file: str = field(repr=False)


@dataclass(frozen=True)
class SealedPart:
    """The sealed part of a task: test trajectories and reference.

    The loader records the declared relative locations but never resolves or opens them; only
    :mod:`aspire_sysid.evaluate.sealed` does.
    """

    test: tuple[SealedTestEntry, ...]
    reference: SealedReferenceEntry | None

    @property
    def n_test_trajectories(self) -> int:
        """Number of sealed test trajectories (0 means: no ranking)."""
        return len(self.test)


@dataclass(frozen=True)
class TaskSpec:
    """A loaded task specification, schema version 1.

    ``task_dir`` is the absolute task folder. Every field except ``data.source_names`` and
    ``sealed`` may be shown to the agent; :func:`aspire_sysid.task.public.public_view` returns
    exactly that part.
    """

    task_dir: Path
    schema_version: int
    id: str
    title: str
    formulation: str
    description: str | None
    intended_use: str | None
    columns: tuple[Column, ...]
    dynamics: Dynamics | None
    evaluation: Evaluation
    data: DataSpec
    constants: tuple[Constant, ...]
    functions: tuple[str, ...]
    added_functions: tuple[AddedFunction, ...]
    requirements: tuple[Requirement, ...]
    requirements_nl: tuple[NLRequirement, ...]
    literature: tuple[str, ...]
    context: tuple[ContextFile, ...]
    discussion_questions: tuple[DiscussionQuestion, ...]
    pool_cap: int
    budget: Budget
    sealed: SealedPart
    roles_defaulted: bool = False

    # -- derived views -------------------------------------------------------------------

    @property
    def column_names(self) -> tuple[str, ...]:
        """Names of the model variables in table order (the trajectory column excluded)."""
        return tuple(c.name for c in self.columns)

    def column(self, name: str) -> Column:
        """The column called ``name`` (KeyError if absent)."""
        for c in self.columns:
            if c.name == name:
                return c
        raise KeyError(name)

    @property
    def output(self) -> str:
        """The name of the single output column."""
        return next(c.name for c in self.columns if "output" in c.roles)

    @property
    def inputs(self) -> tuple[str, ...]:
        """Input columns: the declared inputs, in table order for a static task."""
        if self.dynamics is not None:
            return self.dynamics.inputs
        return tuple(c.name for c in self.columns if "input" in c.roles)

    @property
    def states(self) -> tuple[str, ...]:
        """Declared states; empty for a static task."""
        return self.dynamics.states if self.dynamics is not None else ()

    @property
    def expression_keys(self) -> tuple[str, ...]:
        """The required expression keys of a candidate (see :func:`required_expression_keys`)."""
        return required_expression_keys(self.formulation, self.output, self.states)

    @property
    def argument_names(self) -> tuple[str, ...]:
        """Variables an expression may use: see :func:`argument_names`."""
        delays = self.dynamics.delays if self.dynamics is not None else ()
        return argument_names(self.formulation, self.inputs, self.states, delays)

    @property
    def constant_names(self) -> tuple[str, ...]:
        """Names of the given constants."""
        return tuple(c.name for c in self.constants)


def required_expression_keys(formulation: str, output: str, states: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """The expression keys a candidate must provide (rule E5).

    static: the output column name; continuous: ``d<state>`` per state; discrete:
    ``<state>_next`` per state; narx: ``<output>_next`` only (the shift equations of the
    delayed variables are known and supplied by the task).
    """
    if formulation == "static":
        return (output,)
    if formulation == "continuous":
        return tuple(f"d{s}" for s in states)
    if formulation == "discrete":
        return tuple(f"{s}_next" for s in states)
    if formulation == "narx":
        return (f"{output}_next",)
    raise ValueError(f"unknown formulation {formulation!r}")


def argument_names(
    formulation: str,
    inputs: tuple[str, ...] | list[str],
    states: tuple[str, ...] | list[str],
    delays: tuple[Delay, ...] | list[Delay] = (),
) -> tuple[str, ...]:
    """Variables a candidate expression may contain.

    static: the inputs; continuous and discrete: the states, then the inputs; narx: the output
    (the first state component), the delayed variables in declared order, then the inputs.
    A state-derivative column is never an argument.
    """
    if formulation == "static":
        return tuple(inputs)
    if formulation in ("continuous", "discrete"):
        return tuple(states) + tuple(inputs)
    if formulation == "narx":
        return tuple(states) + tuple(d.name for d in delays) + tuple(inputs)
    raise ValueError(f"unknown formulation {formulation!r}")
