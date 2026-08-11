"""XPath string-literal quoting.

XPath 1.0 has no escape character, so a value containing both quote styles has to
be assembled with concat(). Used whenever test data is injected into a locator.
"""


def xpath_literal(value: str) -> str:
    """Return `value` as a safely quoted XPath string literal."""
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    # Both quote styles present: single-quote each fragment and splice in "'".
    fragments = [f"'{fragment}'" for fragment in value.split("'")]
    return "concat(" + ", \"'\", ".join(fragments) + ")"
