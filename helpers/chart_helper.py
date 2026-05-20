import re
import pandas as pd
from helpers.dtype_helper import prepare_dataframe


# ---------------------------------------------------------------------------
# Column resolution
# ---------------------------------------------------------------------------

def _resolve_column(df, token: str) -> str | None:
    """Resolve a user-supplied token to an exact column name.

    Priority:
      1. Exact match
      2. Case-insensitive exact match
      3. Normalised (underscores ↔ spaces) exact match
      4. Best scored fuzzy match (token is a subsequence of column words)
    """
    if not token:
        return None

    token = token.strip()
    token_norm = token.lower().replace(" ", "_")

    # 1. Exact
    if token in df.columns:
        return token

    # 2. Case-insensitive exact
    for col in df.columns:
        if col.lower() == token.lower():
            return col

    # 3. Normalised exact  (handles "sales amount" ↔ "sales_amount")
    for col in df.columns:
        if col.lower().replace(" ", "_") == token_norm:
            return col

    # 4. Scored fuzzy: prefer columns whose normalised name *starts with* the
    #    token, then columns that *contain* it, then word-level overlap.
    token_words = set(token_norm.replace("_", " ").split())
    best_col, best_score = None, 0

    for col in df.columns:
        col_norm = col.lower().replace(" ", "_")
        col_words = set(col_norm.replace("_", " ").split())

        if col_norm.startswith(token_norm):
            score = 100
        elif token_norm in col_norm:
            score = 80
        else:
            overlap = len(token_words & col_words)
            if not overlap:
                continue
            # Jaccard-style: reward full coverage of token words
            score = int(60 * overlap / len(token_words))

        if score > best_score:
            best_score, best_col = score, col

    # Only return a fuzzy match if it's convincingly close
    return best_col if best_score >= 60 else None


def _is_numeric(df, col: str) -> bool:
    prepared = prepare_dataframe(df[[col]].copy())
    return pd.api.types.is_numeric_dtype(prepared[col])


# ---------------------------------------------------------------------------
# Axis keyword extraction  (NEW – highest priority)
# ---------------------------------------------------------------------------

# Maps synonyms → canonical axis
_X_ALIASES = r"(?:x[\s-]?axis|horizontal[\s-]?axis|x)"
_Y_ALIASES = r"(?:y[\s-]?axis|vertical[\s-]?axis|y)"

_AXIS_PATTERNS = [
    # "x axis: sales"  /  "x axis = sales"  /  "x axis is sales"
    (re.compile(rf"{_X_ALIASES}\s*(?:axis)?\s*(?:=|:|is|should be|→|->)\s*([a-zA-Z_][a-zA-Z0-9_ ]*)", re.I), "x"),
    (re.compile(rf"{_Y_ALIASES}\s*(?:axis)?\s*(?:=|:|is|should be|→|->)\s*([a-zA-Z_][a-zA-Z0-9_ ]*)", re.I), "y"),
    # "put sales on the x axis"  /  "show revenue on y axis"
    (re.compile(rf"(?:put|show|place|use|set)\s+([a-zA-Z_][a-zA-Z0-9_ ]*?)\s+on\s+(?:the\s+)?{_X_ALIASES}", re.I), "x"),
    (re.compile(rf"(?:put|show|place|use|set)\s+([a-zA-Z_][a-zA-Z0-9_ ]*?)\s+on\s+(?:the\s+)?{_Y_ALIASES}", re.I), "y"),
    # "with x as month"
    (re.compile(rf"with\s+{_X_ALIASES}\s+(?:as|=)\s+([a-zA-Z_][a-zA-Z0-9_ ]*)", re.I), "x"),
    (re.compile(rf"with\s+{_Y_ALIASES}\s+(?:as|=)\s+([a-zA-Z_][a-zA-Z0-9_ ]*)", re.I), "y"),
]


def _extract_explicit_axes(df, question: str) -> tuple[str | None, str | None]:
    """Return (x_col, y_col) from explicit axis instructions in the question."""
    x_col = y_col = None

    for pattern, axis in _AXIS_PATTERNS:
        m = pattern.search(question)
        if not m:
            continue
        col = _resolve_column(df, m.group(1).strip())
        if col:
            if axis == "x" and x_col is None:
                x_col = col
            elif axis == "y" and y_col is None:
                y_col = col

    return x_col, y_col


# ---------------------------------------------------------------------------
# Relational keyword extraction  ("A vs B", "A by B", "A against B")
# ---------------------------------------------------------------------------

_REL_PATTERNS = [
    # "revenue vs month"  /  "revenue versus month"
    re.compile(r"([a-zA-Z_][a-zA-Z0-9_ ]*?)\s+(?:vs\.?|versus)\s+([a-zA-Z_][a-zA-Z0-9_ ]*)", re.I),
    # "sales by region"  →  x=region, y=sales
    re.compile(r"([a-zA-Z_][a-zA-Z0-9_ ]*?)\s+by\s+([a-zA-Z_][a-zA-Z0-9_ ]*)", re.I),
    # "revenue against month"
    re.compile(r"([a-zA-Z_][a-zA-Z0-9_ ]*?)\s+against\s+([a-zA-Z_][a-zA-Z0-9_ ]*)", re.I),
    # "compare revenue and month"
    re.compile(r"compare\s+([a-zA-Z_][a-zA-Z0-9_ ]*?)\s+(?:and|with|to)\s+([a-zA-Z_][a-zA-Z0-9_ ]*)", re.I),
]


def _extract_relational(df, question: str, prepared_df) -> tuple[str | None, str | None]:
    """Return (x_col, y_col) from relational keywords."""
    for pattern in _REL_PATTERNS:
        m = pattern.search(question)
        if not m:
            continue

        left = _resolve_column(df, m.group(1).strip())
        right = _resolve_column(df, m.group(2).strip())

        if not (left and right):
            continue

        left_num = _is_numeric(prepared_df, left)
        right_num = _is_numeric(prepared_df, right)

        # For "by" patterns: left=value (y), right=grouping (x)
        if "by" in pattern.pattern:
            return right, left           # x=group, y=value

        # For "vs" / "against": numeric → y, categorical → x
        if left_num and not right_num:
            return right, left           # x=categorical, y=numeric
        elif right_num and not left_num:
            return left, right           # x=categorical, y=numeric
        else:
            return left, right           # both same type: preserve written order

    return None, None


# ---------------------------------------------------------------------------
# Mentioned-column heuristic  (fallback)
# ---------------------------------------------------------------------------

_EXPLICIT_COL_PATTERNS = [
    re.compile(r"(?:chart|graph|plot|visuali[sz]e)\s+(?:of\s+)?([a-zA-Z_][a-zA-Z0-9_ ]*?)(?:\s+by|\s+vs|\s*$|,)", re.I),
    re.compile(r"plot\s+([a-zA-Z_][a-zA-Z0-9_ ]*?)(?:\s+by|\s+vs|\s*$|,)", re.I),
    re.compile(r"make\s+(?:a\s+)?chart\s+of\s+([a-zA-Z_][a-zA-Z0-9_ ]*?)(?:\s+by|\s+vs|\s*$|,)", re.I),
]


def _columns_mentioned(df, question_lower: str) -> list[str]:
    """Return columns mentioned in the question, de-duplicated, high-confidence first."""
    seen: set[str] = set()
    ordered: list[str] = []

    def _add(col):
        if col and col not in seen:
            seen.add(col)
            ordered.append(col)

    # Explicit "chart of X" patterns first
    for pat in _EXPLICIT_COL_PATTERNS:
        m = pat.search(question_lower)
        if m:
            _add(_resolve_column(df, m.group(1).strip()))

    # Substring / word matching
    for col in df.columns:
        col_lower = col.lower()
        col_spaced = col_lower.replace("_", " ")

        if col_lower in question_lower or col_spaced in question_lower:
            _add(col)
            continue

        # At least one significant word must match
        for word in col_spaced.split():
            if len(word) >= 4 and re.search(rf"\b{re.escape(word)}\b", question_lower):
                _add(col)
                break

    return ordered


def _heuristic_axes(df, question_lower: str, prepared_df) -> tuple[str | None, str | None]:
    """Assign axes from mentioned columns when no relational keyword is found."""
    mentioned = _columns_mentioned(df, question_lower)
    if not mentioned:
        return None, None

    numeric = [c for c in mentioned if _is_numeric(prepared_df, c)]
    categorical = [c for c in mentioned if c not in numeric]

    if len(mentioned) == 1:
        col = mentioned[0]
        return (None, col) if _is_numeric(prepared_df, col) else (col, None)

    if numeric and categorical:
        return categorical[0], numeric[0]   # x=cat, y=num

    if len(numeric) >= 2:
        return numeric[0], numeric[1]

    if len(categorical) >= 2:
        return categorical[0], None         # can only sensibly use one

    if numeric:
        return None, numeric[0]

    return categorical[0], None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_chart_columns(
    df: pd.DataFrame,
    question: str,
) -> tuple[str | None, str | None]:
    """Parse a natural-language question and return (x_col, y_col).

    Resolution priority (highest → lowest):
      1. Explicit axis instructions  ("x axis = month", "put revenue on y axis")
      2. Relational keywords         ("revenue by month", "sales vs region")
      3. Mentioned-column heuristic  (numeric → y, categorical → x)
    """
    prepared_df = prepare_dataframe(df.copy())
    q = question.strip()

    # ── Priority 1: explicit axis mentions ──────────────────────────────────
    x_col, y_col = _extract_explicit_axes(df, q)
    if x_col and y_col:
        return x_col, y_col            # both axes fully specified → done

    # ── Priority 2: relational keywords ────────────────────────────────────
    rx, ry = _extract_relational(df, q, prepared_df)

    # Merge: explicit axes override relational ones
    x_col = x_col or rx
    y_col = y_col or ry

    if x_col and y_col:
        return x_col, y_col

    # ── Priority 3: heuristic from mentioned columns ────────────────────────
    hx, hy = _heuristic_axes(df, q.lower(), prepared_df)

    x_col = x_col or hx
    y_col = y_col or hy

    return x_col, y_col