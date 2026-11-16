"""Column -> field map of the game's `powerTypes` table on patch 11.00, derived from the bytecode.

`PowerType.static._-A3R` #6483 reads one power row: for each column it compares the column name (local
32) with a string and, on a match, writes one or more PowerType fields. List columns are split by `,`
into a local array and turned into a vector later by `PowerType._-42F(power, array, …, field, …)`.
This module rebuilds the map from the listing of #6483; it never reads game data, only the ABC.
See docs/knockback-11.00.md §0.
"""
from .movement import listing

PARSER = 6483          # PowerType.static._-A3R
COLUMN_LOCAL = "32"    # the column name is compared from local 32
VECTOR_FILL = "_-42F, 6"


def columns_from_listing(lst):
    """{column: {"fields": [...], "locals": [...]}} from a listing dict {offset: (op, text)}.

    A column block starts with `getlocal 32; pushstring 'Name'; ifne +rel` and ends at the branch
    target (offset after the ifne + rel). Field names are the `_-` names written in the block.
    """
    ins = sorted(lst.items())
    out = {}
    for k in range(1, len(ins) - 1):
        off, (op, text) = ins[k]
        if op != "pushstring" or ins[k - 1][1] != ("getlocal", COLUMN_LOCAL) or ins[k + 1][1][0] != "ifne":
            continue
        col = text.strip("'")
        b_off = ins[k + 1][0]
        end = b_off + 4 + int(ins[k + 1][1][1])
        fields, locs = [], []
        for o2, (op2, t2) in ins[k + 2:]:
            if o2 >= end:
                break
            if op2 in ("initproperty", "setproperty") and t2.startswith("_-") and t2 not in fields:
                fields.append(t2)
            if op2 == "setlocal" and t2 not in locs:
                locs.append(t2)
        out[col] = {"fields": fields, "locals": locs}
    return out


def vector_fields(lst):
    """{local: field} for the `_-42F` calls that turn a split column (a local array) into a field."""
    ins = sorted(lst.items())
    out = {}
    for k, (off, (op, text)) in enumerate(ins):
        if text != VECTOR_FILL:
            continue
        window = [x[1] for x in ins[max(0, k - 8):k]]
        locs = [t for o, t in window if o == "getlocal" and t != "4"]
        props = [t for o, t in window if o == "getproperty" and t.startswith("_-")]
        if locs and props:
            out[locs[0]] = props[0]
    return out


def column_map(abc):
    """{column: [fields]} with list columns resolved through `_-42F` to their vector field."""
    lst = listing(abc, PARSER)
    cols = columns_from_listing(lst)
    vec = vector_fields(lst)
    out = {}
    for col, info in cols.items():
        fields = list(info["fields"])
        for loc in info["locals"]:
            f = vec.get(loc)
            if f and f not in fields:
                fields.append(f)
        out[col] = fields
    return out
