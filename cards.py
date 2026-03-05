"""
Sample Gundam Card Database
Based on the Gundam Card Game comprehensive rules.
Covers Blue (Earth Federation), Red (Zeon), Green (AEUG/Kalaba),
White (Celestial Being), and Purple (misc/multi).

Effects dict keys:
  blocker, first_strike, support:int, breach:int, repair:int,
  high_maneuver, suppression, burst:str, deploy_draw:int,
  when_paired_draw:int, destroyed_draw:int,
  timing: "main" | "action" | "both",
  draw:int, deal_damage:int, destroy_unit:bool, rest_enemy:bool
"""

from engine import CardTemplate

# ─────────────────────────────────────────────
#  RESOURCE CARDS (10 per color for sample decks)
# ─────────────────────────────────────────────

RESOURCES = [
    CardTemplate("RES-B01", "Side 7 Colony",       "Resource", ["blue"],   0, 0, 0, 0, [], {}),
    CardTemplate("RES-B02", "Luna II Base",          "Resource", ["blue"],   0, 0, 0, 0, [], {}),
    CardTemplate("RES-B03", "White Base Hangar",     "Resource", ["blue"],   0, 0, 0, 0, [], {}),
    CardTemplate("RES-R01", "Zeon Asteroid Base",    "Resource", ["red"],    0, 0, 0, 0, [], {}),
    CardTemplate("RES-R02", "Solomon Fortress",      "Resource", ["red"],    0, 0, 0, 0, [], {}),
    CardTemplate("RES-R03", "A Baoa Qu",             "Resource", ["red"],    0, 0, 0, 0, [], {}),
    CardTemplate("RES-G01", "Argama Hangar",         "Resource", ["green"],  0, 0, 0, 0, [], {}),
    CardTemplate("RES-G02", "La Vie en Rose",        "Resource", ["green"],  0, 0, 0, 0, [], {}),
    CardTemplate("RES-G03", "Dublin Colony",         "Resource", ["green"],  0, 0, 0, 0, [], {}),
    CardTemplate("RES-W01", "Celestial Being Facility", "Resource", ["white"], 0, 0, 0, 0, [], {}),
    CardTemplate("RES-W02", "Ptolemy Hangar",        "Resource", ["white"],  0, 0, 0, 0, [], {}),
    CardTemplate("RES-W03", "Moralia Base",          "Resource", ["white"],  0, 0, 0, 0, [], {}),
    CardTemplate("RES-P01", "Neo Zeon Base",         "Resource", ["purple"], 0, 0, 0, 0, [], {}),
    CardTemplate("RES-P02", "Axis Asteroid",         "Resource", ["purple"], 0, 0, 0, 0, [], {}),
    CardTemplate("RES-P03", "Sweetwater Colony",     "Resource", ["purple"], 0, 0, 0, 0, [], {}),
]


# ─────────────────────────────────────────────
#  BLUE DECK — Earth Federation
# ─────────────────────────────────────────────

BLUE_UNITS = [
    # Lv1 Units
    CardTemplate("BLU-U01", "Ball Type-K", "Unit", ["blue"], 1, 1, 1, 2, ["Earth Federation"], {}),
    CardTemplate("BLU-U02", "RGM-79 GM", "Unit", ["blue"], 1, 1, 2, 2, ["Earth Federation"], {}),
    CardTemplate("BLU-U03", "GM Sniper", "Unit", ["blue"], 1, 1, 2, 1, ["Earth Federation"], {"first_strike": True}),

    # Lv2 Units
    CardTemplate("BLU-U04", "RX-77 Guncannon", "Unit", ["blue"], 2, 2, 3, 3, ["Earth Federation"], {"support": 1}),
    CardTemplate("BLU-U05", "RX-75 Guntank", "Unit", ["blue"], 2, 2, 2, 4, ["Earth Federation"], {"blocker": True}),
    CardTemplate("BLU-U06", "GM Command", "Unit", ["blue"], 2, 2, 3, 2, ["Earth Federation"], {"deploy_draw": 1}),

    # Lv3 Units
    CardTemplate("BLU-U07", "RX-78-2 Gundam", "Unit", ["blue"], 3, 3, 4, 4,
                 ["Earth Federation", "Gundam"], {"first_strike": True},
                 link_conditions=["Amuro Ray"]),
    CardTemplate("BLU-U08", "Guncannon Detector", "Unit", ["blue"], 3, 3, 4, 3,
                 ["Earth Federation"], {"support": 2}),
    CardTemplate("BLU-U09", "GM Cannon II", "Unit", ["blue"], 3, 3, 3, 4,
                 ["Earth Federation"], {"blocker": True, "repair": 1}),

    # Lv4 Units
    CardTemplate("BLU-U10", "RX-78 GP01 Gundam", "Unit", ["blue"], 4, 4, 5, 4,
                 ["Earth Federation", "Gundam"], {"breach": 1, "first_strike": True},
                 link_conditions=["Kou Uraki"]),
    CardTemplate("BLU-U11", "FA-78 Full Armor Gundam", "Unit", ["blue"], 4, 4, 5, 6,
                 ["Earth Federation", "Gundam"], {"blocker": True}),
    CardTemplate("BLU-U12", "RX-78-3 G-3 Gundam", "Unit", ["blue"], 4, 4, 6, 4,
                 ["Earth Federation", "Gundam"], {"high_maneuver": True}),

    # Lv5 Units
    CardTemplate("BLU-U13", "RX-93 Nu Gundam", "Unit", ["blue"], 5, 5, 6, 5,
                 ["Earth Federation", "Gundam", "Newtype Machine"], {"breach": 2, "repair": 2},
                 link_conditions=["Amuro Ray"]),
    CardTemplate("BLU-U14", "RX-93-ν2 Hi-Nu Gundam", "Unit", ["blue"], 5, 5, 7, 5,
                 ["Earth Federation", "Gundam"], {"first_strike": True, "suppression": True},
                 link_conditions=["Amuro Ray"]),

    # Lv6 Unit
    CardTemplate("BLU-U15", "RX-0 Unicorn Gundam", "Unit", ["blue"], 6, 6, 8, 6,
                 ["Earth Federation", "Gundam", "Newtype Machine"],
                 {"breach": 3, "repair": 3, "high_maneuver": True},
                 link_conditions=["Banagher Links"]),
]

BLUE_PILOTS = [
    CardTemplate("BLU-P01", "Amuro Ray", "Pilot", ["blue"], 1, 1, 0, 0,
                 ["Earth Federation", "Newtype"], {"pilot_ap": 1, "pilot_hp": 1, "when_paired_draw": 1},
                 pilot_ap=1, pilot_hp=1),
    CardTemplate("BLU-P02", "Sayla Mass", "Pilot", ["blue"], 1, 1, 0, 0,
                 ["Earth Federation"], {"pilot_ap": 0, "pilot_hp": 2},
                 pilot_ap=0, pilot_hp=2),
    CardTemplate("BLU-P03", "Kai Shiden", "Pilot", ["blue"], 2, 2, 0, 0,
                 ["Earth Federation"], {"pilot_ap": 1, "pilot_hp": 2},
                 pilot_ap=1, pilot_hp=2),
    CardTemplate("BLU-P04", "Hayato Kobayashi", "Pilot", ["blue"], 2, 2, 0, 0,
                 ["Earth Federation"], {"pilot_ap": 2, "pilot_hp": 1},
                 pilot_ap=2, pilot_hp=1),
    CardTemplate("BLU-P05", "Kou Uraki", "Pilot", ["blue"], 3, 3, 0, 0,
                 ["Earth Federation"], {"pilot_ap": 2, "pilot_hp": 2, "when_paired_draw": 1},
                 pilot_ap=2, pilot_hp=2),
    CardTemplate("BLU-P06", "Banagher Links", "Pilot", ["blue"], 4, 4, 0, 0,
                 ["Earth Federation", "Newtype"], {"pilot_ap": 2, "pilot_hp": 3},
                 pilot_ap=2, pilot_hp=3),
]

BLUE_COMMANDS = [
    CardTemplate("BLU-C01", "Minovsky Particle Scatter", "Command", ["blue"], 1, 1, 0, 0,
                 [], {"timing": "main", "rest_enemy": True}),
    CardTemplate("BLU-C02", "Beam Rifle Fire", "Command", ["blue"], 2, 2, 0, 0,
                 [], {"timing": "main", "deal_damage": 2}),
    CardTemplate("BLU-C03", "Federation Tactics", "Command", ["blue"], 3, 3, 0, 0,
                 [], {"timing": "main", "draw": 2}),
    CardTemplate("BLU-C04", "Operation V", "Command", ["blue"], 2, 2, 0, 0,
                 [], {"timing": "both", "draw": 1}),
    CardTemplate("BLU-C05", "Newtype Flash", "Command", ["blue"], 3, 3, 0, 0,
                 [], {"timing": "action", "destroy_unit": True}),
]

BLUE_BASES = [
    CardTemplate("BLU-B01", "White Base", "Base", ["blue"], 3, 3, 0, 5, ["Earth Federation"], {}),
    CardTemplate("BLU-B02", "Jaburo HQ", "Base", ["blue"], 4, 4, 0, 8, ["Earth Federation"], {}),
]


# ─────────────────────────────────────────────
#  RED DECK — Principality of Zeon
# ─────────────────────────────────────────────

RED_UNITS = [
    # Lv1
    CardTemplate("RED-U01", "Zaku I", "Unit", ["red"], 1, 1, 2, 1, ["Zeon"], {}),
    CardTemplate("RED-U02", "Zaku II", "Unit", ["red"], 1, 1, 2, 2, ["Zeon"], {}),
    CardTemplate("RED-U03", "Zaku II FS", "Unit", ["red"], 1, 1, 3, 1, ["Zeon"], {"first_strike": True}),

    # Lv2
    CardTemplate("RED-U04", "Dom", "Unit", ["red"], 2, 2, 3, 3, ["Zeon"], {"high_maneuver": True}),
    CardTemplate("RED-U05", "Gouf", "Unit", ["red"], 2, 2, 4, 2, ["Zeon"], {"first_strike": True}),
    CardTemplate("RED-U06", "Rick Dom", "Unit", ["red"], 2, 2, 3, 3, ["Zeon"], {"support": 1}),

    # Lv3
    CardTemplate("RED-U07", "MS-14A Gelgoog", "Unit", ["red"], 3, 3, 4, 4,
                 ["Zeon"], {"breach": 1},
                 link_conditions=["Char Aznable"]),
    CardTemplate("RED-U08", "MSM-07 Z'Gok", "Unit", ["red"], 3, 3, 4, 5,
                 ["Zeon"], {"blocker": True}),
    CardTemplate("RED-U09", "MA-05 Bigro", "Unit", ["red"], 3, 3, 5, 3,
                 ["Zeon"], {"high_maneuver": True}),

    # Lv4
    CardTemplate("RED-U10", "MS-14S Gelgoog Commander", "Unit", ["red"], 4, 4, 5, 5,
                 ["Zeon"], {"first_strike": True, "breach": 1},
                 link_conditions=["Char Aznable"]),
    CardTemplate("RED-U11", "MA-08 Big Zam", "Unit", ["red"], 4, 4, 4, 8,
                 ["Zeon"], {"blocker": True, "suppression": True}),
    CardTemplate("RED-U12", "MSN-02 Zeong", "Unit", ["red"], 4, 4, 6, 4,
                 ["Zeon"], {"breach": 2}),

    # Lv5
    CardTemplate("RED-U13", "MSN-04 Sazabi", "Unit", ["red"], 5, 5, 7, 5,
                 ["Zeon", "Neo Zeon"], {"first_strike": True, "repair": 2},
                 link_conditions=["Char Aznable"]),
    CardTemplate("RED-U14", "NZ-333 Alpha Azieru", "Unit", ["red"], 5, 5, 6, 7,
                 ["Neo Zeon"], {"blocker": True, "breach": 2}),

    # Lv6
    CardTemplate("RED-U15", "MSN-04II Nightingale", "Unit", ["red"], 6, 6, 9, 6,
                 ["Neo Zeon"], {"first_strike": True, "breach": 3, "suppression": True},
                 link_conditions=["Char Aznable"]),
]

RED_PILOTS = [
    CardTemplate("RED-P01", "Char Aznable", "Pilot", ["red"], 1, 1, 0, 0,
                 ["Zeon", "Ace"], {"pilot_ap": 2, "pilot_hp": 1, "when_paired_draw": 1},
                 pilot_ap=2, pilot_hp=1),
    CardTemplate("RED-P02", "Ramba Ral", "Pilot", ["red"], 1, 1, 0, 0,
                 ["Zeon"], {"pilot_ap": 1, "pilot_hp": 2},
                 pilot_ap=1, pilot_hp=2),
    CardTemplate("RED-P03", "Norris Packard", "Pilot", ["red"], 2, 2, 0, 0,
                 ["Zeon"], {"pilot_ap": 2, "pilot_hp": 1},
                 pilot_ap=2, pilot_hp=1),
    CardTemplate("RED-P04", "Johnny Ridden", "Pilot", ["red"], 2, 2, 0, 0,
                 ["Zeon", "Ace"], {"pilot_ap": 2, "pilot_hp": 2},
                 pilot_ap=2, pilot_hp=2),
    CardTemplate("RED-P05", "M'Quve", "Pilot", ["red"], 3, 3, 0, 0,
                 ["Zeon"], {"pilot_ap": 1, "pilot_hp": 3},
                 pilot_ap=1, pilot_hp=3),
    CardTemplate("RED-P06", "Haman Karn", "Pilot", ["red"], 4, 4, 0, 0,
                 ["Neo Zeon", "Newtype"], {"pilot_ap": 3, "pilot_hp": 2},
                 pilot_ap=3, pilot_hp=2),
]

RED_COMMANDS = [
    CardTemplate("RED-C01", "Zeon Ambush", "Command", ["red"], 1, 1, 0, 0,
                 [], {"timing": "action", "draw": 1}),
    CardTemplate("RED-C02", "Heat Hawk Strike", "Command", ["red"], 2, 2, 0, 0,
                 [], {"timing": "main", "deal_damage": 2}),
    CardTemplate("RED-C03", "Zeon Strategy", "Command", ["red"], 3, 3, 0, 0,
                 [], {"timing": "main", "draw": 2}),
    CardTemplate("RED-C04", "I'll Return", "Command", ["red"], 2, 2, 0, 0,
                 [], {"timing": "both", "draw": 1}),
    CardTemplate("RED-C05", "Degwin's Decree", "Command", ["red"], 3, 3, 0, 0,
                 [], {"timing": "main", "destroy_unit": True}),
]

RED_BASES = [
    CardTemplate("RED-B01", "Zeon Submarine Base", "Base", ["red"], 3, 3, 0, 5, ["Zeon"], {}),
    CardTemplate("RED-B02", "Zeon Space Fortress", "Base", ["red"], 4, 4, 2, 7, ["Zeon"], {}),
]


# ─────────────────────────────────────────────
#  GREEN DECK — AEUG / Kalaba
# ─────────────────────────────────────────────

GREEN_UNITS = [
    CardTemplate("GRN-U01", "RMS-179 GM II", "Unit", ["green"], 1, 1, 2, 2, ["AEUG"], {}),
    CardTemplate("GRN-U02", "RGM-86R GM III", "Unit", ["green"], 1, 1, 3, 1, ["AEUG"], {"first_strike": True}),
    CardTemplate("GRN-U03", "MSA-003 Nemo", "Unit", ["green"], 2, 2, 3, 3, ["AEUG"], {"support": 1}),
    CardTemplate("GRN-U04", "MSA-005 Methuss", "Unit", ["green"], 2, 2, 2, 3, ["AEUG"], {"repair": 2, "blocker": True}),
    CardTemplate("GRN-U05", "RX-178 Gundam Mk-II", "Unit", ["green"], 3, 3, 4, 4,
                 ["AEUG", "Gundam"], {"deploy_draw": 1},
                 link_conditions=["Kamille Bidan"]),
    CardTemplate("GRN-U06", "MSZ-006 Zeta Gundam", "Unit", ["green"], 4, 4, 6, 4,
                 ["AEUG", "Gundam"], {"high_maneuver": True, "breach": 1},
                 link_conditions=["Kamille Bidan"]),
    CardTemplate("GRN-U07", "MSZ-010 ZZ Gundam", "Unit", ["green"], 5, 5, 8, 5,
                 ["AEUG", "Gundam"], {"suppression": True, "breach": 2},
                 link_conditions=["Judau Ashta"]),
    CardTemplate("GRN-U08", "MSN-00100 Hyaku Shiki", "Unit", ["green"], 3, 3, 5, 3,
                 ["AEUG"], {"first_strike": True},
                 link_conditions=["Quattro Bajeena"]),
    CardTemplate("GRN-U09", "AMX-004 Qubeley", "Unit", ["green"], 4, 4, 5, 6,
                 ["Neo Zeon"], {"repair": 1, "breach": 1}),
]

GREEN_PILOTS = [
    CardTemplate("GRN-P01", "Kamille Bidan", "Pilot", ["green"], 2, 2, 0, 0,
                 ["AEUG", "Newtype"], {"pilot_ap": 2, "pilot_hp": 1, "when_paired_draw": 1},
                 pilot_ap=2, pilot_hp=1),
    CardTemplate("GRN-P02", "Quattro Bajeena", "Pilot", ["green"], 2, 2, 0, 0,
                 ["AEUG"], {"pilot_ap": 2, "pilot_hp": 2},
                 pilot_ap=2, pilot_hp=2),
    CardTemplate("GRN-P03", "Judau Ashta", "Pilot", ["green"], 3, 3, 0, 0,
                 ["AEUG", "Newtype"], {"pilot_ap": 2, "pilot_hp": 3},
                 pilot_ap=2, pilot_hp=3),
    CardTemplate("GRN-P04", "Emma Sheen", "Pilot", ["green"], 2, 2, 0, 0,
                 ["AEUG"], {"pilot_ap": 1, "pilot_hp": 2},
                 pilot_ap=1, pilot_hp=2),
]

GREEN_COMMANDS = [
    CardTemplate("GRN-C01", "AEUG Intel", "Command", ["green"], 1, 1, 0, 0,
                 [], {"timing": "main", "draw": 2}),
    CardTemplate("GRN-C02", "Biosensor Awakening", "Command", ["green"], 2, 2, 0, 0,
                 [], {"timing": "action", "deal_damage": 3}),
    CardTemplate("GRN-C03", "Gryps Assault", "Command", ["green"], 3, 3, 0, 0,
                 [], {"timing": "main", "destroy_unit": True}),
]

GREEN_BASES = [
    CardTemplate("GRN-B01", "Argama", "Base", ["green"], 3, 3, 0, 6, ["AEUG"], {}),
]


# ─────────────────────────────────────────────
#  WHITE DECK — Celestial Being / 00 Gundam
# ─────────────────────────────────────────────

WHITE_UNITS = [
    CardTemplate("WHT-U01", "GN-001 Gundam Exia", "Unit", ["white"], 2, 2, 4, 3,
                 ["Celestial Being", "Gundam"], {"first_strike": True},
                 link_conditions=["Setsuna F. Seiei"]),
    CardTemplate("WHT-U02", "GN-002 Gundam Dynames", "Unit", ["white"], 2, 2, 3, 3,
                 ["Celestial Being", "Gundam"], {"support": 2},
                 link_conditions=["Lockon Stratos"]),
    CardTemplate("WHT-U03", "GN-003 Gundam Kyrios", "Unit", ["white"], 2, 2, 4, 2,
                 ["Celestial Being", "Gundam"], {"high_maneuver": True},
                 link_conditions=["Allelujah Haptism"]),
    CardTemplate("WHT-U04", "GN-005 Gundam Virtue", "Unit", ["white"], 3, 3, 3, 6,
                 ["Celestial Being", "Gundam"], {"blocker": True, "repair": 2},
                 link_conditions=["Tieria Erde"]),
    CardTemplate("WHT-U05", "GN-0000 00 Gundam", "Unit", ["white"], 4, 4, 6, 5,
                 ["Celestial Being", "Gundam"], {"breach": 2},
                 link_conditions=["Setsuna F. Seiei"]),
    CardTemplate("WHT-U06", "GN-0000+GNR-010 00 Raiser", "Unit", ["white"], 5, 5, 8, 5,
                 ["Celestial Being", "Gundam"], {"breach": 3, "high_maneuver": True},
                 link_conditions=["Setsuna F. Seiei"]),
    CardTemplate("WHT-U07", "CB-002 Raphael Gundam", "Unit", ["white"], 4, 4, 5, 6,
                 ["Celestial Being", "Gundam"], {"blocker": True, "repair": 2}),
    CardTemplate("WHT-U08", "GNX-704T Ahead", "Unit", ["white"], 2, 2, 3, 2,
                 ["Earth Sphere"], {}),
]

WHITE_PILOTS = [
    CardTemplate("WHT-P01", "Setsuna F. Seiei", "Pilot", ["white"], 2, 2, 0, 0,
                 ["Celestial Being"], {"pilot_ap": 2, "pilot_hp": 2, "when_paired_draw": 1},
                 pilot_ap=2, pilot_hp=2),
    CardTemplate("WHT-P02", "Lockon Stratos", "Pilot", ["white"], 2, 2, 0, 0,
                 ["Celestial Being"], {"pilot_ap": 1, "pilot_hp": 2},
                 pilot_ap=1, pilot_hp=2),
    CardTemplate("WHT-P03", "Tieria Erde", "Pilot", ["white"], 2, 2, 0, 0,
                 ["Celestial Being"], {"pilot_ap": 0, "pilot_hp": 3},
                 pilot_ap=0, pilot_hp=3),
    CardTemplate("WHT-P04", "Allelujah Haptism", "Pilot", ["white"], 2, 2, 0, 0,
                 ["Celestial Being"], {"pilot_ap": 2, "pilot_hp": 1},
                 pilot_ap=2, pilot_hp=1),
]

WHITE_COMMANDS = [
    CardTemplate("WHT-C01", "GN Particle Burst", "Command", ["white"], 2, 2, 0, 0,
                 [], {"timing": "main", "deal_damage": 2}),
    CardTemplate("WHT-C02", "Tactical Forecast", "Command", ["white"], 1, 1, 0, 0,
                 [], {"timing": "both", "draw": 1}),
    CardTemplate("WHT-C03", "Armed Intervention", "Command", ["white"], 3, 3, 0, 0,
                 [], {"timing": "main", "draw": 2}),
]

WHITE_BASES = [
    CardTemplate("WHT-B01", "Ptolemaios", "Base", ["white"], 3, 3, 0, 6, ["Celestial Being"], {}),
]


# ─────────────────────────────────────────────
#  PURPLE DECK — Mixed / Neo Zeon
# ─────────────────────────────────────────────

PURPLE_UNITS = [
    CardTemplate("PUR-U01", "AMS-119 Geara Doga", "Unit", ["purple"], 1, 1, 2, 2, ["Neo Zeon"], {}),
    CardTemplate("PUR-U02", "AMS-120X Geara Doga Psycommu", "Unit", ["purple"], 2, 2, 3, 3,
                 ["Neo Zeon"], {"breach": 1}),
    CardTemplate("PUR-U03", "MSN-03 Jagd Doga", "Unit", ["purple"], 3, 3, 5, 4,
                 ["Neo Zeon"], {"first_strike": True},
                 link_conditions=["Rezin Schnyder"]),
    CardTemplate("PUR-U04", "NZ-000 Queen Mansa", "Unit", ["purple"], 5, 5, 7, 7,
                 ["Neo Zeon"], {"blocker": True, "repair": 2, "suppression": True}),
    CardTemplate("PUR-U05", "AMX-107 Bawoo", "Unit", ["purple"], 3, 3, 4, 4,
                 ["Neo Zeon"], {"high_maneuver": True}),
    CardTemplate("PUR-U06", "RX-0 Unicorn Gundam 02 Banshee", "Unit", ["purple"], 6, 6, 8, 7,
                 ["Earth Federation", "Gundam"], {"first_strike": True, "breach": 2},
                 link_conditions=["Marida Cruz"]),
]

PURPLE_PILOTS = [
    CardTemplate("PUR-P01", "Rezin Schnyder", "Pilot", ["purple"], 2, 2, 0, 0,
                 ["Neo Zeon"], {"pilot_ap": 2, "pilot_hp": 2},
                 pilot_ap=2, pilot_hp=2),
    CardTemplate("PUR-P02", "Marida Cruz", "Pilot", ["purple"], 3, 3, 0, 0,
                 ["Neo Zeon", "Newtype"], {"pilot_ap": 2, "pilot_hp": 3, "when_paired_draw": 1},
                 pilot_ap=2, pilot_hp=3),
]

PURPLE_COMMANDS = [
    CardTemplate("PUR-C01", "Axis Drop", "Command", ["purple"], 3, 3, 0, 0,
                 [], {"timing": "main", "destroy_unit": True}),
    CardTemplate("PUR-C02", "Psychoframe Resonance", "Command", ["purple"], 2, 2, 0, 0,
                 [], {"timing": "action", "draw": 2}),
]

PURPLE_BASES = [
    CardTemplate("PUR-B01", "Axis Asteroid Base", "Base", ["purple"], 4, 4, 0, 8, ["Neo Zeon"], {}),
]


# ─────────────────────────────────────────────
#  CARD CATALOG (all cards)
# ─────────────────────────────────────────────

ALL_CARDS: list[CardTemplate] = (
    RESOURCES +
    BLUE_UNITS + BLUE_PILOTS + BLUE_COMMANDS + BLUE_BASES +
    RED_UNITS + RED_PILOTS + RED_COMMANDS + RED_BASES +
    GREEN_UNITS + GREEN_PILOTS + GREEN_COMMANDS + GREEN_BASES +
    WHITE_UNITS + WHITE_PILOTS + WHITE_COMMANDS + WHITE_BASES +
    PURPLE_UNITS + PURPLE_PILOTS + PURPLE_COMMANDS + PURPLE_BASES
)

CARD_LOOKUP: dict[str, CardTemplate] = {c.card_number: c for c in ALL_CARDS}
CARD_NAME_LOOKUP: dict[str, CardTemplate] = {c.card_name: c for c in ALL_CARDS}


# ─────────────────────────────────────────────
#  PRESET DECKS
# ─────────────────────────────────────────────

def build_preset_blue_deck():
    """Balanced Earth Federation deck."""
    main = []
    # Low-cost backbone
    main += [CARD_LOOKUP["BLU-U01"]] * 2
    main += [CARD_LOOKUP["BLU-U02"]] * 4
    main += [CARD_LOOKUP["BLU-U03"]] * 3
    main += [CARD_LOOKUP["BLU-U04"]] * 4
    main += [CARD_LOOKUP["BLU-U05"]] * 3
    main += [CARD_LOOKUP["BLU-U06"]] * 4
    # Mid-range
    main += [CARD_LOOKUP["BLU-U07"]] * 4
    main += [CARD_LOOKUP["BLU-U08"]] * 3
    main += [CARD_LOOKUP["BLU-U09"]] * 2
    # High-cost finishers
    main += [CARD_LOOKUP["BLU-U10"]] * 2
    main += [CARD_LOOKUP["BLU-U11"]] * 2
    main += [CARD_LOOKUP["BLU-U13"]] * 2
    main += [CARD_LOOKUP["BLU-U14"]] * 1
    # Pilots
    main += [CARD_LOOKUP["BLU-P01"]] * 4
    main += [CARD_LOOKUP["BLU-P02"]] * 2
    main += [CARD_LOOKUP["BLU-P03"]] * 2
    main += [CARD_LOOKUP["BLU-P05"]] * 2
    # Commands
    main += [CARD_LOOKUP["BLU-C01"]] * 2
    main += [CARD_LOOKUP["BLU-C02"]] * 2
    main += [CARD_LOOKUP["BLU-C03"]] * 1
    main += [CARD_LOOKUP["BLU-C04"]] * 2
    # Base
    main += [CARD_LOOKUP["BLU-B01"]] * 1

    resource = [CARD_LOOKUP["RES-B01"]] * 4 + [CARD_LOOKUP["RES-B02"]] * 3 + [CARD_LOOKUP["RES-B03"]] * 3
    return main[:50], resource[:10]


def build_preset_red_deck():
    """Aggressive Zeon deck."""
    main = []
    main += [CARD_LOOKUP["RED-U01"]] * 2
    main += [CARD_LOOKUP["RED-U02"]] * 4
    main += [CARD_LOOKUP["RED-U03"]] * 3
    main += [CARD_LOOKUP["RED-U04"]] * 4
    main += [CARD_LOOKUP["RED-U05"]] * 4
    main += [CARD_LOOKUP["RED-U06"]] * 3
    main += [CARD_LOOKUP["RED-U07"]] * 4
    main += [CARD_LOOKUP["RED-U08"]] * 2
    main += [CARD_LOOKUP["RED-U09"]] * 2
    main += [CARD_LOOKUP["RED-U10"]] * 3
    main += [CARD_LOOKUP["RED-U12"]] * 2
    main += [CARD_LOOKUP["RED-U13"]] * 2
    main += [CARD_LOOKUP["RED-U14"]] * 1
    main += [CARD_LOOKUP["RED-P01"]] * 4
    main += [CARD_LOOKUP["RED-P02"]] * 2
    main += [CARD_LOOKUP["RED-P04"]] * 2
    main += [CARD_LOOKUP["RED-P06"]] * 1
    main += [CARD_LOOKUP["RED-C01"]] * 2
    main += [CARD_LOOKUP["RED-C02"]] * 2
    main += [CARD_LOOKUP["RED-C04"]] * 2
    main += [CARD_LOOKUP["RED-B01"]] * 1

    resource = [CARD_LOOKUP["RES-R01"]] * 4 + [CARD_LOOKUP["RES-R02"]] * 3 + [CARD_LOOKUP["RES-R03"]] * 3
    return main[:50], resource[:10]


def build_preset_green_deck():
    """AEUG control/repair deck."""
    main = []
    main += [CARD_LOOKUP["GRN-U01"]] * 3
    main += [CARD_LOOKUP["GRN-U02"]] * 3
    main += [CARD_LOOKUP["GRN-U03"]] * 4
    main += [CARD_LOOKUP["GRN-U04"]] * 4
    main += [CARD_LOOKUP["GRN-U05"]] * 4
    main += [CARD_LOOKUP["GRN-U06"]] * 3
    main += [CARD_LOOKUP["GRN-U07"]] * 2
    main += [CARD_LOOKUP["GRN-U08"]] * 3
    main += [CARD_LOOKUP["GRN-U09"]] * 2
    main += [CARD_LOOKUP["GRN-P01"]] * 4
    main += [CARD_LOOKUP["GRN-P02"]] * 3
    main += [CARD_LOOKUP["GRN-P03"]] * 2
    main += [CARD_LOOKUP["GRN-P04"]] * 3
    main += [CARD_LOOKUP["GRN-C01"]] * 3
    main += [CARD_LOOKUP["GRN-C02"]] * 2
    main += [CARD_LOOKUP["GRN-C03"]] * 2
    main += [CARD_LOOKUP["GRN-B01"]] * 1

    resource = [CARD_LOOKUP["RES-G01"]] * 4 + [CARD_LOOKUP["RES-G02"]] * 3 + [CARD_LOOKUP["RES-G03"]] * 3
    return main[:50], resource[:10]


def build_preset_white_deck():
    """Celestial Being aggro deck."""
    main = []
    main += [CARD_LOOKUP["WHT-U01"]] * 4
    main += [CARD_LOOKUP["WHT-U02"]] * 4
    main += [CARD_LOOKUP["WHT-U03"]] * 4
    main += [CARD_LOOKUP["WHT-U04"]] * 4
    main += [CARD_LOOKUP["WHT-U05"]] * 3
    main += [CARD_LOOKUP["WHT-U06"]] * 2
    main += [CARD_LOOKUP["WHT-U07"]] * 2
    main += [CARD_LOOKUP["WHT-U08"]] * 2
    main += [CARD_LOOKUP["WHT-P01"]] * 4
    main += [CARD_LOOKUP["WHT-P02"]] * 4
    main += [CARD_LOOKUP["WHT-P03"]] * 3
    main += [CARD_LOOKUP["WHT-P04"]] * 3
    main += [CARD_LOOKUP["WHT-C01"]] * 3
    main += [CARD_LOOKUP["WHT-C02"]] * 4
    main += [CARD_LOOKUP["WHT-C03"]] * 2
    main += [CARD_LOOKUP["WHT-B01"]] * 1

    resource = [CARD_LOOKUP["RES-W01"]] * 4 + [CARD_LOOKUP["RES-W02"]] * 3 + [CARD_LOOKUP["RES-W03"]] * 3
    return main[:50], resource[:10]


PRESET_DECKS = {
    "Earth Federation (Blue)": build_preset_blue_deck,
    "Principality of Zeon (Red)": build_preset_red_deck,
    "AEUG / Kalaba (Green)": build_preset_green_deck,
    "Celestial Being (White)": build_preset_white_deck,
}
