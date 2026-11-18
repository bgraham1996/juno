# neo-juno

organising tools for me

```bash
uv sync
uv run main.py doctor
```

## Dev projects → vault notes

Links the dev projects in `~/dev` (as indexed by
[`project-registry`](../project-registry)) to project notes in the Immrama vault, and pushes a few
fields from each project's `metadata.json` into the matching note's frontmatter.

```bash
uv run main.py projects        # report: linked / conflicts / no note / no project code
uv run main.py sync            # dry run: show the frontmatter changes, write nothing
uv run main.py sync --apply    # write the changes
```

To link a project, give its `metadata.json` the code its vault note carries:

```json
{
  "name": "neo-juno",
  "projectCode": "JUNO001",
  "obsidianNote": "Project Juno",
  "cycle": "active"
}
```

- `projectCode` is the join key (matches the note's `ProjectCode`).
- `obsidianNote` is optional: it names the note explicitly and takes precedence over the code.
- The sync only updates existing notes. It sets `ProjectType`, `Cycle` and `DevPath` (and fills a
  blank `ProjectCode`); every other property and the note body are left alone.
- Plain dev values are shown as emoji in the vault (`active` → `🟢 Active`); the vocabularies are
  in `app/sync/vocab.py`.

The registry is read as-is — run `project-registry scan` first if projects have been added.
The vault location defaults to `~/Vaults/Immrama/Immrama`; override with `--vault` or
`NEO_JUNO_VAULT`.
