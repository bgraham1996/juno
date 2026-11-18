"""Tests for the dev -> vault project sync.

Everything runs against `tmp_path` vaults and a fake registry runner; the real
vault and the real `project-registry` are never touched.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import cli
from app.sync import dev, frontmatter, vault
from app.sync.plan import CONFLICT, NO_CODE, NO_NOTE, UNCHANGED, UPDATE, build_plan
from app.sync.vocab import CYCLE, PLAIN, PROJECT_TYPE
from tools import registry

NOTE = """---
Status: 🌱
ReviewDate: 2026-07-25T10:37:00
Priority: 🔴
FileType: 💼 project
ProjectCode: JUNO001
ReviewCount: 1
---

#### Project Summary
- body: with a colon
"""


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def make_vault(tmp_path: Path, notes: dict[str, str]) -> Path:
    root = tmp_path / "vault"
    (root / "Projects").mkdir(parents=True)
    for name, text in notes.items():
        (root / "Projects" / f"{name}.md").write_text(text, encoding="utf-8")
    return root


def make_project(tmp_path: Path, name: str, metadata: dict | str | None) -> dict:
    """Create a dev project dir and return its registry row."""
    project = tmp_path / "dev" / name
    project.mkdir(parents=True)
    meta_path = None
    if metadata is not None:
        meta_path = project / "metadata.json"
        meta_path.write_text(metadata if isinstance(metadata, str) else json.dumps(metadata))
    return {"path": str(project), "projectName": name, "cycle": None, "tags": None,
            "metadataPath": str(meta_path) if meta_path else None}


def plan_for(tmp_path: Path, notes: dict[str, str], projects: list[tuple[str, dict | str | None]]):
    root = make_vault(tmp_path, notes)
    rows = [make_project(tmp_path, name, meta) for name, meta in projects]
    return root, build_plan(dev.load_records(rows), vault.load_notes(root, ("Projects",)))


# --------------------------------------------------------------------------- #
# tools/registry.py
# --------------------------------------------------------------------------- #

def test_registry_parses_rows_and_calls_the_cli():
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout='[{"path": "/x", "projectName": "x"}]', stderr="")

    assert registry.list_projects(runner) == [{"path": "/x", "projectName": "x"}]
    assert calls == [["project-registry", "list", "--json"]]


def test_registry_errors_are_clear():
    def missing(cmd, **kwargs):
        raise FileNotFoundError

    with pytest.raises(registry.RegistryError, match="not on PATH"):
        registry.list_projects(missing)
    with pytest.raises(registry.RegistryError, match="scan"):
        registry.list_projects(lambda c, **k: SimpleNamespace(returncode=1, stdout="", stderr="no db"))
    with pytest.raises(registry.RegistryError, match="JSON"):
        registry.list_projects(lambda c, **k: SimpleNamespace(returncode=0, stdout="nope", stderr=""))


# --------------------------------------------------------------------------- #
# vocab
# --------------------------------------------------------------------------- #

def test_codecs_round_trip():
    for codec, plain in ((CYCLE, "active"), (CYCLE, "template"), (PROJECT_TYPE, "dev"), (PROJECT_TYPE, "log")):
        shown = codec.to_vault(plain)
        assert shown != plain
        assert codec.to_dev(shown) == plain


def test_codec_tolerates_case_and_variation_selector():
    assert CYCLE.to_vault("Active") == "🟢 Active"
    assert PROJECT_TYPE.to_dev("🗃 Log") == "log"  # stored without U+FE0F


def test_codec_passes_unknown_values_through():
    assert CYCLE.to_vault("experimental") == "experimental"
    assert CYCLE.to_dev("🛸 Odd") == "🛸 Odd"
    assert not CYCLE.knows("experimental")
    assert PLAIN.knows("anything")
    assert CYCLE.to_vault(None) is None


# --------------------------------------------------------------------------- #
# frontmatter
# --------------------------------------------------------------------------- #

def test_read_top_level_scalars_only():
    props = frontmatter.read(NOTE)
    assert props["ProjectCode"] == "JUNO001"
    assert props["ReviewDate"] == "2026-07-25T10:37:00"
    assert "body" not in props
    assert frontmatter.read("no frontmatter here") == {}


def test_update_touches_only_the_given_lines():
    updated = frontmatter.update(NOTE, {"Priority": "🟡", "Cycle": "🟢 Active"})
    before, after = NOTE.splitlines(), updated.splitlines()
    assert len(after) == len(before) + 1
    assert after[3] == "Priority: 🟡"
    assert after[7] == "Cycle: 🟢 Active" and after[8] == "---"
    assert [l for l in after if l not in ("Priority: 🟡", "Cycle: 🟢 Active")] == \
           [l for l in before if l != "Priority: 🔴"]


def test_update_quotes_risky_values_and_reads_them_back():
    updated = frontmatter.update(NOTE, {"DevPath": "~/dev/neo-juno"})
    assert 'DevPath: "~/dev/neo-juno"' in updated
    assert frontmatter.read(updated)["DevPath"] == "~/dev/neo-juno"


def test_update_preserves_crlf():
    crlf = NOTE.replace("\n", "\r\n")
    updated = frontmatter.update(crlf, {"Cycle": "x"})
    assert "Cycle: x\r\n---\r\n" in updated
    assert "\n" not in updated.replace("\r\n", "")


def test_block_values_are_detected_and_refused():
    text = "---\nFileType: 💼 project\nProjectCodes:\n  - A001\n  - B001\ntags:\n- x\nStatus: 🌱\n---\nbody\n"
    assert frontmatter.block_keys(text) == {"ProjectCodes", "tags"}
    assert frontmatter.read(text) == {"FileType": "💼 project", "ProjectCodes": "", "tags": "", "Status": "🌱"}
    with pytest.raises(frontmatter.FrontmatterError):
        frontmatter.update(text, {"tags": "y"})
    with pytest.raises(frontmatter.FrontmatterError):
        frontmatter.update("plain note", {"a": "b"})


# --------------------------------------------------------------------------- #
# dev records
# --------------------------------------------------------------------------- #

def test_record_reads_code_and_note_from_metadata(tmp_path):
    row = make_project(tmp_path, "neo-juno", {"projectCode": "juno001", "obsidianNote": "[[Project Juno]]",
                                               "cycle": "active"})
    record = dev.record_from_row(row)
    assert (record.code, record.obsidian_note, record.cycle) == ("JUNO001", "[[Project Juno]]", "active")
    assert record.project_type == "dev"
    assert record.dev_path.endswith("/dev/neo-juno")


def test_bad_metadata_never_raises(tmp_path):
    for metadata in (None, "", "{not json", "[1, 2]"):
        record = dev.record_from_row(make_project(tmp_path, f"p{hash(metadata) % 9999}", metadata))
        assert record.code is None


def test_invalid_code_is_ignored_with_an_issue(tmp_path):
    record = dev.record_from_row(make_project(tmp_path, "p", {"projectCode": "has spaces!"}))
    assert record.code is None and record.issues


@pytest.mark.parametrize(
    "code, valid",
    [("AB", False), ("ABC", True), ("JUNO001", True), ("ABCDEFGHIJ", True), ("ABCDEFGHIJK", False)],
)
def test_code_length_is_3_to_10(tmp_path, code, valid):
    record = dev.record_from_row(make_project(tmp_path, code, {"projectCode": code}))
    assert (record.code == code) is valid


def test_home_is_shortened(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    record = dev.record_from_row(make_project(tmp_path, "p", None))
    assert record.dev_path == "~/dev/p"


# --------------------------------------------------------------------------- #
# vault notes
# --------------------------------------------------------------------------- #

def test_only_project_notes_are_loaded(tmp_path):
    root = make_vault(tmp_path, {
        "Project Juno": NOTE,
        "Juno Logs": "---\nFileType: 💼 project\nProjectType: 🗃️ Log\n---\n",
        "Juno Tasks": "---\nFileType: 📬 Capture\n---\n",
        "Unassigned": "---\nFileType: 💼 project\nProjectCode: UNASSIGNED\nProjectType: 🌐 Organiser\n---\n",
    })
    notes = {n.name: n for n in vault.load_notes(root, ("Projects", "Missing Folder"))}
    assert set(notes) == {"Project Juno", "Unassigned"}
    assert notes["Project Juno"].record.code == "JUNO001"
    assert notes["Unassigned"].record.code is None
    assert notes["Unassigned"].record.project_type == "organiser"


# --------------------------------------------------------------------------- #
# planner
# --------------------------------------------------------------------------- #

def test_match_by_code_plans_managed_keys_only(tmp_path):
    _, plan = plan_for(tmp_path, {"Project Juno": NOTE},
                       [("neo-juno", {"projectCode": "JUNO001", "cycle": "active"})])
    (outcome,) = plan
    assert outcome.kind == UPDATE and outcome.note.name == "Project Juno"
    changes = {c.key: c.after for c in outcome.changes}
    assert set(changes) == {"ProjectType", "Cycle", "DevPath"}
    assert changes["ProjectType"] == "🔹 Dev" and changes["Cycle"] == "🟢 Active"


def test_missing_dev_value_never_clears_the_note(tmp_path):
    note = NOTE.replace("ReviewCount: 1", "ReviewCount: 1\nCycle: 🟢 Active")
    _, plan = plan_for(tmp_path, {"Project Juno": note}, [("neo-juno", {"projectCode": "JUNO001"})])
    assert "Cycle" not in {c.key for c in plan[0].changes}


def test_unknown_cycle_is_written_plain_with_a_warning(tmp_path):
    _, plan = plan_for(tmp_path, {"Project Juno": NOTE},
                       [("neo-juno", {"projectCode": "JUNO001", "cycle": "experimental"})])
    assert {c.key: c.after for c in plan[0].changes}["Cycle"] == "experimental"
    assert any("experimental" in w for w in plan[0].warnings)


def test_no_code_and_no_note(tmp_path):
    _, plan = plan_for(tmp_path, {"Project Juno": NOTE},
                       [("bare", None), ("orphan", {"projectCode": "ORPH001"})])
    assert [o.kind for o in plan] == [NO_CODE, NO_NOTE]


def test_obsidian_note_links_a_note_without_a_code_and_fills_it(tmp_path):
    note = NOTE.replace("ProjectCode: JUNO001", "ProjectCode: UNASSIGNED")
    _, plan = plan_for(tmp_path, {"Project Juno": note},
                       [("neo-juno", {"projectCode": "JUNO001", "obsidianNote": "[[Project Juno|Juno]]"})])
    assert plan[0].kind == UPDATE
    assert {c.key: c.after for c in plan[0].changes}["ProjectCode"] == "JUNO001"


def test_conflicts(tmp_path):
    notes = {"Project Juno": NOTE, "Juno Copy": NOTE, "Other": NOTE.replace("JUNO001", "OTHR001")}
    _, plan = plan_for(tmp_path, notes, [
        ("dup-code", {"projectCode": "JUNO001"}),                                # two notes share the code
        ("missing", {"projectCode": "MISS001", "obsidianNote": "Nope"}),         # note doesn't exist
        ("mismatch", {"projectCode": "ABCD001", "obsidianNote": "Other"}),       # note has another code
    ])
    assert [o.kind for o in plan] == [CONFLICT] * 3
    assert all(o.reason and not o.changes for o in plan)


def test_two_dev_projects_claiming_one_note_conflict(tmp_path):
    _, plan = plan_for(tmp_path, {"Project Juno": NOTE},
                       [("juno", {"projectCode": "JUNO001"}), ("neo-juno", {"projectCode": "JUNO001"})])
    assert [o.kind for o in plan] == [CONFLICT, CONFLICT]
    assert "neo-juno" in plan[0].reason and "juno" in plan[1].reason


def test_block_valued_managed_key_is_a_conflict(tmp_path):
    note = NOTE.replace("ReviewCount: 1", "ProjectType:\n  - 🔹 Dev")
    _, plan = plan_for(tmp_path, {"Project Juno": note}, [("neo-juno", {"projectCode": "JUNO001"})])
    assert plan[0].kind == CONFLICT


# --------------------------------------------------------------------------- #
# end to end through the CLI bodies
# --------------------------------------------------------------------------- #

@pytest.fixture
def wired(tmp_path, monkeypatch):
    root = make_vault(tmp_path, {"Project Juno": NOTE, "Trip": NOTE.replace("JUNO001", "TRIP001")})
    rows = [make_project(tmp_path, "neo-juno", {"projectCode": "JUNO001", "cycle": "active"}),
            make_project(tmp_path, "bare", None)]
    monkeypatch.setattr(registry, "list_projects", lambda: rows)
    return root


def test_dry_run_writes_nothing(wired, capsys):
    before = {p: p.read_bytes() for p in wired.rglob("*.md")}
    assert cli.sync(str(wired)) == 0
    assert cli.projects(str(wired)) == 0
    assert {p: p.read_bytes() for p in wired.rglob("*")if p.is_file()} == before
    out = capsys.readouterr().out
    assert "dry run" in out and "Cycle: (unset)  ->  🟢 Active" in out and "bare" in out


def test_apply_writes_only_managed_keys_and_is_idempotent(wired, capsys):
    trip_before = (wired / "Projects" / "Trip.md").read_bytes()
    assert cli.sync(str(wired), apply=True) == 0
    text = (wired / "Projects" / "Project Juno.md").read_text(encoding="utf-8")
    props = frontmatter.read(text)
    assert props["ProjectType"] == "🔹 Dev" and props["Cycle"] == "🟢 Active"
    assert props["Status"] == "🌱" and props["Priority"] == "🔴"          # untouched
    assert text.split("---\n", 2)[2] == NOTE.split("---\n", 2)[2]          # body identical
    assert (wired / "Projects" / "Trip.md").read_bytes() == trip_before    # unrelated note untouched
    assert not list(wired.rglob("*.tmp"))

    (note,) = [n for n in vault.load_notes(wired, ("Projects",)) if n.name == "Project Juno"]
    rows = registry.list_projects()
    (outcome, _) = build_plan(dev.load_records(rows), [note])
    assert outcome.kind == UNCHANGED


def test_missing_vault_and_registry_failure_exit_nonzero(tmp_path, monkeypatch, capsys):
    assert cli.sync(str(tmp_path / "nope")) == 1

    def boom():
        raise registry.RegistryError("registry down")

    monkeypatch.setattr(registry, "list_projects", boom)
    assert cli.projects(str(make_vault(tmp_path, {}))) == 1
    assert "registry down" in capsys.readouterr().err
