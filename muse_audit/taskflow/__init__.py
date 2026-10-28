"""Taskflow layer for new normal-language tasks.

This layer sits around the existing audit kernel. It does not replace
the frozen budget, the old APIs, or the native XLSX and DOCX adapters.
It only adds a prepare, review, recheck, and repair flow for fresh tasks
whose requirements are frozen before a deliverable is generated.
"""

__version__ = "taskflow-0.1"
