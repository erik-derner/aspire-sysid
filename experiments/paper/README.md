# Results of the manuscript: collection and assessment

This folder holds what turns the six experiments `experiments/paper-*` and the reference models
`experiments/references/` into the numbers, tables and figures of the manuscript, and
the assessment of the model records. The harness is the software of ASPIRE; the
agent is the language model that identifies models. Nothing here calls a language model.

## Files

- `collect_results.py`: reads the aggregations, run records, transcripts, delivered model files
  and reference evaluations and writes `results.json` (every number of the manuscript),
  `results.md` (the same as tables), `tables.tex` (table bodies) and the figures
  `test-<system>.pdf` into the output folder `paper/figures/`, which the script creates. Run after `aspire experiment aggregate` of the six
  experiments: `.venv/Scripts/python.exe experiments/paper/collect_results.py`.
  It also reads the outcomes of the formal requirements per candidate (runs and models of PySINDy
  and PySR) and computes the numbers that the text of the manuscript states over all runs
  (`derived` in `results.json`, section "Numbers of the text" in `results.md`).
- `blind_requirements.py`: applies the formal requirements of `friction-driven` to the recommended
  models of its blind task after renaming the variables, and writes `blind_requirements.json`
  (all five models satisfy R1 and R3 and violate R2).
- `transcript_digest.py`: prints a condensed text of the transcript of one run (one block per
  event, headed by the line number `L<n>` of `transcript.jsonl`), for reading a run.
- `assessment/<experiment>.md` and `.json`: the assessment of the model records (below).
- `assessment/checks/fermenter_requirements.py`: evaluates the recommended models of
  `paper-fermenter-pressure` on a grid against the requirements R1 to R5, which the task states in
  natural language, and writes `assessment/checks/paper-fermenter-pressure-requirements.json`; the
  rule is in the docstring of the script.

The run shown in a figure and in Appendix B of the manuscript is the run whose recommended
candidate has the median test score of the five runs of the experiment (`median_run` in
`results.json`): `paper-turtlebot` r03, `paper-friction-driven` r02, `paper-fermenter-pressure`
r05.

The experiment `paper-fermenter-pressure` is the set of runs of 2026-10-08 13:37 to 14:07 UTC on the
task with five requirements in natural language (R1 to R5). The experiment `paper-friction-driven`
is the set of runs of 2026-10-09 13:37 to 14:04 UTC on the task with three formal requirements: R1
(`dtheta` = `omega`), R2 (`domega*theta <= 0` at rest with zero voltage) and R3 (`domega` does not
decrease with `u`).

## Assessment of the model records

Section 5.6 of the manuscript assesses the model record of the recommended candidate of every
run by five items. The marks in `assessment/` were proposed by an AI coding assistant (Claude)
from the run records only (model file, the agent's scripts, the transcript; no test results) and
checked against this evidence by two of the authors, one for the mobile robot and one for the
friction system and the fermenter; no mark was changed. Each mark has its evidence next to it:
`L<n>` is line n of `runs/<run>/transcript.jsonl`, and a script is a file of
`runs/<run>/workspace/`.

Marking rule (applied to all 30 records):

- **(a) interpretation.** Every term of every expression is interpreted, and correctly. `yes`:
  all terms; `partly`: one term is not interpreted, or one interpretation is vague or wrong;
  `no`: several. Blind task: a term must be described by its mathematical effect. A physical
  meaning stated as fact lowers the mark; a physical analogy that the record labels as a
  hypothesis or analogy, next to the mathematical description, does not.
- **(b) origin.** Every factual claim of `discussion.origin` (what was tried, in which order,
  which result led to a term, which numbers) is found in the transcript. `partly`: the main line
  agrees and one claim is not found or is inaccurate; `no`: the origin contradicts the transcript
  or most claims are not found.
- **(c) parameter types.** `fitted` is a value that an optimizer or a regression in the script
  estimates; `fixed` a constant that the script does not estimate; `tied` is computed by its
  equation; the delivered values agree with what the script computes. `partly`: one parameter
  disagrees or cannot be traced; `no`: several, or the named script does not estimate the model.
- **(d) reasons.** A reason for the criterion, for the method, and for the starting values (or
  the statement that none are needed, with the reason). `partly`: one is missing; `no`: two or
  three.
- **(e) limitations.** Every stated limitation follows from the data or from the structure, and
  at least two specific ones are given. `partly`: a valid limitation is mixed with an
  unsupported, wrong or generic one; `no`: none, or only generic or wrong ones.

Counts (yes / partly / no; five records per experiment):

| Experiment | (a) | (b) | (c) | (d) | (e) |
|---|---|---|---|---|---|
| `paper-turtlebot` | 5 / 0 / 0 | 5 / 0 / 0 | 5 / 0 / 0 | 5 / 0 / 0 | 5 / 0 / 0 |
| `paper-turtlebot-blind` | 5 / 0 / 0 | 3 / 2 / 0 | 5 / 0 / 0 | 4 / 1 / 0 | 5 / 0 / 0 |
| `paper-friction-driven` | 4 / 1 / 0 | 4 / 1 / 0 | 5 / 0 / 0 | 5 / 0 / 0 | 5 / 0 / 0 |
| `paper-friction-driven-blind` | 5 / 0 / 0 | 3 / 2 / 0 | 4 / 1 / 0 | 3 / 2 / 0 | 5 / 0 / 0 |
| `paper-fermenter-pressure` | 5 / 0 / 0 | 2 / 3 / 0 | 5 / 0 / 0 | 5 / 0 / 0 | 5 / 0 / 0 |
| `paper-fermenter-pressure-blind` | 3 / 2 / 0 | 4 / 1 / 0 | 5 / 0 / 0 | 3 / 2 / 0 | 5 / 0 / 0 |
| all | 27 / 3 / 0 | 21 / 9 / 0 | 29 / 1 / 0 | 25 / 5 / 0 | 30 / 0 / 0 |

In total 132 marks are yes, 18 partly and none no; 13 of the 18 concern blind tasks.

Points where the assessment files asked the checker for a ruling (each is described under the
run in the file). Each point stands as the marks
treat it:

1. Borderline marks that were set to `yes`: `paper-turtlebot` r04 (b), (d), (e);
   `paper-turtlebot-blind` r02 (d), r05 (b); `paper-friction-driven` r01 (d), r02 (b), r03 (a),
   (d), r04 (a), r05 (b), (d); `paper-fermenter-pressure` r01 (b), r02 (b). Marks set to `partly`
   that a lenient reading makes `yes`: `paper-friction-driven` r01 (b), r05 (a);
   `paper-fermenter-pressure` r03 (b), r05 (b).
2. `paper-fermenter-pressure-blind` r05 (a): four terms of the polynomial belong to no
   interpreted group; marked `partly`, and `no` under a strict count of terms.
3. Whether a parameter that the optimizer returned at a bound may be declared `fitted` (several
   records; they say so in their text). The marks treat it as agreeing with item (c).
4. Whether the mechanical vocabulary of the blind friction-system records, each with a disclaimer or a
   labeled analogy, satisfies item (a) for a blind task. The marks treat it as satisfying it.
5. Three of the 150 marks were checked a second time against the model
   file, the script and the transcript, and were confirmed: `paper-turtlebot` r04 (c),
   `paper-friction-driven-blind` r03 (c) (the width `w`, declared `fitted`, is excluded from the
   optimized parameters in `fit_final.py` and held at 0.3) and `paper-turtlebot-blind` r04 (d).
   Two further marks were checked a second time and confirmed: `paper-fermenter-pressure` r04 (b)
   (the adjustable pressure exponent is family 3 of `plan.md`, written before the first fit,
   whereas the record attributes it to a residual bias) and `paper-friction-driven` r05 (a) (the
   interpretation of the record does not mention `dtheta`). The other marks were not checked a
   second time.

## Requirements of the two described tasks

**Friction system** (formal requirements R1 to R3, verified by the harness; `results.md`, section
"Formal requirements"; runs of 2026-10-09 UTC): none of the 22 candidates of `paper-friction-driven`
has a demonstrated violation; 30 of the 66 verifications ended with a proof (R1: 22, R2: 5, R3: 3)
and 36 with no violation at the sampled points and no proof. All 12 models of PySINDy and PySR
violate R2 and satisfy R1 and R3 (`experiments/references/README.md`). The five recommended models
of the blind task violate R2 and satisfy R1 and R3 (`blind_requirements.json`). Facts from the run
records are in `assessment/paper-friction-driven.md`, "Facts".

**Fermenter** (requirements in natural language; `assessment/paper-fermenter-pressure.md`): two
marks per requirement and run, confirmed with the other marks. *Addressed*: the model record addresses the
requirement (marked from the record): yes in all 25 cases, by identifier, in
`discussion.limitations`. *Satisfied*: computed by `assessment/checks/fermenter_requirements.py`
on the grid stated there: yes in all 25 cases. Settings of the rule: it evaluates R1, R2 and R5
at pressures of at least 1 bar, because below the equilibrium pressure closing the valve lowers
the inflow from the atmosphere (three records say that R2 does not hold there); "open valve" is
taken as at most 90 % closed and "approximately 1 bar" as within 0.05 bar; two models estimate
the equilibrium pressure (0.992 and 0.986 bar) and three fix it at 1 bar.
