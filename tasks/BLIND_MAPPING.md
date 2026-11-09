# Blind task variants: mapping to the described tasks

A **blind variant** is a task folder generated from a described task by `tasks/make_blind.py`; it keeps the data values and the evaluation settings and omits everything that tells the agent (the language model) what the system is. A blind variant is an ordinary task with its own experiment: the harness neither provisions nor reads this file or `tasks/blind_mapping.yaml`; both document how the blind folders were generated. Regenerate both files and the blind folders with `python tasks/make_blind.py`; `python tasks/make_blind.py --check` verifies that they are up to date.

**Identifiers.** Drawn once: `task-` followed by four characters chosen independently and uniformly from `a`-`z` and `0`-`9` (`secrets.choice`); a second draw (`random.SystemRandom().sample`) fixed the assignment to the described tasks. They are fixed constants of the generator and are not derived from the described identifiers.

**Names.** Output column `y`; other input and state columns `x1, x2, ...` in the described column order; a state-derivative column `d<state>` in the blind names, which is also the expression key of that state; the expression key of a state of a discrete-time task is `<state>_next` in the blind names. The trajectory column keeps its name `trajectory` (a harness word, used in every dynamic brief). Test files `test/held_out_<i>.csv`. Unit of every column and failure limit: `not supplied`. A blind column declares no range.

| Blind task | Described task | Title of the blind task |
|---|---|---|
| `task-jdhj` | `friction-driven` | Identification task jdhj |
| `task-qtqm` | `fermenter-pressure` | Identification task qtqm |
| `task-kt5o` | `turtlebot` | Identification task kt5o |

## `task-jdhj` (blind variant of `friction-driven`)

| Blind column | Described column |
|---|---|
| `y` | `theta` |
| `x1` | `omega` |
| `x2` | `u` |
| `dx1` | `domega` |
| `trajectory` (trajectory column) | `trajectory` |

| Blind expression key | Described expression key |
|---|---|
| `dx1` | `domega` |
| `dy` | `dtheta` |

| Blind file | Described file | Recording name |
|---|---|---|
| `data/train.csv` | `data/train.csv` | not stated |
| `data/val.csv` | `data/val.csv` | not stated |
| `test/held_out_1.csv` | `test/test_trajectory_1.csv` | not stated |
| `test/held_out_2.csv` | `test/test_trajectory_2.csv` | not stated |
| `test/held_out_3.csv` | `test/test_trajectory_3.csv` | not stated |
| `test/held_out_4.csv` | `test/test_trajectory_4.csv` | not stated |

Kept: data values, row order and trajectory boundaries of every file; split into training, validation and test data; column roles; sampling period T_s, states, inputs, measurement equation, input hold, integrator, substeps; evaluation mode, initialization, scoring interval, time limits, horizon of the training evaluation; failure limits (numbers); budget; pool limit; permitted functions.

Omitted: system description; intended use; formal requirements; column symbols; column descriptions; units (every unit is 'not supplied'); declared column ranges; failure-limit justifications (regenerated from the training values).

## `task-qtqm` (blind variant of `fermenter-pressure`)

| Blind column | Described column |
|---|---|
| `y` | `p` |
| `x1` | `valve` |
| `x2` | `flow` |
| `dy` | `dp` |

| Blind expression key | Described expression key |
|---|---|
| `dy` | `dp` |

| Blind file | Described file | Recording name |
|---|---|---|
| `data/train.csv` | `data/train.csv` | not stated |
| `data/val.csv` | `data/val.csv` | not stated |
| `test/held_out_1.csv` | `test/test_trajectory_1.csv` | not stated |

Kept: data values, row order and trajectory boundaries of every file; split into training, validation and test data; column roles; sampling period T_s, states, inputs, measurement equation, input hold, integrator, substeps; evaluation mode, initialization, scoring interval, time limits, horizon of the training evaluation; failure limits (numbers); budget; pool limit; permitted functions.

Omitted: system description; intended use; natural-language requirements; column symbols; column descriptions; units (every unit is 'not supplied'); declared column ranges; failure-limit justifications (regenerated from the training values).

## `task-kt5o` (blind variant of `turtlebot`)

| Blind column | Described column |
|---|---|
| `y` | `x` |
| `x1` | `y` |
| `x2` | `phi` |
| `x3` | `v_f` |
| `x4` | `v_a` |
| `trajectory` (trajectory column) | `trajectory` |

| Blind expression key | Described expression key |
|---|---|
| `x1_next` | `y_next` |
| `x2_next` | `phi_next` |
| `y_next` | `x_next` |

| Blind file | Described file | Recording name |
|---|---|---|
| `data/train.csv` | `data/train.csv` | randrealFeb18_5Hz_ep1, randrealFeb18_5Hz_ep2, randrealFeb18_5Hz_ep3 |
| `test/held_out_1.csv` | `test/test_trajectory_1.csv` | not stated |
| `test/held_out_10.csv` | `test/test_trajectory_10.csv` | not stated |
| `test/held_out_11.csv` | `test/test_trajectory_11.csv` | not stated |
| `test/held_out_12.csv` | `test/test_trajectory_12.csv` | not stated |
| `test/held_out_2.csv` | `test/test_trajectory_2.csv` | not stated |
| `test/held_out_3.csv` | `test/test_trajectory_3.csv` | not stated |
| `test/held_out_4.csv` | `test/test_trajectory_4.csv` | not stated |
| `test/held_out_5.csv` | `test/test_trajectory_5.csv` | not stated |
| `test/held_out_6.csv` | `test/test_trajectory_6.csv` | not stated |
| `test/held_out_7.csv` | `test/test_trajectory_7.csv` | not stated |
| `test/held_out_8.csv` | `test/test_trajectory_8.csv` | not stated |
| `test/held_out_9.csv` | `test/test_trajectory_9.csv` | not stated |

Kept: data values, row order and trajectory boundaries of every file; split into training, validation and test data; column roles; sampling period T_s, states, inputs, measurement equation, input hold, integrator, substeps; evaluation mode, initialization, scoring interval, time limits, horizon of the training evaluation; failure limits (numbers); budget; pool limit; permitted functions.

Omitted: system description; intended use; column symbols; column descriptions; units (every unit is 'not supplied'); declared column ranges; recording names (data.source_name, test[].source_name; listed in this mapping only); failure-limit justifications (regenerated from the training values).
