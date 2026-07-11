"""shared_validation — internal library of genuinely-identical validation
helpers extracted from encounters/encounters_scripts/validate_encounters.py
and discovery/discovery_scripts/validate_discovery.py.

This is a spike: a pure library, not wired into either pipeline. Nothing in
this package performs network calls or filesystem I/O at import time.
"""
