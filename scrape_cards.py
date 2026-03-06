#!/usr/bin/env python3
"""
Gundam Card Game — Card Data Scraper  (v3, Playwright)
=======================================================
Uses Playwright instead of Selenium — works out of the box in GitHub
Codespaces, Google Colab, and any Linux environment without needing
a system Chrome install.

HOW TO INSTALL & RUN
---------------------
    pip install playwright
    playwright install chromium
    playwright install-deps chromium

    python scrape_cards.py                     # all sets
    python scrape_cards.py --sets GD01 ST01    # specific sets only
    python scrape_cards.py --out my_cards.csv  # custom output path
    python scrape_cards.py --headed            # show browser window (local only)
    python scrape_cards.py --delay 1.2         # slower clicks (if getting blocked)

Output: gundam_cards.csv  — drop next to app.py, simulator auto-loads it.
"""

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

# ─────────────────────────────────────────────
#  DEPENDENCY CHECK
# ─────────────────────────────────────────────

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("Playwright not found. Run:")
    print("    pip install playwright")
    print("    playwright install chromium")
    print("    playwright install-deps chromium")
    sys.exit(1)

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

BASE_URL = "https://www.gundam-gcg.com/asia-en/cards/"

ALL_SET_CODES = [
    "GD01", "GD02", "GD03",
    "ST01", "ST02", "ST03", "ST04", "ST05", "ST06", "ST07", "ST08",
]

SET_PACKAGE_IDS = {
    "GD01": "619097",
    "GD02": "619098",
    "GD03": "619099",
    "ST01": "619100",
    "ST02": "619101",
    "ST03": "619102",
    "ST04": "619103",
    "ST05": "619104",
    "ST06": "619105",
    "ST07": "619106",
    "ST08": "619107",
}

CSV_COLUMNS = [
    "card_number", "card_name", "card_type", "colors",
    "lv", "cost", "ap", "hp",
    "traits", "effects", "link_conditions",
    "pilot_name", "pilot_ap", "pilot_hp",
    "rarity", "set_id", "zone", "effect_raw",
]

CLICK_DELAY = 0.9   # seconds between card clicks

# ─────────────────────────────────────────────
#  EFFECT PARSING
# ─────────────────────────────────────────────

KEYWORD_PATTERNS = [
    ("blocker",          r"<Blocker>"),
    ("first_strike",     r"<First Strike>"),
    ("high_maneuver",    r"<High-Maneuver>"),
    ("suppression",      r"<Suppression>"),
    ("support",          r"<Support\s*(\d+)>"),
    ("breach",           r"<Breach\s*(\d+)>"),
    ("repair",           r"<Repair\s*(\d+)>"),
    ("deploy_draw",      r"【Deploy】.*?[Dd]raw\s*(\d+)"),
    ("when_paired_draw", r"【When Paired[^】]*】.*?[Dd]raw\s*(\d+)"),
    ("destroyed_draw",   r"【Destroyed】.*?[Dd]raw\s*(\d+)"),
]

COMMAND_EFFECT_PATTERNS = [
    ("draw",         r"[Dd]raw\s+(\d+)\s+card"),
    ("deal_damage",  r"deal[s]?\s+(\d+)\s+damage"),
    ("destroy_unit", r"[Dd]estroy\s+(?:1\s+)?(?:enemy\s+)?Unit"),
    ("rest_enemy",   r"[Rr]est\s+(?:1\s+)?(?:enemy\s+)?Unit"),
]

PILOT_AP_RE = re.compile(r"AP\s*[+]\s*(\d+)", re.IGNORECASE)
PILOT_HP_RE = re.compile(r"HP\s*[+]\s*(\d+)", re.IGNORECASE)


def clean_html(text):
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    for esc, ch in [("&lt;","<"),("&gt;",">"),("&amp;","&"),("&nbsp;"," ")]:
        text = text.replace(esc, ch)
    return text.strip()


def parse_effects(raw, card_type):
    if not raw:
        return ""
    text = clean_html(raw)
    effects = {}

    for kw, pat in KEYWORD_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            effects[kw] = int(m.group(1)) if m.lastindex else True

    if card_type.upper() == "COMMAND":
        has_main   = bool(re.search(r"【Main】",   text))
        has_action = bool(re.search(r"【Action】", text))
        effects["timing"] = "both" if (has_main and has_action) \
                            else "action" if has_action else "main"
        for ek, ep in COMMAND_EFFECT_PATTERNS:
            m = re.search(ep, text, re.IGNORECASE | re.DOTALL)
            if m:
                effects[ek] = int(m.group(1)) if m.lastindex else True

    if re.search(r"【Burst】", text):
        if   re.search(r"[Dd]raw\s*2",         text): effects["burst"] = "draw2"
        elif re.search(r"[Dd]raw\s*1",         text): effects["burst"] = "draw1"
        elif re.search(r"[Dd]eploy|place.*deck",text, re.I): effects["burst"] = "deploy_top"
        elif re.search(r"[Rr]ecover|[Hh]eal",  text): effects["burst"] = "heal_base"
        else: effects["burst"] = "draw1"

    return ",".join(
        f"{k}:{v}" if v is not True else k
        for k, v in effects.items() if v is not False
    )


def safe_int(v, d=0):
    try:
        return int(str(v).strip().lstrip("+"))
    except:
        return d


def parse_pilot_stats(effect_text):
    text = clean_html(effect_text)
    pa, ph, pn = 0, 0, ""
    if "Pilot" not in text:
        return pa, ph, pn
    sm = re.search(r"【Pilot】(.*)", text, re.DOTALL | re.I)
    if sm:
        sec = sm.group(1)
        m = PILOT_AP_RE.search(sec); pa = safe_int(m.group(1)) if m else 0
        m = PILOT_HP_RE.search(sec); ph = safe_int(m.group(1)) if m else 0
    nm = re.search(r"【Pilot】\s*([^\n【】\[]+?)(?:\s*[\[【]|$)", text, re.I)
    if nm:
        pn = nm.group(1).strip()
    return pa, ph, pn


# ─────────────────────────────────────────────
#  PAGE SCRAPING WITH PLAYWRIGHT
# ─────────────────────────────────────────────

def get_text_by_selectors(page, selectors):
    """Try each selector in order, return first non-empty text."""
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.count() > 0 and el.is_visible():
                t = el.inner_text().strip()
                if t:
                    return t
        except:
            pass
    return ""


def extract_card_number_from_src(src):
    """Pull card number like GD01-001 from an image URL."""
    m = re.search(r"([A-Z]{2,4}\d{2}-\d{3}[a-z]?)", src or "")
    return m.group(1) if m else ""


def scrape_card_panel(page):
    """
    After clicking a card thumbnail, read all visible card detail fields.
    The official site shows a detail overlay/panel with the card stats.
    Returns a raw dict or None.
    """
    time.sleep(CLICK_DELAY)

    # Wait for any kind of detail element to appear
    detail_appeared = False
    for sel in [".cardDetail", ".card-detail", "[class*='detail']",
                ".modal", "[class*='modal']", ".popup"]:
        try:
            page.wait_for_selector(sel, state="visible", timeout=4000)
            detail_appeared = True
            break
        except PWTimeout:
            continue

    # Even if no panel found, try to read whatever's on screen
    # Card number — most reliable from the card image URL
    card_number = ""
    try:
        imgs = page.locator("img").all()
        for img in imgs:
            src = img.get_attribute("src") or ""
            num = extract_card_number_from_src(src)
            if num:
                card_number = num
                break
    except:
        pass

    # ── Field extraction: try many selector patterns ──
    # The official site uses Japanese-style class names; we cast a wide net.

    def txt(*selectors):
        return get_text_by_selectors(page, list(selectors))

    card_name = txt(
        ".cardDetail .name", ".card-detail .name",
        "[class*='cardName']", "[class*='card-name']",
        "[class*='detail'] h2", "[class*='detail'] h3",
        ".modal h2", ".popup h2",
    )

    card_type = txt(
        "[class*='cardType']", "[class*='card-type']",
        "[class*='category']", "td.type",
    )

    color = txt(
        "[class*='color']:not([class*='background'])",
        "[class*='colour']", "td.color",
    )

    lv   = txt("[class*='lv']:not([class*='level-bar'])", "[class*='level']", "td.lv", "td.level")
    cost = txt("[class*='cost']", "td.cost")
    ap   = txt("[class*=':ap']", "[class*='_ap']", "[class*='-ap']", "td.ap", "[class*='attack']")
    hp   = txt("[class*=':hp']", "[class*='_hp']", "[class*='-hp']", "td.hp", "[class*='health']")

    trait = txt("[class*='trait']", "[class*='attribute']", "td.trait")
    link  = txt("[class*='link']", "td.link")
    rarity = txt("[class*='rarity']", "td.rarity", ".rarity")
    zone   = txt("[class*='zone']", "td.zone")

    # Effect text: grab innerHTML from effect-like containers, clean later
    effect_raw = ""
    for sel in ["[class*='effect']", "[class*='ability']",
                "[class*='skillText']", "[class*='skill-text']",
                "[class*='cardText']", "td.effect"]:
        try:
            els = page.locator(sel).all()
            parts = []
            for el in els:
                if el.is_visible():
                    html = el.inner_html()
                    if html.strip():
                        parts.append(html)
            if parts:
                effect_raw = "\n".join(parts)
                break
        except:
            pass

    # If we got almost nothing useful, return None to skip
    if not card_name and not card_number:
        return None

    # Infer card number from text if image didn't have it
    if not card_number:
        card_number = txt(
            "[class*='number']", "[class*='cardNo']",
            "[class*='card-no']", "td.no",
        )

    return {
        "card_number": card_number,
        "card_name":   card_name,
        "card_type":   card_type,
        "colors":      color,
        "lv":          lv,
        "cost":        cost,
        "ap":          ap,
        "hp":          hp,
        "traits":      trait,
        "link":        link,
        "rarity":      rarity,
        "zone":        zone,
        "effect_raw":  effect_raw,
    }


def close_panel(page):
    """Try to dismiss the card detail panel."""
    for sel in [".close", ".btn-close", "[class*='close']",
                ".modal-close", "[aria-label='close']"]:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                el.click()
                time.sleep(0.3)
                return
        except:
            pass
    try:
        page.keyboard.press("Escape")
        time.sleep(0.3)
    except:
        pass


def scrape_set(page, set_code, package_id):
    url = f"{BASE_URL}?package={package_id}"
    print(f"\n[{set_code}] {url}")
    page.goto(url, wait_until="networkidle", timeout=30000)
    time.sleep(2)

    # Find card thumbnail elements — the site renders a <ul> of <li> cards
    thumb_sel = "ul li"
    try:
        page.wait_for_selector(thumb_sel, timeout=15000)
    except PWTimeout:
        print(f"  [WARN] No thumbnails found for {set_code}")
        return []

    thumbs = page.locator(thumb_sel).all()
    print(f"  Found {len(thumbs)} thumbnails")

    cards = []
    for i in range(len(thumbs)):
        try:
            # Re-query each time to avoid stale handles
            thumb = page.locator(thumb_sel).nth(i)
            thumb.scroll_into_view_if_needed()
            time.sleep(0.15)
            thumb.click()

            detail = scrape_card_panel(page)
            if detail:
                detail["set_id"] = set_code
                cards.append(detail)
                num  = detail.get("card_number", "?")
                name = detail.get("card_name",   "?")
                print(f"  [{i+1:3d}/{len(thumbs)}] {num:13s} {name}")
            else:
                print(f"  [{i+1:3d}/{len(thumbs)}] (skipped — no data extracted)")

            close_panel(page)
            time.sleep(0.2)

        except Exception as e:
            print(f"  [{i+1:3d}] Error: {e}")

    return cards


# ─────────────────────────────────────────────
#  TRANSFORM RAW → CSV ROW
# ─────────────────────────────────────────────

def transform(raw):
    num  = (raw.get("card_number") or "").strip()
    name = (raw.get("card_name")   or "").strip()
    if not num and not name:
        return None

    ct_raw    = (raw.get("card_type") or "").strip()
    type_map  = {"unit":"Unit","pilot":"Pilot","command":"Command",
                 "base":"Base","resource":"Resource"}
    card_type = type_map.get(ct_raw.lower(), ct_raw.title() or "Unit")

    raw_color = (raw.get("colors") or "").strip()
    colors    = "/".join(
        c.strip().lower() for c in re.split(r"[/,& ]+", raw_color) if c.strip()
    ) or "blue"

    trait_raw = raw.get("traits") or ""
    traits    = ",".join(re.findall(r"\(([^)]+)\)", trait_raw)) or trait_raw

    link_raw  = raw.get("link") or ""
    link_str  = ",".join(re.findall(r"\[([^\]]+)\]", link_raw)) or link_raw

    effect_raw = raw.get("effect_raw") or ""
    effects    = parse_effects(effect_raw, ct_raw)

    pilot_ap, pilot_hp, pilot_name = 0, 0, ""
    if card_type in ("Pilot", "Command") and "Pilot" in effect_raw:
        pilot_ap, pilot_hp, pilot_name = parse_pilot_stats(effect_raw)
    if card_type == "Pilot":
        text = clean_html(effect_raw)
        m = PILOT_AP_RE.search(text); pilot_ap = safe_int(m.group(1)) if m else pilot_ap
        m = PILOT_HP_RE.search(text); pilot_hp = safe_int(m.group(1)) if m else pilot_hp

    return {
        "card_number":     num,
        "card_name":       name,
        "card_type":       card_type,
        "colors":          colors,
        "lv":              safe_int(raw.get("lv",   0)),
        "cost":            safe_int(raw.get("cost", 0)),
        "ap":              safe_int(raw.get("ap",   0)),
        "hp":              safe_int(raw.get("hp",   0)),
        "traits":          traits,
        "effects":         effects,
        "link_conditions": link_str,
        "pilot_name":      pilot_name,
        "pilot_ap":        pilot_ap,
        "pilot_hp":        pilot_hp,
        "rarity":          raw.get("rarity",""),
        "set_id":          raw.get("set_id",""),
        "zone":            raw.get("zone",""),
        "effect_raw":      clean_html(effect_raw),
    }


# ─────────────────────────────────────────────
#  CSV OUTPUT
# ─────────────────────────────────────────────

def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"\n✅  Saved {len(rows)} cards → {path}")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    global CLICK_DELAY

    p = argparse.ArgumentParser(
        description="Scrape Gundam Card Game data using Playwright (no Chrome install needed)."
    )
    p.add_argument("--out",     default="gundam_cards.csv",
                   help="Output CSV file (default: gundam_cards.csv)")
    p.add_argument("--sets",    nargs="*", metavar="SET",
                   help=f"Sets to scrape, e.g. --sets GD01 ST01. Default: all. "
                        f"Known: {', '.join(ALL_SET_CODES)}")
    p.add_argument("--headed",  action="store_true",
                   help="Show browser window (local machines only, not Codespaces)")
    p.add_argument("--delay",   type=float, default=CLICK_DELAY,
                   help=f"Seconds between card clicks (default: {CLICK_DELAY})")
    p.add_argument("--preview", action="store_true",
                   help="Print first 3 cards as JSON and exit without saving")
    args = p.parse_args()

    CLICK_DELAY = args.delay

    targets = args.sets or ALL_SET_CODES
    targets = [s.upper() for s in targets]
    unknown = [s for s in targets if s not in SET_PACKAGE_IDS]
    if unknown:
        print(f"[WARN] Unknown sets (will skip): {unknown}")
    targets = [s for s in targets if s in SET_PACKAGE_IDS]
    if not targets:
        sys.exit("No valid sets. Known: " + ", ".join(ALL_SET_CODES))

    print("=" * 60)
    print("  Gundam Card Game Scraper  v3  (Playwright)")
    print(f"  Sets   : {', '.join(targets)}")
    print(f"  Output : {args.out}")
    print(f"  Headed : {args.headed}")
    print("=" * 60)

    all_raw = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed)
        context = browser.new_context(
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        for set_code in targets:
            raw = scrape_set(page, set_code, SET_PACKAGE_IDS[set_code])
            all_raw.extend(raw)
            print(f"  → {len(raw)} cards from {set_code} (running total: {len(all_raw)})")

        browser.close()

    if not all_raw:
        print("\n⚠️  No cards were extracted. The site structure may have changed.")
        print("   Try running with --headed to watch what the browser sees (local only).")
        sys.exit(1)

    if args.preview:
        print("\n── Preview (first 3 raw cards) ──")
        for r in all_raw[:3]:
            print(json.dumps(r, indent=2, ensure_ascii=False))
        return

    print(f"\nTransforming {len(all_raw)} raw cards…")
    rows = [t for raw in all_raw if (t := transform(raw))]
    rows.sort(key=lambda r: r["card_number"])
    skipped = len(all_raw) - len(rows)
    print(f"Transformed {len(rows)} cards ({skipped} skipped — no number/name).")

    write_csv(rows, Path(args.out))

    from collections import Counter
    print("\n── Summary ──")
    print("  Card types :", dict(Counter(r["card_type"]  for r in rows)))
    print("  Colors     :", dict(Counter(
        c for r in rows for c in r["colors"].split("/") if c
    )))
    print(f"\n✅  Drop '{args.out}' next to app.py and relaunch the simulator.")
    print("   Or upload it via: Deck Builder tab → Upload CSV")


if __name__ == "__main__":
    main()
