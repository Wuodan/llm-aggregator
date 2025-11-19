# Task 07: UI Serving Improvements

## Goal
Refine how the FastAPI app serves the built-in UI and allow operators to swap in their own static frontend (or disable UI entirely). Work is split into two subtasks:

1. **Subtask 07-01:** Remove brittle HTML string replacements in `api.py` and clarify the role of `api_base` (`doc/task/07/subtasks/01/SUBTASK.md`).
2. **Subtask 07-02:** Introduce config-driven UI settings (custom static paths, ability to disable serving any HTML/JS) (`doc/task/07/subtasks/02/SUBTASK.md`).

Complete both subtasks so the serving layer becomes predictable, configurable, and easy to document. During implementation, engineers/AI agents may ask clarifying questions if needed.
