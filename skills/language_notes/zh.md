# Language Notes: Chinese (ZH)

## Simplified vs. Traditional
Output **Simplified Chinese** characters, never Traditional, unless the caller
explicitly asks for Traditional/zh-Hant. The SOT Bible version code (`CUV1919`) does not
itself disambiguate script — resolve verse text via VerseResolver as usual, but the
prose you write (title, narrative, content, etc.) must be simplified-character output.
A mechanical spot-check for this is in `zh.json`'s `forbidden_patterns` — run it, don't
just eyeball the output.

## 你/您 register
Never use 您 for God/Jesus — always 你. This is mechanically checkable — see
`zh.json`.
