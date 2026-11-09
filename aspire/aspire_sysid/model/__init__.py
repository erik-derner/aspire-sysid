"""Expressions, model files and the file and expression checks.

Implements the permitted expressions and the file and expression checks, the candidate
contents (labels, parameter table with fitted, fixed and tied parameters, estimation
record), the discussion, answers and recommendation, the model file content and the default
permitted functions; rules F1 to P1.

- :mod:`aspire_sysid.model.checks` is the single check module. It depends only on the Python
  standard library and SymPy, because the working directory receives a byte-identical copy as
  ``check_submission.py``.
- :mod:`aspire_sysid.model.workspace` is the harness side: check configuration from the task,
  writing the checking files, in-process checks of a working directory, loading checked
  candidates and pools, the example model files and the rule table.
"""

from .checks import (
    DEFAULT_FUNCTIONS,
    DISCUSSION_SECTIONS,
    ESTIMATION_FIELDS,
    FORMAT_VERSION,
    RULES,
    TIE_RELATIVE_TOLERANCE,
    Candidate,
    CandidateResult,
    CheckConfig,
    CheckReport,
    ExpressionError,
    Issue,
    Parameter,
    ParsedExpression,
    Pool,
    evaluate_expression,
    format_report,
    is_finite_value,
    numeric_function,
    parse_expression,
)
from .workspace import (
    CHECK_SCRIPT,
    CandidateCheckError,
    check_config_from_task,
    check_workspace,
    example_model_data,
    example_model_files,
    load_candidate,
    load_pool,
    rule_table,
    write_check_files,
)

__all__ = [
    "CHECK_SCRIPT",
    "DEFAULT_FUNCTIONS",
    "DISCUSSION_SECTIONS",
    "ESTIMATION_FIELDS",
    "FORMAT_VERSION",
    "RULES",
    "TIE_RELATIVE_TOLERANCE",
    "Candidate",
    "CandidateCheckError",
    "CandidateResult",
    "CheckConfig",
    "CheckReport",
    "ExpressionError",
    "Issue",
    "Parameter",
    "ParsedExpression",
    "Pool",
    "check_config_from_task",
    "check_workspace",
    "example_model_data",
    "example_model_files",
    "evaluate_expression",
    "format_report",
    "is_finite_value",
    "numeric_function",
    "load_candidate",
    "load_pool",
    "parse_expression",
    "rule_table",
    "write_check_files",
]
