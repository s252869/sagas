"""Build one family-situation sheet per labeller from the named-killings files.

For every killer and victim it prefills kin from SagaDB_family_network.xlsx,
reads the father from a patronymic, and attaches saga sentences that mention
the person together with a kinship word, so the gaps can be filled by hand.

Usage: python make_family_sheets.py <downloads_dir> <out_dir>
"""
import collections, re, sys, urllib.parse
from pathlib import Path
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

DL, OUT = Path(sys.argv[1]), Path(sys.argv[2])
ROOT = Path(__file__).resolve().parents[1]
TEXTS = ROOT / "data" / "raw" / "is"
OUT.mkdir(parents=True, exist_ok=True)

KIN = re.compile(r"\b(sonur|son|sonar|syni|synir|sona|sonu|dóttir|dóttur|dætur|faðir|föður|feður|móðir|móður|"
                 r"bróðir|bróður|bræður|bræðra|systir|systur|kona|konu|átti|gekk að eiga|fékk|kvæntist|"
                 r"frændi|frænda|frændur|mágur|mág|mági|fóstri|fóstra|fóstbróðir|fóstbræður|stjúp\w*|tengda\w*)\b", re.I)

# ---------- family network ----------
fam = openpyxl.load_workbook(DL / "SagaDB_family_network.xlsx", read_only=True)
nodes = list(fam["nodes"].iter_rows(values_only=True))[1:]
edges = list(fam["network_edges"].iter_rows(values_only=True))[1:]
node_name = {n[0]: n[2] for n in nodes}
by_saga = collections.defaultdict(list)
for n in nodes:
    forms = {n[2]} | {f.strip() for f in str(n[4] or "").split("|") if f.strip()}
    by_saga[n[1]].append((n[0], forms))

kin = collections.defaultdict(lambda: collections.defaultdict(list))  # node -> slot -> names
for e in edges:
    _, saga, s, t, rel, directed, layer = e[:7]
    S, T = node_name.get(s, s), node_name.get(t, t)
    if rel == "parent_of":
        kin[t]["parents"].append(S); kin[s]["children"].append(T)
    elif rel == "sibling_of":
        kin[s]["siblings"].append(T); kin[t]["siblings"].append(S)
    elif rel == "spouse_of":
        kin[s]["spouses"].append(T); kin[t]["spouses"].append(S)
    else:
        slot = {"marriage_and_affinity": "in_laws", "foster_or_sworn": "foster_sworn"}.get(layer, "other_kin")
        kin[s][slot].append(f"{T} ({rel})"); kin[t][slot].append(f"{S} ({rel})")


def match_node(saga, name):
    exact = [nid for nid, forms in by_saga[saga] if name in forms]
    if exact:
        return exact[0], "exact"
    first = name.split()[0]
    cand = [nid for nid, forms in by_saga[saga] if any(f.split()[0] == first for f in forms)]
    return (cand[0], "first-name (check!)") if len(cand) == 1 else (None, "")


# ---------- saga sentences ----------
SPLIT = re.compile(r'(?<=[.!?])["“”]?\s+(?=["„“]?[A-ZÁÉÍÓÚÝÞÆÖÐ0-9])')
sentences = {}
for f in TEXTS.glob("*.is.txt"):
    saga, ch, out = f.name.split(".")[0], 0, []
    for para in re.split(r"\n\s*\n", f.read_text(encoding="utf-8")):
        para = " ".join(para.split())
        m = re.fullmatch(r"(\d+)\. kafli", para)
        if m:
            ch = int(m.group(1)); continue
        out += [(ch, s) for s in SPLIT.split(para) if s]
    sentences[saga] = out


def stem(tok):
    for suf in ("ur", "ir", "i", "a", "r"):
        if tok.endswith(suf) and len(tok) - len(suf) >= 3:
            return tok[: -len(suf)]
    return tok


def snippets(saga, name, k=4):
    toks = [t for t in re.split(r"[\s()]+", name) if t and t[0].isupper()]
    if not toks:
        return []
    pat = re.compile(r"\b" + re.escape(stem(toks[0])) + r"\w*")
    hits = [(c, s) for c, s in sentences.get(saga, []) if pat.search(s) and KIN.search(s)]
    if len(toks) > 1:  # prefer sentences that also contain the byname / patronymic
        p2 = re.compile(re.escape(stem(toks[1])))
        hits.sort(key=lambda x: (not p2.search(x[1]), x[0]))
    return [f"[ch {c}] {s[:350]}" for c, s in hits[:k]]


def patronymic(name):
    m = re.search(r"\b([A-ZÁÉÍÓÚÝÞÆÖÐ]\w+?)(son|dóttir)\b", name)
    return f"{m.group(1)}- (from patronymic {m.group(0)})" if m else ""


def split_people(cell):
    return [g.strip() for g in str(cell or "").split(";")]


# ---------- build ----------
HEAD = ["person", "saga", "role", "n_killings_as_killer", "n_as_victim", "killed", "killed_by",
        "family_net_node", "match", "parents (father; mother)", "siblings", "spouses", "children",
        "in_laws", "foster_sworn", "other_kin", "family_group (kin group / household)",
        "source (saga ch / wikipedia)", "status", "notes", "saga_kin_snippets", "wikipedia_search"]
KHEAD = ["saga", "killer", "victim", "n_sentences", "first_sentence_id", "relation_killer_to_victim",
         "same_family_group?", "source", "notes"]
FILL = PatternFill("solid", fgColor="FFF2CC")

for p in ["person1", "person2", "person3"]:
    ws = openpyxl.load_workbook(DL / f"{p}_named_killings.xlsx", read_only=True)["my_sentences"]
    rows = list(ws.iter_rows(values_only=True))
    h = rows[0]
    pairs = collections.OrderedDict()
    for r in rows[1:]:
        r = dict(zip(h, r))
        if str(r["killing"]).strip().lower() != "yes":
            continue
        ks, vs = split_people(r["killer"]), split_people(r["victim"])
        if len(ks) != len(vs):  # uneven: everyone on left killed everyone on right
            ks, vs = [", ".join(ks)], [", ".join(vs)]
        for k, v in zip(ks, vs):
            for kk in [x.strip() for x in k.split(",") if x.strip()]:
                for vv in [x.strip() for x in v.split(",") if x.strip()]:
                    key = (r["saga"], kk, vv)
                    pairs.setdefault(key, []).append(r["id"])

    people = collections.OrderedDict()
    for (saga, k, v), ids in pairs.items():
        for nm, role, other in ((k, "killer", v), (v, "victim", k)):
            d = people.setdefault((saga, nm), {"killed": [], "killed_by": []})
            d["killed" if role == "killer" else "killed_by"].append(other)

    wb = openpyxl.Workbook()
    sh = wb.active; sh.title = "people"
    sh.append(HEAD)
    for (saga, nm), d in sorted(people.items()):
        nid, how = match_node(saga, re.sub(r"\s*\(.*?\)", "", nm))
        kk = kin.get(nid, {}) if nid else {}
        parents = kk.get("parents", [])
        role = "both" if d["killed"] and d["killed_by"] else ("killer" if d["killed"] else "victim")
        prefilled = bool(nid)
        sh.append([nm, saga, role, len(set(d["killed"])), len(set(d["killed_by"])),
                   "; ".join(dict.fromkeys(d["killed"])), "; ".join(dict.fromkeys(d["killed_by"])),
                   nid or "", how,
                   "; ".join(dict.fromkeys(parents)) or patronymic(nm),
                   *("; ".join(dict.fromkeys(kk.get(s, []))) for s in
                     ("siblings", "spouses", "children", "in_laws", "foster_sworn", "other_kin")),
                   "", "family network (AI, unchecked)" if prefilled else "",
                   "to check" if prefilled else "todo", "",
                   "\n".join(snippets(saga, nm)),
                   "https://is.wikipedia.org/w/index.php?search=" + urllib.parse.quote(re.sub(r"\s*\(.*?\)", "", nm))])
    kh = wb.create_sheet("killings")
    kh.append(KHEAD)
    for (saga, k, v), ids in pairs.items():
        kh.append([saga, k, v, len(ids), ids[0], "", "", "", ""])

    g = wb.create_sheet("guide")
    for line in [
        ["Goal", "Fill in the family situation of every killer and victim, so killings can be compared with kinship (SQ1/SQ2)."],
        ["people tab", "One row per person per saga. Yellow columns are yours to fill or correct."],
        ["Prefilled", "parents/siblings/etc. come from SagaDB_family_network.xlsx (AI-extracted, not human-checked) or from the patronymic. Verify, don't trust: the prefill mixes fathers and mothers and has some wrong links. Write as 'father; mother'."],
        ["saga_kin_snippets", "Sentences in the saga that mention this name together with a kin word (sonur, dóttir, átti, bróðir...). Usually the character's introduction is among them."],
        ["Wikipedia", "Icelandic Wikipedia has pages for major characters; the link searches it. English Wikipedia/Íslendingabók-style genealogies also help. Note the source."],
        ["Names", "Nominative, with patronymic when known (Gunnar Hámundarson). Same spelling as in the named_killings file so they join."],
        ["family_group", "A short label for the kin group/household, e.g. 'Njálssynir', 'Hlíðarendi'. Use the same label for people in the same family so we can test cross-family killings."],
        ["status", "todo → done / to check / not found (minor character, saga gives no family)."],
        ["killings tab", "One row per unique killer→victim pair. relation_killer_to_victim: none / blood (e.g. brother, cousin) / affinity (in-law) / foster / sworn. same_family_group?: yes / no / unknown."],
    ]:
        g.append(line)

    for wsx, widths in ((sh, [24, 22, 8, 8, 8, 28, 28, 30, 14, 30, 30, 26, 30, 26, 22, 26, 22, 24, 10, 24, 90, 30]),
                        (kh, [22, 24, 24, 8, 26, 26, 14, 24, 30]), (g, [18, 120])):
        for i, w in enumerate(widths, 1):
            wsx.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
        for c in wsx[1]:
            c.font = Font(bold=True)
        wsx.freeze_panes = "B2"
    for row in sh.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
        for idx in range(9, 20):
            row[idx].fill = FILL
    for row in kh.iter_rows(min_row=2):
        for idx in range(5, 9):
            row[idx].fill = FILL
    dv = DataValidation(type="list", formula1='"todo,done,to check,not found"', allow_blank=True)
    sh.add_data_validation(dv); dv.add(f"S2:S{sh.max_row}")
    dv2 = DataValidation(type="list", formula1='"yes,no,unknown"', allow_blank=True)
    kh.add_data_validation(dv2); dv2.add(f"G2:G{kh.max_row}")
    sh.auto_filter.ref = sh.dimensions; kh.auto_filter.ref = kh.dimensions

    wb.save(OUT / f"{p}_family.xlsx")
    n_pref = sum(1 for (s, nm) in people if match_node(s, re.sub(r"\s*\(.*?\)", "", nm))[0])
    print(f"{p}: {len(people)} people ({n_pref} prefilled from family net), {len(pairs)} unique killings")
