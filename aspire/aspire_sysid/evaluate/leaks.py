"""Leak scanner: search files and texts for sealed information of a task.

Sealed data are inaccessible through the agent's files, tools and conversation;
filenames and descriptions visible to the agent do not disclose withheld information, such
as the names of the recordings or the way the datasets were split; no test number reaches
the agent. The scanner can be applied to every file written to a working directory and
to every message sent to the agent.

The scanner builds a fingerprint of the sealed part of a task and reports every occurrence of:

- ``sealed_path``: a declared or absolute path of a sealed file or folder;
- ``sealed_file_name``: the file name of a sealed file;
- ``source_name``: a recording name (``data.source_name`` or a test entry's ``source_name``), or
  its stem without a trailing episode or part number (``recording-A-ep1`` → ``recording-A``,
  see :func:`source_name_stems`);
- ``file_hash``: a file or text whose SHA-256 digest equals that of a sealed file;
- ``test_row``: a data row of a test file, as written in the file, that does not also occur in
  the agent-visible data;
- ``test_value``: a number in the text, written with ``d`` ≥ :data:`MIN_SIGNIFICANT_DIGITS`
  significant digits in any spelling (positional, exponent, NumPy output), that equals a test
  value rounded to ``d`` significant digits. The comparison is by value: the token and the test
  values are both rounded to ``d`` digits. Test values that also occur in the agent-visible data
  (training, validation, supporting files) are excluded, and so is, for each ``d``, every rounded
  test value that coincides with a rounded agent-visible value, so that numbers derived from the
  visible data are not reported. Limitation: a test value printed with fewer than
  :data:`MIN_SIGNIFICANT_DIGITS` significant digits (for example 0.046057, five digits) is not
  detected; rows are still detected by ``test_row`` when printed in the file's spelling;
- ``reference_expression``: the text of a sealed reference expression (whitespace ignored).

Transcripts (JSON Lines, ``*.jsonl``): the ``test_value`` check reads every line without the
fields that the harness writes for its own record and never sends to the agent
(:data:`HARNESS_BOOKKEEPING_FIELDS`: costs, token counts, times, limits, counters). Their numbers
are harness bookkeeping, not content the agent saw or wrote; a running cost total, for example,
can match a test value to six digits. Every other field (messages,
responses, tool calls and results, reasoning, check reports) is compared, and all other checks
read the complete text.

The scanner may read the sealed files; it lives in ``aspire_sysid.evaluate`` for that reason
. The harness applies it to briefs, messages and transcripts.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Union

from ..task.schema import TaskSpec
from .sealed import REFERENCE_DIR, TEST_DIR, reference_file_path, sealed_test_paths

MIN_SIGNIFICANT_DIGITS = 6
"""Minimum number of significant digits of a number in a scanned text compared with test values.

Choice: with six digits, a number that is unrelated to the test data matches one of
the ``M`` distinctive test values only when it lies within half a unit of the sixth digit of one
of them; for M of a few thousand (friction-driven: about 2800) and numbers spread over a decade,
this is a chance of the order of M / 9e5, below 0.5 % per number of the same magnitude. Numbers
derived from the agent-visible data are excluded by construction (module docstring). Five
digits would raise that chance tenfold and flag ordinary fitted coefficients."""

MAX_SIGNIFICANT_DIGITS = 17
"""Digits of a double-precision number; longer spellings are compared at 17 digits."""

MIN_ROW_LENGTH = 12
"""Minimum length in characters of a test row counted as a fingerprint."""

MIN_STEM_LENGTH = 8
"""Minimum length of a recording-name stem added to the fingerprint."""

_STEM_SUFFIX = re.compile(r"[-_ ](?:ep|episode|traj|trajectory|part|seg|run)?\d+$", re.IGNORECASE)

_NUMBER = re.compile(r"(?<![\w.])[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")

HARNESS_BOOKKEEPING_FIELDS: frozenset[str] = frozenset({
    # labels, times and counters of every event (aspire_sysid.record.transcript, agent.loop)
    "recorded_at", "timestamp", "elapsed_s", "seq", "line", "waiting_s",
    # cost and token accounting of requests and responses
    "cost_usd", "usage", "usage_charged", "totals", "agent_totals", "excess", "attempts", "latency_s",
    # limits, allowances and request settings
    "limits", "limit", "allowance", "price", "timeout_s", "max_output_tokens", "n_messages", "tools_line",
    # measurements of tool executions and evaluations
    "duration_s", "content_chars", "stdout_chars", "stderr_chars",
})
"""Fields of transcript events that the harness writes for its own record and never sends to the
agent; the ``test_value`` check of a transcript skips them (module docstring). A field of this name
inside content that the agent saw or wrote is a string of that content, not a field of the event,
and is still compared."""


def _without_bookkeeping(obj: object) -> object:
    if isinstance(obj, dict):
        return {k: _without_bookkeeping(v) for k, v in obj.items() if k not in HARNESS_BOOKKEEPING_FIELDS}
    if isinstance(obj, list):
        return [_without_bookkeeping(v) for v in obj]
    return obj


def _value_text(where: str, text: str) -> str:
    """The text whose numbers are compared with the test values: for a JSON Lines transcript, each
    line without :data:`HARNESS_BOOKKEEPING_FIELDS`; otherwise the text itself. A line that is not
    JSON is compared as written."""
    if not where.endswith(".jsonl"):
        return text
    out = []
    for line in text.splitlines():
        try:
            out.append(json.dumps(_without_bookkeeping(json.loads(line)), ensure_ascii=False))
        except ValueError:
            out.append(line)
    return "\n".join(out)

ScanItem = Union[Path, str, tuple[str, str]]
"""A path (file or folder, scanned recursively), a text, or a pair (label, text)."""


@dataclass(frozen=True)
class LeakFinding:
    """One occurrence of sealed information: its kind, where it was found, and what matched."""

    kind: str
    where: str
    detail: str


@dataclass(frozen=True)
class SealedFingerprint:
    """The searchable fingerprint of the sealed part of a task."""

    path_strings: tuple[str, ...]
    file_names: tuple[str, ...]
    source_names: tuple[str, ...]
    hashes: dict[str, str]
    rows: frozenset[str]
    values: dict[int, frozenset[str]]
    reference_texts: tuple[str, ...]


def _significant_digits(token: str) -> int:
    mant = re.split(r"[eE]", token.lstrip("+-"))[0].replace(".", "")
    return len(mant.lstrip("0"))


def _key(x: float, d: int) -> str:
    """``|x|`` rounded to ``d`` significant digits, as a canonical string."""
    return f"{abs(x):.{d - 1}e}"


def source_name_stems(name: str) -> set[str]:
    """``name`` and its stems without trailing episode or part numbers.

    ``recording-A-ep1`` gives ``recording-A``; a stem shorter than
    :data:`MIN_STEM_LENGTH` characters is not added.
    """
    out = {name}
    stem = name
    while True:
        new = _STEM_SUFFIX.sub("", stem)
        if new == stem or len(new) < MIN_STEM_LENGTH:
            return out
        out.add(new)
        stem = new


def _data_lines(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines[1:] if ln.strip()]


def sealed_fingerprint(task: TaskSpec) -> SealedFingerprint:
    """Build the fingerprint of the sealed part of ``task`` (reads the sealed files).

 Rows and values that also occur in the
    agent-visible data (training, validation, supporting files) are not part of the
    fingerprint, because their occurrence discloses nothing.
    """
    test_paths = sealed_test_paths(task)
    ref_path = reference_file_path(task)
    sealed_files = test_paths + ([ref_path] if ref_path is not None else [])
    root = task.task_dir.resolve()

    paths: set[str] = set()
    for p in sealed_files:
        rel = p.relative_to(root).as_posix()
        paths.update({rel, rel.replace("/", "\\"), str(p), p.as_posix(), f"{task.id}/{rel}"})
    for folder in (TEST_DIR, REFERENCE_DIR):
        paths.update({str(root / folder), (root / folder).as_posix(), f"tasks/{task.id}/{folder}", f"tasks\\{task.id}\\{folder}"})
    names = {p.name for p in sealed_files}

    sources: set[str] = set()
    for group in task.data.source_names.values():
        sources.update(s for s in group if s)
    sources.update(e.source_name for e in task.sealed.test if e.source_name)
    sources = set().union(*(source_name_stems(n) for n in sources)) if sources else set()

    hashes = {hashlib.sha256(p.read_bytes()).hexdigest(): p.relative_to(root).as_posix() for p in sealed_files}

    visible_files = [task.data.train_path] + ([task.data.val_path] if task.data.val_path else [])
    visible_rows: set[str] = set()
    visible_values: set[float] = set()
    tc = task.data.trajectory_column
    for vf in visible_files:
        lines = vf.read_text(encoding="utf-8").splitlines()
        header = [h.strip() for h in lines[0].split(",")]
        keep = [i for i, h in enumerate(header) if h != tc]
        for ln in lines[1:]:
            cells = [c.strip() for c in ln.split(",")]
            if len(cells) != len(header):
                continue
            visible_rows.add(",".join(cells[i] for i in keep))
            visible_values.update(abs(float(c)) for c in cells)
    for ctx in task.context:
        text = ctx.path.read_text(encoding="utf-8", errors="replace")
        visible_values.update(abs(float(tok)) for tok in _NUMBER.findall(text))

    rows: set[str] = set()
    test_values: set[float] = set()
    for p in test_paths:
        for ln in _data_lines(p):
            cells = [c.strip() for c in ln.split(",")]
            norm = ",".join(cells)
            if norm not in visible_rows and len(norm) >= MIN_ROW_LENGTH:
                rows.add(norm)
            test_values.update(abs(float(c)) for c in cells)
    test_values -= visible_values
    values = {}
    for d in range(MIN_SIGNIFICANT_DIGITS, MAX_SIGNIFICANT_DIGITS + 1):
        keys = {_key(x, d) for x in test_values} - {_key(x, d) for x in visible_values}
        values[d] = frozenset(keys)

    ref_texts: list[str] = []
    if ref_path is not None:
        from .sealed import load_reference

        ref = load_reference(task)
        for key in ref.expressions:
            ref_texts.append(re.sub(r"\s+", "", ref.expressions[key]))
            ref_texts.append(re.sub(r"\s+", "", str(ref.parsed[key])))

    return SealedFingerprint(
        path_strings=tuple(sorted(paths)),
        file_names=tuple(sorted(names)),
        source_names=tuple(sorted(sources)),
        hashes=hashes,
        rows=frozenset(rows),
        values=values,
        reference_texts=tuple(sorted(set(ref_texts))),
    )


def _iter_items(items: Iterable[ScanItem] | ScanItem) -> Iterable[tuple[str, bytes]]:
    if isinstance(items, (str, Path)) or (isinstance(items, tuple) and len(items) == 2 and all(isinstance(x, str) for x in items)):
        items = [items]
    for i, item in enumerate(items):
        if isinstance(item, Path):
            if item.is_dir():
                for f in sorted(p for p in item.rglob("*") if p.is_file()):
                    yield str(f), f.read_bytes()
            elif item.is_file():
                yield str(item), item.read_bytes()
        elif isinstance(item, tuple):
            yield item[0], item[1].encode("utf-8")
        else:
            yield f"text[{i}]", str(item).encode("utf-8")


def scan_for_sealed_leaks(
    task: TaskSpec, items: Iterable[ScanItem] | ScanItem, *, fingerprint: SealedFingerprint | None = None
) -> list[LeakFinding]:
    """Search ``items`` for sealed information of ``task``; return every finding (empty: none).

 ``items`` are paths (a folder is scanned
    recursively, every file as text), texts, or ``(label, text)`` pairs. A precomputed
    ``fingerprint`` (:func:`sealed_fingerprint`) may be passed when many items are scanned.
    """
    fp = fingerprint or sealed_fingerprint(task)
    findings: list[LeakFinding] = []
    for where, blob in _iter_items(items):
        digest = hashlib.sha256(blob).hexdigest()
        if digest in fp.hashes:
            findings.append(LeakFinding("file_hash", where, f"identical to sealed file {fp.hashes[digest]}"))
        text = blob.decode("utf-8", errors="replace")
        for s in fp.path_strings:
            if s in text:
                findings.append(LeakFinding("sealed_path", where, s))
        for s in fp.file_names:
            if s in text:
                findings.append(LeakFinding("sealed_file_name", where, s))
        for s in fp.source_names:
            if s in text:
                findings.append(LeakFinding("source_name", where, s))
        compact = re.sub(r"\s+", "", text)
        for s in fp.reference_texts:
            if s and s in compact:
                findings.append(LeakFinding("reference_expression", where, s))
        row_text = re.sub(r"[ \t]*,[ \t]*", ",", text)
        for r in fp.rows:
            if r in row_text:
                findings.append(LeakFinding("test_row", where, r))
        seen: set[str] = set()
        for tok in _NUMBER.findall(_value_text(where, text)):
            d = min(_significant_digits(tok), MAX_SIGNIFICANT_DIGITS)
            if d < MIN_SIGNIFICANT_DIGITS:
                continue
            try:
                key = _key(float(tok), d)
            except (ValueError, OverflowError):
                continue
            if key in fp.values[d] and tok not in seen:
                seen.add(tok)
                findings.append(LeakFinding("test_value", where, tok))
    return findings
