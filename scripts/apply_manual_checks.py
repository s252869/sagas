"""Apply the manual checks (data/review/manual_check_*.xlsx) to the final killings.

in : data/final/killings_prereview.csv  (output of finalize_killings.py)
     data/final/manual_corrections.csv   (every change, with who found it and why)
     data/final/broad_kin.csv            (indirect ties for the wide-definition robustness check)
out: data/final/killings_final.csv       (+ columns relation_broad, kin_broad, manually_checked_by)
Prints the manual-check accuracy figures for the paper."""
import collections, csv, shutil
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
FIN, REV = ROOT / "data/final", ROOT / "data/review"
pre = FIN / "killings_prereview.csv"
if not pre.exists():
    shutil.copy(FIN / "killings_final.csv", pre)
rows = list(csv.DictReader(open(pre, encoding="utf-8")))
corr = list(csv.DictReader(open(FIN / "manual_corrections.csv", encoding="utf-8")))
broad = {r["kid"]: r["broad_tie"] for r in csv.DictReader(open(FIN / "broad_kin.csv", encoding="utf-8"))}

# ---- manual-check accuracy (raw verdicts, before adjudication) ----
checked, stats = {}, collections.Counter()
for who, f in [("Ylfa", "manual_check_ylfa.xlsx"), ("Tanja", "manual_check_tanja.xlsx"), ("Andrea", "manual_check_andrea.xlsx")]:
    ws = openpyxl.load_workbook(REV / f, read_only=True)["check"]
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r[1]:
            continue
        checked[r[1]] = who
        k = str(r[10] or "").strip().lower(); rel = str(r[11] or "").strip().lower()
        stats["k_" + k] += 1
        stats["rel_yes" if rel.startswith("yes") else "rel_no"] += 1
        stats[f"kin_{'kin' if r[6] != 'none' else 'non'}_{'ok' if rel.startswith('yes') else 'no'}"] += 1
n = len(checked)
print(f"manual check: {n} killings by 3 authors")
print(f"  attribution: {stats['k_yes']} correct, {stats['k_partly']} partly, {stats['k_no']} wrong")
print(f"  relation: {stats['rel_yes']}/{n} confirmed  (kin rows {stats['kin_kin_ok']}/{stats['kin_kin_ok']+stats['kin_kin_no']}, "
      f"non-kin rows {stats['kin_non_ok']}/{stats['kin_non_ok']+stats['kin_non_no']})")

# ---- apply corrections ----
by = {r["kid"]: r for r in rows}
for c in corr:
    if c["kid"] not in by:
        print("!! unknown kid", c["kid"]); continue
    if c["field"] == "drop":
        by[c["kid"]]["_drop"] = c["reason"]
    else:
        by[c["kid"]][c["field"]] = c["new_value"]
        by[c["kid"]]["correction"] = (by[c["kid"]]["correction"] + " | " if by[c["kid"]]["correction"] else "") + f"manual ({c['found_by']}): {c['reason']}"
out = []
for r in rows:
    if r.get("_drop"):
        continue
    r.pop("_drop", None)
    r["relation_broad"] = r["relation"] if r["relation"] != "none" else (broad.get(r["kid"], "none"))
    r["kin_broad"] = "yes" if r["relation_broad"] != "none" else "no"
    r["manually_checked_by"] = checked.get(r["kid"], "")
    out.append(r)
with open(FIN / "killings_final.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(out[0])); w.writeheader(); w.writerows(out)
print(f"final: {len(out)} killings, {len({(r['saga'], p) for r in out for p in (r['killer'], r['victim'])})} people")
print("  relation (strict):", dict(collections.Counter(r["relation"] for r in out)))
print("  kin (wide definition):", dict(collections.Counter(r["kin_broad"] for r in out)))
print("  same_group:", dict(collections.Counter(r["same_group"] for r in out)),
      "| support:", dict(collections.Counter(r["support"] for r in out)),
      "| manually checked:", sum(1 for r in out if r["manually_checked_by"]))
