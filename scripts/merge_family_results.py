"""Merge the filled-in JSON results (data/family/work/*_output.json) into data/family/personN_family.xlsx."""
import json
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
FAM = ROOT / "data" / "family"
PCOLS = {"parents": "parents (father; mother)", "siblings": "siblings", "spouses": "spouses",
         "children": "children", "in_laws": "in_laws", "foster_sworn": "foster_sworn",
         "other_kin": "other_kin", "family_group": "family_group (kin group / household)",
         "source": "source (saga ch / wikipedia)", "status": "status", "notes": "notes"}
KCOLS = {"relation_killer_to_victim": "relation_killer_to_victim", "same_family_group": "same_family_group?",
         "source": "source", "notes": "notes"}

for p, chunks in {"person1": ["person1a", "person1b"], "person2": ["person2"], "person3": ["person3"]}.items():
    res_p, res_k = {}, {}
    for c in chunks:
        f = FAM / "work" / f"{c}_output.json"
        if not f.exists():
            print(f"!! missing {f.name}"); continue
        d = json.loads(f.read_text(encoding="utf-8"))
        res_p.update({(x["saga"], x["person"]): x for x in d.get("people", [])})
        res_k.update({(x["saga"], x["killer"], x["victim"]): x for x in d.get("killings", [])})

    path = FAM / f"{p}_family.xlsx"
    wb = openpyxl.load_workbook(path)
    for sheet, res, keyf, cols in (
        ("people", res_p, lambda r, h: (r[h["saga"]].value, r[h["person"]].value), PCOLS),
        ("killings", res_k, lambda r, h: (r[h["saga"]].value, r[h["killer"]].value, r[h["victim"]].value), KCOLS),
    ):
        ws = wb[sheet]
        h = {c.value: i for i, c in enumerate(ws[1])}
        hit = miss = 0
        for row in ws.iter_rows(min_row=2):
            x = res.get(keyf(row, h))
            if not x:
                miss += 1; continue
            hit += 1
            for k, col in cols.items():
                v = x.get(k, "")
                if isinstance(v, list):
                    v = "; ".join(map(str, v))
                row[h[col]].value = v if v not in (None, "") else row[h[col]].value
        print(f"{p} {sheet}: {hit} filled, {miss} not in results")
    wb.save(path)
