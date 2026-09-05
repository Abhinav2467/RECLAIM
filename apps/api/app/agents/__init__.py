"""Agents package for RECLAIM — lightweight orchestration.

This module intentionally avoids pulling external LangGraph dependencies so tests
can run in this environment. The `decision_agent` implements a small
deterministic state graph API that mirrors LangGraph's StateGraph semantics at a
very small scale and remains easy to replace later.
"""

__all__ = ["decision_agent"]
