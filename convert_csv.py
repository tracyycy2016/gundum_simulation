#!/usr/bin/env python3
"""
Convert cards_details.csv (custom format) → gundam_cards.csv (simulator format)
Usage: python convert_csv.py cards_details.csv
"""

import csv, re, sys
from pathlib import Path

INPUT  = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("cards_details.csv")
OUTPUT = Path("gundam_cards.csv")

CSV_COLUMNS = [
    "card_number", "card_name", "card_type", "colors",
    "lv", "cost", "ap", "hp",
    "traits", "effects", "link_conditions",
    "pilot_name", "pilot_ap", "pilot_hp",
    "rarity", "set_id", "zone", "effect_raw",
]

def safe_int(v, d=0):
    try:
        return int(re.sub(r"[^0-9]", "", str(v)) or str(d))
    except:
        return d

def parse_traits(raw):
    """'(Earth Federation)(White Base Team)' → 'Earth Federation,White Base Team'"""
    found = re.findall(r"\(([^)]+)\)", raw or "")
    return ",".join(found)

def parse_link(raw):
    """'Amuro Ray' or 'None' → 'Amuro Ray' or ''"""
    raw = (raw or "").strip()
    return "" if raw.lower() in ("none", "no", "") else raw

def parse_color(raw):
    """'Blue' → 'blue', 'Blue/Red' → 'blue/red'"""
    return "/".join(c.strip().lower() for c in re.split(r"[/,]", raw or "") if c.strip()) or "blue"

def parse_effects(row):
    """
    Build effects dict from the structured boolean/numeric columns.
    Returns comma-separated string like 'repair:1,breach:2,blocker'
    """
    fx = {}

    # Repair: '1', '1^', '2', '3*' — strip non-digits, treat 0 as absent
    repair_val = safe_int(row.get("Repair", 0))
    if repair_val > 0:
        fx["repair"] = repair_val

    # Breach: same pattern
    breach_val = safe_int(row.get("Breach", 0))
    if breach_val > 0:
        fx["breach"] = breach_val

    # Support: numeric
    support_val = safe_int(row.get("Support", 0))
    if support_val > 0:
        fx["support"] = support_val

    # Boolean flags
    def is_yes(v):
        return str(v).strip().lower() not in ("no", "0", "", "none", "false")

    if is_yes(row.get("High Maneuver")):
        fx["high_maneuver"] = True
    if is_yes(row.get("Blocker")):
        fx["blocker"] = True
    if is_yes(row.get("First Strike Effect")):
        fx["first_strike"] = True

    # Deploy draw
    if is_yes(row.get("Deploy Effect")) and is_yes(row.get("Draw Card Effect")):
        fx["deploy_draw"] = 1
    elif is_yes(row.get("Deploy Effect")):
        fx["deploy"] = True

    # Draw card (non-deploy context)
    if is_yes(row.get("Draw Card Effect")) and not is_yes(row.get("Deploy Effect")):
        # Check pair description for when_paired_draw
        pair_desc = (row.get("Pair Description") or "").lower()
        if "draw" in pair_desc:
            m = re.search(r"draw\s*(\d+)", pair_desc)
            fx["when_paired_draw"] = int(m.group(1)) if m else 1
        else:
            fx["deploy_draw"] = 1

    # Recover (base HP heal)
    if is_yes(row.get("Recover Effect")):
        fx["recover"] = True

    # Ping (deal damage to a unit)
    if is_yes(row.get("Ping Effect")):
        fx["ping"] = True

    # Command timing — infer from Effect Description
    card_type = (row.get("Card Type") or "").strip()
    if "Command" in card_type:
        desc = (row.get("Effect Description") or "").lower()
        has_main   = "【main】" in desc or "[main]" in desc
        has_action = "【action】" in desc or "[action]" in desc
        fx["timing"] = "both" if (has_main and has_action) \
                       else "action" if has_action else "main"

    # Burst — look in Effect Description
    desc = row.get("Effect Description") or ""
    if re.search(r"【Burst】|\[Burst\]", desc, re.I):
        if re.search(r"draw\s*2", desc, re.I):      fx["burst"] = "draw2"
        elif re.search(r"draw\s*1", desc, re.I):    fx["burst"] = "draw1"
        elif re.search(r"deploy|place.*deck", desc, re.I): fx["burst"] = "deploy_top"
        elif re.search(r"recover|heal", desc, re.I): fx["burst"] = "heal_base"
        else:                                        fx["burst"] = "draw1"

    return ",".join(
        f"{k}:{v}" if v is not True else k
        for k, v in fx.items() if v is not False
    )

def parse_set_id(code):
    """'GD01-001' → 'GD01'"""
    m = re.match(r"([A-Z]{2,4}\d{2})", code or "")
    return m.group(1) if m else ""

def transform(row):
    name = (row.get("Name") or "").strip()
    code = (row.get("Code") or "").strip()

    # Skip blank/placeholder rows
    if not name or not code:
        return None

    raw_type = (row.get("Card Type") or "").strip()

    # Normalise card type
    if raw_type == "Command/Pilot":
        card_type = "Command"   # treat as Command, pilot stats stored separately
    elif raw_type in ("Unit","Pilot","Command","Base","Resource"):
        card_type = raw_type
    else:
        card_type = "Unit"      # fallback

    # Pilot stats
    pilot_name = ""
    pilot_ap   = 0
    pilot_hp   = 0
    if card_type in ("Pilot", "Command"):
        pilot_name = parse_link(row.get("Command Pilot/Pilot Name"))
        pilot_ap   = safe_int(row.get("AP", 0)) if card_type == "Pilot" else 0
        pilot_hp   = safe_int(row.get("HP", 0)) if card_type == "Pilot" else 0

    # For Pilot cards the AP/HP cols are the pilot bonuses
    # For Units/Bases/Commands they are the card's own stats
    if card_type == "Pilot":
        ap = 0
        hp = 0
    else:
        ap = safe_int(row.get("AP", 0))
        hp = safe_int(row.get("HP", 0))

    # Link condition: Units link to a Pilot name or Trait
    link_raw = row.get("Unit Link (Pilot/Trait)") or ""
    link_str = parse_link(link_raw)

    return {
        "card_number":     code,
        "card_name":       name,
        "card_type":       card_type,
        "colors":          parse_color(row.get("Color", "")),
        "lv":              safe_int(row.get("Level", 0)),
        "cost":            safe_int(row.get("Cost", 0)),
        "ap":              ap,
        "hp":              hp,
        "traits":          parse_traits(row.get("Trait", "")),
        "effects":         parse_effects(row),
        "link_conditions": link_str,
        "pilot_name":      pilot_name,
        "pilot_ap":        pilot_ap,
        "pilot_hp":        pilot_hp,
        "rarity":          "",
        "set_id":          parse_set_id(code),
        "zone":            "",
        "effect_raw":      (row.get("Effect Description") or "").strip(),
    }


def main():
    print(f"Reading {INPUT}…")
    with open(INPUT, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"  {len(rows)} rows found")

    converted = []
    skipped   = 0
    for row in rows:
        result = transform(row)
        if result:
            converted.append(result)
        else:
            skipped += 1

    converted.sort(key=lambda r: r["card_number"])

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(converted)

    print(f"\n✅ Converted {len(converted)} cards → {OUTPUT}  ({skipped} blank rows skipped)")

    from collections import Counter
    print("\n── Card types ──")
    for t, n in Counter(r["card_type"] for r in converted).most_common():
        print(f"  {t:12s} {n}")
    print("\n── Colors ──")
    for c, n in Counter(col for r in converted for col in r["colors"].split("/") if col).most_common():
        print(f"  {c:10s} {n}")
    print("\n── Sets ──")
    for s, n in sorted(Counter(r["set_id"] for r in converted).items()):
        print(f"  {s:8s} {n}")

if __name__ == "__main__":
    main()
