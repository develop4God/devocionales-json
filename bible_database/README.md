# bible_database

The Bible SQLite databases are **not stored in this repo**. The source of truth is the
[`develop4God/bible_versions`](https://github.com/develop4God/bible_versions) repo and its `index.json`
(the index lists every available language/version, with each file's `url` and `hash`). Never copy databases here.

## Where to read from

1. **Local checkout first.** If a `bible_versions` checkout exists on this machine, it is the source of truth:
   use its `index.json` and files in place. Point to it with `BIBLE_VERSIONS_DIR=<path to checkout>`.
2. **Otherwise, remote.** Use the remote index:
   <https://raw.githubusercontent.com/develop4God/bible_versions/main/index.json>
   (files are downloaded, hash-verified and cached by `bible_resolver`).

Always read the index to find out what exists; do not assume a list of languages or versions.

## Usage

```python
from bible_resolver import database_path, VerseResolver

with VerseResolver(str(database_path("hi", "HERV"))) as r:   # language code, version code
    cita, texto, error = r.resolve("Titus 2:11")
```

`database_path` follows the order above. Note that merely having a checkout on disk is not enough: the
package must be told where it is (`BIBLE_VERSIONS_DIR`, or an editable install of the checkout), otherwise it
falls back to the remote.

Errors are explicit: `DatabaseNotFoundError` (not in the index) and `DatabaseIntegrityError`
(no network and no cache, or a corrupt download).
