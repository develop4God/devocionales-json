class TrackedDict(dict):
    """A dict that remembers which keys were ever looked up (via `[]`,
    `.get()`, `in`, or iteration), recursively wrapping any nested dict/list
    it returns so access anywhere in the structure is tracked too.

    This replaces hand-maintained "which fields does this script render"
    allowlists: instead of a list a human has to update every time the
    renderer changes, the real render code IS the source of truth --
    whatever key it actually reads is "rendered", automatically, forever in
    sync. See find_unrendered_keys() below for the other half.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._accessed_keys = set()

    def _wrap(self, value):
        if isinstance(value, dict) and not isinstance(value, TrackedDict):
            return TrackedDict(value)
        if isinstance(value, list):
            return [self._wrap(v) for v in value]
        return value

    def __getitem__(self, key):
        self._accessed_keys.add(key)
        return self._wrap(super().__getitem__(key))

    def get(self, key, default=None):
        self._accessed_keys.add(key)
        if key in self:
            return self._wrap(super().get(key))
        return default

    def __contains__(self, key):
        self._accessed_keys.add(key)
        return super().__contains__(key)

    @property
    def accessed_keys(self):
        return set(self._accessed_keys)


def find_unrendered_keys(tracked, ignored_keys=()):
    """Compare every populated key on a TrackedDict against the keys that
    were actually accessed while rendering it. Anything populated but never
    read is a real silent drop -- automatic, no allowlist to maintain.

    `ignored_keys` is only for keys that are deliberately non-visual
    (internal bookkeeping like `order`/`type`, or authoring-only metadata)
    -- not a substitute list of "things that render".
    """
    if not isinstance(tracked, TrackedDict):
        raise TypeError(
            "find_unrendered_keys requires a TrackedDict -- wrap the JSON "
            "dict in TrackedDict(...) before rendering so key access can be "
            "recorded."
        )
    return sorted(
        k
        for k, v in tracked.items()
        if v not in (None, "", [], {})
        and k not in tracked.accessed_keys
        and k not in ignored_keys
    )
