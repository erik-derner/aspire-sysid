# Task specifications

This folder holds the task specifications of ASPIRE. ASPIRE consists of the **harness**, the
software in `aspire/`, and the **agent**, the language model that identifies the models. A **task** is an identification problem specified by
the user: its data, the permitted model forms and the evaluation requirements. The harness
reads a task folder, gives the agent the agent-visible part in a **working directory** (the
folder in which the agent reads and writes files), and keeps the **sealed** part (test data and
reference expression, inaccessible through the agent's files, tools and conversation) for its own
evaluation. The format is schema version 1;
the loader is `aspire/aspire_sysid/task/`.

| Task | Formulation | Output | Evaluation | Test trajectories | Reference |
|---|---|---|---|---|---|
| `friction-driven` | continuous-time, states θ and ω, input u, T_s = 0.01 s | θ (rad) | simulation | 4 | no |
| `fermenter-pressure` | continuous-time, state p, inputs valve and flow, T_s = 5 s | p (bar) | simulation | 1 | no |
| `task-jdhj`, `task-qtqm` | blind variants of `friction-driven` and `fermenter-pressure` (Section 7) | `y` (unit not supplied) | as described | as described | no |
| `task-kt5o` | blind variant of `turtlebot` (Section 7): states `y`, `x1`, `x2`, inputs `x3`, `x4`, T_s = 0.2 s | `y` (unit not supplied) | simulation | as `turtlebot` | no |
| `turtlebot` | discrete-time, states x, y and φ, inputs v_f and v_a, T_s = 0.2 s | x (m) | simulation | 12 segments of 5 s from 2 trajectories | no |
| `example-static`, `example-dynamic` | examples with synthetic data for `GUIDE.md`: a static task (input d) and a discrete-time task (state h, input u, T_s = 1 s) | F (N); h (m) | algebraic; simulation | 1 data set; 1 trajectory | no |

The tasks of the paper are `turtlebot` (mobile robot), `friction-driven` (rotational motion under dry
friction) and `fermenter-pressure` (fermenter) with their blind variants `task-kt5o`, `task-jdhj` and
`task-qtqm`. The file `provenance.md` of each task describes its data and its requirements.

## 1 Folder layout

    tasks/<task-id>/
      task.yaml          specification (Section 2)
      data/train.csv     training data (agent-visible)
      data/val.csv       validation data (agent-visible, offered; optional)
      context/           supporting files (agent-visible; optional)
      test/*.csv         sealed test data, one trajectory or dataset per file
      reference/         sealed reference expression (optional)
      provenance.md      origin and construction of the data, requirements (never shown to the agent)

A data file is a comma-separated table with one header row of column names and one numeric row
per sample. In the training and validation files, an optional integer column, declared as
`data.trajectory_column`, marks the trajectories (ordered sequences of samples from one
experiment); each trajectory is one contiguous block of rows. A test file is always one
trajectory and has no trajectory column. The reference file is YAML:
`{format_version: 1, expressions: {<expression key>: "<expression>"}}`.

File names visible to the agent are neutral: the harness copies the data to `data/train.csv`,
`data/val.csv` and `context/<file name>` in the working directory, whatever the file names in
the task folder.

## 2 Fields of `task.yaml`

"Shown" states whether the field reaches the agent, through the public view
(`aspire_sysid.task.public_view`) from which the brief is rendered.

| Field | Content | Shown |
|---|---|---|
| `schema_version` | `1` | yes |
| `id` | lower-case letters, digits and hyphens; visible to the agent, so descriptive only on purpose | yes |
| `title`, `description` | title; system and data in prose (`description` optional: a blind variant has none) | yes |
| `intended_use` | purpose of the model (optional) | yes |
| `formulation` | `static`, `continuous`, `discrete` or `narx` | yes |
| `columns` | list of `name`, `symbol`, `roles`, `unit`, `description`, `range`, and `derivative_of` for a state derivative (Section 3) | yes |
| `dynamics` | dynamic tasks: `sampling_period` (T_s, s), `states`, `inputs`, `measurement` (expression of the measurement equation y = h(x, u); default: the output state), `input_hold` (`zero_order`), `integrator` (`rk4`, continuous only), `substeps` (default 1, continuous only); NARX: `delays` (list of `name`, `variable`, `lag`) and optional `shift_equations` | yes |
| `evaluation` | `mode` (`algebraic` for static tasks, `one_step` or `simulation` for dynamic tasks); `initialization` (initial samples per trajectory: 0 for static tasks, at least 1 for dynamic tasks, at least the largest delay + 1 for NARX); `scoring` (`all_samples` for static tasks, `after_initialization` for dynamic tasks); `failure_limits` (per simulated state or output: `variable`, `lower`, `upper`, `unit`, `justification`); `time_limit_s` (evaluation time limit per candidate); `symbolic_time_limit_s` (optional: time limit of one symbolic verification attempt, after which the attempt is inconclusive); `horizon` (optional, simulation mode only: the number of simulated samples of a test trajectory; the harness then evaluates the training and validation data in consecutive segments of that length, each started from the measured state, so that their errors are comparable with the test error) | yes, except `horizon` |
| `data` | `train`, `val` (paths), `trajectory_column`, `noise`, `preprocessing`, `source_name` (`{train: name or list, val: name or list}`, the original recording names) | noise, preprocessing, trajectory column; file facts |
| `constants` | given constants: `name`, `value`, `unit`, `source` | yes |
| `functions` | permitted functions, SymPy spelling; default (`sin cos tan asin acos atan atan2 sinh cosh tanh exp log sqrt Abs sign Min Max Piecewise`) | yes |
| `added_functions` | functions added to the list: `name`, `arguments`, `definition` (expression over the arguments), `domain` | yes |
| `requirements` | formal requirements (Section 4) | yes |
| `requirements_nl` | natural-language requirements: `id` (default `NL<i>`), `text` (verbatim), `source` | yes |
| `literature` | verified references, one string each | yes |
| `context` | supporting files: `file`, `note` (the user's explanation) | yes |
| `discussion_questions` | list of `id` (`Q1`, ...) and `text` | yes |
| `pool_cap` | maximum number of candidates evaluated | yes |
| `budget` | `round`, `session`, `analysis_exchange`, each `{turns, seconds, usd}`; round default 60 turns, 3600 s, 10 USD; session default equal to the round; `analysis_exchange` optional | yes |
| `test` | sealed test entries: `file` (in `test/`), `trajectory` (identifier), `source_name` | no |
| `reference` | sealed reference: `file` (in `reference/`), `domain` (`{box: {variable: [lower, upper]}}`) | no |

The public view also contains, for the brief, the neutral working-directory names of the data
files with their sample and trajectory counts, the required expression keys and the argument
names. It never contains a path of the task folder, a recording name, a test entry or the
reference.

## 3 Columns, roles and expression keys

The `unit` of a column, failure limit, constant or tolerance is a string; `-` denotes a
dimensionless quantity or a unit that was not supplied (the description says which), and the
reserved string `not supplied` (`aspire_sysid.task.schema.UNIT_NOT_SUPPLIED`) states that the task
does not give the unit; the brief renders it verbatim. A column without `description` has none,
and the brief says that the task does not describe the columns.

A column has one or more roles: `input` (exogenous signal, read from the data
during simulation), `state` (computed by the model during simulation), `output` (the measured
signal on which the model is evaluated; exactly one per task) and `state_derivative` (sampled
time derivative of the state named in `derivative_of`; a possible fitting target, never
simulated or evaluated). `range` is a declared interval that contains every training sample; the
loader checks the containment. A static task whose columns carry no roles, or that has no
`columns` field, uses the default column order: inputs in columns 1 to N − 1,
output in column N.

A candidate stores one expression per **expression key**; the keys depend on the formulation:

| Formulation | Expression keys | Arguments of the expressions |
|---|---|---|
| `static` | the output column name, for ŷ = f(u; p, c) | the inputs |
| `continuous` | `d<state>` per state, for dx/dt = g_c(x, u; p, c) | the states, then the inputs |
| `discrete` | `<state>_next` per state, for x[k+1] = g_d(x[k], u[k]; p, c) | the states, then the inputs |
| `narx` | `<output>_next`, the regression of y[k+1] | the output, the delayed variables, the inputs |

For a NARX task, the output is the only declared state, the task declares
the delayed variables (for example `y_d1` with lag 1 and `y_d2` with lag 2 of `y`), and the
shift equations `y_d1[k+1] = y[k]`, `y_d2[k+1] = y_d1[k]` are known and supplied by the task; the
agent writes only the regression expression. A state-derivative column may carry the name of the
matching expression key (for example the column `domega` and the key `domega`). Given constants,
π (`pi`) and e (`E`) may also appear in expressions.

## 4 Formal requirements

Each entry of `requirements` has these fields:

| Field | Content |
|---|---|
| `id` | identifier, unique across formal and natural-language requirements |
| `type` | one of `symmetry`, `monotonicity`, `parity`, `exact_value`, `inequality`, `curvature`, `limit`, `equation`, `relation_at_points` |
| `target` | an expression key, or the output column name |
| `variables` | the arguments the requirement ranges over (default: all arguments) |
| `domain` | `{box: {variable: [lower, upper]}}`, or `{points: [{variable: value}, ...]}` for `exact_value` and `relation_at_points`; default box: the declared column ranges |
| `tolerance` | `{value, unit}`; the unit is that of the checked quantity |
| `verification` | `symbolic`, `sampling` or `symbolic_then_sampling` (default); `sampling: {samples, seed}` is required when the verification uses sampling, so that the sample count and the seed are recorded |
| `exclude_on_violation` | default `true`: a demonstrated violation excludes the candidate; `false` only with `exception`, the source of the user's explicit instruction |
| `source` | `{stated_by, date, note}` |
| `statement` | the requirement in words (optional) |

Type-specific fields: `symmetry`: `transform` (variable → expression) and `factor` (1 or −1),
meaning f(T(v)) = factor · f(v); `monotonicity`: `variable`, `direction` (`increasing` or
`decreasing`); `parity`: `parity` (`even` or `odd`) and optional `flip` (the variables whose
signs are flipped jointly; default all); `exact_value`: `value` at every point of the domain;
`inequality`: `relation` over the target name and the variables, for example
`domega*omega <= 0` (the harness checks `lhs − rhs ≤ tolerance`; a strict relation `<` is
treated like `<=`, so that with tolerance 0 equality is accepted); `curvature`: `variable`, `sign` (`convex` or `concave`); `limit`:
`variable`, `approach` (a number, `oo` or `-oo`), `value` (the box covers the other variables);
`equation`: `equals`, the expression the target must equal; `relation_at_points`: `relation`
over `at1, at2, ...`, the target values at the listed points in their order. A requirement stated
in words belongs in `requirements_nl`; the harness reports it as unresolved and the human
assesses it.

## 5 Sealing rules

1. Only the package `aspire_sysid.evaluate` resolves and opens the files of `test/` and
   `reference/` (`evaluate/sealed.py`); the task loader records their declared locations
   without opening them. No other module contains a string constant equal to `test` or
   `reference` or containing it as a path segment, apart from the definition `SEALED_FOLDERS` in
   `task/schema.py` and the YAML field names in `task/loader.py`.
2. Nothing shown to the agent may contain a recording name, a file name of the raw data, the
   split provenance or the history of the experiments. Recording
   names live only in `data.source_name` and `test[].source_name`. Context that the user chooses
   deliberately, such as the description of the system, is permitted.
3. An agent-visible path (`data.train`, `data.val`, `context[].file`) may not resolve into
   `test/`, `reference/` or the folder of a declared test or reference file; the loader rejects
   such a path without opening the file (symbolic links followed).
4. The working directory receives only `data/train.csv`, `data/val.csv` and `context/<file>`
   from the task folder (`aspire_sysid.task.provision_data`).
5. The leak scanner `aspire_sysid.evaluate.leaks.scan_for_sealed_leaks` searches files and
   texts for sealed paths and file names, recording names and their stems without episode
   numbers, SHA-256 digests of the sealed files, test rows, test values compared by value at the
   precision they are written with (at least six significant digits, any number format), and the
   text of the reference expression; values that also occur in the agent-visible data are not
   reported. The harness runs it on the transcript and the files of every run and on the results
   sent to the agent in interactive operation.

6. The blind-to-described mapping (`BLIND_MAPPING.md`, `blind_mapping.yaml`, Section 7) lies in
   this folder, outside every task folder, and is never provisioned; `provenance.md` of a task
   folder is never provisioned either (rule 4). No module of the harness names the mapping files.

## 6 Adding and validating a task

A user who defines a task starts from `GUIDE.md` and the two example tasks, whose `task.yaml` files
carry a comment on every field. Validate a task, including the sealed part, and inspect what the
agent will see:

    aspire task validate tasks/<task-id>
    aspire task show tasks/<task-id>

Line endings in this folder are LF on every platform (`tasks/.gitattributes`), so that the SHA-256
digests of the files do not depend on the operating system.

## 7 Blind variants

A **blind variant** tests what the task context contributes: it is a task folder generated from a described task that keeps the data and the
evaluation settings and omits everything that tells the agent what the system is. The blind
variants of `turtlebot`, `fermenter-pressure` and `friction-driven` are generated by `make_blind.py` in this
folder:

    python tasks/make_blind.py            # (re)write task-jdhj/, task-qtqm/, task-kt5o/ and both mapping files
    python tasks/make_blind.py --check    # verify that they are up to date (byte for byte)

| Kept | Replaced | Omitted |
|---|---|---|
| data values, row order and trajectory boundaries of every file (only the header row differs); split into training, validation and test data; T_s; column roles; states, inputs, measurement equation, input hold, integrator, substeps; evaluation mode, initialization, scoring interval, time limits; failure limits (numbers); budget; pool limit 10; permitted functions; noise and preprocessing statements as data-quality information, rewritten in the blind names from the table `DATA_QUALITY` of `make_blind.py` (no physical quantity, unit or system, no relation between columns beyond the roles); the sealed reference expression, rewritten in the blind names | column names: `y` for the output, `x1, x2, ...` for the other inputs and states in the described column order, `d<state>` for a state derivative (also the expression key); task identifier `task-` + four random characters; title `Identification task <characters>`; test files `test/held_out_<i>.csv`; failure-limit justifications regenerated from the training values | declared column ranges (a blind column declares none); units (`not supplied`); symbols; column descriptions; description; intended use; formal and natural-language requirements; literature; supporting files; discussion questions; given constants; the physical wording of the noise and preprocessing statements; recording names (`source_name`) |

The trajectory column keeps the name `trajectory`, a word of the harness that every dynamic brief
uses. The identifiers were drawn once with `secrets.choice` and assigned with
`random.SystemRandom.sample`; they are fixed constants of the generator and are not
derived from the described identifiers. Each blind folder has a `provenance.md` for the user, never shown to the agent, that
names its described task; `BLIND_MAPPING.md` lists the mapping of task identifiers, column names,
expression keys, file names and recording names and the kept and omitted fields per task, and
`blind_mapping.yaml` is its machine-readable form. Both files document for the reader how the blind
folders were generated; the harness reads neither. A blind variant is an ordinary task with its
own experiment (`experiments/<id>/experiment.yaml` names one task), and no module of the harness
links it to its described task; the link is stated in the mapping files and in
`provenance.md` of the blind folder, never in what the agent receives. 
