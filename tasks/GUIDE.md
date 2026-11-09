# How to define a task

This guide is for a user who wants ASPIRE to identify a model from their own data. ASPIRE
consists of the harness (the software in `aspire/`) and the agent (a language model that proposes
closed-form models). A **task** tells both what to do: it is a folder with one specification file,
`task.yaml`, and the data files. The complete reference of the file is `tasks/README.md`; this
guide covers what a first task needs.

Two example tasks can be copied and edited. Their `task.yaml` files carry a comment on every
field, and their data are synthetic:

| Folder | Kind of task | Model sought |
|---|---|---|
| `tasks/example-static/` | static: the output depends on the inputs of the same row | `F` as an expression of `d` |
| `tasks/example-dynamic/` | dynamic, discrete time: the next state depends on the present state and input | `h_next` as an expression of `h` and `u` |

`tasks/turtlebot/` is a task with measured data, three states and two inputs.

## 1 What you need

1. **The data as tables.** Comma-separated files with one header row of column names and one
   numeric row per sample. For a dynamic task the rows are consecutive samples with a constant
   sampling period.
2. **The role of every column.** Which column is the output to be modelled, which columns are
   inputs, and, for a dynamic task, which are states.
3. **The sampling period** T_s in seconds, for a dynamic task.
4. **A part of the data set aside as test data.** The agent never sees the test data; the harness
   scores every model on them.
5. **A few sentences** on what the system is and what the model will be used for. They are
   optional, and they are the main information the agent has besides the data.

## 2 Steps

1. Copy an example folder to `tasks/<your-id>/`. The identifier consists of lower-case letters,
   digits and hyphens. Delete `build.py`; it only generates the synthetic data of the example.
2. Put your training data into `data/train.csv` and your test data into `test/`, one file per
   test trajectory (Section 4).
3. Edit `task.yaml` (Section 3). Set `id` to the name of the folder.
4. Check the task and read what the agent will receive:

       aspire task validate tasks/<your-id>
       aspire brief tasks/<your-id>

   The first command names every error of the file with its field. The second prints the task
   brief `TASK.md`. The harness writes the brief from `task.yaml` by fixed rules; no language
   model is involved, and you do not write `TASK.md` yourself.
5. Create an experiment, `experiments/<your-id>/experiment.yaml`. An experiment is one task, run
   one or more times with identical settings:

       schema_version: 2
       id: <your-id>            # the name of the experiment folder
       model: gpt-6.1-sol
       task: <your-id>          # the name of the task folder
       runs: 3                  # repeated runs differ only in the responses of the language model
       concurrency: 3           # runs executed at the same time

6. Try it without cost, then run it, then read the report:

       aspire experiment run experiments/<your-id> --dry-run --agent-python <interpreter>
       aspire experiment run experiments/<your-id> --agent-python <interpreter>
       aspire experiment report experiments/<your-id>

   The dry run replaces the language model by a scripted agent and tests the task and the
   software. A real run needs the API key of the model's vendor and a committed state of
   `aspire/` and `tasks/`; `aspire/README.md`, section "Experiments", describes both and the
   agent's interpreter. The report is `experiments/<your-id>/report/index.html`.

## 3 The fields of `task.yaml`

"Required" refers to a first task; `tasks/README.md`, Section 2, lists every field.

| Field | Required | Content |
|---|---|---|
| `schema_version` | yes | `1` |
| `id` | yes | the name of the task folder |
| `title` | yes | one line; the heading of the brief |
| `formulation` | yes | `static`, or `discrete` for a dynamic task in discrete time (also `continuous` and `narx`) |
| `description` | no | what the system is and how the data were obtained |
| `intended_use` | no | what the model will be used for |
| `columns` | yes | per column: `name` (as in the data files), `symbol`, `roles`, `unit`, `description`, `range` |
| `dynamics` | dynamic tasks | `sampling_period`, `states`, `inputs`, `measurement`, `input_hold` |
| `evaluation` | yes | `mode`, `initialization`, `scoring`, `failure_limits`, `time_limit_s` |
| `data` | yes | `train`; optional `val`, `trajectory_column`, `noise`, `preprocessing` |
| `test` | recommended | the sealed test files with a name for each trajectory; the file is valid without them, but the models then cannot be scored on data the agent has not seen |
| `pool_cap` | yes | the largest number of models evaluated per run; 10 in the examples |
| `budget` | no | the limits of one run: turns, seconds of execution time, US dollars; default 60 turns, 3600 s, 10 US dollars |

Notes on the fields that need a decision:

- **Roles.** `input`: read from the data. `state`: computed by the model during a simulation.
  `output`: the measured signal on which the models are scored; exactly one column. In a dynamic
  task the output is usually also a state (`roles: [state, output]`).
- **Range.** An interval that contains every training value of the column; the validation
  reports a value outside it. The brief shows the range to the agent.
- **Unit.** A text such as `m` or `rad/s`; `"-"` for a dimensionless quantity.
- **Evaluation mode.** `algebraic` for a static task. For a dynamic task, `simulation` starts
  from the first sample of each trajectory and applies the model repeatedly with the logged
  inputs, and `one_step` predicts each sample from the measured previous one. Choose the mode
  that matches the intended use of the model.
- **Failure limits.** Bounds on the model output (static) or on every simulated state (dynamic)
  far outside the physical range. A model that leaves them has failed numerically. A bound of
  about one hundred times the largest training value serves the purpose.
- **Budget.** The defaults of the examples are 60 turns, 3600 s and 10 US dollars per run; a turn
  is one response of the language model. Three runs of the task `turtlebot` used 17 to 22
  turns, 813 to 2286 s and 1.50 to 2.35 US dollars each.

Further information can be given to the agent when you have it; each is one more field of
`task.yaml` (`tasks/README.md`): physical requirements, formal (`requirements`) or in natural
language (`requirements_nl`); given constants (`constants`); references (`literature`);
supporting files (`context`); questions that the agent must answer for every model
(`discussion_questions`). To restrict the agent, for example to forbid web access, write the
restriction into `description`; the harness does not enforce it.

## 4 Training and test data

- `data/train.csv` is the only data the agent sees, together with `data/val.csv` when you
  provide validation data.
- In a dynamic task, a training file may hold several trajectories (separate experiments). Add
  an integer column that numbers them, and name it in `data.trajectory_column`. Each trajectory
  is one contiguous block of rows.
- Each file in `test/` is one trajectory (dynamic) or one data set (static) and has no trajectory
  column. List every test file under `test` in `task.yaml` with a name of your choice.
- Split by whole trajectories where you can. A test trajectory that continues a training
  trajectory starts in a state the model was fitted to.
- In simulation mode, set `evaluation.horizon` to the number of simulated samples of a test
  trajectory (its rows minus the initialization samples; 25 in `turtlebot`). The harness then
  computes the training error on segments of that length, so that the report can compare it with
  the test error. Without it, the training error is simulated over each whole training
  trajectory.
- In simulation mode, a simulation error grows with the length of the trajectory. Give the test
  trajectories the length over which the model will be used (the TurtleBot task uses test
  trajectories of 5 s for a model intended for simulations of about 5 s).
- Do not name files or columns so that they reveal what should stay unknown to the agent. The
  agent sees the column names and the texts of `task.yaml`; it never sees the names of the files
  in `test/`.

## 5 Without writing `task.yaml` yourself

The interactive session can start from your data files instead of a task folder:

    aspire session --train <training.csv> [--val <validation.csv>] [--test <test.csv> ...]

The same is offered in the browser: `aspire web` opens a start page where you choose the files
and, later, read and answer in forms; there you can also edit a `task.yaml` with a check before it
is saved.

The harness copies the files into a new task folder (`tasks/task-<date>-<n>`, or the folder named
with `--new-task`; your files stay where they are). An agent then examines the training data, asks
you what the data do not show (what the system is, what the model is for, which column is the
output, the units), and writes `task.yaml`. You read the resulting task brief and accept it, ask
for changes, or stop; after you accept it the identification starts. Only the training data are
required. If you want test data, set them aside yourself and give one file per test trajectory
with `--test`, as several files or as a pattern such as `held_out_*.csv`; no agent can read them.
The harness does not divide a file for you.
