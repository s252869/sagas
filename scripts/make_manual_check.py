"""Manual-check sheets: each group member checks a different random sample of final killings
against the saga text, by hand. Samples do not overlap. Seed 2805.
  Ylfa:   20 random non-kin + 10 random kin   (data/review/manual_check_ylfa.xlsx, made first)
  Tanja:  24 non-kin + 6 kin from the rest    (manual_check_tanja.xlsx)
  Andrea: 24 non-kin + 6 kin from the rest    (manual_check_andrea.xlsx)
Existing files are never overwritten."""
import csv, random, re
from pathlib import Path
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
rows = list(csv.DictReader(open(ROOT / "data/final/killings_final.csv", encoding="utf-8")))
rng = random.Random(2805)
kin = [r for r in rows if r["relation"] != "none"]
non = [r for r in rows if r["relation"] == "none"]
# Ylfa's sample: identical draw order to the original sheet
ylfa = rng.sample(non, 20) + rng.sample(kin, 10); rng.shuffle(ylfa)
used = {r["kid"] for r in ylfa}
non_left = [r for r in non if r["kid"] not in used]; kin_left = [r for r in kin if r["kid"] not in used]
tanja_non, tanja_kin = rng.sample(non_left, 24), rng.sample(kin_left, 6)
non_left = [r for r in non_left if r not in tanja_non]; kin_left = [r for r in kin_left if r not in tanja_kin]
andrea_non, andrea_kin = rng.sample(non_left, 24), rng.sample(kin_left, 6)
SAMPLES = {"manual_check_ylfa.xlsx": ylfa,
           "manual_check_tanja.xlsx": tanja_non + tanja_kin,
           "manual_check_andrea.xlsx": andrea_non + andrea_kin}

_ch = {}
def chapters(saga):
    if saga not in _ch:
        t = (ROOT / f"data/raw/is/{saga}.is.txt").read_text(encoding="utf-8")
        parts = re.split(r"\n\s*(\d+)\. kafli\s*\n", t)
        _ch[saga] = {parts[i]: " ".join(parts[i + 1].split()) for i in range(1, len(parts) - 1, 2)}
    return _ch[saga]

def passage(r):
    c = re.findall(r"\d+", r["chapter"] or "")
    txt = chapters(r["saga"]).get(c[0], "") if c else ""
    key = (r["evidence"] or "").strip('"„“ ')[:30]
    i = txt.find(key) if key else -1
    if i < 0:
        i = txt.find(r["victim"].split()[0][:4])
    if i < 0:
        return txt[:900]
    return ("…" if i > 450 else "") + txt[max(0, i - 450):i + 500] + "…"

H = ["#", "kid", "saga", "chapter", "killer", "victim", "AI: relation", "AI: relation detail", "AI: same family group",
     "saga passage (around the killing)", "killing correct? (yes/no/partly)", "relation correct? (yes/no)", "your correction / note"]
HOWTO = [
    ["What", "Check 30 killings from the final dataset against the saga text, by yourself, without AI."],
    ["killing correct?", "yes = the passage shows this killer killing this victim. partly = killer was in the attacking group but someone else struck the blow, or it is only reported. no = wrong killer/victim, or no killing."],
    ["relation correct?", "Is the AI's family relation right? Rules: blood = kin up to second cousins; affinity = one marriage link (spouse, in-laws); foster = foster-father/son/brothers; sworn = sworn brotherhood; none = no such tie. If the passage doesn't show the family, look up the character's introduction in the saga (search the name) or write 'can't tell'."],
    ["Sample", "Random killings + some killings between relatives (oversampled because they matter most for the result). Each group member has a different sample (seed 2805)."],
    ["Time", "About 30-40 minutes. If the passage doesn't contain the killing, search the chapter in the saga text (sagadb.org)."],
]
Y = PatternFill("solid", fgColor="FFF2CC")
for fname, sample in SAMPLES.items():
    out = ROOT / "data/review" / fname
    if out.exists():
        print("kept existing", fname); continue
    sample = list(sample); rng.shuffle(sample)
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "check"; ws.append(H)
    for i, r in enumerate(sample, 1):
        ws.append([i, r["kid"], r["saga"], r["chapter"], r["killer"], r["victim"], r["relation"],
                   r["relation_detail"], r["same_group"], passage(r), "", "", ""])
    for i, w in enumerate([4, 8, 20, 8, 20, 20, 11, 40, 10, 90, 14, 12, 40], 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    for c in ws[1]:
        c.font = Font(bold=True); c.alignment = Alignment(wrap_text=True)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
        for c in row[10:]:
            c.fill = Y
    ws.freeze_panes = "E2"
    n = ws.max_row
    dv = DataValidation(type="list", formula1='"yes,no,partly"'); ws.add_data_validation(dv); dv.add(f"K2:K{n}")
    dv2 = DataValidation(type="list", formula1='"yes,no"'); ws.add_data_validation(dv2); dv2.add(f"L2:L{n}")
    g = wb.create_sheet("how to")
    for l in HOWTO:
        g.append(l)
    g.column_dimensions["A"].width = 18; g.column_dimensions["B"].width = 110
    for row in g.iter_rows():
        row[1].alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(out)
    print("made", fname, len(sample), "killings")
