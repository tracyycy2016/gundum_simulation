"""
Gundam Card Game Simulator — Streamlit App
===========================================
Run:  streamlit run app.py
Deps: pip install streamlit pandas
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import copy
import random
import io
import json
import time
from collections import Counter, defaultdict

import pandas as pd
import streamlit as st

from engine import GameEngine, validate_deck, CardTemplate
from cards import (
    get_all_cards, get_card_lookup, get_resource_cards,
    using_real_data, real_card_count, load_cards_from_csv,
    ALL_CARDS, CARD_LOOKUP, CARD_NAME_LOOKUP, RESOURCES,
    PRESET_DECKS
)

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Gundam Card Game Simulator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  CUSTOM CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
  .main-header {
      background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
      padding: 1.5rem 2rem;
      border-radius: 12px;
      margin-bottom: 1.5rem;
      text-align: center;
  }
  .main-header h1 { color: #00d4ff; font-size: 2.2rem; margin: 0; text-shadow: 0 0 20px #00d4ff55; }
  .main-header p  { color: #aaa; margin: 0.3rem 0 0; font-size: 0.9rem; }

  .card-badge {
      display: inline-block;
      padding: 0.15rem 0.5rem;
      border-radius: 20px;
      font-size: 0.75rem;
      font-weight: bold;
      margin: 0.1rem;
  }
  .badge-blue   { background: #1a3a6e; color: #90c8ff; border: 1px solid #3a7bd5; }
  .badge-red    { background: #6e1a1a; color: #ffa8a8; border: 1px solid #d53a3a; }
  .badge-green  { background: #1a4a2a; color: #90ffa8; border: 1px solid #3ad55e; }
  .badge-white  { background: #4a4a4a; color: #ffffff; border: 1px solid #aaaaaa; }
  .badge-purple { background: #3a1a6e; color: #d4a8ff; border: 1px solid #8b3ad5; }

  .stat-box {
      background: #1e2530;
      border-radius: 10px;
      padding: 1rem;
      border-left: 4px solid #00d4ff;
      margin: 0.5rem 0;
  }
  .win-highlight { color: #00ff88; font-weight: bold; }
  .lose-highlight { color: #ff6b6b; }
  .log-entry { font-family: monospace; font-size: 0.82rem; line-height: 1.4; }
  .valid-ok   { color: #00ff88; }
  .valid-fail { color: #ff6b6b; }

  div[data-testid="stMetricValue"] { font-size: 2rem !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────

st.markdown("""
<div class="main-header">
  <h1>⚡ Gundam Card Game Simulator ⚡</h1>
  <p>Rules: Comprehensive Rules Ver. 1.5.0 &nbsp;|&nbsp; Build decks · Validate · Simulate battles</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  DATA SOURCE BANNER + CSV UPLOAD
# ─────────────────────────────────────────────

# Allow uploading a real card CSV directly on the main page
with st.expander("📂 Load Real Card Data (gundam_cards.csv)", expanded=not using_real_data()):
    if using_real_data():
        st.success(f"✅ **Real card data loaded** — {real_card_count()} cards from `gundam_cards.csv`")
        st.caption(
            "Data sourced from apitcg.com. Re-run `scrape_cards.py` anytime to refresh."
        )
    else:
        st.warning(
            "⚠️ Using **built-in sample cards** (fake stats). "
            "Run the scraper to load real card data."
        )
        st.markdown("""
        **To load real cards:**
        1. Run: `pip install requests` then `python scrape_cards.py`
        2. This creates `gundam_cards.csv` next to `app.py`
        3. **Or** upload the CSV file here:
        """)
        uploaded_csv = st.file_uploader(
            "Upload gundam_cards.csv", type=["csv"], key="global_csv_upload",
            label_visibility="collapsed"
        )
        if uploaded_csv:
            import tempfile, shutil
            tmp = Path(tempfile.mktemp(suffix=".csv"))
            tmp.write_bytes(uploaded_csv.read())
            loaded = load_cards_from_csv(tmp)
            if loaded:
                import cards as _cards_module
                _cards_module.REAL_ALL_CARDS = loaded
                _cards_module.REAL_CARDS_LOADED = True
                st.success(f"✅ Loaded {len(loaded)} cards! Please refresh the page.")
                st.rerun()
            else:
                st.error("Failed to parse CSV. Check the format matches the template.")

if using_real_data():
    st.info(f"🃏 **{real_card_count()} real cards loaded** from `gundam_cards.csv` (via apitcg.com)")
else:
    st.warning("🎲 Using **sample card data** — run `scrape_cards.py` for real stats.")


# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────

COLOR_MAP = {
    "blue": "badge-blue", "red": "badge-red", "green": "badge-green",
    "white": "badge-white", "purple": "badge-purple"
}

def color_badge(color: str) -> str:
    cls = COLOR_MAP.get(color, "badge-white")
    return f'<span class="card-badge {cls}">{color.upper()}</span>'

def type_icon(t: str) -> str:
    icons = {"Unit": "🤖", "Pilot": "👨‍✈️", "Command": "⚡", "Base": "🏰", "Resource": "💎"}
    return icons.get(t, "📄")

def cards_to_df(cards: list[CardTemplate]) -> pd.DataFrame:
    rows = []
    for c in cards:
        rows.append({
            "#": c.card_number,
            "Name": c.card_name,
            "Type": c.card_type,
            "Color": "/".join(c.colors),
            "Lv": c.lv,
            "Cost": c.cost,
            "AP": c.ap if c.ap else "-",
            "HP": c.hp if c.hp else "-",
            "Traits": ", ".join(c.traits) if c.traits else "-",
            "Effects": ", ".join(
                [k if not isinstance(v, bool) else k for k, v in c.effects.items()
                 if k not in ("timing",) and v is not False]
            ) or "-",
        })
    return pd.DataFrame(rows)

def deck_to_df(deck: list[CardTemplate]) -> pd.DataFrame:
    from collections import Counter
    counts = Counter(c.card_number for c in deck)
    seen = {}
    rows = []
    for c in deck:
        if c.card_number not in seen:
            seen[c.card_number] = True
            rows.append({
                "Qty": counts[c.card_number],
                "Name": c.card_name,
                "Type": c.card_type,
                "Color": "/".join(c.colors),
                "Lv": c.lv,
                "Cost": c.cost,
                "AP": c.ap if c.ap else "-",
                "HP": c.hp if c.hp else "-",
            })
    return pd.DataFrame(rows).sort_values(["Type", "Lv"])

def parse_csv_to_cards(df: pd.DataFrame) -> tuple[list[CardTemplate], list[str]]:
    """
    CSV columns: card_number, card_name, card_type, colors, lv, cost, ap, hp,
                 traits, effects, link_conditions, pilot_name, pilot_ap, pilot_hp
    Returns (cards, errors)
    """
    required = {"card_number", "card_name", "card_type", "colors", "lv", "cost"}
    missing = required - set(df.columns.str.lower())
    if missing:
        return [], [f"CSV missing required columns: {', '.join(missing)}"]

    df.columns = df.columns.str.lower().str.strip()
    cards = []
    errors = []
    for i, row in df.iterrows():
        try:
            colors = [c.strip() for c in str(row.get("colors", "")).split("/") if c.strip()]
            traits = [t.strip() for t in str(row.get("traits", "")).split(",") if t.strip() and t != "nan"]
            link_conditions = [l.strip() for l in str(row.get("link_conditions", "")).split(",") if l.strip() and l != "nan"]

            # Parse effects from string like "blocker,first_strike,support:2"
            effects = {}
            eff_str = str(row.get("effects", ""))
            if eff_str and eff_str != "nan":
                for part in eff_str.split(","):
                    part = part.strip()
                    if ":" in part:
                        k, v = part.split(":", 1)
                        try:
                            effects[k.strip()] = int(v.strip())
                        except ValueError:
                            effects[k.strip()] = v.strip()
                    elif part:
                        effects[part] = True

            pilot_name = str(row.get("pilot_name", "")).strip()
            if pilot_name == "nan":
                pilot_name = ""

            card = CardTemplate(
                card_number=str(row["card_number"]).strip(),
                card_name=str(row["card_name"]).strip(),
                card_type=str(row["card_type"]).strip(),
                colors=colors,
                lv=int(row.get("lv", 0)),
                cost=int(row.get("cost", 0)),
                ap=int(row.get("ap", 0)) if str(row.get("ap", "0")) not in ("nan", "-", "") else 0,
                hp=int(row.get("hp", 0)) if str(row.get("hp", "0")) not in ("nan", "-", "") else 0,
                traits=traits,
                effects=effects,
                link_conditions=link_conditions,
                pilot_name=pilot_name,
                pilot_ap=int(row.get("pilot_ap", 0)) if str(row.get("pilot_ap", "0")) not in ("nan", "-", "") else 0,
                pilot_hp=int(row.get("pilot_hp", 0)) if str(row.get("pilot_hp", "0")) not in ("nan", "-", "") else 0,
            )
            cards.append(card)
        except Exception as e:
            errors.append(f"Row {i+2}: {e}")
    return cards, errors


def run_simulations(
    deck1: list[CardTemplate], rdeck1: list[CardTemplate],
    deck2: list[CardTemplate], rdeck2: list[CardTemplate],
    name1: str, name2: str,
    n: int, progress_bar=None
) -> dict:
    results = {"p1_wins": 0, "p2_wins": 0, "draws": 0, "turns": [], "logs": []}
    for i in range(n):
        engine = GameEngine(
            copy.deepcopy(deck1), copy.deepcopy(rdeck1),
            copy.deepcopy(deck2), copy.deepcopy(rdeck2),
            deck1_name=name1, deck2_name=name2
        )
        result = engine.run()
        if result["winner"] == 1:
            results["p1_wins"] += 1
        elif result["winner"] == 2:
            results["p2_wins"] += 1
        else:
            results["draws"] += 1
        results["turns"].append(result["turns"])
        results["logs"].append(result)
        if progress_bar:
            progress_bar.progress((i + 1) / n, text=f"Game {i+1}/{n}")
    return results


# ─────────────────────────────────────────────
#  SESSION STATE INIT
# ─────────────────────────────────────────────

for key, default in {
    "deck1": [], "rdeck1": [], "deck2": [], "rdeck2": [],
    "deck1_name": "Deck 1", "deck2_name": "Deck 2",
    "sim_results": None, "deck1_valid": False, "deck2_valid": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────

tab_catalog, tab_deck1, tab_deck2, tab_sim, tab_results = st.tabs([
    "📚 Card Catalog",
    "🔵 Deck 1 Builder",
    "🔴 Deck 2 Builder",
    "⚡ Simulate",
    "📊 Results & Logs",
])

# ════════════════════════════════════════════════
#  TAB 0 — CARD CATALOG
# ════════════════════════════════════════════════

with tab_catalog:
    st.subheader("📚 Card Catalog")
    st.caption(
        "This simulator ships with a built-in sample card database. "
        "You can also upload your own cards via CSV in the deck builders. "
        "The real card list is available at https://www.gundam-gcg.com/asia-en/cards/index.php"
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        type_filter = st.multiselect("Card Type", ["Unit", "Pilot", "Command", "Base", "Resource"], default=[])
    with col2:
        color_filter = st.multiselect("Color", ["blue", "red", "green", "white", "purple"], default=[])
    with col3:
        lv_range = st.slider("Level Range", 0, 6, (0, 6))

    name_search = st.text_input("🔍 Search by name or trait", "")

    filtered = get_all_cards()
    if type_filter:
        filtered = [c for c in filtered if c.card_type in type_filter]
    if color_filter:
        filtered = [c for c in filtered if any(col in c.colors for col in color_filter)]
    filtered = [c for c in filtered if lv_range[0] <= c.lv <= lv_range[1]]
    if name_search:
        q = name_search.lower()
        filtered = [c for c in filtered if q in c.card_name.lower() or any(q in t.lower() for t in c.traits)]

    st.markdown(f"**{len(filtered)}** cards found")
    if filtered:
        st.dataframe(cards_to_df(filtered), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("📥 CSV Template")
    st.markdown(
        "Download the template below to import your own cards."
    )
    sample_rows = [
        {
            "card_number": "GCG-001", "card_name": "Example Unit", "card_type": "Unit",
            "colors": "blue", "lv": 3, "cost": 3, "ap": 4, "hp": 4,
            "traits": "Earth Federation,Gundam", "effects": "first_strike,breach:1",
            "link_conditions": "Amuro Ray", "pilot_name": "", "pilot_ap": "", "pilot_hp": "",
        },
        {
            "card_number": "GCG-002", "card_name": "Example Pilot", "card_type": "Pilot",
            "colors": "blue", "lv": 2, "cost": 2, "ap": 0, "hp": 0,
            "traits": "Earth Federation,Newtype", "effects": "when_paired_draw:1",
            "link_conditions": "", "pilot_name": "", "pilot_ap": 2, "pilot_hp": 1,
        },
        {
            "card_number": "GCG-003", "card_name": "Example Resource", "card_type": "Resource",
            "colors": "blue", "lv": 0, "cost": 0, "ap": 0, "hp": 0,
            "traits": "", "effects": "", "link_conditions": "", "pilot_name": "", "pilot_ap": "", "pilot_hp": "",
        },
    ]
    template_df = pd.DataFrame(sample_rows)
    csv_bytes = template_df.to_csv(index=False).encode()
    st.download_button("📥 Download CSV Template", csv_bytes, "gundam_card_template.csv", "text/csv")


# ════════════════════════════════════════════════
#  DECK BUILDER HELPER
# ════════════════════════════════════════════════

def deck_builder_ui(deck_slot: str, label: str, color_accent: str):
    """Reusable deck builder for slot 'deck1' or 'deck2'."""
    rdeck_slot = "r" + deck_slot  # rdeck1 / rdeck2
    name_slot = deck_slot + "_name"
    valid_slot = deck_slot + "_valid"

    st.subheader(f"{label} Builder")

    st.session_state[name_slot] = st.text_input("Deck Name", value=st.session_state[name_slot], key=f"{deck_slot}_name_input")

    mode = st.radio("Build Mode", ["🎯 Choose Preset", "🔧 Custom Builder", "📤 Upload CSV"], key=f"{deck_slot}_mode", horizontal=True)

    if mode == "🎯 Choose Preset":
        preset_choice = st.selectbox("Choose a Preset Deck", list(PRESET_DECKS.keys()), key=f"{deck_slot}_preset")
        if st.button(f"Load Preset: {preset_choice}", key=f"{deck_slot}_load_preset"):
            main, rdeck = PRESET_DECKS[preset_choice]()
            st.session_state[deck_slot] = main
            st.session_state[rdeck_slot] = rdeck
            st.session_state[name_slot] = preset_choice
            st.success(f"Loaded '{preset_choice}' ({len(main)} cards + {len(rdeck)} resources)")

    elif mode == "🔧 Custom Builder":
        st.markdown("**Step 1 — Filter & Add Cards to Main Deck**")
        col1, col2, col3 = st.columns(3)
        with col1:
            ftype = st.multiselect("Type", ["Unit", "Pilot", "Command", "Base"], key=f"{deck_slot}_ftype")
        with col2:
            fcolor = st.multiselect("Color", ["blue", "red", "green", "white", "purple"], key=f"{deck_slot}_fcolor")
        with col3:
            fname = st.text_input("Search", key=f"{deck_slot}_fname")

        pool = [c for c in get_all_cards() if c.card_type != "Resource"]
        if ftype:
            pool = [c for c in pool if c.card_type in ftype]
        if fcolor:
            pool = [c for c in pool if any(col in c.colors for col in fcolor)]
        if fname:
            pool = [c for c in pool if fname.lower() in c.card_name.lower()]

        if pool:
            pool_df = cards_to_df(pool)
            selected_indices = st.multiselect(
                "Select cards to add (multi-select)",
                options=[f"{c.card_number} — {c.card_name} (Lv{c.lv} {c.card_type})" for c in pool],
                key=f"{deck_slot}_selected"
            )
            copies = st.number_input("Copies of each selected card", 1, 4, 1, key=f"{deck_slot}_copies")
            if st.button("➕ Add to Deck", key=f"{deck_slot}_add"):
                added = 0
                for sel in selected_indices:
                    card_num = sel.split(" — ")[0]
                    _cl = get_card_lookup()
                if card_num in _cl:
                        card = _cl[card_num]
                        existing_count = sum(1 for c in st.session_state[deck_slot] if c.card_number == card_num)
                        can_add = min(copies, 4 - existing_count)
                        if can_add > 0:
                            st.session_state[deck_slot] += [card] * can_add
                            added += can_add
                if added:
                    st.success(f"Added {added} card copy/copies to deck.")

        st.divider()
        st.markdown("**Step 2 — Add Resource Cards**")
        res_pool = get_resource_cards()
        res_selected = st.multiselect(
            "Select resource cards",
            options=[f"{c.card_number} — {c.card_name}" for c in res_pool],
            key=f"{deck_slot}_res_sel"
        )
        res_copies = st.number_input("Resource copies", 1, 10, 1, key=f"{deck_slot}_res_copies")
        if st.button("➕ Add Resources", key=f"{deck_slot}_add_res"):
            for sel in res_selected:
                card_num = sel.split(" — ")[0]
                _cl = get_card_lookup()
            if card_num in _cl:
                    card = _cl[card_num]
                    st.session_state[rdeck_slot] += [card] * res_copies
            st.success("Resources added.")

        if st.button("🗑️ Clear Deck", key=f"{deck_slot}_clear"):
            st.session_state[deck_slot] = []
            st.session_state[rdeck_slot] = []

    else:  # CSV Upload
        st.markdown("Upload a CSV with columns matching the template from the Card Catalog tab.")
        uploaded = st.file_uploader("Upload CSV", type=["csv"], key=f"{deck_slot}_csv")
        deck_type = st.radio("CSV contains", ["Main Deck", "Resource Deck", "Both (card_type column used)"],
                             key=f"{deck_slot}_csv_type", horizontal=True)
        if uploaded and st.button("📥 Import CSV", key=f"{deck_slot}_import"):
            df = pd.read_csv(uploaded)
            cards, errs = parse_csv_to_cards(df)
            if errs:
                for e in errs:
                    st.error(e)
            else:
                if deck_type == "Main Deck":
                    st.session_state[deck_slot] = cards
                elif deck_type == "Resource Deck":
                    st.session_state[rdeck_slot] = cards
                else:
                    main_cards = [c for c in cards if c.card_type != "Resource"]
                    res_cards  = [c for c in cards if c.card_type == "Resource"]
                    st.session_state[deck_slot] = main_cards
                    st.session_state[rdeck_slot] = res_cards
                st.success(f"Imported {len(cards)} cards.")

    # ── Current Deck Preview ──
    st.divider()
    st.markdown("### 📋 Current Deck")
    main = st.session_state[deck_slot]
    rdeck = st.session_state[rdeck_slot]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Main Deck", f"{len(main)}/50")
    c2.metric("Resource Deck", f"{len(rdeck)}/10")
    counts = Counter(c.card_type for c in main)
    c3.metric("Units", counts.get("Unit", 0))
    c4.metric("Pilots", counts.get("Pilot", 0))

    if main:
        st.dataframe(deck_to_df(main), use_container_width=True, hide_index=True, height=300)

    if rdeck:
        with st.expander("Resource Deck"):
            st.dataframe(cards_to_df(rdeck), use_container_width=True, hide_index=True)

    # ── Validation ──
    st.divider()
    st.markdown("### ✅ Deck Validation")
    if st.button(f"🔍 Validate {label}", key=f"{deck_slot}_validate"):
        valid, errors = validate_deck(main, rdeck, st.session_state[name_slot])
        st.session_state[valid_slot] = valid
        if valid:
            st.success("✅ Deck is **valid** and ready for simulation!")
        else:
            st.error("❌ Deck has validation errors:")
            for e in errors:
                st.markdown(f"- {e}")

    if st.session_state.get(valid_slot):
        st.markdown('<p class="valid-ok">✅ Last validation passed</p>', unsafe_allow_html=True)


# ════════════════════════════════════════════════
#  TAB 1 & 2 — DECK BUILDERS
# ════════════════════════════════════════════════

with tab_deck1:
    deck_builder_ui("deck1", "🔵 Deck 1", "#3a7bd5")

with tab_deck2:
    deck_builder_ui("deck2", "🔴 Deck 2", "#d53a3a")


# ════════════════════════════════════════════════
#  TAB 3 — SIMULATE
# ════════════════════════════════════════════════

with tab_sim:
    st.subheader("⚡ Run Simulation")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Deck 1:** {st.session_state['deck1_name']}")
        d1_ok = len(st.session_state["deck1"]) == 50 and len(st.session_state["rdeck1"]) == 10
        st.markdown(
            f"{'✅ Ready' if d1_ok else '❌ Not ready — needs 50 main + 10 resource cards'} "
            f"({len(st.session_state['deck1'])} main, {len(st.session_state['rdeck1'])} resource)"
        )
    with col2:
        st.markdown(f"**Deck 2:** {st.session_state['deck2_name']}")
        d2_ok = len(st.session_state["deck2"]) == 50 and len(st.session_state["rdeck2"]) == 10
        st.markdown(
            f"{'✅ Ready' if d2_ok else '❌ Not ready — needs 50 main + 10 resource cards'} "
            f"({len(st.session_state['deck2'])} main, {len(st.session_state['rdeck2'])} resource)"
        )

    st.divider()

    # Quick-load presets if decks not ready
    if not d1_ok or not d2_ok:
        st.info("💡 Tip: Use the preset loader below to quickly populate both decks for a demo simulation.")
        c1, c2 = st.columns(2)
        with c1:
            p1 = st.selectbox("Quick-load Deck 1", list(PRESET_DECKS.keys()), key="quick_p1")
            if st.button("Load Deck 1", key="quick_load_d1"):
                m, r = PRESET_DECKS[p1]()
                st.session_state["deck1"] = m
                st.session_state["rdeck1"] = r
                st.session_state["deck1_name"] = p1
                st.rerun()
        with c2:
            p2 = st.selectbox("Quick-load Deck 2", list(PRESET_DECKS.keys()), index=1, key="quick_p2")
            if st.button("Load Deck 2", key="quick_load_d2"):
                m, r = PRESET_DECKS[p2]()
                st.session_state["deck2"] = m
                st.session_state["rdeck2"] = r
                st.session_state["deck2_name"] = p2
                st.rerun()

    st.divider()

    n_games = st.slider("Number of Games to Simulate", min_value=1, max_value=500, value=50, step=1)
    seed = st.number_input("Random Seed (0 = random each run)", min_value=0, value=42)

    st.markdown("""
    **Simulation rules implemented:**
    - 50-card main deck, 10-card resource deck
    - EX Base (0 AP / 3 HP) for each player; EX Resource for Player 2
    - Full turn cycle: Start → Draw → Resource → Main → End phases
    - Units cannot attack on deploy turn (unless Link Unit)
    - <First Strike>, <Blocker>, <Breach>, <Support>, <Repair>, <High-Maneuver>, <Suppression>
    - 【Burst】 effects on shields
    - Hand limit of 10 at end of turn
    - Defeat by direct damage or empty deck
    - AI: greedy card play, best-target attacking, basic blocking
    """)

    run_disabled = not (d1_ok and d2_ok)
    if st.button("🚀 Run Simulation", disabled=run_disabled, type="primary"):
        if seed > 0:
            random.seed(seed)

        # Validate first
        v1, e1 = validate_deck(st.session_state["deck1"], st.session_state["rdeck1"], st.session_state["deck1_name"])
        v2, e2 = validate_deck(st.session_state["deck2"], st.session_state["rdeck2"], st.session_state["deck2_name"])

        all_errors = e1 + e2
        if all_errors:
            st.error("Deck validation failed before simulation:")
            for e in all_errors:
                st.markdown(f"- {e}")
        else:
            pb = st.progress(0, text="Starting simulation...")
            start_time = time.time()

            results = run_simulations(
                st.session_state["deck1"], st.session_state["rdeck1"],
                st.session_state["deck2"], st.session_state["rdeck2"],
                st.session_state["deck1_name"], st.session_state["deck2_name"],
                n_games, pb
            )

            elapsed = time.time() - start_time
            pb.progress(1.0, text=f"Done! {n_games} games in {elapsed:.1f}s")
            st.session_state["sim_results"] = results
            st.success(f"✅ Simulation complete! Switch to the **📊 Results & Logs** tab.")


# ════════════════════════════════════════════════
#  TAB 4 — RESULTS & LOGS
# ════════════════════════════════════════════════

with tab_results:
    res = st.session_state.get("sim_results")
    if res is None:
        st.info("Run a simulation first in the ⚡ Simulate tab.")
    else:
        n = res["p1_wins"] + res["p2_wins"] + res["draws"]
        name1 = st.session_state["deck1_name"]
        name2 = st.session_state["deck2_name"]

        # ── Summary metrics ──
        st.subheader("📊 Simulation Summary")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Games", n)
        col2.metric(f"🔵 {name1[:20]} Wins", res["p1_wins"],
                    delta=f"{res['p1_wins']/n*100:.1f}%")
        col3.metric(f"🔴 {name2[:20]} Wins", res["p2_wins"],
                    delta=f"{res['p2_wins']/n*100:.1f}%")
        col4.metric("Draws / Timeout", res["draws"])

        # Win rate bars
        p1_rate = res["p1_wins"] / n * 100
        p2_rate = res["p2_wins"] / n * 100
        draw_rate = res["draws"] / n * 100

        st.markdown(f"""
        <div class="stat-box">
          <strong>Win Rates</strong><br>
          <span style="color:#3a7bd5">■</span> {name1}: <strong>{p1_rate:.1f}%</strong> &nbsp;
          <span style="color:#d53a3a">■</span> {name2}: <strong>{p2_rate:.1f}%</strong> &nbsp;
          <span style="color:#888">■</span> Draw: <strong>{draw_rate:.1f}%</strong>
        </div>
        """, unsafe_allow_html=True)

        # Winner announcement
        if p1_rate > p2_rate:
            st.success(f"🏆 **{name1}** wins the simulation with {p1_rate:.1f}% win rate!")
        elif p2_rate > p1_rate:
            st.success(f"🏆 **{name2}** wins the simulation with {p2_rate:.1f}% win rate!")
        else:
            st.info("🤝 The decks are evenly matched!")

        # Turn statistics
        st.divider()
        st.subheader("📈 Game Length Statistics")
        turns = res["turns"]
        avg_turns = sum(turns) / len(turns)
        min_turns = min(turns)
        max_turns = max(turns)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Avg Turns", f"{avg_turns:.1f}")
        c2.metric("Min Turns", min_turns)
        c3.metric("Max Turns", max_turns)
        c4.metric("Median Turns", f"{sorted(turns)[len(turns)//2]}")

        turn_counts = Counter(turns)
        turn_df = pd.DataFrame([{"Turns": t, "Games": c} for t, c in sorted(turn_counts.items())])
        st.bar_chart(turn_df.set_index("Turns"), use_container_width=True)

        # Win rate over time
        st.divider()
        st.subheader("📉 Win Rate Over Games")
        p1_cumulative = []
        p1_count = 0
        for i, game_log in enumerate(res["logs"]):
            if game_log["winner"] == 1:
                p1_count += 1
            p1_cumulative.append({"Game": i+1, f"{name1} Win Rate %": p1_count/(i+1)*100})

        rate_df = pd.DataFrame(p1_cumulative)
        st.line_chart(rate_df.set_index("Game"), use_container_width=True)

        # ── Final State Analysis ──
        st.divider()
        st.subheader("🏁 Final State Analysis")

        shield_data = defaultdict(list)
        for game in res["logs"]:
            fs = game["final_state"]
            if game["winner"] == 1:
                shield_data["Winner Shields Left"].append(fs["p1_shields"])
                shield_data["Loser Shields Left"].append(fs["p2_shields"])
            elif game["winner"] == 2:
                shield_data["Winner Shields Left"].append(fs["p2_shields"])
                shield_data["Loser Shields Left"].append(fs["p1_shields"])

        if shield_data.get("Winner Shields Left"):
            avg_winner_shields = sum(shield_data["Winner Shields Left"]) / len(shield_data["Winner Shields Left"])
            st.markdown(f"**Average shields remaining for winner:** {avg_winner_shields:.1f}")

        # ── Game Logs ──
        st.divider()
        st.subheader("📜 Detailed Game Logs")

        log_idx = st.slider("View Game #", 1, n, 1)
        game = res["logs"][log_idx - 1]

        winner_label = (
            f"🏆 Winner: **{name1}** (P1)" if game["winner"] == 1
            else f"🏆 Winner: **{name2}** (P2)" if game["winner"] == 2
            else "🤝 Draw / Timeout"
        )
        st.markdown(winner_label)
        st.markdown(f"**Turns played:** {game['turns']}")
        fs = game["final_state"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"P1 Shields", fs["p1_shields"])
        c2.metric(f"P2 Shields", fs["p2_shields"])
        c3.metric(f"P1 Units", fs["p1_units"])
        c4.metric(f"P2 Units", fs["p2_units"])

        # Filter log entries
        show_types = st.multiselect(
            "Filter log events",
            ["system", "turn_start", "board_hand", "board_battle", "board_status",
             "deploy", "pair", "attack", "damage",
             "destroy", "shield_destroy", "burst", "draw", "support",
             "defeat", "command", "block", "breach"],
            default=["turn_start", "board_hand", "board_battle", "board_status",
                     "deploy", "pair", "attack", "damage",
                     "destroy", "shield_destroy", "burst", "draw", "defeat", "breach"],
            key="log_filter"
        )

        entries = [e for e in game["log_entries"] if e["type"] in show_types] if show_types else game["log_entries"]

        log_text_lines = []
        prev_turn = None
        for e in entries:
            if e["turn"] != prev_turn:
                log_text_lines.append(f"\n{'─'*60}")
                log_text_lines.append(f"  TURN {e['turn']}")
                log_text_lines.append(f"{'─'*60}")
                prev_turn = e["turn"]
            icon = {
                "defeat": "💀", "attack": "⚔️", "destroy": "💥", "shield_destroy": "🛡️",
                "deploy": "🤖", "pair": "👨‍✈️", "burst": "✨", "damage": "❤️",
                "draw": "🃏", "command": "⚡", "block": "🛡", "breach": "🔥",
                "turn_start": "🔄", "support": "💪",
                "board_hand":   "🖐️",
                "board_battle": "⚔ ",
                "board_status": "📋",
            }.get(e["type"], "•")
            # Indent board state lines for readability
            indent = "    " if e["type"].startswith("board_") else "  "
            log_text_lines.append(f"{indent}{icon} [{e['phase']:15s}] {e['actor']}: {e['message']}")

        st.code("\n".join(log_text_lines), language=None)

        # Export
        st.divider()
        st.subheader("💾 Export")
        c1, c2 = st.columns(2)
        with c1:
            full_log = "\n\n".join(
                f"=== GAME {i+1} | Winner: {'P1 ' + name1 if g['winner']==1 else 'P2 ' + name2 if g['winner']==2 else 'DRAW'} | Turns: {g['turns']} ===\n{g['log_text']}"
                for i, g in enumerate(res["logs"])
            )
            st.download_button(
                "📥 Download All Logs (TXT)",
                full_log.encode(),
                f"gundam_sim_logs_{n}games.txt",
                "text/plain"
            )
        with c2:
            summary = {
                "deck1": name1, "deck2": name2,
                "total_games": n,
                "p1_wins": res["p1_wins"], "p1_win_rate": f"{p1_rate:.2f}%",
                "p2_wins": res["p2_wins"], "p2_win_rate": f"{p2_rate:.2f}%",
                "draws": res["draws"],
                "avg_turns": round(avg_turns, 2),
                "min_turns": min_turns, "max_turns": max_turns,
            }
            st.download_button(
                "📥 Download Summary (JSON)",
                json.dumps(summary, indent=2).encode(),
                f"gundam_sim_summary_{n}games.json",
                "application/json"
            )

# ─────────────────────────────────────────────
#  SIDEBAR — Rules Reference
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📖 Rules Quick Reference")
    st.markdown("""
    **Deck Construction (Rule 6-1)**
    - Main deck: exactly **50 cards**
    - Resource deck: exactly **10 cards**
    - Max **4 copies** per card number
    - Max **2 colors** in main deck

    **Winning / Losing (Rule 1-2)**
    - Take battle damage with empty shield area → lose
    - Empty deck at draw step → lose

    **Turn Order (Rule 7)**
    1. Start Phase (unrest all)
    2. Draw Phase (draw 1)
    3. Resource Phase (place 1 resource)
    4. Main Phase (play cards, attack)
    5. End Phase (discard to 10)

    **Attacks (Rule 8)**
    - Rest an active Unit to attack
    - Target: player or rested enemy Unit
    - Damage resolves simultaneously (unless First Strike)

    **Keyword Effects**
    - 🛡 `<Blocker>` — intercept attacks
    - ⚡ `<First Strike>` — deal damage first
    - 💪 `<Support N>` — boost ally AP
    - 🔥 `<Breach N>` — pierce shield on kill
    - 💊 `<Repair N>` — recover HP end of turn
    - 🌀 `<High-Maneuver>` — cannot be blocked
    - 💣 `<Suppression>` — destroy 2 shields
    """)
    st.divider()
    st.caption("Gundam Card Game Comprehensive Rules Ver. 1.5.0")
    st.caption("This is a fan-made simulation tool.")
