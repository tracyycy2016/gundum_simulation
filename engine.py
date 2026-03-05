"""
Gundam Card Game Simulation Engine
Follows Comprehensive Rules Ver. 1.5.0
"""
import random
import copy
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any

# ─────────────────────────────────────────────
#  DATA MODELS
# ─────────────────────────────────────────────

@dataclass
class CardTemplate:
    card_number: str
    card_name: str
    card_type: str          # Unit | Pilot | Command | Base | Resource
    colors: List[str]       # blue | green | red | white | purple
    lv: int                 # level requirement
    cost: int               # resource cost
    ap: int                 # attack points (0 if N/A)
    hp: int                 # hit points (0 if N/A)
    traits: List[str]       # faction/type traits
    effects: Dict[str, Any] # effect tags -> values
    link_conditions: List[str] = field(default_factory=list)  # pilot names/traits for linking
    pilot_name: str = ""    # secondary name if Command+Pilot card
    pilot_traits: List[str] = field(default_factory=list)
    pilot_ap: int = 0
    pilot_hp: int = 0

    def __hash__(self):
        return hash(self.card_number + self.card_name)

    def __eq__(self, other):
        return isinstance(other, CardTemplate) and self.card_number == other.card_number


@dataclass
class UnitInPlay:
    template: CardTemplate
    is_rested: bool = False
    damage: int = 0
    paired_pilot: Optional[CardTemplate] = None
    deployed_this_turn: bool = True  # cannot attack unless link unit

    @property
    def effective_ap(self) -> int:
        ap = self.template.ap
        if self.paired_pilot:
            ap += self.paired_pilot.pilot_ap if self.paired_pilot.pilot_ap else self.paired_pilot.ap
        return max(0, ap)

    @property
    def effective_hp(self) -> int:
        hp = self.template.hp
        if self.paired_pilot:
            hp += self.paired_pilot.pilot_hp if self.paired_pilot.pilot_hp else self.paired_pilot.hp
        return max(0, hp)

    @property
    def current_hp(self) -> int:
        return self.effective_hp - self.damage

    @property
    def is_link_unit(self) -> bool:
        if not self.template.link_conditions or not self.paired_pilot:
            return False
        pilot_name = self.paired_pilot.card_name.lower()
        for cond in self.template.link_conditions:
            if cond.lower() in pilot_name:
                return True
        return False

    def has_effect(self, effect_name: str) -> bool:
        return effect_name in self.template.effects

    def get_effect_val(self, effect_name: str, default=0):
        return self.template.effects.get(effect_name, default)

    def can_attack(self) -> bool:
        if self.is_rested:
            return False
        if self.deployed_this_turn and not self.is_link_unit:
            return False
        return True


@dataclass
class BaseInPlay:
    template: CardTemplate
    damage: int = 0
    is_rested: bool = False

    @property
    def effective_ap(self) -> int:
        return self.template.ap

    @property
    def effective_hp(self) -> int:
        return self.template.hp

    @property
    def current_hp(self) -> int:
        return self.effective_hp - self.damage


@dataclass
class PlayerState:
    player_num: int
    deck: List[CardTemplate]
    hand: List[CardTemplate]
    battle_area: List[UnitInPlay]
    shield_section: List[CardTemplate]   # face down stack, [0]=top
    base: Optional[BaseInPlay]            # None = EX Base already placed
    resource_area: List[Tuple[CardTemplate, bool]]  # (card, is_active)
    resource_deck: List[CardTemplate]
    trash: List[CardTemplate]
    removal: List[CardTemplate]
    ex_base_hp: int = 3                  # EX Base hp (tracks damage)
    ex_base_destroyed: bool = False
    ex_resource_active: bool = False     # Player 2 only

    @property
    def active_resource_count(self) -> int:
        return sum(1 for _, active in self.resource_area if active)

    @property
    def total_resource_count(self) -> int:
        return len(self.resource_area)

    @property
    def has_shield_or_base(self) -> bool:
        return bool(self.shield_section) or (not self.ex_base_destroyed and self.base is None) or (self.base is not None)

    @property
    def effective_base_hp(self) -> int:
        if self.base:
            return self.base.current_hp
        if not self.ex_base_destroyed:
            return 3 - self.ex_base_damage
        return 0

    # EX base damage tracking
    _ex_base_damage: int = field(default=0, init=False, repr=False)

    @property
    def ex_base_damage(self) -> int:
        return self._ex_base_damage

    def deal_ex_base_damage(self, amount: int) -> bool:
        """Returns True if EX Base destroyed."""
        self._ex_base_damage += amount
        if self._ex_base_damage >= 3:
            self.ex_base_destroyed = True
            return True
        return False

    def has_base(self) -> bool:
        return (self.base is not None) or (not self.ex_base_destroyed)

    def base_hp_remaining(self) -> int:
        if self.base:
            return self.base.current_hp
        if not self.ex_base_destroyed:
            return 3 - self._ex_base_damage
        return 0

    def base_ap(self) -> int:
        if self.base:
            return self.base.effective_ap
        return 0  # EX Base has 0 AP

    def rest_resources_for_cost(self, cost: int) -> bool:
        """Rest active resources to pay cost. Returns False if not enough."""
        active = [(i, card) for i, (card, active) in enumerate(self.resource_area) if active]
        if self.ex_resource_active:
            active_count = len(active) + 1
        else:
            active_count = len(active)
        if active_count < cost:
            return False
        paid = 0
        # First use EX resource if available (it gets removed on use)
        if self.ex_resource_active and paid < cost:
            self.ex_resource_active = False
            paid += 1
        for i, _ in active:
            if paid >= cost:
                break
            self.resource_area[i] = (self.resource_area[i][0], False)
            paid += 1
        return True

    def can_afford(self, card: CardTemplate) -> bool:
        """Check level + cost requirements."""
        if self.total_resource_count < card.lv:
            return False
        active_count = self.active_resource_count + (1 if self.ex_resource_active else 0)
        return active_count >= card.cost


# ─────────────────────────────────────────────
#  DECK VALIDATION
# ─────────────────────────────────────────────

def validate_deck(
    main_deck: List[CardTemplate],
    resource_deck: List[CardTemplate],
    deck_name: str = "Deck"
) -> Tuple[bool, List[str]]:
    """Returns (is_valid, list_of_errors)."""
    errors = []

    # Rule 6-1-1: exactly 50 main, 10 resource
    if len(main_deck) != 50:
        errors.append(f"[{deck_name}] Main deck must be exactly 50 cards (currently {len(main_deck)}).")
    if len(resource_deck) != 10:
        errors.append(f"[{deck_name}] Resource deck must be exactly 10 cards (currently {len(resource_deck)}).")

    # Rule 6-1-1-1: main deck types
    valid_main_types = {"Unit", "Pilot", "Command", "Base"}
    for card in main_deck:
        if card.card_type not in valid_main_types:
            errors.append(f"[{deck_name}] Card '{card.card_name}' (type={card.card_type}) is not allowed in main deck.")

    # Rule 6-1-1-4: resource deck only Resource type
    for card in resource_deck:
        if card.card_type != "Resource":
            errors.append(f"[{deck_name}] Card '{card.card_name}' is not a Resource card and cannot be in resource deck.")

    # Rule 6-1-1-2: 1 or 2 colors in main deck
    all_colors = set()
    for card in main_deck:
        all_colors.update(card.colors)
    if len(all_colors) > 2:
        errors.append(f"[{deck_name}] Deck uses {len(all_colors)} colors ({', '.join(sorted(all_colors))}). Maximum is 2 colors.")

    # Rule 6-1-1-3: max 4 copies per card number
    from collections import Counter
    counts = Counter(c.card_number for c in main_deck)
    for card_num, count in counts.items():
        if count > 4:
            card_names = [c.card_name for c in main_deck if c.card_number == card_num]
            errors.append(f"[{deck_name}] Card '{card_names[0]}' ({card_num}) appears {count} times. Maximum is 4 copies.")

    return len(errors) == 0, errors


# ─────────────────────────────────────────────
#  GAME LOG
# ─────────────────────────────────────────────

class GameLog:
    def __init__(self):
        self.entries: List[Dict] = []
        self.turn = 0
        self.phase = ""

    def log(self, msg: str, actor: int = 0, event_type: str = "action"):
        self.entries.append({
            "turn": self.turn,
            "phase": self.phase,
            "actor": f"P{actor}" if actor else "SYSTEM",
            "type": event_type,
            "message": msg
        })

    def set_context(self, turn: int, phase: str):
        self.turn = turn
        self.phase = phase

    def to_text(self) -> str:
        lines = []
        prev_turn = None
        for e in self.entries:
            if e["turn"] != prev_turn:
                lines.append(f"\n{'='*60}")
                lines.append(f"  TURN {e['turn']}")
                lines.append(f"{'='*60}")
                prev_turn = e["turn"]
            actor = e["actor"]
            lines.append(f"  [{e['phase']:15s}] {actor}: {e['message']}")
        return "\n".join(lines)


# ─────────────────────────────────────────────
#  GAME ENGINE
# ─────────────────────────────────────────────

MAX_TURNS = 50  # Safety limit

class GameEngine:

    def __init__(self, deck1: List[CardTemplate], rdeck1: List[CardTemplate],
                 deck2: List[CardTemplate], rdeck2: List[CardTemplate],
                 deck1_name: str = "Deck 1", deck2_name: str = "Deck 2"):
        self.deck1_name = deck1_name
        self.deck2_name = deck2_name
        self.log = GameLog()
        self.p = [None, None, None]  # 1-indexed
        self._init_players(deck1, rdeck1, deck2, rdeck2)

    def _init_players(self, d1, rd1, d2, rd2):
        for pnum, (deck, rdeck) in enumerate([(d1, rd1), (d2, rd2)], 1):
            d = copy.deepcopy(deck)
            r = copy.deepcopy(rdeck)
            random.shuffle(d)
            # Draw 5 cards
            hand = d[:5]
            remaining = d[5:]
            # Shields: top 6 of remaining
            shields = remaining[:6]
            deck_left = remaining[6:]
            ps = PlayerState(
                player_num=pnum,
                deck=deck_left,
                hand=hand,
                battle_area=[],
                shield_section=shields,
                base=None,
                resource_area=[],
                resource_deck=r,
                trash=[],
                removal=[],
            )
            ps._ex_base_damage = 0
            if pnum == 2:
                ps.ex_resource_active = True
            self.p[pnum] = ps

    def run(self) -> Dict:
        """Run a complete game. Returns result dict."""
        self.log.set_context(0, "SETUP")
        self.log.log(f"Game Start: {self.deck1_name} (P1) vs {self.deck2_name} (P2)", event_type="system")
        self.log.log(f"P1 shield count: {len(self.p[1].shield_section)}, P2 shield count: {len(self.p[2].shield_section)}", event_type="system")

        # Optional mulligan (AI logic: redraw if avg cost > resources)
        for pnum in [1, 2]:
            self._maybe_mulligan(pnum)

        active = 1
        turn_num = 0

        while True:
            turn_num += 1
            if turn_num > MAX_TURNS:
                self.log.set_context(turn_num, "END")
                self.log.log("Turn limit reached — declaring draw.", event_type="system")
                return self._result(None, turn_num)

            result = self._run_turn(active, turn_num)
            if result is not None:
                return self._result(result, turn_num)

            active = 3 - active  # Toggle 1↔2

    def _result(self, winner: Optional[int], turns: int) -> Dict:
        name_map = {1: self.deck1_name, 2: self.deck2_name}
        return {
            "winner": winner,
            "winner_name": name_map.get(winner, "Draw"),
            "turns": turns,
            "log_text": self.log.to_text(),
            "log_entries": self.log.entries,
            "final_state": {
                "p1_shields": len(self.p[1].shield_section),
                "p2_shields": len(self.p[2].shield_section),
                "p1_hand": len(self.p[1].hand),
                "p2_hand": len(self.p[2].hand),
                "p1_units": len(self.p[1].battle_area),
                "p2_units": len(self.p[2].battle_area),
            }
        }

    def _maybe_mulligan(self, pnum: int):
        ps = self.p[pnum]
        hand = ps.hand
        if not hand:
            return
        avg_lv = sum(c.lv for c in hand) / len(hand)
        # Redraw if average level > 3 (too many high cost cards early)
        if avg_lv > 3.2:
            self.log.set_context(0, "MULLIGAN")
            self.log.log(f"P{pnum} redraws (avg lv={avg_lv:.1f})", pnum)
            ps.deck.extend(ps.hand)
            random.shuffle(ps.deck)
            ps.hand = ps.deck[:5]
            ps.deck = ps.deck[5:]

    def _run_turn(self, active: int, turn_num: int) -> Optional[int]:
        """Run one player's full turn. Returns winning player or None."""
        self.log.set_context(turn_num, "START")
        standby = 3 - active
        ps = self.p[active]
        self.log.log(f"--- P{active}'s Turn {turn_num} ---", event_type="turn_start")

        # ── START PHASE ──
        # Active step: unrest all
        self.log.set_context(turn_num, "ACTIVE_STEP")
        self._active_step(active)

        # ── DRAW PHASE ──
        self.log.set_context(turn_num, "DRAW")
        if not ps.deck:
            self.log.log(f"P{active} has no cards in deck — defeated!", active, "defeat")
            return standby
        drawn = ps.deck.pop(0)
        ps.hand.append(drawn)
        self.log.log(f"P{active} draws '{drawn.card_name}'", active)

        # ── RESOURCE PHASE ──
        self.log.set_context(turn_num, "RESOURCE")
        if ps.resource_deck:
            res = ps.resource_deck.pop(0)
            ps.resource_area.append((res, True))
            self.log.log(f"P{active} places resource '{res.card_name}' (total: {len(ps.resource_area)})", active)

        # ── MAIN PHASE ──
        self.log.set_context(turn_num, "MAIN")
        # Mark existing units as no longer freshly deployed
        for unit in ps.battle_area:
            unit.deployed_this_turn = False

        # Play cards: greedy AI
        self._ai_play_cards(active)

        # Attack phase within main
        result = self._ai_attack(active, turn_num)
        if result is not None:
            return result

        # ── END PHASE ──
        self.log.set_context(turn_num, "END")
        # Repair effects
        for unit in ps.battle_area:
            if "repair" in unit.template.effects:
                amt = unit.template.effects["repair"]
                healed = min(amt, unit.damage)
                unit.damage -= healed
                if healed > 0:
                    self.log.log(f"P{active} {unit.template.card_name} repairs {healed} HP", active)

        # Hand limit: discard to 10
        while len(ps.hand) > 10:
            discarded = ps.hand.pop(0)
            ps.trash.append(discarded)
            self.log.log(f"P{active} discards '{discarded.card_name}' (hand limit)", active)

        return None

    def _active_step(self, pnum: int):
        ps = self.p[pnum]
        unrest_count = 0
        for unit in ps.battle_area:
            if unit.is_rested:
                unit.is_rested = False
                unrest_count += 1
        ps.resource_area = [(c, True) for c, _ in ps.resource_area]
        if ps.base and ps.base.is_rested:
            ps.base.is_rested = False
        if unrest_count > 0:
            self.log.log(f"P{pnum} unrests {unrest_count} unit(s) and all resources", pnum)

    # ── AI LOGIC ──

    def _ai_play_cards(self, pnum: int):
        ps = self.p[pnum]
        played_something = True
        play_rounds = 0
        while played_something and play_rounds < 20:
            played_something = False
            play_rounds += 1

            # 1. Try pairing pilots to satisfy link conditions
            if self._ai_pair_pilot(pnum):
                played_something = True
                continue

            # 2. Try deploying units
            if self._ai_deploy_unit(pnum):
                played_something = True
                continue

            # 3. Try deploying base
            if self._ai_deploy_base(pnum):
                played_something = True
                continue

            # 4. Try playing command cards
            if self._ai_play_command(pnum):
                played_something = True
                continue

        # Activate support effects
        self._ai_activate_support(pnum)

    def _ai_deploy_unit(self, pnum: int) -> bool:
        ps = self.p[pnum]
        if len(ps.battle_area) >= 6:
            return False
        candidates = [c for c in ps.hand if c.card_type == "Unit" and ps.can_afford(c)]
        if not candidates:
            return False
        # Sort by cost descending (play most expensive first)
        candidates.sort(key=lambda c: c.cost, reverse=True)
        card = candidates[0]
        if not ps.rest_resources_for_cost(card.cost):
            return False
        ps.hand.remove(card)
        unit = UnitInPlay(template=card, deployed_this_turn=True)
        ps.battle_area.append(unit)
        self.log.log(f"P{pnum} deploys '{card.card_name}' (AP:{unit.effective_ap} HP:{unit.effective_hp})", pnum, "deploy")
        # Deploy effect
        if "deploy_draw" in card.effects:
            self._draw(pnum, card.effects["deploy_draw"])
        return True

    def _ai_pair_pilot(self, pnum: int) -> bool:
        ps = self.p[pnum]
        pilot_cards = [c for c in ps.hand if c.card_type == "Pilot" and ps.can_afford(c)]
        if not pilot_cards:
            # Also check Command cards with Pilot effect
            pilot_cards = [c for c in ps.hand if c.card_type == "Command" and c.pilot_name and ps.can_afford(c)]
        if not pilot_cards:
            return False
        # Find units without pilots
        unpiloted = [u for u in ps.battle_area if u.paired_pilot is None]
        if not unpiloted:
            return False
        # Sort pilots by value (ap + hp) desc
        pilot_cards.sort(key=lambda c: (c.pilot_ap + c.pilot_hp + c.ap + c.hp), reverse=True)
        pilot = pilot_cards[0]
        # Find best unit to pair with (prefer one that satisfies link conditions)
        target_unit = None
        for unit in unpiloted:
            if unit.template.link_conditions:
                pilot_name = pilot.pilot_name if pilot.pilot_name else pilot.card_name
                for cond in unit.template.link_conditions:
                    if cond.lower() in pilot_name.lower():
                        target_unit = unit
                        break
            if target_unit:
                break
        if not target_unit:
            # No link match; pair with highest AP unit
            target_unit = max(unpiloted, key=lambda u: u.effective_ap)

        if not ps.rest_resources_for_cost(pilot.cost):
            return False
        ps.hand.remove(pilot)
        target_unit.paired_pilot = pilot
        self.log.log(
            f"P{pnum} pairs '{pilot.card_name}' with '{target_unit.template.card_name}' "
            f"→ AP:{target_unit.effective_ap} HP:{target_unit.effective_hp}"
            + (" [LINK UNIT]" if target_unit.is_link_unit else ""),
            pnum, "pair"
        )
        if "when_paired_draw" in pilot.effects:
            self._draw(pnum, pilot.effects["when_paired_draw"])
        return True

    def _ai_deploy_base(self, pnum: int) -> bool:
        ps = self.p[pnum]
        # Only deploy base if current base HP is low
        if ps.base:
            return False
        # Check if ex base is still healthy enough
        if not ps.ex_base_destroyed and ps.base_hp_remaining() > 1:
            return False
        candidates = [c for c in ps.hand if c.card_type == "Base" and ps.can_afford(c)]
        if not candidates:
            return False
        candidates.sort(key=lambda c: c.hp, reverse=True)
        card = candidates[0]
        if not ps.rest_resources_for_cost(card.cost):
            return False
        ps.hand.remove(card)
        # Remove old base (destroyed or not)
        ps.base = BaseInPlay(template=card)
        ps.ex_base_destroyed = True  # Effectively replaced
        self.log.log(f"P{pnum} deploys base '{card.card_name}' (HP:{card.hp})", pnum, "deploy")
        return True

    def _ai_play_command(self, pnum: int) -> bool:
        ps = self.p[pnum]
        candidates = [c for c in ps.hand
                      if c.card_type == "Command" and not c.pilot_name and ps.can_afford(c)
                      and "main" in c.effects.get("timing", "")]
        if not candidates:
            return False
        card = candidates[0]
        if not ps.rest_resources_for_cost(card.cost):
            return False
        ps.hand.remove(card)
        ps.trash.append(card)
        self.log.log(f"P{pnum} plays command '{card.card_name}'", pnum, "command")
        # Apply effects
        if "draw" in card.effects:
            self._draw(pnum, card.effects["draw"])
        if "deal_damage" in card.effects:
            self._deal_effect_damage(pnum, 3 - pnum, card.effects["deal_damage"])
        if "destroy_unit" in card.effects:
            self._ai_destroy_enemy_unit(pnum)
        if "rest_enemy" in card.effects:
            self._rest_enemy_unit(pnum)
        return True

    def _ai_activate_support(self, pnum: int):
        ps = self.p[pnum]
        standby = 3 - pnum
        # Find strongest attacking unit that isn't rested
        attackers = [u for u in ps.battle_area if not u.is_rested and u.can_attack()]
        if not attackers:
            return
        best_attacker = max(attackers, key=lambda u: u.effective_ap)
        # Find support units (not the best attacker, not rested)
        supporters = [u for u in ps.battle_area
                      if u != best_attacker and not u.is_rested
                      and "support" in u.template.effects]
        for supporter in supporters[:1]:  # Use one support per turn
            amt = supporter.template.effects["support"]
            supporter.is_rested = True
            self.log.log(
                f"P{pnum} activates Support on '{supporter.template.card_name}', "
                f"'{best_attacker.template.card_name}' gains AP+{amt} this turn",
                pnum, "support"
            )
            best_attacker.template.effects["_support_bonus"] = (
                best_attacker.template.effects.get("_support_bonus", 0) + amt
            )

    def _ai_attack(self, active: int, turn_num: int) -> Optional[int]:
        ps = self.p[active]
        standby = 3 - active
        ps_s = self.p[standby]

        attackers = [u for u in ps.battle_area if u.can_attack()]

        for attacker in list(attackers):
            if attacker not in ps.battle_area:
                continue
            # Clean up temporary support bonus
            bonus = attacker.template.effects.pop("_support_bonus", 0)
            eff_ap = attacker.effective_ap + bonus

            # Decide target
            # Option A: Attack a unit we can kill (and survive or it doesn't matter)
            target_unit = self._pick_attack_target_unit(attacker, eff_ap, ps_s)

            if target_unit:
                result = self._resolve_unit_attack(active, attacker, eff_ap, standby, target_unit, turn_num)
                if result is not None:
                    return result
            else:
                # Attack player (hits shields or base)
                result = self._resolve_player_attack(active, attacker, eff_ap, standby, turn_num)
                if result is not None:
                    return result

        return None

    def _pick_attack_target_unit(self, attacker: UnitInPlay, eff_ap: int, ps_standby: PlayerState) -> Optional[UnitInPlay]:
        """Pick a rested enemy unit to attack, preferring ones we can kill."""
        rested_enemies = [u for u in ps_standby.battle_area if u.is_rested]
        if not rested_enemies:
            return None
        # Prefer killing enemies with lowest HP we can destroy
        killable = [u for u in rested_enemies if u.current_hp <= eff_ap]
        if killable:
            return min(killable, key=lambda u: u.effective_hp)
        return None

    def _resolve_unit_attack(self, active: int, attacker: UnitInPlay, eff_ap: int,
                              standby: int, target: UnitInPlay, turn_num: int) -> Optional[int]:
        ps_a = self.p[active]
        ps_s = self.p[standby]

        # Rest attacker
        attacker.is_rested = True
        self.log.log(
            f"P{active} attacks P{standby}'s '{target.template.card_name}' "
            f"with '{attacker.template.card_name}' (AP:{eff_ap} vs HP:{target.current_hp})",
            active, "attack"
        )

        # Blocker check
        blocker = self._check_blocker(standby, target)
        if blocker:
            self.log.log(f"P{standby} activates <Blocker> on '{blocker.template.card_name}'", standby, "block")
            target = blocker

        # First strike
        first_strike = attacker.has_effect("first_strike")
        target_ap = target.effective_ap
        target_hp_before = target.current_hp

        if first_strike:
            target.damage += eff_ap
            self.log.log(f"<First Strike>: '{attacker.template.card_name}' deals {eff_ap} to '{target.template.card_name}' (HP now {target.current_hp})", active, "damage")
            if target.current_hp <= 0:
                self._destroy_unit(standby, target, f"'{target.template.card_name}' destroyed by first strike")
                # Breach
                if attacker.has_effect("breach"):
                    self._apply_breach(active, attacker, standby, turn_num)
                return self._check_defeat(active, standby, turn_num)
            # Target retaliates
            attacker.damage += target_ap
            self.log.log(f"'{target.template.card_name}' retaliates {target_ap} to '{attacker.template.card_name}'", standby, "damage")
        else:
            # Simultaneous
            attacker.damage += target_ap
            target.damage += eff_ap
            self.log.log(
                f"Battle: '{attacker.template.card_name}' deals {eff_ap} dmg, "
                f"'{target.template.card_name}' deals {target_ap} dmg (simultaneous)",
                active, "damage"
            )

        # Check destruction
        attacker_dead = attacker.current_hp <= 0
        target_dead = target.current_hp <= 0

        if target_dead:
            self._destroy_unit(standby, target, f"'{target.template.card_name}' destroyed")
            if attacker.has_effect("breach") and not attacker_dead:
                self._apply_breach(active, attacker, standby, turn_num)

        if attacker_dead:
            self._destroy_unit(active, attacker, f"'{attacker.template.card_name}' destroyed in battle")

        return self._check_defeat(active, standby, turn_num)

    def _resolve_player_attack(self, active: int, attacker: UnitInPlay, eff_ap: int,
                                standby: int, turn_num: int) -> Optional[int]:
        ps_s = self.p[standby]
        attacker.is_rested = True

        # Blocker check
        blocker = self._check_blocker(standby, None)
        if blocker and not attacker.has_effect("high_maneuver"):
            self.log.log(f"P{standby} activates <Blocker> on '{blocker.template.card_name}'", standby, "block")
            return self._resolve_unit_attack(active, attacker, eff_ap, standby, blocker, turn_num)

        # Attack player
        self.log.log(f"P{active} attacks P{standby} with '{attacker.template.card_name}' (AP:{eff_ap})", active, "attack")

        if ps_s.has_base():
            # Damage goes to base
            base_hp = ps_s.base_hp_remaining()
            if ps_s.base:
                # Real base
                ps_s.base.damage += eff_ap
                self.log.log(
                    f"P{standby}'s base '{ps_s.base.template.card_name}' takes {eff_ap} damage "
                    f"(HP: {base_hp} → {ps_s.base.current_hp})",
                    standby, "damage"
                )
                if ps_s.base.current_hp <= 0:
                    self.log.log(f"P{standby}'s base '{ps_s.base.template.card_name}' is destroyed!", standby, "destroy")
                    ps_s.trash.append(ps_s.base.template)
                    ps_s.base = None
            else:
                # EX Base
                destroyed = ps_s.deal_ex_base_damage(eff_ap)
                self.log.log(
                    f"P{standby}'s EX Base takes {eff_ap} damage "
                    f"(HP: {base_hp} → {max(0, ps_s.base_hp_remaining())})",
                    standby, "damage"
                )
                if destroyed:
                    self.log.log(f"P{standby}'s EX Base is destroyed!", standby, "destroy")
        elif ps_s.shield_section:
            # Hit top shield
            shield = ps_s.shield_section.pop(0)
            remaining_shields = len(ps_s.shield_section)
            self.log.log(
                f"P{standby}'s shield '{shield.card_name}' is destroyed! "
                f"({remaining_shields} shields remaining)",
                standby, "shield_destroy"
            )
            # Check for BURST
            if "burst" in shield.effects:
                burst_effect = shield.effects["burst"]
                self.log.log(f"P{standby} activates BURST on '{shield.card_name}': {burst_effect}", standby, "burst")
                self._apply_burst(standby, shield, burst_effect)
            else:
                ps_s.trash.append(shield)

            # Suppression: hit 2 shields
            if attacker.has_effect("suppression") and ps_s.shield_section:
                shield2 = ps_s.shield_section.pop(0)
                self.log.log(f"<Suppression>: P{standby}'s shield '{shield2.card_name}' also destroyed!", standby, "shield_destroy")
                if "burst" in shield2.effects:
                    self._apply_burst(standby, shield2, shield2.effects["burst"])
                else:
                    ps_s.trash.append(shield2)
        else:
            # No shield, no base: player defeated
            self.log.log(f"P{standby} takes direct battle damage — DEFEATED!", standby, "defeat")
            return active

        return self._check_defeat(active, standby, turn_num)

    def _check_blocker(self, pnum: int, target: Optional[UnitInPlay]) -> Optional[UnitInPlay]:
        """Find a unit with <Blocker> to intercept."""
        ps = self.p[pnum]
        for unit in ps.battle_area:
            if unit != target and not unit.is_rested and unit.has_effect("blocker"):
                # AI: only block if we can survive or kill the attacker
                unit.is_rested = True
                return unit
        return None

    def _apply_breach(self, active: int, attacker: UnitInPlay, standby: int, turn_num: int):
        ps_s = self.p[standby]
        amt = attacker.get_effect_val("breach", 1)
        if ps_s.has_base():
            if ps_s.base:
                ps_s.base.damage += amt
                self.log.log(f"<Breach {amt}>: P{standby}'s base takes {amt} damage", active, "breach")
                if ps_s.base.current_hp <= 0:
                    self.log.log(f"<Breach> destroys P{standby}'s base!", standby, "destroy")
                    ps_s.trash.append(ps_s.base.template)
                    ps_s.base = None
            else:
                ps_s.deal_ex_base_damage(amt)
                self.log.log(f"<Breach {amt}>: P{standby}'s EX Base takes {amt} damage", active, "breach")
        elif ps_s.shield_section:
            shield = ps_s.shield_section.pop(0)
            self.log.log(f"<Breach {amt}>: P{standby}'s shield '{shield.card_name}' destroyed!", active, "breach")
            if "burst" in shield.effects:
                self._apply_burst(standby, shield, shield.effects["burst"])
            else:
                ps_s.trash.append(shield)

    def _apply_burst(self, pnum: int, shield: CardTemplate, burst_type: str):
        if burst_type == "draw1":
            self._draw(pnum, 1)
        elif burst_type == "draw2":
            self._draw(pnum, 2)
        elif burst_type == "deploy_top":
            self._burst_deploy_top(pnum)
        elif burst_type == "heal_base":
            ps = self.p[pnum]
            if ps.base:
                old = ps.base.damage
                ps.base.damage = max(0, ps.base.damage - 2)
                self.log.log(f"P{pnum} BURST heals base 2 HP", pnum, "burst")
            elif not ps.ex_base_destroyed:
                ps._ex_base_damage = max(0, ps._ex_base_damage - 2)
                self.log.log(f"P{pnum} BURST heals EX Base 2 HP", pnum, "burst")
        self.p[pnum].trash.append(shield)

    def _burst_deploy_top(self, pnum: int):
        ps = self.p[pnum]
        if ps.deck and len(ps.battle_area) < 6:
            top = ps.deck.pop(0)
            if top.card_type == "Unit":
                unit = UnitInPlay(template=top, deployed_this_turn=True)
                ps.battle_area.append(unit)
                self.log.log(f"P{pnum} BURST deploys '{top.card_name}' from deck", pnum, "burst")
            else:
                ps.trash.append(top)

    def _destroy_unit(self, pnum: int, unit: UnitInPlay, msg: str):
        ps = self.p[pnum]
        if unit in ps.battle_area:
            ps.battle_area.remove(unit)
            ps.trash.append(unit.template)
            if unit.paired_pilot:
                ps.trash.append(unit.paired_pilot)
            self.log.log(msg, pnum, "destroy")
            # Destroyed trigger
            if "destroyed_draw" in unit.template.effects:
                self._draw(pnum, unit.template.effects["destroyed_draw"])

    def _ai_destroy_enemy_unit(self, pnum: int):
        ps_s = self.p[3 - pnum]
        if ps_s.battle_area:
            target = min(ps_s.battle_area, key=lambda u: u.effective_hp)
            self._destroy_unit(3 - pnum, target, f"Command effect destroys '{target.template.card_name}'")

    def _rest_enemy_unit(self, pnum: int):
        ps_s = self.p[3 - pnum]
        unrasted = [u for u in ps_s.battle_area if not u.is_rested]
        if unrasted:
            target = max(unrasted, key=lambda u: u.effective_ap)
            target.is_rested = True
            self.log.log(f"Command effect rests enemy '{target.template.card_name}'", pnum, "command")

    def _deal_effect_damage(self, from_pnum: int, to_pnum: int, amount: int):
        ps_s = self.p[to_pnum]
        if ps_s.battle_area:
            target = min(ps_s.battle_area, key=lambda u: u.current_hp)
            target.damage += amount
            self.log.log(f"Effect deals {amount} damage to '{target.template.card_name}'", from_pnum, "damage")
            if target.current_hp <= 0:
                self._destroy_unit(to_pnum, target, f"'{target.template.card_name}' destroyed by effect damage")

    def _draw(self, pnum: int, count: int):
        ps = self.p[pnum]
        drawn = []
        for _ in range(count):
            if ps.deck:
                card = ps.deck.pop(0)
                ps.hand.append(card)
                drawn.append(card.card_name)
        if drawn:
            self.log.log(f"P{pnum} draws {len(drawn)} card(s): {', '.join(drawn)}", pnum, "draw")

    def _check_defeat(self, active: int, standby: int, turn_num: int) -> Optional[int]:
        """Check if either player meets defeat condition."""
        for pnum in [active, standby]:
            ps = self.p[pnum]
            if not ps.deck:
                self.log.log(f"P{pnum} has no cards in deck — defeated!", pnum, "defeat")
                return 3 - pnum
        return None
