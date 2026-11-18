"""Sync between dev projects (~/dev, via project-registry) and vault project notes.

Currently one-way, dev -> vault, update-only. Both sides are read into the same
`ProjectRecord` (plain-text vocabulary) and diffed by `plan.build_plan`, so adding
the reverse direction means adding a writer for the dev side, not restructuring.
Decisions are recorded in `project/vault/wiki/design.md`.
"""
