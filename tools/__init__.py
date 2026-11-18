"""Plumbing for the external tools neo-juno drives (one module per tool).

Each module wraps one outside program behind a small Python function, so the rest
of the project never builds a command line or parses tool output itself.
"""
