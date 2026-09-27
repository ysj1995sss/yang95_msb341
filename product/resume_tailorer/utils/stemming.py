"""
Tiny inflectional-suffix stemmer shared across the codebase.

Extracted from DiffGenerator (which used it to compare word stems when
checking for dropped/added content) so competency_map.py can use the same
logic for concept normalization without a circular import (diff_generator
already imports FROM competency_map). ONE stemmer, not two.

Deliberately minimal: strips only inflectional suffixes (plurals, -ing,
-ed), not derivational ones. It will correctly normalize "executives" to
"executive", but will NOT bridge "communicate" and "communication" -- those
are different word forms entirely, not an inflection of the same root.
Closing that gap needs a real lemmatizer or a curated synonym table, not a
suffix stripper; not attempted here.
"""

_SUFFIXES = ("ing", "edly", "ed", "ies", "es", "s")


def stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            stripped = word[: -len(suffix)]
            return stripped + "y" if suffix == "ies" else stripped
    return word
