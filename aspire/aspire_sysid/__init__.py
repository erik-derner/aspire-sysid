"""Harness of ASPIRE (Agentic System-identification Platform for Iterative Reasoning and Exploration).

ASPIRE consists of the harness and the agent(s). This package is the harness: the
software that builds the task brief, provisions the working directory, sends the requests to the
language model, executes the tool calls the agent requests, enforces the budget, checks the
candidate files, evaluates the candidates on sealed test data and records every event. The
method it implements is described in the paper.
"""

__version__ = "0.1.0.dev0"

__all__ = ["__version__"]
