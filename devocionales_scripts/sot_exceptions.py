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
        "ja",
        "新改訳2003",
    ): "Confirmed not a user-facing risk — pending formal SOT update",
    (
        "ja",
        "リビングバイブル",
    ): "Confirmed not a user-facing risk — pending formal SOT update",
    (
        "zh",
        "和合本1919",
    ): "Confirmed not a user-facing risk — pending formal SOT update",
    ("zh", "新译本"): "Confirmed not a user-facing risk — pending formal SOT update",
    # ("fr", "TOB"): still open — usage/risk not yet confirmed, stays an error.
}
