"""sot_exceptions.py — acknowledged (lang, version) SOT mismatches.

The remote Bible-versions SOT (shared_validation.bible_sot) does not
recognize every version code this corpus actually uses in production.
Some of these are known, accepted divergences (confirmed not a user-facing
risk); others are still open questions pending a decision.

This is DATA, not logic — CorpusFileValidator reads it, never branches on
language or version by name itself. To change a mismatch from warning to
error (e.g. once a decision is made), remove its entry here — nothing else
in the validator needs to change.

Each key is (lang, version); the value is a short note for why it's
acknowledged, shown in the warning message for traceability.
"""

ACKNOWLEDGED_SOT_MISMATCHES = {
    (
        "fr",
        "TOB",
    ): "TOB Bible text not obtainable for verification — pending SOT/Bible source",
}

# User-facing version names that differ from the bible_versions index code
# for the SAME Bible. Devotional files carry the native name shown to users
# (e.g. 新改訳2003); the SOT index and the databases use its own code (SK2003).
# Validators resolve the database and check allowed_versions through
# canonical_version(); the files themselves are never renamed.
BIBLE_VERSION_ALIASES = {
    ("ja", "新改訳2003"): "SK2003",
    ("ja", "リビングバイブル"): "JCB",
    ("zh", "和合本1919"): "CUV1919",
    ("zh", "新译本"): "CNVS",
}


def canonical_version(lang: str, version: str) -> str:
    """The bible_versions index code for a (lang, file-declared version)."""
    return BIBLE_VERSION_ALIASES.get((lang, version), version)
