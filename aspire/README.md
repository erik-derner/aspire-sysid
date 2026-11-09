# aspire-sysid: the harness of ASPIRE

ASPIRE (Agentic System-identification Platform for Iterative Reasoning and Exploration) consists
of two parts. The **harness** is the software in
this folder: it builds the task brief, provisions the working directory, sends the requests to
the language model, executes the tool calls that the language model requests, enforces the
budget (the limits on turns, elapsed time and cost of a round), checks the candidate files,
evaluates the candidates on sealed test data and records every event. The **agent** is the
language model that carries out the identification; it reaches files only through the tools
that the harness executes. The method is described in the paper.

## Overview for users

**Quick start.** `QUICKSTART.md` in the repository root gives the shortest sequence of steps from
a computer without Python to the running web app (`aspire web`) on Windows, Linux and macOS.

**Install.** Python 3.11 or later. From the repository root:

    pip install -e "aspire[runner]"      # the harness and the vendor adapters (openai, anthropic)
    aspire --version

The console script `aspire` and the vendor adapters need the editable installation.

**Commands** (`aspire <command> --help` gives the options):

| Command | Purpose | Section |
|---|---|---|
| `aspire prices` | the dated price schedule | "Language models and cost" |
| `aspire task validate <task-dir>`, `aspire task show <task-dir>` | validate a task folder, including its sealed part; print the public view | "Tasks" |
| `aspire brief <task-dir>`, `aspire format`, `aspire prompt` | render the task brief, the format reference `FORMAT.md` and the system prompt | "Task brief, system prompts and the working directory" |
| `aspire check <working-dir> [--task <task-dir>]` | the file and expression checks | "Model files and checks" |
| `aspire evaluate <task-dir> <working-dir> --out <folder>` | evaluate a pool on the sealed data | "Evaluation" |
| `aspire record show <run-dir>`, `aspire record verify <run-dir>` | summary of a run record; offline recomputation of its evaluation | "Records and exports" |
| `aspire export <run-dir> ... [--python] [--matlab]` | Python and Matlab exports | "Records and exports" |
| `aspire experiment run <experiment-dir> [--dry-run] [--resume]`, `status`, `aggregate`, `report`, `export`, `agent-env` | the runs of an experiment (one task, repeated runs), their state, their aggregation, the HTML report, the agent's Python environment | "Experiments", "Report" |
| `aspire session <task-dir>` or `aspire session --train <file> [--val <file>] [--test <file> ...]` | interactive operation on the terminal, from a task folder or from data files (task interview) | "Interactive operation" |
| `aspire record report <session-dir>` | the HTML report of a session, written again | "Interactive operation" |
| `aspire web`, or `aspire session ... --web` | interactive operation in the browser instead of on the terminal | "Interactive operation", "Web app" |

**Where things are.** Tasks in `tasks/<task-id>/`, experiments in `experiments/<id>/`
(`experiment.yaml`, run folders `runs/<run-id>/`, the dry-run output `dry-run/`, which git
ignores), working directories of the agent under `<system temp>/aspire-runs/` outside the
repository. Before a real run: the API key in `.env` at the repository root, the agent's Python
environment (`aspire experiment agent-env`, section "Experiments"), a committed state of `aspire/`
and `tasks/`, and a dry run of the experiment (`--dry-run`, no cost).

**What the harness does not guarantee.** The trust zones below separate the task store, the
harness and the working directory by location and by command filters, not by an operating-system
boundary. The agent's commands run as the same operating-system user as the harness; a program
the agent writes can read any file that user can read, including the sealed test data, and the
agent's shell has network access (there is one tool configuration with every tool).
The exact limits are stated in "Tool policy and its limits" and in
"Experiments" (working directories, API key); full isolation needs a container, a virtual
machine or a separate operating-system user, which this harness does not provide. The post-run
leak scan detects sealed values that appear in the transcript or in a file, not test data that a
program read and used silently.

**Windows.** The experiments were run on Windows; the harness was developed and tested on Linux.
Windows-specific code: the job object that ends every process of an agent command
(`agent/shell.py`), the job object that ends the worker processes with the grid
(`experiment/procs.py`), the re-launch of `aspire experiment run` under a copy of the interpreter
named `aspire-host.exe` (`experiment/host.py`), and process identification by creation time
(`experiment/procs.py`). The renamed interpreter is a copy of the base interpreter with its DLLs,
so that a virtual environment does not start a child named `python.exe`; the sealing filter
covers the `cmd.exe` path forms `\Users\...`, `\` and `%TEMP%`; text files are written with LF
line endings. On Windows the agent's shell is `cmd.exe`. The
re-execution of `aspire session` without the key in its process image is POSIX-only; on Windows a
key taken from the environment variable stays in the environment block with which the session
process started, so `.env` is the safer source there (sections "Experiments" and
"Interactive operation").

## Layout

The distribution is named `aspire-sysid` and the import
package `aspire_sysid`, because the name `aspire` is taken on the Python Package Index (PyPI).

| Path | Content |
|---|---|
| `pyproject.toml` | distribution `aspire-sysid`, console script `aspire`, pytest configuration |
| `aspire_sysid/task/` | task specification: schema (`schema.py`), loader (`loader.py`), full validation (`validate.py`), public view (`public.py`), provisioning of the working directory (`provision.py`) |
| `aspire_sysid/model/` | the check module (`checks.py`, copied into every working directory as `check_submission.py`) with the restricted expression parser, the model and pool files and rules F1 to P1; the harness side (`workspace.py`): check configuration, checking files, in-process checks, example model files |
| `aspire_sysid/evaluate/` | sealed access (`sealed.py`) and leak scanner (`leaks.py`); evaluation: trajectories (`data.py`), numerical form of the expressions (`compiled.py`), evaluation modes and numerical failures (`predict.py`), error measures and score (`metrics.py`, `errors.py`), requirements (`constraints.py` with `symbolic.py`, `symbolic_jobs.py`, `interval.py`), complexity and structures (`complexity.py`), sensitivity rank test (`sensitivity.py`), reference comparison (`reference.py`), pool evaluation, eligibility, ranking and permitted view (`pool.py`), plots (`plots.py`), reports (`report.py`); blind variants: mapping and requirement diagnostic (`blind.py`) |
| `aspire_sysid/agent/` | provider adapters (`providers.py`), price schedule (`prices.py`), turn loop (`loop.py`), execution clock and budget tracker (`budget.py`), tools and their registry (`tools.py`), command policy and shell environment (`policy.py`), commands with process-tree termination (`shell.py`), tool configurations (`config.py`), event sink (`events.py`), environment probe (`probe.py`) |
| `aspire_sysid/session/` | interactive operation: the session (`session.py`), the `ask_user` tool (`ask_user.py`), the permitted-results filter (`permitted.py`), task changes by the user (`changes.py`), the user channel (`channel.py`), the subcommand `aspire session` (`cli.py`) |
| `aspire_sysid/brief/` | execution messages (`messages.py`); task brief `TASK.md` (`render.py`), system prompts, helper prompt and first user message (`prompts.py`), provisioning of the working directory and hashes (`workspace.py`) |
| `aspire_sysid/record/` | JSON Lines transcript and its reader (`transcript.py`), dataset provenance record (`provenance.py`), run record and offline recomputation of the evaluation (`run_record.py`) |
| `aspire_sysid/export/` | Python export (`python_export.py`), Matlab export for the Matlab framework (`matlab_export.py`), Matlab and NumPy printers and the restricted Matlab translator (`printing.py`), runs in GNU Octave (`octave.py`), the evaluated pool read back from a record (`common.py`) |
| `aspire_sysid/experiment/` | experiment configuration (`experiment.py`), working directories outside the repository (`workspace.py`), one run (`runner.py`), grid with crash-resume and lock (`grid.py`, `worker.py`), host-process protection (`host.py`), dry-run agent (`dryrun.py`), aggregation (`aggregate.py`), agent environment (`agentenv.py`), API key (`credentials.py`), web fetch backend (`web.py`), subcommand `aspire experiment` (`commands.py`) |
| `aspire_sysid/cli.py` | console script `aspire` with subcommands |
| `configs/prices.yaml` | dated price schedule |
| `configs/models.yaml` | accepted model identifiers without a date (OpenAI models without a dated snapshot, Anthropic models) |
| `configs/tools.yaml` | the tool configuration: one configuration with every tool |

Tasks are stored in `tasks/<task-id>/` and experiments in `experiments/<experiment-id>/` at the
repository root.

## Trust zones

The harness separates three zones.

1. The **task store** `tasks/<task-id>/` holds the task specification, the training and
   validation data, and the sealed test data (`test/`) and sealed reference expression
   (`reference/`). "Sealed" means inaccessible through the agent's files, tools and
   conversation.
2. The **harness** reads the whole task store. Only `aspire_sysid/evaluate/` opens `test/` and
   `reference/`; no other module receives their paths.
3. The **working directory** of a run, `<workspace root>/[dry-run/]<random>/workspace/`
   outside every git repository (default workspace root `<system temp>/aspire-runs`; section
   "Experiments"), receives the brief `TASK.md`, the training and validation data, the
   supporting files, the model file format, the checking script `check_submission.py` and an
   empty `models/` folder. The agent works only there. At the end of the run the harness copies
   it into the run folder `experiments/<id>/runs/<run>/workspace/` for the record.

## Tasks

A task is a folder `tasks/<task-id>/` at the repository root; its format (schema version 1) is
documented in `tasks/README.md`. `aspire task validate <task-dir>` validates a task folder,
including its sealed part; `aspire task show <task-dir>` prints the public view, the part of the
specification that may be shown to the agent. Only `aspire_sysid/evaluate/` opens the sealed
folders `test/` and `reference/`; `aspire_sysid.evaluate.leaks.scan_for_sealed_leaks` searches
files and texts for sealed information.

**Blind task variants**. A blind variant is a task folder
`tasks/task-<four characters>/` that `tasks/make_blind.py` generates from a described task: the
data values, the split into training, validation and test data, T_s, the column roles, the
evaluation settings, the failure limits, the budget, the pool limit and the permitted functions
are kept; the columns are renamed to `y` (output) and `x1, x2, ...` (other inputs and states), a
state derivative to `d<state>`; units are `not supplied` (the schema's `UNIT_NOT_SUPPLIED`, which
the brief renders verbatim); description, intended use, requirements, literature, supporting
files, discussion questions, constants, symbols, column descriptions and recording names are
omitted, the noise and preprocessing statements are rewritten neutrally in the blind names, and the declared ranges are
the minimum and maximum of the training data. The brief renders every absent field as "The task
gives no ..." or "not supplied". A blind variant is an ordinary task: it has its own experiment,
and no module of the harness links it to the described task. The generator documents how each blind folder
was made in `tasks/BLIND_MAPPING.md` and `tasks/blind_mapping.yaml`, outside every task folder, so
that no provisioning function can copy them; the harness reads neither file.

## Model files and checks

A **candidate** is one proposed model with its parameter information, estimation record and
discussion; the **pool** is the set of candidates delivered at the end of a round.
The agent writes one file per candidate, `models/<label>.json`, and one pool file,
`models/pool.json`, in the working directory. The **file
and expression checks** are implemented once, in `aspire_sysid/model/checks.py`,
which depends only on the Python standard library and SymPy. The harness writes a byte-identical
copy of it into the working directory as `check_submission.py`, together with the configuration
file `check_config.json` (`aspire_sysid.model.write_check_files`). The agent runs
`python check_submission.py` in the working directory; the harness runs the same functions
in-process (`aspire_sysid.model.check_workspace(workspace, task)`), with the configuration built
from the task and the training data read from the task store, so that an edited copy of either in
the working directory does not change the harness's verdict. `aspire check <workspace-dir>
[--task <task-dir>]` prints the same report from the command line.

### Candidate file `models/<label>.json`

The label of a candidate is its file name without `.json`: a letter, then up to 31 letters, digits, underscores
or hyphens. The file states neither a format version nor the label. An unknown field is rejected
(rule F1).

| Field | Content |
|---|---|
| `expressions` | required: one expression text per required key of the task formulation: the output column name for a static task, `d<state>` per state for a continuous-time task, `<state>_next` per state for a discrete-time task, `<output>_next` for a NARX task |
| `parameters` | required: the parameter table, one row per named quantity (fields below); repeated uses of a parameter share one row |
| `estimation` | required: the estimation record: `criterion`, `data`, `method`, `script`; each a non-empty text or list of texts |
| `discussion` | required: the four sections of the discussion in this order: `family`, `interpretation`, `origin`, `limitations`; non-empty texts |
| `answers` | required exactly when the task has discussion questions: the answer to every question, keyed by the question identifier (`Q1`, ...) |
| `predecessor` | optional, only in a later round of interactive operation: the label of the revised candidate of the previous pool version |

A parameter row has `name` (an identifier that differs from every column, delayed variable,
expression key, given constant, function name, `pi`, `E` and Python keyword), `value` (a finite
number), `unit` (`"-"` for a dimensionless quantity), `type` (`fitted`, `fixed` or `tied`),
`description` (what the parameter represents and, for a fixed value, where the value comes from;
rule P1) and, for a tied parameter only, `equation` (its defining equation over other parameters,
given constants, numbers, `pi` and `E`). The source and the starting value of a parameter are not
recorded per row: the estimation method states the starting values once. The harness computes the value of a tied parameter from
its equation, resolving chains of ties, with the numerical semantics below, and requires agreement
with the recorded value within the relative tolerance 1e-6 (absolute tolerance 1e-12 at zero); a
disagreement is reported under rule E4. A fitted value that equals a mathematical or given
constant, for example 2/π, is accepted.

### Pool file `models/pool.json`

| Field | Content |
|---|---|
| `order` | required: the candidate labels in the agent's order, without repetitions; an empty list states that no candidate is justified, and the round then has no candidate to evaluate |
| `recommended` | the label of the recommended candidate, or `null` when the agent recommends none |
| `reason` | why the agent recommends this candidate, or why it recommends none |

The pool file states neither a format version, the task, the formulation nor the pool version; the
harness knows them (`Pool.pool_version` is the version that the harness assigned to the round).
The pool limit `pool_cap` of the task is not a rejection criterion: the first
`pool_cap` labels of `order` are evaluated, and the others are retained, checked, marked "outside
the limit" and not evaluated. A recommended label must lie within the limit. A flawed
recommendation (`recommended` absent, a label outside the order or the limit, `reason` missing or
empty) is reported as a recommendation issue under rule F1 with the remark that it does not affect
the acceptance of the candidates; the recommendation is then treated as absent
(`Pool.recommendation` is `None`), and the round passes if a candidate passes. Otherwise
`Pool.recommendation` is `{"label": ..., "reason": ...}`. An unknown field or an invalid order
makes the pool file invalid, and the round then does not pass.

### Configuration file `check_config.json`

Written by the harness from the public view of the task (`aspire_sysid.task.public_view`), so that
it contains nothing the brief does not show: `format_version` (2), `task_id`, `formulation`, `columns`
(name and roles), `arguments` (the variables an expression may use), `expression_keys`, `delays`
(NARX), `constants` (name and value), `functions` (permitted functions), `added_functions` (name,
arguments, definition), `discussion_questions` (identifiers), `pool_cap`, `trajectory_column`,
`train_file` (`data/train.csv`), `pool_version` and `previous_labels` (the labels of the previous
pool version in interactive operation, otherwise empty).

### Rules

The checking script and the harness print the same identifiers and texts
(`aspire_sysid.model.rule_table`); the brief does not list the rules, the script names the rule of every violation.

| Rule | Rejection |
|---|---|
| F1 | a required field of the model file or the pool file is missing or malformed (invalid JSON, duplicate keys, NaN, unknown fields, invalid or duplicate labels, invalid or clashing parameter names, an invalid predecessor, an oversized file, a link leaving the working directory; a flawed recommendation is reported under F1 without affecting the candidates) |
| F2 | a label in `order` has no file, or a file in `models/` is not in `order` |
| E1 | an expression does not follow the expression syntax, or contains a character, operator, name or function outside the task's permitted list |
| E2 | a symbol is neither a declared variable, a delayed variable, a parameter, a given constant, `pi` nor `E` |
| E3 | a parameter entry is not used in any expression or tie equation |
| E4 | a tie equation refers to a name that is not a parameter or given constant, forms a cycle, does not yield a finite real value, or disagrees with the recorded value |
| E5 | the expressions do not have exactly the required keys of the formulation |
| E6 | an expression yields a non-real or non-finite value on a training sample |
| P1 | a parameter row (fitted, fixed or tied) has no description (what the parameter represents and, for a fixed value, where the value comes from) |

Errors of one candidate never stop the checks of the others. A working directory
passes (script exit status 0) when the pool file is valid and at least one candidate within the
limit passes every check; otherwise the exit status is 1, and 2 when the configuration or the
training data cannot be read. The report gives, per passing candidate, the counts of fitted, fixed
and tied parameters and the count of non-integer numeric literals, counted in the canonical form
(`0.5` and `1e-3` count, `2`, `2.0`, `1e3` and `1/2` do not, and `0.5*x + 0.25*x`
counts once, as `0.75*x`). At most 100 model files of at most 1,000,000 bytes each are read (the
labels of the order first); a model file or pool file that is a link to a location outside the
working directory is not followed. An unexpected error while checking one file becomes an F1
issue of that file, and the other files are still checked.

**Rule E6** evaluates every resolved expression (tied parameters replaced by their equations),
with the parameter values, on every row of `data/train.csv`: static tasks at the inputs of each
row, dynamic tasks at the measured states and inputs of each row, NARX tasks with the delayed
variables built inside each trajectory, so that the first rows of a trajectory without the
required history are not evaluated and no value is taken across a trajectory boundary. A final
value that is infinite or not a number (NaN) is a rejection; the report names the first failing
row, its trajectory, the kind of failure in plain words and the number of failing rows.

**Numerical semantics** (`aspire_sysid.model.checks.numeric_function`, shared by rule E6, the tie
values and the evaluation). `numeric_function(expr, names)` compiles a
canonical expression into a Python function `f(*values) -> float` of the values of `names`, in
that order; `evaluate_expression(expr, values)` evaluates once, and `is_finite_value(y)` is the
E6 criterion. Every value is an IEEE 754 double, and numbers of the expression are rounded to the
nearest double. Intermediate results follow IEEE 754 and C99 without raising an error: an
overflow of `+ - * / **`, `exp`, `sinh` or `cosh` gives ±inf; a nonzero number divided by zero
gives ±inf; `0/0`, `inf - inf` and `0*inf` give NaN; `0**b` with `b < 0` gives inf; a negative
base with a non-integer exponent, `sqrt` or `log` of a negative number, `asin` or `acos` outside
[-1, 1], and `sin`, `cos`, `tan` of ±inf give NaN; `log(0)` is -inf; `sign` is -1, 0 or 1;
`Min` and `Max` return NaN when an argument is NaN; `Piecewise` returns the value of the first pair
whose condition holds and NaN when none holds; a comparison with NaN is false. Only the final value
is judged: it must be finite. For example, `a1/(1 + exp(-a1*x))` with `a1 = 1000` at `x = -1`
overflows in `exp` and yields 0, which is accepted. NumPy with float64 arrays and
`numpy.errstate(all="ignore")` follows the same rules; an evaluator in NumPy reaches the same
verdicts, with values that can differ in the last bits where the order of operations differs.
`Candidate.numeric_function(key)` is exactly the function that rule E6 evaluated, and
`numeric_function` applied to `Candidate.numeric_expressions[key]` gives the same values bit for
bit.

### Expressions

Expressions use the column names of the task and SymPy spelling. The default permitted functions
 are `sin cos tan asin acos atan atan2 sinh cosh tanh exp log sqrt Abs sign
Min Max Piecewise`, with the operators `+ - * / **`; `log` is the natural logarithm; `abs`, `min`
and `max` are accepted as aliases of `Abs`, `Min` and `Max` whenever these are permitted. π and e
are written `pi` and `E`; no column, constant or parameter may take these names. `log` and
`sqrt` take exactly one argument (write `log(x)/log(b)` for the logarithm to base `b`, and
`x**(1/n)` for another root). `Piecewise`
takes pairs `(value, condition)`, for example `Piecewise((a*x, (x > 0) & (x < 1)), (0, True))`;
conditions are comparisons `< <= > >=`, `Eq(a, b)` and `Ne(a, b)`, or `True`, combined with
`&`, `|` and `~`, each comparison in parentheses; comparisons are permitted only inside
`Piecewise` conditions, and a number or an arithmetic expression is not a condition. `^`, `==`, `and`, `or`, `not`, chained comparisons and `if ... else` are rejected
with a message that names the permitted form.

The parser does not execute arbitrary Python. The text must pass a character whitelist (letters,
digits, `_ + - * /  , .`, white space, `< > = & | ~`), contain no double underscore and have at
most 4000 characters. Python's parser turns it into a syntax tree without executing it; the tree
may contain only numbers, the declared names, calls of the permitted functions with their number
of arguments and without keyword arguments, the operators above and `Piecewise` pairs; attribute
access, subscripts, lambda expressions and every other construct are rejected. The harness then
builds the SymPy expression itself, node by node, from the admitted tree (so a name such as
`Float` or `Integer` is an ordinary name). Every node is bounded before or right after it is
built, so that no expression can exhaust time or memory and no wall-clock limit is needed: at
most 50 levels of true nesting (a sum or product of many terms is one level); no number of more
than 1000 decimal digits (numerator, denominator or magnitude of a float), and a power of numbers
is refused before it is computed if its result would exceed that size; numeric exponents at most
1024 in magnitude and real; at most 32 arguments of `Min` or `Max` (also after nested calls are
merged) and 32 pairs of a `Piecewise`; at most 10,000 distinct parts. Integer literals become
exact integers and decimal literals doubles.

**Canonical form.** Each node is built with SymPy's automatic evaluation, and the result is the
canonical form of the expression: numbers are folded (`2*3` is `6`, `sin(0)` is `0`), like terms
and factors are combined (`x + x` is `2*x`, `x/x` is `1`, `0*b1` is `0`), and simple identities
for real symbols are applied (`sqrt(x**2)` is `Abs(x)`, `E**x` is `exp(x)`). The checks, the
numerical evaluation and the exports use the canonical form; the agent's text is kept only for
the record (`Candidate.expression_texts`). Rule E3 is judged on the canonical form: in
`a1*x + 0*b1`, the parameter `b1` disappears and is unused.

The expressions written by the task author (the measurement equation, NARX shift equations,
requirement relations, definitions of added functions, the sealed reference expression) are parsed
by `aspire_sysid.task.expr`, not by the check module. The two parsers are kept separate on purpose:
task expressions are trusted input of the user, must admit a relation as the whole expression (a
requirement such as `domega*omega <= 0`) and placeholder names (`at1`, `at2`), and are validated
when the task is loaded; candidate expressions are untrusted input of the agent and pass the
restricted parser above. The function lists and the constant names of both parsers are
identical.

### Harness interface

`aspire_sysid.model` exports: `check_config_from_task(task)`, `write_check_files(task,
workspace_dir)`, `check_workspace(workspace_dir, task)` returning a `CheckReport` (with
`passed`, `pool`, `pool_issues`, `candidates` per label, `order`, `within_limit`, `outside_limit`,
`evaluated`, `recommendation_issues`, `folder_issues` and `text`), `load_candidate(path, task)` and `load_pool(path, task)`,
`example_model_files(task)` (a complete pool with one candidate that has one fitted, one fixed
and one tied parameter and passes the checks of the task; written by the dry run's scripted agent,
not shown to the agent), `rule_table`, and
`parse_expression`; `aspire_sysid.model.checks` also provides `numeric_function`,
`evaluate_expression`, `is_finite_value` and `rebuild` (a substitution under the same bounds). A
checked `Candidate` holds the canonical expressions as SymPy objects over real symbols
(`expressions`), the same with the tied parameters resolved (`resolved`), the arguments in task
order, the parameter table, the tie equations resolved to fitted and fixed parameters, the values
of all parameters (tied values computed by the harness), the estimation record, the discussion,
the answers, the predecessor and the literal counts; `numeric_expressions` substitutes all
values, and `numeric_function(key)` returns the function of the arguments that rule E6
evaluated.

## Evaluation

The evaluation is a pure function of the task specification and the candidate files
: `aspire_sysid.evaluate.evaluate_pool(task, models)` takes a working directory,
its `models/` folder or a `CheckReport`, and returns a `PoolEvaluation`. From the command line:

    aspire evaluate <task-dir> <working-dir or models-dir> --out <folder> [--no-plots]

prints a summary and writes `evaluation.json` and `evaluation.md` (the complete report for the
user, with the results on sealed data), `permitted.json` and `permitted.md` (the permitted view:
the part the agent may receive) and `plots/<label>_<group>.png`. JSON is written
with sorted keys; the same inputs give byte-identical files.

**Horizon of the training and validation errors**. A simulation error
grows with the length of the simulated trajectory. A task in simulation mode may declare
`evaluation.horizon`, the number of simulated samples of its test trajectories. The harness then
evaluates the training and validation data in consecutive segments of that length
(`aspire_sysid.evaluate.data.segments`): each segment starts from the measured state, and every
sample after the initialization samples of a trajectory is scored exactly once; the segment `j`
of trajectory `t` is named `t-j`. The test files are evaluated as they are, and the parameter
sensitivity diagnostic uses the uncut trajectories. The horizon is not part of the public view of
the task, and the brief does not state it. `turtlebot` declares 25: its training error is computed
on 18 segments instead of 3 trajectories of 150 samples.

Per candidate, in this order:

1. **File and expression checks**. Only the first `pool_cap` labels of the order are
   evaluated; later ones are checked and marked "outside the limit".
2. **Requirements**. Each formal requirement is reduced to a quantity `Q` that
   must satisfy `Q ≤ tol` on the declared box or points (`constraints.py` lists the reduction
   per type). The symbolic stage runs in a worker process that is terminated at the task's
   `symbolic_time_limit_s` (default 10 s; `symbolic.py` describes the mechanism, which works on
   Linux and Windows): constant evaluation, verified interval arithmetic with branch and bound
   (`interval.py`, `mpmath.iv`), SymPy `simplify` and `maximum`, SymPy `limit`. The sampling stage
   draws the declared number of points with the declared seed and confirms a violation at 30
   significant digits. No proof is accepted unless the target and the other expressions of the
   requirement are shown to be real and finite on the whole domain (interval arithmetic); a
   point where one is not is a counterexample. A strict relation `<` is treated like `<=` under
   the tolerance, so with tolerance 0 equality is accepted. Outcomes: proof (satisfied), counterexample (violated; excludes unless
   `exclude_on_violation` is false with the user's recorded instruction), inconclusive and
   unavailable (both unresolved). Sampling without a violation is inconclusive, never a proof.
   Requirements in natural language are unresolved and assessed by the human.
3. **Output errors** on the test, training and validation data, each
   trajectory on its own (`predict.py`): algebraic evaluation for static tasks; one-step
   prediction from the measured state, or simulation from one initial state per trajectory, for
   dynamic tasks; classical fourth-order Runge–Kutta with the declared substeps and zero-order
   hold of `u[k]` over `[t_k, t_{k+1})`; `ŷ[k] = h(x[k], u[k])` with the input at the same index
   (the measurement equation); NARX simulation with the model's own outputs. A value outside a failure limit,
   a non-real or non-finite value, an evaluation error or the evaluation time limit (per candidate
   and data group) is a numerical failure with trajectory, index, time, reason and variable; the
   error on the samples before it is a prefix diagnostic. Error measures per trajectory (sum of
   squared errors, RMSE, NRMSE and R²; population σ; NRMSE and R² undefined for σ = 0) and the pooled score `S`, the root-mean-square error pooled over all scored samples of
   the test trajectories.
4. **Diagnostics**: fitted, fixed and tied parameter counts, non-integer
   literals and the expression-tree node count (convention in `complexity.py`); distinct
   structures (fitted parameters renamed P1..Pn, fixed values and repeated uses kept, ties
   resolved); the local rank of the sensitivity matrix of the formulation's fitting target on
   the fitting data named in the estimation record (analytic derivatives through the tie
   equations, row and column scaling, threshold `s_i/s_1 > 1e-8`, dependent groups); the
   comparison with a sealed reference expression (proven equivalence, established
   non-equivalence or unresolved; every number is the exact decimal it is written as, candidate
   literals converted before SymPy combines them, parameter values in their shortest decimal
   form; proven equivalence also requires binary64 agreement within 1e-12 relative at every
   sampled point; numerical agreement at 2000 sampled points reported separately).

**Scripts.** The symbolic stages run in a worker process started with the `spawn` method, which
imports the calling script's main module. A script that calls `evaluate_pool` must therefore
protect its entry point with `if __name__ == "__main__":`; otherwise the worker cannot start, and
every symbolic stage is reported as unavailable with that explanation (the sampling stages still
run). The console script `aspire` satisfies this.

**Eligibility and ranking**. A candidate is eligible when it passed the checks, has
no demonstrated violation of a mandatory requirement, and finished on every test trajectory. The
eligible candidates are ranked by increasing `S`; consecutive scores within a relative 1e-12 are
a numerical tie (shared rank, agent's order). The best five ranks (with all candidates tied at
rank five) are reported under the label "oracle-based selection on test data" with the number of
candidates considered and the pool size. Without test data no ranking is made. The agent's
recommendation is reported separately, with harness notes on exclusions and unresolved
requirements.

## Language models and cost

`aspire_sysid.agent.providers` defines one vendor-neutral interface, `Provider.complete`, with
adapters for the OpenAI Responses API and the Anthropic Messages API, and a
`ScriptedProvider` for the dry run. The OpenAI adapter uses the Responses API, not Chat
Completions: from GPT-5.4 on, Chat Completions rejects function tools together with a
reasoning effort other than `none`, carries no reasoning between turns and returns no reasoning
summaries. The Responses API is used statelessly (`store: false`): every request carries the
system prompt, the complete history and the tool descriptions, and the reasoning items of
earlier responses are sent back with their encrypted content. Both adapters pass the reasoning
settings of the tool configuration (`requests.reasoning_effort`, `requests.reasoning_summary`;
effort `medium` and summary `auto`) and return the vendor's readable
reasoning summaries, never the raw chain of thought. The transcript records the summaries and
the vendor's output items verbatim (`response.reasoning`, `response.vendor_items`), so that every
request remains reconstructable. The adapters import the vendor software development kit only
when constructed and read the API key only from the environment variables `OPENAI_API_KEY` and
`ANTHROPIC_API_KEY`. A model is named by its dated snapshot identifier where the vendor publishes
one: an OpenAI identifier must end with its snapshot date (`gpt-5.5-2026-04-23`), and a floating
alias such as `gpt-5.5` is rejected. A model for which the vendor publishes no dated snapshot is
accepted when `configs/models.yaml` lists its identifier (`openai.undated`; Anthropic identifiers
under `anthropic.pinned`); results obtained with an undated identifier are reported with the dates
of the runs. The default model (`default_model` of `configs/models.yaml`) is `gpt-6.1-sol`, which
has no dated snapshot; the experiments of the paper used it.

The cost of a request is computed from `configs/prices.yaml`, which lists each price with the
date of its verification and its source; `aspire prices` prints it. The schedule contains
`gpt-6.1-sol`, the default model, at 2.00 USD per 1,000,000 input tokens and 10.00 USD per
1,000,000 output tokens, verified on 2026-10-05 on its official model page, and
`gpt-5.5-2026-04-23` at 5.00 and 30.00 USD, verified on 2026-08-02 on the official OpenAI API
pricing documentation. Cached
input tokens are charged at the full input price, because no cached-input price has been
verified; the computed cost is therefore an upper bound for requests that used the vendor's
cache. A model without an entry has no cost and is rejected. Not modeled: OpenAI prices a
request of `gpt-5.5` with more than 272,000 input tokens at 2 times the input and 1.5 times the
output price (model page, consulted 2026-09-28).

Web search has a fee per call in addition to the tokens: 0.01 USD per call for
`gpt-5.5-2026-04-23` ("$10.00 / 1k calls + search content tokens billed at model rates", OpenAI
API pricing documentation, built-in tools, consulted 2026-10-05; field `web_search_call` of the
schedule with its own verification date). The content that a search returns to the model is part
of the input tokens of the response. The harness charges the fee for every web search action that
the vendor reports in a response (`search`, `open_page`, `find_in_page`); if the vendor bills
only the `search` actions, the computed cost exceeds the billed cost and never falls below it.
A model whose entry has no verified fee cannot use the vendor's web search: the cost computation
stops with an error instead of assuming a fee. The budget tracker sees the fee with the cost of
the response in which the searches were made, that is, after they were made.

## Agent execution

A **turn** is one completed language-model response to the system prompt, the conversation
history and the descriptions of the available tools. A **round** is one attempt
to produce or revise a pool within limits on turns, elapsed execution time and cost, the
**budget**. `aspire_sysid.agent.run_round` runs one round:

    result = run_round(provider, system_prompt, first_user_message, workspace, task, config,
                       limits, sink, evaluate_callback=None, parent_tracker=None, history=,
                       pool_version=1, previous_labels=, registry=None, clock=None, ...)

`workspace` is prepared by `aspire_sysid.agent.prepare_workspace(task, workspace)`, which delegates
to `aspire_sysid.brief.provision_workspace` (section "Task brief, system prompts and the working
directory");
`config` is `load_tool_config`; `limits` is normally
`task.budget.round`; `sink` receives the events; `evaluate_callback(report, labels)` evaluates
the checked candidates. The result states the outcome (`completed`,
`checks_failed_twice`, `budget_turns`, `budget_time`, `budget_cost` or `error`), the turns,
tokens, cost, elapsed execution time, user waiting time, the excess over each limit, the
complete, incomplete and missing candidate files, the check report, the evaluated labels and
the conversation history. `run_analysis_exchange` runs an analysis exchange of interactive
operation, which the agent's first text-only answer ends.

Rules implemented by the loop (details in the docstring of `aspire_sysid/agent/loop.py`):

1. **Completion message.** A response without tool requests whose last non-empty line is
   exactly `DONE`. A response with tool requests is executed normally even if its text says
   `DONE`.
2. **Text-only reply.** It counts as a turn and receives the continuation message.
3. **Checks after `DONE`.** The harness runs the checks itself. A valid pool file with at least
   one passing candidate within the pool limit ends the round (`completed`). Otherwise the
   check-failure message lists the reasons with rule identifiers, once; the correction runs
   within the remaining budget of the same tracker; a second failed `DONE` ends the round
   (`checks_failed_twice`).
4. **Budget.** One tracker per round (`aspire_sysid.agent.budget.BudgetTracker`), shared by the
   correction attempt and the helper agents and tested before every request and every tool
   execution; the request timeout is the remaining round time; the excess is recorded. The
   trackers form a chain (helper, round, session), so that every charge counts toward the
   enclosing totals when it occurs. The execution clock (`ExecutionClock`) can be paused while
   the harness waits for the user (`with ctx.clock.paused: ...`); the waiting time is
   recorded separately.
5. **Reminder.** Once per round, when the turns or the cost first reach 80 % of the limit and no
   candidate file exists in `models/`.
6. **Termination.** At a budget limit the budget-termination message is recorded, complete
   candidate files are checked and the passing ones evaluated, and incomplete and missing
   files are reported separately. A request that fails after a limit has been reached (cut off
   by its timeout, which is the remaining round time) counts as that budget limit, not as an
   error. When the pool file is missing or invalid at a budget stop or an error, the candidates
   that pass the checks are evaluated in file-name order up to the pool limit, and the result
   marks the order as assigned by the harness (`order_assigned_by_harness`); at
   `checks_failed_twice` nothing is evaluated. The round's elapsed time and excess are fixed
   when the conversation stops; the final checks and the evaluation are timed separately
   (`checks_s`, `evaluation_s`).
7. **Unreported usage.** A response without a usage record is charged an estimate (output
   tokens = `max_output_tokens`; input tokens = request characters / 2), marked in the record.

The execution messages (continuation, reminder, check failure, budget termination and the
messages of interactive operation) are stored verbatim in `aspire_sysid/brief/messages.py`.

**Events.** The loop records every event through `EventSink.emit(kind, **fields)`
(`aspire_sysid/agent/events.py`): round start (system prompt and its SHA-256 digest, tool
configuration, tool descriptions, model, limits, environment probe, price entry), user
message, request (the messages added since the previous request), response (text, tool calls,
usage, cost, round totals), tool call, tool result (complete output and the text sent to the
agent), continuation, reminder, check outcome, check-failure message, correction, budget
termination, helper start and end, evaluation and round end. Every event carries task,
session, round, pool version, agent, sequence number, timestamp and elapsed execution time,
and is JSON-serializable; the transcript writer (section "Records and exports") writes it as
JSON Lines. `MemorySink` keeps the
events in memory.

### Tools

There is one tool configuration. The agent always has every tool; the harness has no switch that removes one. A user who wants to restrict the use of a
tool, for example to forbid web access, states the restriction in the task description. The
harness does not enforce such a restriction; the transcript records every tool call, so that the
user can check it.

| Tool | Content |
|---|---|
| `read_file`, `write_file`, `list_files` | files of the working directory; absolute paths, `..` escapes and symbolic links leaving the directory are refused |
| `run_shell` | one command in the working directory; limit min(`shell.limit_s` = 600 s, remaining round time), stated in the tool description; the processes the command started end at the limit and when the command finishes |
| `web_fetch` | through an injectable backend, which receives min(600 s, remaining round time) as its timeout; without a backend the tool reports that it is unavailable. Real runs use `experiment/web.py` (`urllib_fetch`); addresses that contain a denied substring (`web.denied_url_substrings`: this repository, which holds the test data, and addresses of this computer, where the web app shows test results to the user) are refused |
| `web_search` | with a model of OpenAI: the vendor's built-in web search tool of the Responses API (`{"type": "web_search"}`, default settings). The vendor executes the searches inside a response; the harness executes nothing, records every search action (`search`, `open_page`, `find_in_page`) with its query or address and the addresses consulted (response event, field `web_searches`), and charges the fee per call. With any other provider (Anthropic adapter, scripted agent) it is a function tool that reports that it is unavailable, unless a search backend is injected |
| `install_package` | `pip install <requirement>` into a package folder of the run; options, URLs and paths are refused |
| `start_helper` | a helper agent with the same tools except `start_helper`, limits within the remaining allowance, run synchronously |

The settings are in `configs/tools.yaml` (shell limit, output caps, `max_output_tokens`,
reasoning settings, helper and web settings). The file must name every tool; the loader refuses
a file that leaves one out. The records name the one configuration `open`
(`configuration.name`). The tool registry (`aspire_sysid.agent.tools.ToolRegistry`) accepts
further tools; interactive operation registers `ask_user` there. The environment probe (`aspire_sysid.agent.probe.probe_environment`) lists the installed
packages and their versions of the interpreter that the agent's shell uses and names PySR,
gplearn or PySINDy only when the distribution is installed and its module is found; a failed
probe yields "unknown: the environment probe failed". The shell and the probe use the same
interpreter (`python_executable`, by default the harness's own), whose folder is first on the
shell's `PATH`; `run_round` refuses a probe of another interpreter.

### Tool policy and its limits

Every shell command runs with an environment from which variables that may hold credentials
are removed: names containing `KEY`, `TOKEN`, `SECRET`, `PASS`, `CREDENTIAL`, `AUTH`,
`COOKIE`, `PRIVATE` or `WEBHOOK`, names ending in `_PWD` or `_DSN`, `DATABASE_URL`, vendor
and service prefixes (`OPENAI`, `ANTHROPIC`, `AWS_`, `GITHUB_`, ...), the whole `GIT_*` group
(including `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`,
`GIT_ALTERNATE_OBJECT_DIRECTORIES` and `GIT_CONFIG_*`), and any variable whose value contains
an address with user and password (`scheme://user:pass@host`). `GIT_CEILING_DIRECTORIES` is
set to the working directory's parent folder and the working directory, so that `git` started
in the working directory does not find an enclosing repository and cannot read the task store
from its history.

One filter reads the agent's command text before it runs, and a second one is used by the harness itself:

- the **sealing filter** refuses a command of the agent that names the task store,
  the repository of the harness, a path outside the working directory (absolute paths, `..`
  also when split by quotes or backslashes, `~` and `~name`, `$HOME`, drive letters, network
  shares), the root folder `/` as an argument, an absolute path with a pattern or variable in
  its first folder (`/h*/user`), `cd -`, `$OLDPWD`, `pushd`/`popd`, a parameter expansion that
  edits a value (`${PWD%/*}`), the parent of the current folder (`dirname "$PWD"`,
  `Path.cwd.parent`), a `git` command with `-C`, `--git-dir`, `--work-tree` or a `GIT_*`
  assignment, or the harness package `aspire_sysid`;
- the **network filter** is not applied to the agent's shell. It
  is a function of the policy module, used for the harness's own environment probe: it
  refuses a command that has a network program
  (`curl`, `wget`, `ssh`, ...), a package installer (`pip install`, `conda install`, ...) or a
  remote `git` operation in a command position (at the start or after `;`, `&&`, `|`, `(`,
  `$(`, possibly after `sudo`, `env` or a folder path), or that contains `python -m pip`, a
  PowerShell web command, a URL, or inline code importing or calling a Python network module.
  The scripts in the working directory that the command names are checked too: shell scripts
  with the same rules, other scripts with the code rules only (imports and calls of network
  modules, a network program as the first element of an argument list, a process call whose
  string starts with a network program, `-m pip`), so that ordinary words in comments and
  strings (`links`, `curl of the surface`) do not count. With the filter, the proxy variables of the shell point to an
  unreachable address and `pip` has no package index.

A third filter, the **host-process filter**, refuses
commands that would end the harness's own processes, which run as the same operating-system
user: `pkill` and `killall` except with exact matching (`pkill -x`, `killall -e`), an optional
signal and exact process names other than those of the Python interpreter or the harness
(`python*`, `py`, `pypy*`, `aspire*`, `worker`, `experiment`), so that no pattern (`pkill thon`, `pkill
.`, `pkill "^p"`) and no option such as `-f`, `-v`, `-u`, `-P`, `-g`, `-s` or `-r` passes; `kill -1`
in any signal spelling and `os.kill(-1, ...)`; `killall5`; finding and ending processes in one
command (`pgrep python | xargs kill`, ``kill $(pgrep ...)``, `ps ... | xargs kill`); ending the
parent process or its group (`kill $PPID`, `os.kill(os.getppid, ...)`,
`os.killpg(os.getpgid(os.getppid), ...)`, also in the scripts a command names); `taskkill /IM
python.exe`, `Stop-Process -Name python` and `wmic process ... delete`. Ending a process by its
number in a separate command (`kill 12345`) stays possible.

`read_file`, `write_file` and `list_files` refuse absolute paths, paths that resolve outside
the working directory through `..` or symbolic links, and files with more than one hard link
(a hard link made by a program can give a file outside the working directory a name inside
it). Processes started by a command end when the command ends: on POSIX the command's process
group is killed, and on Linux every process whose environment carries the command's random
marker `ASPIRE_SHELL_TOKEN` is killed as well (this ends processes that left the group with
`setsid` or a double fork); on Windows the command runs in a job object that ends all its
processes when it is closed.

**Limits.** These measures read text and follow processes; they do not isolate the agent.

1. Scripts named in a command are checked for network use only, never for paths. A script, or
   a module it imports, can open any absolute path that the operating-system user of the
   harness can read, including the task store.
2. A path assembled at run time, a symbolic link created by a program and then read by another
   program, or a command encoded so that the text does not show it, passes the filters.
3. A process that leaves its process group and also replaces its whole environment, or any
   process that leaves its group on a POSIX system without `/proc`, is not ended with the
   command.
4. `git` inside the working directory is confined by `GIT_CEILING_DIRECTORIES`; a program that
   opens the repository's object store directly is not.
5. The post-run leak scan (`aspire_sysid.evaluate.leaks`) searches the transcript and the files
   for sealed values; it cannot detect test data that a program read and used silently, for
   example for fitting, without writing them anywhere. In a transcript, the comparison of numbers
   with the test values skips the fields that the harness writes for its own record and never
   sends to the agent (`HARNESS_BOOKKEEPING_FIELDS`: costs, token counts, times, limits,
   counters), because such a number, for example a running cost total, can match a test value by
   chance. Everything the agent saw or wrote is compared.
6. The host-process filter reads command text only. A process ended by its number in a separate
   command (`ps`, then `kill 12345`), a signal sent by a program or script (`os.kill(pid, ...)`,
   `subprocess.run(["kill", ...])`), a command whose text hides the words (variables, `eval`,
   encodings), and on Windows `taskkill /PID` or `Stop-Process -Id` pass it and can end the grid
   runner or a run worker. Workers end with the grid, and `--resume` repeats the unfinished run.

The experiment runner therefore places the working directories outside every git repository, and
the interpreter of the agent's shell should be an environment without the harness package
installed (section "Experiments"). Full isolation requires an
operating-system sandbox (a container or virtual machine without network and without the task
store) or a separate operating-system user without read access to `tasks/`; this harness
provides neither.

## Task brief, system prompts and the working directory

The agent receives two texts in the working directory. Both are produced by plain code; no language model takes part in producing them.

The **task brief** `TASK.md` states what only this task determines.
`aspire_sysid.brief.render_brief(task, interactive=False)` renders it from the public view of the
task (`aspire_sysid.task.public_view`) alone; it never reads the sealed part or the recording
names. Its sections are: 1 system and intended use; 2 data (files, trajectories, `T_s`, the
variable table, noise, given constants); 3 what the agent delivers (expression keys and arguments,
the files, the recommendation sentence, the pool request, the task's questions; the functions only
when the task departs from the default list, which `FORMAT.md` states);
4 evaluation (evaluation mode, score, failure limits); 5 physical
requirements, only when the task states any; and limits and completion as the last section. The
brief of `turtlebot` has 644 whitespace-separated tokens, table separators included; the briefs of
`fermenter-pressure` and `friction-driven` have 960 and 1585, most of it the task's own
description and requirements.

The **format reference** `FORMAT.md` is one fixed text, the same for every task
(`aspire_sysid.brief.format_reference`, module `brief/reference.py`): the model
file format with an explanation of every field, what an expression may contain (variables, the
agent's parameters, constants, numbers and the default operators and functions in one list) and its
syntax, one general example, the
checking command and the writing rules for the agent's texts (eight rules). The example is on an
invented task with the input `q` and the output `z`, names that no task of the repository uses, so
that it cannot suggest a model structure for the task's variables; the example passes the file and
expression checks.

Decisions:

1. **Deterministic provisioning.** The tools and the installed software are stated in the
   environment description at the end of the system prompt, not in the brief. Two working
   directories provisioned for one task are identical byte for byte.
2. **Interactive operation.** The paragraph on `ask_user`, analysis requests, further rounds and
   the session limits is rendered only with `interactive=True`, because the agent of an autonomous
   round has no `ask_user` tool.
3. **No task word in `FORMAT.md` or in the checking script.** Both files reach described and blind
   working directories alike. `format_reference` stops when its text contains a
   word of a task (column names such as `theta`, model families such as Stribeck, systems such as
   pendulum or robot; `FORBIDDEN_WORDS` in `brief/reference.py`, checked case-insensitively as
   words); `model/checks.py` contains no such word either.
4. **Tolerance of a formal requirement.** The brief states the tolerance as the admissible
   violation margin in the unit of the checked quantity; the evaluation applies the same reading.
5. **Field explanations.** `FORMAT.md` explains every field from tables keyed by the field
   constants of the check module; a field without an explanation stops the rendering, so that the
   reference cannot fall behind a change of the file format.
6. **What the brief does not contain.** The error-measure formulas, the eligibility and ranking
   rules, the verification method of each requirement, the rule table of the checks and a
   per-task example are not shown to the agent. The checking script reports each
   violation with its rule text, and the evaluation report states the measures and the ranking for
   the human reader.

**System prompt** (`aspire_sysid.brief.render_system_prompt(configuration,
probe, interactive=False)`; `configuration` is the tool configuration object or `None` for the
one of `configs/tools.yaml`). The three paragraphs of the prompt verbatim, each on one line; the
first names `TASK.md` and `FORMAT.md`, the second states what the agent may do (files, code, web, installation, helper
agents, the installed symbolic-regression packages) and the third what it reports and what it cannot reach; the prompt
repeats nothing that the brief states; in interactive operation the interactive paragraph
appended; then, after one empty line, the environment description: the tool configuration and its
tools, the Python version of the agent's interpreter and every installed distribution with its
version from the environment probe, except the harness's own distribution `aspire-sysid`, about
which the description states nothing. Real runs should give the agent an interpreter without the
harness package installed (a separate environment, created with `aspire experiment agent-env`;
section "Experiments"). `{packages}` is filled with the installed symbolic-regression
packages among PySR, gplearn and PySINDy with their versions ("gplearn 0.4.2", "PySR 1.5.2 and
PySINDy 1.7.5"), with `none` when the probe found none of them, and with `none that the harness
could verify` when the probe failed; an uninstalled package is never named. The helper agents' prompt (`HELPER_SYSTEM_PROMPT`) and the first
user message of a round (`FIRST_USER_MESSAGE`) are harness texts in the same module. The
environment description also names the shell of `run_shell` (`shell_line`): on
Windows "run_shell passes each command to the Windows command interpreter cmd.exe, not to a POSIX
shell", with the note that POSIX here-documents do not work there; elsewhere `/bin/sh`. The line
is in the system prompt because the same statement in the `run_shell` tool description alone did
not keep the agent from writing a POSIX here-document as one of its first shell commands.
The helper prompt does not contain the line (the tool description does).

**Working directory.** `aspire_sysid.brief.provision_workspace(task, workspace_dir, configuration=None,
*, interactive=False)` is the single entry point that writes a working directory. It writes exactly
`TASK.md`, `FORMAT.md`, `data/train.csv`, `data/val.csv` (when present), `context/<file>`,
`check_submission.py`, `check_config.json` and the empty folder `models/`, refuses a non-empty
folder, and returns a `WorkspaceManifest` with every file and its SHA-256 digest, the digest of the
brief (`brief_sha256`) and the digest of `FORMAT.md` (`format_sha256`), which is the version of the
writing rules supplied to the agent. `text_hashes(brief, system_prompt)` returns the
SHA-256 digests of the UTF-8 bytes of both texts for the record; they equal the digest
of the file `TASK.md` and the `system_prompt_sha256` of the loop's `round_start` event.
`render_run_texts(task, configuration, probe, interactive=False)` returns the brief, the system
prompt, the first user message, the helper prompt and their digests in one `RunTexts` object.

**Command line and previews.**

    aspire brief <task-dir> [--interactive] [--out FILE] [--preview]
    aspire format [--out FILE] [--preview]
    aspire prompt [--interactive] [--python EXE] [--helper] [--preview]

With `--preview` a header with the command that regenerates the text precedes it; the header
carries no date or revision.

## Records and exports

The harness writes a reproducible record of every run and exports of every evaluated pool as
Python and Matlab files. A **run** is one session for one task and tool configuration; its **run folder** (for an experiment `experiments/<id>/runs/<run>/`, written by the experiment runner) holds

| Path | Content |
|---|---|
| `transcript.jsonl` | the transcript (below), written during the run |
| `run_record.json` | the run record (below) |
| `provenance.json` | the dataset provenance record (below) |
| `pools/v<k>/models/`, `pools/v<k>/snapshot.json` | verbatim copies of every file of `models/`, taken by `snapshot_pool(run_dir, workspace, k)` at the end of the round that produced pool version `k` (before a later round in the same working directory can change them), with their digests |
| `evaluation/v<k>/` | the evaluation reports (section "Evaluation"; `evaluation.json`, `evaluation.md`, `permitted.json`, `permitted.md`, `plots/`) |
| `workspace/` | the copy of the final working directory; the working directory itself lies outside the repository, and the record states where (`extra.experiment_run.workspace`) |
| `export/python/`, `export/matlab/` | the exports (below) |

The run folder is for the user, never shown to the agent: it holds results on sealed data and the recording names, and it is
never inside a working directory. Nothing in it is overwritten: a second record or pool version
with the same number is refused. `RoundEntry(result, workspace, ..., pool_snapshot=<snapshot folder>)`
passes the snapshot to `write_run_record`; without a snapshot, the record copies `models/` when it is
written and says so (`"taken": "when the run record was written ..."`). `run_texts` and `manifest`
may be omitted; the record then states `"supplied": false` for them.

**Transcript** (`aspire_sysid.record.TranscriptWriter`, an event sink of the turn loop). One JSON
object per line (JSON Lines), appended, flushed and synchronized to the disk per event, so that a
crash loses at most the line being written; every line has `schema_version`, `line`, `kind`,
`recorded_at` (UTC) and the labels `task`, `session`, `round`, `pool_version`, `agent` and
`candidate`, and the fields of the event (`aspire_sysid/agent/events.py`): the full requests (the
system prompt and tool descriptions of `round_start`, the messages added before each `request`),
the full responses with usage and cost, the full tool requests and results, user messages,
reminders, continuation and check-failure messages, check outcomes, corrections, helpers, the
evaluation and the termination. The first line (`transcript_start`) holds the harness version,
the code revision and the header fields of the caller (the experiment runner passes the run
identifier, seeds, model and tool configuration); a system prompt is written in full once and
referred to by its SHA-256 digest afterwards. When a harness reopens a transcript whose last line
was cut off by a crash, the writer cuts the partial bytes before appending and records a
`transcript_repair` line with their number and text. The writer derives the candidate label of a tool request that writes
`models/<label>.json`. The reader rebuilds the rounds (`reconstruct_rounds`: turns, tokens, cost,
elapsed execution time, user waiting time, excess, outcome, and whether they agree with the totals
the loop recorded) and every language-model request exactly as it was sent
(`reconstruct_requests`).

**Dataset provenance** (`aspire_sysid.record.dataset_provenance`). For every dataset (training
file, validation file, each sealed test trajectory): source (recording names, file in the task
folder), version (SHA-256), trajectory identifiers and sample counts, sampling period, operating
conditions ("not stated" per dataset, with the task description), noise, preprocessing and
assignment; and the statement of how the assignment keeps evaluation data out of fitting and
selection (sealing, per-trajectory evaluation, delayed variables, filtering, selection, the
use of the test data as development data). The facts of the sealed files come from
`aspire_sysid.evaluate.sealed.sealed_dataset_records`, the only module that opens them. The
**authorized part** that the agent receives (`authorized_provenance`) is exactly the data facts of
the public view; the leak scanner finds no sealed information in it.

**Run record** (`aspire_sysid.record.write_run_record(run_dir, task, configuration=..., model_id=...,
rounds=[RoundEntry(result, workspace), ...], run_texts=..., manifest=..., probe=..., seeds=...)`):
task identifier and the SHA-256 digests of the task specification (`task.yaml` and the
agent-visible files; separately the sealed files), tool configuration, model identifier and
vendor, harness version and code revision (git commit and whether tracked files had uncommitted
changes), software versions, the probe of the agent's interpreter, the system prompt and the
brief with their digests, the manifest of the working directory, seeds (requirement sampling,
reference comparison; the language model receives none), the dated price, budget and consumption
(turns, tokens, cost, elapsed execution time, user waiting time and excess separately), outcome and
termination reason, per round the check report, the copied candidate files with their digests and
the evaluation report, the dataset provenance and the digest of the transcript.
`recompute_evaluation(run_dir)` loads the task (its digests must equal the record's), checks the
copied candidate files with the round's pool version, re-runs `evaluate_pool` and compares the
result with the stored `evaluation.json` field by field (`RecordMismatchError` lists the
differences). The result does not depend on the string hash seed of the process: in the structure
comparison, `evaluate/complexity.py` numbers the fitted parameters by traversing the arguments of
`Min` and `Max` in SymPy's fixed order, not in their set order.

**Python export** (`aspire_sysid.export.export_python(run_dir)`): one module
`<task>_pool_v<k>.py` per evaluated pool that needs NumPy only, with the reference to the run
record, the variables (name, symbol, roles, unit, description), the known measurement and shift
equations, the evaluation settings, per candidate the canonical and the agent's expressions, the
parameter table (fitted, fixed, tied with equation and resolved equation), estimation record,
origin, predecessor and status (exclusions, allowed violations, numerical failures, unresolved
requirements, test score with the label of the oracle-based selection), the recommendation, and
one function per candidate returning one array per expression key. The written module is imported
and compared with the harness's numerical form of the SymPy expressions at the training rows and
random points of the declared ranges (relative tolerance 1e-9); the result is stored in
`VERIFICATION`.

**Matlab export** (`aspire_sysid.export.export_matlab(run_dirs, out_dir)`): one working folder per
task for the Matlab framework (`matlab-framework/README.md`):

    <out>/<task-id>/
      <train name>.mat, <val name>.mat, <test names>.mat   D, Ts, inputInd, varNames, varNamesLong, varRanges
      splitData.m, evaluationSets.m, startup.m, README.md
      aspire_export.json   task digests, data files with digests, one entry per export call
      HP/<configuration>-open=<o>-run=<n>-pool=<k>/<train name>/modelNN.m
      other_models/run=<n>-pool=<k>/modelNN.m

`srScanModels` turns `run` and `pool` into numeric columns. A later export into the same task folder adds its settings; the README lists the
models of every setting of every export; the export is refused (`ExportConflictError`) when the
task digests of the manifest or a recorded data file differ. An export folder (Python or Matlab)
is refused (`ExportLocationError`) when it lies inside, equals or contains a working directory
named by the run record (including the copy `<run-dir>/workspace`), or lies inside or contains
a folder with `TASK.md` or `check_submission.py`; the default locations `<run-dir>/export/python`
and `<run-dir>/export/matlab` are accepted.

Decisions: (1) the data sets and the model folders are named after the original recording names
(`data.source_name`; several recordings: the first name and `_plus<m>`), never shown to the agent;
(2) the sealed **test data are included** as data sets, because the export is for the user,
never shown to the agent, and must reproduce the evaluation in the Matlab framework; they are
listed in `evaluationSets.m`, never
in `splitData.m`; (3) an M-file is `function [y, info] = modelNN(x)` with a header (label, task,
run, pool version, record, regressor mapping, equations, parameter table with status, source and
initial value, estimation record, origin, evaluation settings, exclusions, numerical failures,
unresolved requirements, test score); fitted parameters are flat assignments `name = value;` (the
lines that `srProvenance` rewrites), fixed parameters and given constants are numbers in the
expressions, a tied parameter is the assignment `name = <equation>;` after the fitted ones (so that
the evaluator of `srProvenance` computes it), `info.TiedParameters` lists only identity ties with a
fitted parameter (the meaning of that field in `srProvenance`) and the extension
`info.TiedEquations` every tie; a `Piecewise` is computed in auxiliary statements
(`aspire_pw<n> = NaN(size(x,1),1)`, then, from the last pair to the first,
`aspire_pw<n>(m) = v(m)` on the rows where the pair's condition holds), so that the first true
pair wins and a value that is not selected, even if infinite or NaN, never enters the result; (4) dynamic models follow `srSimulate`: the regressors are the
states, then the inputs; the states form a chain of integrators and `y` is the derivative of the
last state; a candidate whose other state equations are not that chain (for `friction-driven`:
`dtheta = omega`, requirement R1) goes to `other_models/`, a one-state model always fits;
discrete-time and NARX tasks are not exported to Matlab. Every M-file is re-verified by a
restricted Matlab translator in Python (`printing.matlab_evaluate`) against the harness's values;
a file that fails goes to `other_models/`. With GNU Octave installed (`octave-cli`), every M-file
also runs in Octave, `srProvenance` runs on it, and the Matlab framework runs on the folder: under Octave
8.4, `startup`, `srLoadData`, `srSplitDataVal`, `srProvenance` and `srSimulate` run with two
compatibility functions (`string`, `strlength`) on the path and without the field `form` for
`srSimulate`, and reproduce the ASPIRE errors of every model on every data set within 1e-6
relative; `srScanModels` and `srEvalHP` stop in Octave because Matlab's `table` class is missing,
and `srModelProps`, `srEvaluate` and `srSummary`, which operate on those tables, were therefore not
run. The check in Matlab remains open. The README of each folder states the differences
between the framework and the ASPIRE evaluation (for example `'IgnoreOffset', false`).

**Machine-independent paths** (`aspire_sysid/portable.py`). Run folders, exports,
logs and aggregations are committed, so no file of them names a folder of the computer that wrote
it. Every path the harness writes into them passes through one helper: a path inside the
repository is written relative to the repository root with `/` (`tasks/turtlebot`,
`aspire/configs/prices.yaml`, `experiments/<id>/runs/<run>/run_record.json`); a path inside the
system temporary folder starts with `<tmp>` (`<tmp>/aspire-runs/<random>/workspace`); a path inside
the home folder starts with `~` on POSIX and `%USERPROFILE%` on Windows; other paths (`/usr/bin/python3`)
are kept. The helper is applied to the whole run record, `run_start.json`, `provenance.json`,
`snapshot.json`, `export/status.json`, `INTERRUPTED.json`, the grid and worker logs,
`aggregate.json` and `aggregate.md`, the Matlab export manifest and README, the record reference
of the M-files and of the Python module, and the settings fields of the transcript's `round_start`
line (`workspace`, `environment`, `configuration`, `price`); the verbatim texts of the transcript
(requests, responses, tool results) are not changed. Readers turn a recorded path back into a path
of this computer with `local_path` (relative paths against the repository root that holds the
harness, the placeholders against this computer's folders), so `record verify`, the exports and
`--resume` work on both forms. `startup.m` of a Matlab export outside the repository reads the
environment variable `SR_FRAMEWORK` instead of an absolute path of the framework.

**Command line.**

    aspire record show <run-dir>          summary of the record and of the transcript: outcome, consumption,
                                          the agent's recommendation and the oracle-based selection per round
    aspire record verify <run-dir>        recompute the evaluation offline and compare
    aspire export <run-dir> [<run-dir> ...] [--python] [--matlab] [--out DIR] [--no-octave]

## Experiments

An **experiment** is one task, run one or more times with identical settings: one pinned model
identifier, one harness revision and one round budget. The runs
differ only in the responses of the language model, because the requests set no seed; they are
repeated to report the mean and the sample standard deviation of the results. Two tasks are two
experiments, and a blind variant of a task is a task of its own with its own experiment. A set of
experiments has no file and no command of its own.

An experiment is the file `experiments/<id>/experiment.yaml`; its fields are documented in
`aspire_sysid/experiment/config.py`: `schema_version` (2), `id` (the folder name), `model`,
`task`, `runs`, `concurrency`, `budget` (`null`: the task's round budget), `seeds` (the seed
policy), `exports` (`python`, `matlab`, `octave`), `plots`, `workspace_root`, `agent_python`,
`keep_workspaces`, `tasks_root` and `notes`. A run is identified by `r<NN>` (run index from 01)
and recorded in `experiments/<id>/runs/r<NN>/`. A file with one of the fields `tasks`,
`runs_per_cell`, `kind`, `pool_cap`, `exclude_cells` or `configurations` is refused with the name
of the field that takes its place.

    aspire experiment run <experiment-dir> [--resume] [--dry-run] [--yes] [--concurrency N]
                        [--workspace-root DIR] [--agent-python EXE] [--no-octave]
    aspire experiment status <experiment-dir> [--dry-run]
    aspire experiment aggregate <experiment-dir> [--dry-run] [--out DIR]
    aspire experiment report <experiment-dir> [--dry-run] [--out DIR]
    aspire experiment export <experiment-dir> [--dry-run]
    aspire experiment agent-env <folder> [--package P ...]

**One run** (`aspire_sysid.experiment.runner.execute_run`) creates the run folder
`experiments/<id>/runs/r<NN>/` with `run_start.json`; creates the working
directory under the workspace root; inspects and probes the agent's interpreter; renders the
brief and the prompts and provisions the working directory; runs the round with the
transcript and the evaluation; takes the pool snapshot; copies the final working
directory into the run folder (caches such as `__pycache__` and `.venv` and files above 20 MB are
left out and listed); runs the **leak scan** on the transcript and on every file the agent wrote
or changed (recording names, sealed paths and file names, test rows, test values, the reference
expression); writes the run record with the fields of the experiment in `extra.experiment_run` and the scan in
`extra.leak_scan`; and writes the exports into `export/` with `export/status.json` (a run whose
pool has no evaluated candidate has no export, and the status says why). After the runs, the grid
adds every finished run to the experiment-level Matlab export `experiments/<id>/export/matlab/`
(the working folder of the task for the Matlab framework; `exported_runs.json` lists the runs).

**Working directories outside the repository.** The working directory of an attempt is
`<workspace root>/[dry-run/]<random>/workspace`, with a new random name for every attempt: the
path names no experiment, task or run, so that the agent of a blind task cannot learn from its
working directory which task it is. The
mapping from the random name to the run is kept only in the run folder (`run_start.json`); the
owner file of the attempt folder (`aspire-attempt.json`) holds only a random token, and an
existing non-empty attempt folder is refused and never deleted. The default workspace root is
`<system temp>/aspire-runs` (interactive sessions use `<system temp>/aspire-sessions`).
Residual risk for blind tasks: all working directories lie under one workspace root and belong to
the same operating-system user, so a program of a run on a blind task that lists the root and reads the
`TASK.md` of a sibling folder (a run on the described task) learns the task; the command
filter refuses such absolute paths in command text, but not in a program. Only a separate
operating-system user per run, or a separate workspace root for the blind tasks, prevents it.
The runner refuses a root inside the harness repository or inside any folder that holds `.git`,
so that neither `..` nor git's search for a repository reaches `tasks/` or its history. Residual
risk: the agent's commands run as the same operating-system user as the harness, so a program
that opens the absolute path of the task store can still read it (section "Tool policy and its
limits").

**The agent's shell environment.** The agent's commands do not inherit `PYTHONPATH`,
`PYTHONHOME`, `PYTHONSTARTUP`, `PYTHONUSERBASE`, `VIRTUAL_ENV` or the installation targets of
`pip` from the harness. Packages installed by the agent go into the
attempt's own folder (`PIP_TARGET` and `PYTHONPATH` point to `<random>/packages`), so that no
run changes the environment of a later or concurrent run. Real runs receive the web
fetch backend `aspire_sysid.experiment.web.urllib_fetch`. The web search is the vendor's (OpenAI;
"Tool policy and its limits"); the run record states under `extra.experiment_run.web_backends`
what each of the two tools was in the run.

**Crash-resume.** A run is finished when its run record has a final outcome; it is never
repeated (a missing export is completed). A run folder without such a record is unfinished. If
the process recorded in its `run_start.json` (number, host, start time) still runs on this host,
the resumed grid leaves the run alone and reports it as still running (exit status 1; resume again
after it has ended). Otherwise the run is interrupted: `--resume` moves it to `experiments/<id>/interrupted/<run>__attempt<k>/`, labels it with
`INTERRUPTED.json` (never aggregated), copies its working directory when it still exists, and
repeats the run from the beginning as attempt `k + 1`. Without `--resume` the grid refuses to
start when any run folder exists. The lock file `experiments/<id>/experiment.lock` refuses a second
grid process on the same experiment; a lock of a process that no longer exists on the same host
is replaced. Runs execute in worker processes, `concurrency` at a time; `logs/grid.jsonl` records
every grid event and `logs/<run>__attempt<k>.log` the output of each worker. Three measures keep
one run from being executed twice at once (`aspire_sysid/experiment/procs.py`): (1) the check of
the recorded process above; (2) the workers end when the grid process ends, for any reason (Linux:
`prctl(PR_SET_PDEATHSIG, SIGTERM)`; all systems: a watchdog thread that polls the parent process
number; Windows: a job object with `KILL_ON_JOB_CLOSE` held by the grid; `SIGTERM` ends the
worker's running agent command with its process group and writes no record); (3) a worker writes
into its run folder only while `run_start.json` there carries its own random token, and the grid
counts a run record only when it belongs to the attempt it started.

**Host-process protection**. On Windows, `aspire experiment run` re-launches
itself under a copy of the interpreter named `aspire-host.exe`, and the workers use the same
interpreter, so that `taskkill /IM python.exe` cannot end the grid. In a virtual environment,
`python.exe` is a launcher that may start the base interpreter as a child process named
`python.exe`; the renamed copy is therefore made of the base interpreter. When the renamed copy cannot be written or started, the grid runs under
`python.exe` without this protection and prints a warning. On POSIX, a renamed interpreter is not needed for this case, because
every agent command runs in its own process group; the host-process filter refuses `pkill python`,
`killall python3`, `kill -1`, `kill $PPID` and the like, with the gaps stated above.

**Dry run.** `--dry-run` replaces the language model by a scripted agent (list the files, read
the brief, write the example model files of the task, run the checking script, `DONE`) under the
experiment's model identifier, and writes into `experiments/<id>/dry-run/` (ignored by git). Every
other step is the real one. Dry-run records carry `dry_run: true` and vendor `scripted` and are
never aggregated with real runs.

**A real run** reads the API key from `OPENAI_API_KEY` in the environment or from a `.env` file
(`OPENAI_API_KEY=...`) in the experiment folder, the current folder or the repository root
(`.env` is ignored by git), and refuses to start without it. The file is read as UTF-8, with or
without a byte-order mark, or as UTF-16 with one (the forms that editors and the output
redirection of Windows PowerShell write); a file in another
encoding stops the start with a message that names it. The key never stays in a process
environment: a key from the environment is removed from the grid process's environment, a key
from `.env` is never put into it, the workers are started without it and receive it through
their standard input, and the provider object receives it as an argument
(`make_provider(model, api_key=...)`); records hold only whether it was received. The key is taken
before any subprocess of the harness starts (the interpreter inspection included), and the
Windows re-launch under `aspire-host.exe` starts without the key variables and receives the keys
through its standard input. Remaining risk:
(a) a key that was in the environment of the shell that started `aspire` stays readable in
`/proc/<grid pid>/environ` (Linux), because that file shows the environment at the start of the
process; `.env` avoids this; (b) the key is in the memory of the grid and of each worker, and a
program of the agent, which runs as the same operating-system user, could read that memory where
the system permits it (for example Linux with `kernel.yama.ptrace_scope = 0`); only a separate
operating-system user for the agent removes this risk. It prints the number of runs and their largest cost,
the sum of their round cost limits (for example 3 runs × 10 USD = 30 USD; a
round can exceed its limit by the cost of the request during which the limit was reached), and
starts only with `--yes` or a typed confirmation. A real run is refused when
`aspire/` or `tasks/` has uncommitted changes (`--allow-dirty`) or when the harness
package can be imported from the agent's interpreter (`--allow-harness-interpreter`). The exit
status is 3 when the leak scan found sealed information in any run; the summary then lists every
finding.

**Aggregation** (`aspire experiment aggregate`; `aspire_sysid.experiment.aggregate`) writes
`aggregate.json` and `aggregate.md` of an experiment: planned, attempted (runs with a
record), delivered (the final check report passed: a valid pool file with at least one passing
candidate within the pool limit) and eligible (at least one candidate eligible for ranking) runs,
runs evaluated without a valid pool file, interrupted attempts and outcomes; for each per-run
quantity the mean and the sample standard deviation over the `k` runs with a finite result,
`s = sqrt(Σ(x_i − x̄)² / (k − 1))` (divisor `k − 1`; undefined, never 0, for `k < 2`), the number of
finite results and every run without one with its reason, for every quantity (never assigned
zero, never dropped). Planned runs without a record are listed with their state and reason, and
the tokens and cost of interrupted attempts and unfinished run folders are totalled from their
transcripts and reported as spend, outside the statistics. Quantities: the test
score `S` (the pooled test RMSE) of the recommended candidate (practical selection; no finite result when
the recommendation is absent, invalid, "no recommendation is supported", not evaluated or not
eligible), the training error of the recommended candidate, the best eligible `S` of the pool (labeled "oracle-based selection on test data", with
the pool sizes), turns, input and output tokens, cost, elapsed time, pool size, evaluated
candidates, distinct structures, sensitivity rank deficiencies, the complexity of the recommended
candidate, the RMSE per test trajectory of the recommended and the best eligible candidate, and
the requirement outcomes. The aggregation refuses records of different tasks, model identifiers,
harness identities or dry-run status.

**Harness identity.** The run record's `harness.code_revision.identity` holds the git tree hashes
of `aspire/` and `tasks/` (`git rev-parse HEAD:aspire`, `HEAD:tasks`) and whether these folders
have changes (`git status --porcelain -- aspire tasks`, tracked and untracked); this identifies
the code and the tasks of a run, so that a commit that changes only other folders of the
repository does not split an experiment. The repository commit and its repository-wide dirty flag
are recorded for information (`aspire_sysid.record.harness_identity`, `code_revision`).

**The agent's environment.** Create it once, outside the repository, with the
harness's interpreter as base (PySR needs Julia and is therefore not in the default list):

    aspire experiment agent-env %LOCALAPPDATA%\aspire\agent-env            (Windows)
    aspire experiment agent-env ~/.local/share/aspire/agent-env            (Linux, macOS)
    aspire experiment agent-env <folder> --package pysr                    (with PySR)

The command installs numpy, scipy, sympy, pandas, matplotlib, scikit-learn, gplearn and pysindy,
checks that `aspire_sysid` cannot be imported from the new
interpreter, and prints the option for `aspire experiment run`, for example
`--agent-python C:\Users\<user>\AppData\Local\aspire\agent-env\Scripts\python.exe`. The path is
passed on the command line and never committed in `experiment.yaml`, because it names a folder of
one computer; the record stores it in machine-independent form. The probe of every run lists the
installed packages in the system prompt and in the record.

## Report

`aspire experiment report <experiment-dir>` (`aspire_sysid.report.build_report`) writes a static
HTML report into `experiments/<id>/report/`. It is written for the user of ASPIRE and is generated
from the stored records only; besides formatting it computes the mean and the sample standard
deviation over the runs. It contains results on the sealed test data and is never placed into a
working directory of an agent. The pages need no server and no network access.

- **`index.html`**, the experiment: (1) Assignment, that is `TASK.md` as the agent received
  it; (2) Configuration: model, tools, limits per run, runs and date, with the system prompt,
  `FORMAT.md` and the first message collapsed; (3) Results: one table row per run with the
  model the agent recommended (training and test error), the model with the lowest test error,
  the number of models, turns, cost and time, a first row with mean ± sample standard deviation
  when there are two or more runs, and the recommended model of every run with its equations;
  (4) the files.
- **`r<NN>.html`**, one page per run: (1) Models: a table in the agent's order, the
  agent's recommendation with its reason, and one card per model. A card shows the equations, the
  parameter values in one line and the errors; collapsed below them are the equations as written
  in the model file, the equations with the values substituted, the parameter table with the estimation record, the agent's explanation
  (model family, interpretation, how it arrived at the expression, limitations), the outcomes of
  the physical requirements when the task states any, and the plots with the errors per
  trajectory. (2) Course of the run: one line per turn (turn, execution time, action, cost so
  far) and per action of the harness; a line unfolds to the reasoning summary, the agent's text,
  the commands and files, and the outputs. The action text is derived by plain code from the tool
  calls (tool, file name, first line of the command); no language model writes it. (3) The files.

One caption states what the two error columns are: the agent recommends a model from the training
data, and the model with the lowest test error is found with the test data, in hindsight, among
the models of the run (the oracle-based selection on test data). When the training and the test
trajectories differ in length and the errors are simulation errors, the caption says that the two
errors are not directly comparable. The expressions are typeset as they are written in the model
file: the order of the terms and the names are unchanged (`phi` stays `phi`), and the text is
parsed into Python's syntax tree, never evaluated. In the agent's texts, a fragment between
backticks is typeset the same way when it is an expression (`FORMAT.md` asks the agent to write
expressions in its texts between backticks); any other fragment between backticks is shown as
code. The agent's own texts are rendered as Markdown wherever they are shown, in the report and in the
web app (`agent_markdown`: headings, lists, tables, quotations, links to http and https addresses,
bold and italic), because language models write their answers in Markdown: the explanation and
the estimation record of a model, the recommendation, the texts and reasoning summaries in the
course of a run, the questions to the user and the answers to analysis requests. The wording is
never changed, the text is escaped, and an asterisk of an expression written without backticks is
not read as a mark. The user's and the harness's texts are shown as written. Plots and files open in a new browser tab. A finding of the leak scan and a model that was
excluded or not evaluated are shown only when they occur.

## Interactive operation

In interactive operation a **session** contains several rounds and, between them,
**analysis exchanges**: requests of the user for an explanation or an analysis that do not create
a new pool. `aspire_sysid.session.Session(task, provider, config, channel, out_dir, ...)` runs a
session; `Session.run` runs round 1 and then follows the user's choices until the user ends the
session or the session budget is reached. From the command line:

    aspire session <task-dir> [--model <id>] [--out <dir>] [--python EXE] [--allow-harness-interpreter] [--workspace-root DIR] [--no-plots] [--no-reexec] [--user NAME]

Only the task folder is required. Without `--model` the session uses the default model
(`default_model` of `configs/models.yaml`, `gpt-6.1-sol`). Without `--out` the record
folder is `sessions/<task>-<YYYYMMDD>-<n>` under the current directory, with the first number `n`
for which no folder exists. Without `--python` the agent's shell uses the environment created by
`aspire experiment agent-env` at its default place (`%LOCALAPPDATA%\aspire\agent-env` on Windows,
`~/.local/share/aspire/agent-env` elsewhere; the environment variable `ASPIRE_AGENT_ENV` names
another folder) when it exists, and the harness's interpreter otherwise. `aspire experiment
agent-env` without a folder creates the environment at that place.

**Starting from data files: the task interview** (`aspire_sysid.session.interview`; the task folder is made by `aspire_sysid.task.stub`, the only module outside the evaluation and the task loader that names the sealed folders: it writes the test files there and never reads them).

    aspire session --train <file> [--val <file>] [--test <file> ...] [--new-task <folder>]

Only the training data are required; validation and test data are optional, and the division of
the data is the user's (one `--test` file per test trajectory, given as several files or as a
pattern such as `held_out_*.csv`, which the harness expands itself in natural order; the harness
does not divide a file). The harness

1. copies the files into a new task folder (`--new-task`, default `tasks/task-<YYYYMMDD>-<n>`
   under the current directory; the name of the folder is the task identifier) as
   `data/train.csv`, `data/val.csv` and `test/test_<i>.csv`. The originals are not touched, and
   their names are kept only in `interview/stub.json`, never shown to an agent;
2. runs the interview agent: the model of the session with the tools of the identification
   agent, `ask_user` and `check_task`. Its working directory holds the training and validation
   data, a draft `task.yaml`, `TASK_GUIDE.md` (`tasks/GUIDE.md`), `TASK_REFERENCE.md` (Sections 2
   to 4 of `tasks/README.md`) and the two example definitions; it never holds the test data,
   and the tool policy protects the task folder as in every run;
3. checks the agent's `task.yaml` with the task loader, on the agent's request (`check_task`) and
   after every reply that ends an exchange, after setting its own fields: `schema_version`, `id`,
   `data.train`, `data.val` and `test` (and removing `reference` and `data.source_name`), so that
   the agent cannot change which files are sealed;
4. shows the task brief of the checked definition to the user, who types `y` (the identification
   starts), `q` (stop; the task folder is kept) or the change wanted (a further exchange).

The interview is a separate conversation with its own limits (`INTERVIEW_LIMITS`: 60 turns,
3600 s, 5 USD); its cost is not charged to the session budget, which the task defines. The
identification agent receives nothing of it. Records in `<task folder>/interview/`: `stub.json`,
`transcript.jsonl`, `interview.json` (outcome, consumption, questions and answers, checks, the
user's verdicts, the system prompt) and `workspace/` (the files the agent wrote, without the
data). The prompt of the interview agent is a harness text of `aspire_sysid.session.interview`.

**Web app** (`aspire_sysid.web`). The browser is an alternative to the terminal
for both ways of starting a session, and it runs the same session: the web app replaces only the
channel to the user (`WebChannel` in place of `TerminalChannel`) and the progress lines
(`WebProgress`); the session, the task interview, the checks, the evaluation, the records and the
HTML report are unchanged.

    aspire web [--port N] [--no-browser] [--tasks DIR] [--sessions DIR] [--model ID] [--python EXE] [--no-plots] [--user NAME]
    aspire session <task-dir> --web            (or: aspire session --train <file> ... --web)

`aspire web` opens a start page: a session on a task folder of `tasks/`, or a session from data
files chosen in the browser (training data required; validation and test data optional; the files
are copied into a new task folder, and the task interview runs first). `aspire session ... --web`
skips the start page and runs the session of the command line. One session runs at a time; after
it the page offers another one.

- **During a round, an analysis or the interview** the page shows the course as in the HTML report:
  one line per response of the agent, which unfolds to the reasoning summary, the commands and the
  outputs. A status line says what happens now.
- **A question of the agent** is answered in a form (or declined). **After a round** the page of
  the round from the session's report is shown, with three actions: an analysis request, a new
  round with feedback and a form for task changes (allow or exclude a violation, set a tolerance,
  add a requirement in words), or the end.
- **Editing `task.yaml` in the browser.** On the start page for a task folder, and at the task
  brief of an interview. "Check" shows the errors of the text, or the task brief it gives, and
  never writes; "Save" writes the file only when the task loader accepts the text. At the brief of
  an interview the user's version also replaces the agent's draft, so that a later change by the
  agent starts from it; the user may change every field, since the task is the user's. A
  definition cannot be edited while a session runs on it: changes during a session are the task
  changes above, which are recorded with the round in which they take effect.
- **State.** The pending question or choice lives in the server, so that reloading or closing the
  page loses nothing; the session waits, and the waiting time is user waiting time.

The server is the Python standard library's `http.server`, bound to `127.0.0.1`; the page is one
HTML document with its style and script and loads nothing from another site. Every address
contains a random token generated at start; without it, or for another host name, the server
answers "not found". It serves files of the session record only. The token and the refusal of
local addresses by the agent's `web_fetch` (`web.denied_url_substrings` in `configs/tools.yaml`)
keep the server from being a way for the agent to the results on the test data; the limit of the
section "Tool policy and its limits" remains. On POSIX the web app runs the session without the
re-execution described above, because the server and the session share one process: keep the API
key in a `.env` file. `?snapshot=1` appended to the address shows the present state once, for a
picture of the page.

**What the user sees on the terminal.** While the agent works, the session prints one line per
response of the agent: the turn number, the execution time of the round, and what the response did
(`TerminalProgress`; the text is derived from the event by plain code, as in the HTML report), and
one line per check and evaluation of the harness. After a round it prints one line per model with
its training and test error, the agent's recommendation with its reason, and the addresses of the
page of the round and of `evaluation.md`; the complete evaluation report is in these files and is
not printed. Then the user types `a` (analysis request), `r` (new round with feedback and
task changes) or `e` (end). A text that the user types ends with a line containing only a full stop. Every input is
acknowledged with a line that starts with `[received]` and says what happens next (the answer was
passed to the agent, a new round starts, the record is being written), so that the terminal is
never silent after an input.

**HTML report of a session** (`aspire_sysid.report.session_report`; `report/` in the record
folder). The session writes it after every round and analysis exchange and at its end:
`index.html` with the assignment, the configuration, one table row per round and the course of the
session (rounds, questions and answers, analysis requests and answers, feedback, task changes, the
end), and `round<k>.html` with the models of pool version `k` in the form of a run page of an
experiment and the course of that round. A round that started after the user had seen test errors
is marked test-informed. The report reads `session.json`, `transcript.jsonl`, `pools/` and
`evaluation/`; `session.json` holds, under `report`, the texts the agent received and the public
columns of the task, so that the report needs neither the task folder nor the run record. `aspire
record report <session-dir>` writes it again. A failure of the report never ends a session.

With a real model, `aspire session` applies the measures of the experiment runner: the workspace
root must lie outside every git repository (`check_workspace_root`); the interpreter of the agent's
shell (`--python`, best an environment made with `aspire experiment agent-env <folder>`) is refused when
the harness package can be imported from it, unless `--allow-harness-interpreter` is given; the shell
environment is derived by `agent_base_environment`, and the agent's package installations go to a `packages/` folder next to the working directory. The API key is
handled as in a real run of an experiment (`take_api_key`): it is taken before any subprocess starts (the
interpreter inspection included), a key from `.env` is never put into an environment, the provider
object receives it as an argument, and neither the record nor the agent's shell environment
contains it. The record states its source (`extra.api_key.source`: `environment` or `dotenv`).

**Re-execution.** The session process is the parent of every agent command, and a command can read
`/proc/$PPID/environ`, `/proc/$PPID/cmdline` and `/proc/$PPID/cwd`; the first two show the state at
the start of the process, so removing the key from `os.environ` later does not hide it. With a real
model on POSIX, `aspire session` therefore replaces its own process image (`os.execve`) right after
taking the key: the new image starts without any API key variable (`PWD` set to the workspace root,
`OLDPWD` removed), in the workspace root as working directory, with the command line
`python -c <bootstrap>` that contains no path; the key, the arguments (task and record paths) and
`sys.path` reach it through an inherited pipe. `extra.api_key.reexecuted` records it. `--no-reexec`
disables it and prints a warning; Windows does not support it. The key travels in the form of the relaunch of `aspire experiment run` (`{variable: key}`, received with `accept_passed_keys`), and the new image takes it with `take_api_key` (source `launcher`); the record keeps the original source. `aspire session` ends on `SIGTERM` and `SIGHUP` through `SystemExit` (`request_termination` of `agent/shell.py`), so that a running agent command and its process tree are ended. Remaining channels: `/proc/$PPID/fd`
lists the files the process holds open (among them the transcript in the record folder); the memory
of the harness process holds the key and is readable by the agent where the system permits it (for
example Linux with `kernel.yama.ptrace_scope = 0`); the process that started `aspire session` (the
user's shell) keeps its own command line, working directory and environment, readable through
`/proc` as well. Only a separate operating-system user for the agent's commands closes these.

The user answers the agent's questions, reads the results after each round and
chooses on the terminal (`TerminalChannel`); `ScriptedChannel` supplies scripted answers. Both implement
`UserChannel` (`ask`, `show_report`, `show_text`, `choose`).

**Two folders.** The agent's working directory is created outside the session record, in
`<workspace root>/<random>/workspace` (a path that names no task, session, context or configuration, as for the runs of an experiment); the workspace root is `--workspace-root`
(`Session(..., workspace_root=...)`), by default `<system temporary folder>/aspire-sessions`. The
harness refuses a record folder anywhere under the workspace root and a working directory inside the
record folder (`check_separation`), because the record holds the complete reports with
sealed results. At the end of the session the final working directory is copied into the record and
the working copy is removed. **Limit:** the separation is by location only. A program that the agent
runs can read every absolute path that the operating-system user of the harness can read, including
the record and the task store (section "Tool policy and its limits"). In real runs the record root
(`--out`) must therefore lie where the agent's commands cannot reach it, for example under a
different operating-system user or outside a container that runs the agent's commands; the default
temporary workspace root only prevents discovery by walking up from the working directory.

The session record folder is a run folder (section "Records and exports"), so that `aspire record verify <dir> --pool-version k`,
`aspire record show <dir>` and `aspire export <dir>` work on it. It receives

| Path | Content |
|---|---|
| `transcript.jsonl` | the transcript: every event of the turn loop and of the session (`SESSION_EVENT_KINDS` in `aspire_sysid/agent/events.py`) |
| `run_record.json`, `provenance.json` | the run record, written at the end of the session: one round entry per round and per analysis exchange, in order, with the test-informed label, the pool snapshot, the stored reports and the task changes in force (`task_changes_in_force`, which `recompute_evaluation` accepts only in an interactive record and only when it equals the `task_change` events of the transcript up to that round, applies before re-evaluating the pool, and `aspire record verify` prints); `consumption` holds the sums over the entries (`summed_over`: user waiting and harness time inside them only) and `consumption.session`, the totals of the whole session as in `session.json`; `extra` holds the session summary, the agent interpreter, the shell environment, the workspace copy and the leak scan, as for a run of an experiment |
| `workspace/` | a copy of the agent's final working directory (the copy rules of the experiment runner), written at the end of the session |
| `pools/v<k>/models/`, `pools/v<k>/snapshot.json` | the snapshot of `models/` at the end of round `k`, never overwritten (pool version `k`) |
| `pools/v<k>/recommendation.json` | the agent's recommendation of round `k`, recorded before its test results are shown to the user |
| `evaluation/v<k>/` | the complete evaluation report of pool version `k`, for the user, with the round's label test-informed or not test-informed (header of `evaluation.md`, field `test_informed` of `evaluation.json` and of its recommendation; `recompute_evaluation` requires the label to equal the round entry's flag and compares the rest) |
| `pools/v<k>/agent_results.json` | what the agent received after round `k`: `sent_text` (the text inserted into the round-completion message), `sent_blocks` (the same per block, after the leak screen), `screen_findings` and `withheld_blocks` (the reasons for withheld blocks, never sent), and `permitted_before_screen` (the whitelisted structure from which the text was rendered) |
| `pools/v<k>/agent_results.txt` | `sent_text` alone |
| `session.json` | the session record: rounds, questions and answers, exchanges, task changes, test-informed label, totals, termination |

Every event of an analysis exchange carries the label `exchange` (its number), so that
`reconstruct_rounds` keeps the exchange apart from the round whose round label it shares; autonomous
events carry no such field. The exports of a pool version of a session (Python module docstring and
`RECORD["interaction"]`, the header of each M-file, the README of the Matlab export) state its label
test-informed or not test-informed and the task changes in force.

Rules implemented by the session (details in the docstring of `aspire_sysid/session/session.py`):

1. **`ask_user`.** Offered to the main agent in every round and analysis exchange of a session,
   never in autonomous operation and never to helper agents. The response that requests it is one
   turn; the execution clock is paused while the user answers, so the waiting time is recorded as
   user waiting time and not as execution time. The question, the decision it affects and the
   answer are recorded verbatim (events `user_question`, `user_answer`). An empty answer declines
   the question; the tool result is then the declined-question message.
2. **Permitted results.** After a round the agent receives the round-completion message with
   the permitted results: the file and expression checks, the training and
   validation errors and failures, the requirement assessments on the declared domains, the
   complexity, the structures and the sensitivity diagnostic. `permitted_results` builds them
   from the evaluation by a whitelist of named fields; it never reads the sealed parts (test
   errors and trajectories, score, eligibility, ranking, reference comparison); the counts are
   recomputed from the whitelisted candidate fields. Each candidate's text block, and the summary
   in the new-round message, is then scanned with the leak scanner; on a finding it is replaced
   by the neutral notice "withheld by the harness", and the reason is recorded (event
   `permitted_results_screened`, `agent_results.json`, the round record).
3. **Analysis exchange.** Started by the analysis-request message with the user's
   request verbatim, within the task's `budget.analysis_exchange` (or the remaining session
   allowance when the task declares none), charged to the session totals. The agent's first
   response without a tool request (also one ending with `DONE`) is the completed answer and ends
   the exchange; the continuation message of rounds does not apply. No pool version is created.
4. **New round.** Started by the new-round message with the previous pool, a summary
   of its permitted results, the user's feedback verbatim, all task changes in force with their
   sources and rounds, the label test-informed or not test-informed, the round limits and the
   remaining session allowance. `check_config.json` is rewritten with the new pool version and the
   labels of the previous version; a revised candidate names its predecessor in `predecessor`
   (rule F1). After a task change `TASK.md` is rendered again for the effective task and its new
   SHA-256 digest is recorded (event `brief_regenerated`, round record). The conversation continues
   across rounds and exchanges.
5. **Task changes.** With a new round the user may allow a violation of a formal requirement
   without exclusion, restore the exclusion, change a tolerance, or add a requirement in natural
   language (`TaskChange`). The change is recorded with the user's instruction and the round in
   which it takes effect; each pool version is evaluated under the settings of its round.
6. **Test-informed label.** When the user has been shown a report with any result on sealed data,
   test results or a reference comparison (event `user_shown_sealed_results`), every later
   round, its recommendation, its complete report and every later exchange are labeled
   test-informed, whatever the user's text contains.
7. **Session budget and end.** One tracker with the task's session limits is the parent of the
   trackers of all rounds and exchanges; a session limit ends a round like its own limit. The
   session's execution time is the sum of the execution times of its rounds and exchanges; the
   harness's checks, evaluation and reports between them are recorded as `harness_s`. The session
   ends at the user's request or at the session budget, with the session-completion message
   (reason, completed pool versions, unfinished work, resource use), which is recorded
   and shown to the user. This message and the round-completion message of the last round are
   appended to the conversation and recorded, but no request to the language model follows them.

## Installation

    pip install -e "aspire[runner]"
    aspire --version
    aspire prices

The configuration folder `configs/` is found relative to the package folder; an editable
installation is therefore required.
