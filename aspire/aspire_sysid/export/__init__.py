"""Exports of evaluated pools as Python and Matlab files.

The exports contain the equations, parameter values, origin and estimation history, variable
definitions, known shift and measurement equations, exclusions, numerical failures, unresolved
requirements and the evaluation settings or a reference to the record; the Matlab files follow
the ``[y, info]`` form of the ``srProvenance`` convention of the Matlab framework. Both exports are
generated from a run record (:mod:`aspire_sysid.record`), because the evaluation is a pure
function of the record.

- :func:`export_python` (``python_export``): one standalone module per evaluated pool (NumPy only),
  numerically re-verified;
- :func:`export_matlab` (``matlab_export``): working folders for the Matlab framework (data sets,
  ``splitData.m``, ``evaluationSets.m``, ``startup.m``, ``README.md``, ``HP/<setting>/<train
  name>/modelNN.m``), every M-file re-verified by the restricted translator of ``printing`` and,
  when GNU Octave is installed, in Octave (``octave``);
- ``printing``: the Matlab and NumPy printers and the restricted Matlab translator.
"""

from .common import ExportLocationError, ExportSource, candidate_status, check_export_location, load_export_source, sample_arguments
from .matlab_export import MatlabExportReport, MatlabModel, chain_ok, dataset_names, export_matlab, framework_layout
from .octave import octave_available
from .python_export import PythonExportResult, export_python, verify_python_module

__all__ = [
    "ExportLocationError",
    "ExportSource",
    "MatlabExportReport",
    "MatlabModel",
    "PythonExportResult",
    "candidate_status",
    "chain_ok",
    "check_export_location",
    "dataset_names",
    "export_matlab",
    "export_python",
    "framework_layout",
    "load_export_source",
    "octave_available",
    "sample_arguments",
    "verify_python_module",
]
