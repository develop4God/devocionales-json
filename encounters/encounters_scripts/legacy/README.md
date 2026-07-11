# legacy/

Archived encounters validator, kept for reference only. **Nothing in this folder is executed by
any pipeline or master validator.**

- `validate_encounters_legacy.py` — the encounters validator as it existed before the
  `shared_validation/` migration (archived 2026-07-11). Fully standalone and runnable on its own
  (`python3 validate_encounters_legacy.py`), but not wired into `encounters_master_validator.py`.
- `verify_image_urls.py` — a frozen, standalone copy of the live
  `../verify_image_urls.py`, so this archive never depends on (or is affected by) future changes
  to the live copy. The two are expected to drift apart over time — that's intentional, not a bug.

The live validator is `../validate_encounters.py`, invoked by `../encounters_master_validator.py`.
If you're trying to fix or change encounters validation behavior, edit that file, not this folder.
