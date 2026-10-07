# bible_database

The Bible SQLite databases are **not stored in this repo**. The single source of truth is
[`develop4God/bible_versions`](https://github.com/develop4God/bible_versions) (public); never copy them here.

Get a path to one from Python:

```python
from bible_resolver import database_path, VerseResolver

with VerseResolver(str(database_path("hi", "HERV"))) as r:   # language code, version code
    cita, texto, error = r.resolve("Titus 2:11")
```

| Where you run | What `database_path` does |
|---|---|
| A machine with a `bible_versions` checkout (set `BIBLE_VERSIONS_DIR=~/Projects/bible_versions`, or install the package editable) | Reads the file in place, no copy, and checks its hash against that checkout's `index.json`. |
| CI, cloud sessions, any machine without a checkout | Downloads the file listed in `index.json` from `main`, verifies the hash, caches it in `~/.cache/bible_resolver/dbs/`, and reuses the cache offline. |

Errors are explicit: `DatabaseNotFoundError` (version not in the index) and `DatabaseIntegrityError`
(no network and no cache, or a corrupt/half-updated download).

Without Python: `https://raw.githubusercontent.com/develop4God/bible_versions/main/index.json` lists every
version's `url` and `hash` (first 16 hex chars of sha256).
