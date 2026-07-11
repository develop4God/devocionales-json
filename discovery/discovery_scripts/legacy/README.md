# legacy/

Archived discovery validator, kept for reference only. **Nothing in this folder is executed by
any pipeline or master validator.**

- `validate_discovery_legacy.py` — the discovery validator as it existed before the
  `shared_validation/` migration (archived 2026-07-11). Fully standalone and runnable on its own
  (`python3 validate_discovery_legacy.py`), but not wired into `discovery_master_validator.py`.

The live validator is `../validate_discovery.py`, invoked by `../discovery_master_validator.py`.
`../validate_structure_bulk.py` (the master validator's second phase) is unrelated to this
migration and was never touched.

If you're trying to fix or change discovery validation behavior, edit `../validate_discovery.py`,
not this folder.
