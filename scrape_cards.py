#!/usr/bin/env python3
"""
Gundam Card Game — Card Data Scraper  (v2)
==========================================
Scrapes real card data from the official Gundam Card Game website
(www.gundam-gcg.com) using Selenium, since the site is JavaScript-rendered.

HOW TO INSTALL & RUN
---------------------
1.  pip install selenium webdriver-manager
2.  Python 3.8+ required
3.  Google Chrome must be installed (or Firefox — see --browser flag)
4.  Run:
        python scrape_cards.py                        # all sets, Asia-EN
        python scrape_cards.py --sets GD01 GD02       # specific sets only
        python scrape_cards.py --browser firefox      # use Firefox instead
        python scrape_cards.py --headless false       # watch the browser work
        python scrape_cards.py --out my_cards.csv     # custom output path

The output CSV is directly importable into the Gundam Card Game Simulator app.

NOTES
------
- Uses Selenium to execute JavaScript on the official site.
- Clicks every card thumbnail, reads the detail panel, and extracts stats.
- Expected runtime: ~3-8 minutes for a full card pool.
- If it fails mid-way, re-run with --sets to retry specific sets.
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

def check_deps():
    missing = []
    for pkg, import_name in [("selenium", "selenium"), ("webdriver-manager", "webdriver_manager")]:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("Missing dependencies. Install them first:")
        print(f"    pip install {' '.join(missing)}")
        sys.exit(1)

check_deps()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService


# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

BASE_URL = "https://www.gundam-gcg.com/asia-en/cards/"

# All known sets — extend as new sets release
ALL_SET_CODES = [
    "GD01", "GD02", "GD03",
    "ST01", "ST02", "ST03", "ST04", "ST05", "ST06", "ST07", "ST08",
]

# ?package= query param for each set on the official site.
# Find these by clicking each set filter on the site and reading the URL.
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

WAIT_TIMEOUT = 15
CLICK_DELAY  = 0.9

CSV_COLUMNS = [
    "card_number", "card_name", "card_type", "colors",
    "lv", "cost", "ap", "hp",
    "traits", "effects", "link_conditions",
    "pilot_name", "pilot_ap", "pilot_hp",
    "rarity", "set_id", "zone", "effect_raw",
]


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
        if re.search(r"[Dd]raw\s*2", text):    effects["burst"] = "draw2"
        elif re.search(r"[Dd]raw\s*1", text):  effects["burst"] = "draw1"
        elif re.search(r"[Dd]eploy|place.*deck", text, re.I): effects["burst"] = "deploy_top"
        elif re.search(r"[Rr]ecover|[Hh]eal",  text): effects["burst"] = "heal_base"
        else: effects["burst"] = "draw1"
    return ",".join(f"{k}:{v}" if v is not True else k for k, v in effects.items() if v is not False)


def safe_int(v, d=0):
    try:
        return int(str(v).strip())
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
#  BROWSER
# ─────────────────────────────────────────────

def make_driver(browser="chrome", headless=True):
    if browser == "chrome":
        opts = ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1400,900")
        opts.add_argument("--lang=en-US")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        svc = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=svc, options=opts)
    else:
        opts = FirefoxOptions()
        if headless:
            opts.add_argument("--headless")
        svc = FirefoxService(GeckoDriverManager().install())
        return webdriver.Firefox(service=svc, options=opts)


# ─────────────────────────────────────────────
#  SCRAPING — card list + detail panel
# ─────────────────────────────────────────────

def get_card_number_from_img(driver):
    """Extract card number from the detail image src, e.g. GD01-001."""
    try:
        imgs = driver.find_elements(By.CSS_SELECTOR, ".detail img, [class*='detail'] img, [class*='card'] img")
        for img in imgs:
            src = img.get_attribute("src") or ""
            m = re.search(r"([A-Z]{2,4}\d{2}-\d{3}[a-z]?)", src)
            if m:
                return m.group(1)
    except:
        pass
    return ""


def get_text(driver, selectors):
    """Try a list of CSS selectors, return first non-empty text found."""
    for sel in selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                t = el.text.strip()
                if t:
                    return t
        except:
            pass
    return ""


def scrape_card_detail(driver):
    """
    After a card has been clicked (detail panel visible), extract all fields.
    Returns a raw dict or None.
    """
    time.sleep(0.25)  # let panel animate in

    # Confirm a detail panel is visible
    detail_selectors = [
        ".cardDetail", ".card-detail", "[class*='detail']",
        ".modal", "[class*='modal']", ".popup", "[class*='popup']",
    ]
    panel = None
    for sel in detail_selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed():
                    panel = el
                    break
        except:
            pass
        if panel:
            break

    # Card number from image URL (most reliable)
    card_number = get_card_number_from_img(driver)

    # --- Try to extract each field using multiple selector strategies ---

    # Name
    card_name = get_text(driver, [
        ".cardDetail .name", ".card-detail .name",
        "[class*='detail'] [class*='name']",
        "[class*='cardName']", ".modal h2", ".popup h2",
        "[class*='detail'] h2", "[class*='detail'] h3",
    ])

    # Card type
    card_type = get_text(driver, [
        "[class*='cardType']", "[class*='card-type']", "[class*='type']",
        "td.type", "dt:contains('Type') + dd",
    ])

    # Color
    color = get_text(driver, [
        "[class*='color']", "[class*='colour']",
        "td.color", "[class*='detail'] .color",
    ])

    # Level
    lv = get_text(driver, ["[class*='lv']","[class*='level']","td.lv","td.level"])

    # Cost
    cost = get_text(driver, ["[class*='cost']","td.cost"])

    # AP
    ap = get_text(driver, ["[class*='ap']","td.ap","[class*='attack']"])

    # HP
    hp = get_text(driver, ["[class*='hp']","td.hp","[class*='health']"])

    # Trait
    trait = get_text(driver, ["[class*='trait']","td.trait","[class*='attribute']"])

    # Link condition
    link = get_text(driver, ["[class*='link']","td.link"])

    # Rarity
    rarity = get_text(driver, ["[class*='rarity']","td.rarity",".rarity"])

    # Zone
    zone = get_text(driver, ["[class*='zone']","td.zone"])

    # Effect text — grab all effect-like text blocks
    effect_els = []
    for sel in ["[class*='effect']","[class*='ability']","[class*='text']","td.effect"]:
        try:
            effect_els.extend(driver.find_elements(By.CSS_SELECTOR, sel))
        except:
            pass
    effect_raw = "\n".join(
        el.get_attribute("innerHTML") or el.text
        for el in effect_els
        if el.is_displayed() and el.text.strip()
    )

    # If we got almost nothing, try reading the page source for structured data
    if not card_name and not card_number:
        return None

    # Infer card number from name if not found in image
    if not card_number:
        card_number = get_text(driver, [
            "[class*='number']","[class*='cardNo']","[class*='card-no']","td.no",
        ])

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


def close_detail_panel(driver):
    """Try to close the card detail panel before clicking the next card."""
    for sel in [".close", ".btn-close", "[class*='close']", ".modal-close"]:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed():
                    el.click()
                    time.sleep(0.3)
                    return
        except:
            pass
    # Fallback: press Escape
    try:
        from selenium.webdriver.common.keys import Keys
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(0.3)
    except:
        pass


def scrape_set(driver, set_code, package_id):
    url = f"{BASE_URL}?package={package_id}"
    print(f"\n[{set_code}] {url}")
    driver.get(url)

    # Wait for cards to load
    for sel in ["ul li img", ".card-list li", "[class*='card'] img", "li img"]:
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, sel))
            )
            break
        except TimeoutException:
            continue
    time.sleep(2)

    # Gather clickable card elements
    thumb_selectors = [
        "ul li", ".card-list > li", "[class*='card-list'] li",
        "[class*='cards'] li", ".list li",
    ]
    thumbs = []
    for sel in thumb_selectors:
        thumbs = driver.find_elements(By.CSS_SELECTOR, sel)
        if thumbs:
            break

    if not thumbs:
        print(f"  [WARN] No card thumbnails found for {set_code}")
        return []

    print(f"  Found {len(thumbs)} thumbnails")
    cards = []

    for i in range(len(thumbs)):
        try:
            # Re-fetch thumbs each iteration to avoid stale refs
            thumbs = driver.find_elements(By.CSS_SELECTOR, thumb_selectors[0])
            if i >= len(thumbs):
                break
            thumb = thumbs[i]
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", thumb)
            time.sleep(0.2)
            thumb.click()
            time.sleep(CLICK_DELAY)

            detail = scrape_card_detail(driver)
            if detail:
                detail["set_id"] = set_code
                cards.append(detail)
                num  = detail.get("card_number", "?")
                name = detail.get("card_name",   "?")
                print(f"  [{i+1:3d}/{len(thumbs)}] {num:12s} {name}")
            else:
                print(f"  [{i+1:3d}] (no detail extracted)")

            close_detail_panel(driver)
            time.sleep(0.3)

        except StaleElementReferenceException:
            print(f"  [{i+1}] Stale element, skipping")
        except Exception as e:
            print(f"  [{i+1}] Error: {e}")

    return cards


# ─────────────────────────────────────────────
#  TRANSFORM + OUTPUT
# ─────────────────────────────────────────────

def transform(raw):
    num  = (raw.get("card_number") or "").strip()
    name = (raw.get("card_name")   or "").strip()
    if not num and not name:
        return None

    card_type_raw = (raw.get("card_type") or "").strip()
    type_map = {"unit":"Unit","pilot":"Pilot","command":"Command","base":"Base","resource":"Resource"}
    card_type = type_map.get(card_type_raw.lower(), card_type_raw.title() or "Unit")

    raw_color = raw.get("colors") or ""
    colors = "/".join(c.strip().lower() for c in re.split(r"[/,&]", raw_color) if c.strip()) or "blue"

    trait_raw = raw.get("traits") or ""
    traits    = ",".join(re.findall(r"\(([^)]+)\)", trait_raw)) or trait_raw

    link_raw = raw.get("link") or ""
    link_str = ",".join(re.findall(r"\[([^\]]+)\]", link_raw)) or link_raw

    effect_raw = raw.get("effect_raw") or ""
    effects    = parse_effects(effect_raw, card_type_raw)

    pilot_ap, pilot_hp, pilot_name = 0, 0, ""
    if card_type in ("Pilot", "Command") and "Pilot" in effect_raw:
        pilot_ap, pilot_hp, pilot_name = parse_pilot_stats(effect_raw)
    if card_type == "Pilot":
        m = PILOT_AP_RE.search(clean_html(effect_raw)); pilot_ap = safe_int(m.group(1)) if m else pilot_ap
        m = PILOT_HP_RE.search(clean_html(effect_raw)); pilot_hp = safe_int(m.group(1)) if m else pilot_hp

    return {
        "card_number":     num,
        "card_name":       name,
        "card_type":       card_type,
        "colors":          colors,
        "lv":              safe_int(raw.get("lv",  0)),
        "cost":            safe_int(raw.get("cost",0)),
        "ap":              safe_int(raw.get("ap",  0)),
        "hp":              safe_int(raw.get("hp",  0)),
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
        description="Scrape Gundam Card Game from gundam-gcg.com using Selenium."
    )
    p.add_argument("--out",      default="gundam_cards.csv")
    p.add_argument("--sets",     nargs="*", metavar="SET")
    p.add_argument("--browser",  default="chrome", choices=["chrome","firefox"])
    p.add_argument("--headless", default="true",   choices=["true","false"])
    p.add_argument("--delay",    type=float, default=CLICK_DELAY)
    p.add_argument("--preview",  action="store_true")
    args = p.parse_args()

    CLICK_DELAY = args.delay
    headless    = args.headless.lower() == "true"

    targets = args.sets or ALL_SET_CODES
    targets = [s for s in targets if s in SET_PACKAGE_IDS]
    if not targets:
        sys.exit("No valid set codes. Known sets: " + ", ".join(ALL_SET_CODES))

    print("=" * 60)
    print("  Gundam Card Game Scraper  (Selenium)")
    print(f"  Browser  : {args.browser} (headless={headless})")
    print(f"  Sets     : {', '.join(targets)}")
    print(f"  Output   : {args.out}")
    print("=" * 60)

    driver = make_driver(args.browser, headless)
    all_raw = []
    try:
        for set_code in targets:
            raw = scrape_set(driver, set_code, SET_PACKAGE_IDS[set_code])
            all_raw.extend(raw)
    finally:
        driver.quit()

    if args.preview:
        for r in all_raw[:3]:
            print(json.dumps(r, indent=2, ensure_ascii=False))
        return

    rows = [t for raw in all_raw if (t := transform(raw))]
    rows.sort(key=lambda r: r["card_number"])
    write_csv(rows, Path(args.out))

    from collections import Counter
    print("\n── Summary ──")
    print("  Card types :", dict(Counter(r["card_type"]  for r in rows)))
    print("  Colors     :", dict(Counter(c for r in rows for c in r["colors"].split("/") if c)))
    print("\nImport the CSV in the app → Deck Builder → Upload CSV")


if __name__ == "__main__":
    main()
