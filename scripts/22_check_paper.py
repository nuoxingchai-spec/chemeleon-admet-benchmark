"""Static checks for the LNCS manuscript: refs, labels, citations, includes."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"


def read(p):
    return p.read_text(encoding="utf-8")


def main():
    main = read(PAPER / "main.tex")
    files = [PAPER / "main.tex"] + sorted((PAPER / "sections").glob("*.tex"))
    files += sorted((PAPER / "tables").glob("*.tex"))
    text = "\n".join(read(p) for p in files)

    labels = re.findall(r"\\label\{([^}]+)\}", text)
    refs = re.findall(r"\\ref\{([^}]+)\}", text)
    dup = sorted({x for x in labels if labels.count(x) > 1})
    missing = sorted(set(refs) - set(labels))
    unused = sorted(set(labels) - set(refs))

    cites = set()
    for m in re.findall(r"\\cite\{([^}]+)\}", text):
        cites.update(k.strip() for k in m.split(","))
    bib = read(PAPER / "refs.bib")
    bibkeys = set(re.findall(r"@\w+\{([^,]+),", bib))
    nocite = sorted(cites - bibkeys)
    uncited = sorted(bibkeys - cites)

    included = re.findall(r"\\input\{([^}]+)\}", text)
    missing_inputs = []
    for inc in included:
        p = PAPER / inc
        if not p.with_suffix(".tex").exists() and not p.exists():
            missing_inputs.append(inc)

    graphic = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text)
    missing_graphics = [g for g in graphic if not (PAPER / "figures" / (g + ".pdf")).exists()]

    envs = re.findall(r"\\begin\{(\w+)\}", text)
    ends = re.findall(r"\\end\{(\w+)\}", text)
    env_bad = []
    for e in set(envs):
        if envs.count(e) != ends.count(e):
            env_bad.append((e, envs.count(e), ends.count(e)))

    brace_bad = []
    for p in files:
        s = read(p)
        depth = 0
        for i, ch in enumerate(s):
            if ch == "\\":
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth < 0:
                    brace_bad.append((p.name, i))
                    break
        if depth != 0:
            brace_bad.append((p.name, depth))

    nonascii = []
    for p in files:
        s = read(p)
        bad = sorted({c for c in s if ord(c) > 127})
        if bad:
            nonascii.append((p.name, "".join(bad)))

    print("labels:", len(labels), "refs:", len(refs))
    print("duplicate labels:", dup)
    print("missing refs:", missing)
    print("unused labels:", unused)
    print("citations:", len(cites), "bib keys:", len(bibkeys))
    print("uncited bib:", uncited)
    print("missing bib keys:", nocite)
    print("missing inputs:", missing_inputs)
    print("missing graphics:", missing_graphics)
    print("env mismatch:", env_bad)
    print("brace issues:", brace_bad[:10])
    print("non-ascii:", nonascii)


if __name__ == "__main__":
    main()