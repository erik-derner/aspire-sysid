"""HTML report of an experiment for the user of ASPIRE.

:func:`build_report` reads the stored records of an experiment folder (run records, evaluation
reports, model files, transcripts) and writes a static HTML report into
``experiments/<id>/report/``: ``index.html`` (the assignment, how it was run, what came out, the
files) and one page per run, ``r<NN>.html`` (the models found and what the agent did). The report
contains results on the sealed test data; it is never placed into a working directory of an agent.

    aspire experiment report <experiment-dir> [--dry-run] [--out DIR]
    python -m aspire_sysid.report <experiment-dir> [--out DIR]
"""

from .html_report import build_report

__all__ = ["build_report"]
