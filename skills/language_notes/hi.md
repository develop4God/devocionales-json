# Language Notes: Hindi (HI)

## Respectful plural for Jesus
Jesus takes the respectful plural — verbs included, not just pronouns.
Example: ✗ "यीशु आया...उसने कहा" → ✓ "यीशु आए...उन्होंने कहा".
Does not apply to quoted verse fields — those follow the cited Bible version's own grammar.

## Ergative-verb exception (do not over-apply the rule above)
This rule governs subject agreement only. In ने-ergative compound-verb constructions
("X ने ... करने दिया/न दिया", "जिसे यीशु ने बदल दिया"), the verb agrees with the **direct
object**, not the subject — and when the object is postposition-marked (उसे, जिसे, etc.)
or absent, the verb defaults to masculine singular (दिया), never दिए. Applying the
respectful-plural rule here produces a real grammar error (यीशु ने ... दिए ✗), not a
register fix — this exact mistake shipped once and was only caught on a second review
pass. Always distinguish subject-agreement contexts from ने-ergative object-agreement
contexts before "fixing" a दिया/दिए-type verb near यीशु.

## HIOV database book-name patch
The HIOV database's `books.long_name` stores the Gospels in liturgical long form
(e.g. `लूका रचित सुसमाचार`, "the Gospel composed by Luke") instead of the short form real
Hindi Bibles cite (`लूका`). `VerseResolver` already rewrites this for HIOV specifically —
it is not a general behavior, don't assume any other language DB needs the same
shortening, and never hand-type the long form yourself.
