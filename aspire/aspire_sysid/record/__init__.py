"""Records: transcript, hashes, dataset provenance and run record.

Reproducible records: every language-model request and response, tool request and result,
user message, reminder, check outcome and termination event; dataset provenance; the record from
which the evaluation is recomputed.

- :mod:`aspire_sysid.record.transcript`: :class:`TranscriptWriter`, the JSON Lines transcript
  (an :class:`~aspire_sysid.agent.events.EventSink` of the turn loop), and the reader
  :func:`read_transcript`, :func:`reconstruct_rounds`, :func:`reconstruct_requests`;
- :mod:`aspire_sysid.record.provenance`: :func:`dataset_provenance` (for the user only) and
  :func:`authorized_provenance` (the part the agent receives);
- :mod:`aspire_sysid.record.run_record`: :func:`write_run_record`, :func:`load_run_record`,
  :func:`recompute_evaluation` and the layout of a run folder.

The hashes of the brief and the system prompt are computed by
:func:`aspire_sysid.brief.text_hashes` and stored in the run record.
"""

from .provenance import (
    DATASET_FIELDS,
    NOT_STATED,
    SEPARATION_FIELDS,
    authorized_provenance,
    dataset_provenance,
)
from .run_record import (
    EVALUATION_DIR,
    POOLS_DIR,
    PROVENANCE_FILE,
    RUN_RECORD_FILE,
    TRANSCRIPT_FILE,
    RecordError,
    RecordExistsError,
    RecordMismatchError,
    RoundEntry,
    code_revision,
    harness_identity,
    evaluation_dir,
    load_run_record,
    pool_dir,
    recompute_evaluation,
    record_task,
    snapshot_pool,
    software_versions,
    stored_evaluation,
    task_digests,
    write_run_record,
)
from .transcript import (
    TRANSCRIPT_SCHEMA_VERSION,
    ReconstructedRequest,
    RoundSummary,
    TranscriptContents,
    TranscriptError,
    TranscriptWriter,
    read_transcript,
    reconstruct_requests,
    reconstruct_rounds,
    summarize_transcript,
)

__all__ = [
    "DATASET_FIELDS",
    "EVALUATION_DIR",
    "NOT_STATED",
    "POOLS_DIR",
    "PROVENANCE_FILE",
    "RUN_RECORD_FILE",
    "SEPARATION_FIELDS",
    "TRANSCRIPT_FILE",
    "TRANSCRIPT_SCHEMA_VERSION",
    "ReconstructedRequest",
    "RecordError",
    "RecordExistsError",
    "RecordMismatchError",
    "RoundEntry",
    "RoundSummary",
    "TranscriptContents",
    "TranscriptError",
    "TranscriptWriter",
    "authorized_provenance",
    "code_revision",
    "harness_identity",
    "dataset_provenance",
    "evaluation_dir",
    "load_run_record",
    "pool_dir",
    "read_transcript",
    "recompute_evaluation",
    "reconstruct_requests",
    "reconstruct_rounds",
    "record_task",
    "snapshot_pool",
    "software_versions",
    "stored_evaluation",
    "summarize_transcript",
    "task_digests",
    "write_run_record",
]
