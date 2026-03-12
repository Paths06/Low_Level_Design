# fmt: off
# ==============================================================================
#  COUNTER-STRIKE STYLE FPS GAME — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                COUNTER-STRIKE FPS GAME SYSTEM                           │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌───────────────────────────────────────────────────────────────────────┐
#  │                         GameMatch  (Facade)                           │
#  ├───────────────────────────────────────────────────────────────────────┤
#  │ + match_id: str                                                       │
#  │ + ct_team: Team, t_team: Team                                         │
#  │ + state: MatchState (enum)                                            │
#  │ + current_round: int                                                  │
#  │ + ct_score, t_score: int                                              │
#  │ + observers: List[GameEventObserver]                                  │
#  ├───────────────────────────────────────────────────────────────────────┤
#  │ + start_match()  + start_round()  + end_round(winner)                 │
#  │ + add_observer() + notify(event)   ← Observer Pattern                 │
#  └───────────────────────────────────────────────────────────────────────┘
#                     │                 │ notifies
#           ┌─────────┘                 ▼
#           ▼                 ┌─────────────────────────────┐
#  ┌──────────────────┐       │   GameEventObserver (ABC)   │
#  │       Team       │       ├─────────────────────────────┤
#  ├──────────────────┤       │ + on_event(event): void     │
#  │ + id: str        │       └──────────────┬──────────────┘
#  │ + name: str      │                      │
#  │ + side: TeamSide │                      ▼
#  │   (enum)         │              ┌───────────────────┐
#  │ + players: List  │              │  MatchLogger      │
#  │ + wins: int      │              ├───────────────────┤
#  ├──────────────────┤              │ + on_event(event) │
#  │ + add_player()   │              │  (prints log)     │
#  │ + alive_players[]│              └───────────────────┘
#  └────────┬─────────┘
#           │ 1..*
#           ▼
#  ┌──────────────────────────────────────────────────────────┐
#  │                         Player                           │
#  ├──────────────────────────────────────────────────────────┤
#  │ + player_id: str                                         │
#  │ + name: str                                              │
#  │ + team: Team                                             │
#  │ + health: int                                            │
#  │ + armor: int                                             │
#  │ + money: int                                             │
#  │ + weapon: Optional[Weapon]                               │
#  │ + kills: int                                             │
#  ├──────────────────────────────────────────────────────────┤
#  │ + is_alive(): bool                                       │
#  │ + buy_weapon(weapon, game_match)                         │
#  │ + shoot(target, game_match)         ← DamageStrategy    │
#  │ + take_damage(amount)                                    │
#  │ + plant_bomb(game_match)                                 │
#  └──────────────────────────────────────────────────────────┘
#
#  ┌──────────────────────────────────────────┐
#  │             Weapon  (ABC)                │  ← Factory Pattern
#  ├──────────────────────────────────────────┤
#  │ + name: str                              │
#  │ + damage: int                            │
#  │ + price: int                             │
#  │ + damage_strategy: DamageStrategy        │
#  ├──────────────────────────────────────────┤
#  │ + apply_damage(shooter, target): int     │
#  └──────────────────────────────────────────┘
#           │
#    ┌──────┼──────────────┐
#    ▼      ▼              ▼
#  ┌──────┐ ┌──────┐ ┌───────────┐
#  │Pistol│ │Rifle │ │  Sniper   │
#  ├──────┤ ├──────┤ ├───────────┤
#  │$300  │ │$2700 │ │  $4750    │
#  │25dmg │ │30dmg │ │  100dmg   │
#  └──────┘ └──────┘ └───────────┘
#
#  ┌──────────────────────────┐   ┌───────────────────────────────┐
#  │   DamageStrategy (ABC)   │   │           Bomb                │
#  ├──────────────────────────┤   ├───────────────────────────────┤
#  │+calculate(dmg,armor): int│   │ + is_planted: bool            │
#  └────────────┬─────────────┘   │ + plant_time: datetime        │
#               │                 │ + defuse_time_secs: int       │
#      ┌────────┴────────┐        ├───────────────────────────────┤
#      ▼                 ▼        │ + plant() + defuse()          │
#  ┌──────────┐  ┌────────────┐   │ + is_detonated(): bool        │
#  │ Standard │  │ ArmorPierc.│   └───────────────────────────────┘
#  │ Damage   │  │ Damage     │
#  └──────────┘  └────────────┘   ┌─────────────────────────────────────┐
#                                 │       WeaponFactory                 │
#                                 ├─────────────────────────────────────┤
#                                 │ + create(weapon_type): Weapon       │
#                                 │   (PISTOL / RIFLE / SNIPER)         │
#                                 └─────────────────────────────────────┘
#
#  ┌───────────────────────────┐  ┌────────────────────────┐
#  │   MatchState (Enum)       │  │   TeamSide (Enum)      │
#  ├───────────────────────────┤  ├────────────────────────┤
#  │ WAITING / IN_ROUND        │  │  CT / TERRORIST        │
#  │ ROUND_OVER / MATCH_OVER   │  └────────────────────────┘
#  └───────────────────────────┘
#
#  RELATIONSHIPS:
#  GameMatch ──2──> Team                     (CT + T sides)
#  GameMatch ──1──> Bomb                     (one bomb per map)
#  GameMatch ──*──> GameEventObserver        (Observer list)
#  Team ──*──> Player                        (squad)
#  Player ──1──> Weapon (optional)           (current equipped weapon)
#  Weapon ──1──> DamageStrategy              (how damage is calculated)
#  WeaponFactory creates Pistol|Rifle|Sniper (Factory Pattern)
#  MatchLogger ──▷── GameEventObserver       (implements observer)
#  StandardDamage / ArmorPiercingDamage ──▷── DamageStrategy (implements)
# ==============================================================================
# fmt: on
import threading
import uuid
import random
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Optional

"""
==============================================================================================
COUNTER-STRIKE STYLE FPS GAME LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features Implemented:
1. Teams: Terrorists vs Counter-Terrorists, each with roles.
2. Weapons: Guns and Grenades with different stats; WeaponFactory.
3. Player Lifecycle: Alive -> Dead -> Respawn (in newer modes).
4. Match & Round: Full round lifecycle (Buy Phase -> Active -> End).
5. Bomb: Plant (by T), Defuse (by CT); special win condition.
6. Observer: EventBus for game events (kill, round end, bomb plant, etc.).
7. Score Tracking: Per-player stats (kills, deaths, assists).
8. Concurrency: Thread-safe player actions and score updates.

Design Patterns:
1. Facade: GameManager (orchestrates match, rounds, teams).
2. Factory: WeaponFactory (creates weapons by type).
3. Observer: EventBus + GameEventListener (kill feed, match events).
4. State: Match states (WAITING -> IN_PROGRESS -> ROUND_OVER -> MATCH_OVER).
5. Strategy: DamageStrategy (headshot vs body shot multipliers).

Class Design Diagram:
---------------------
[GameManager] "1" *-- "1" [Match]
[Match] "1" *-- "2" [Team]
[Match] "1" *-- "*" [Round]
[Match] "1" *-- "1" [EventBus]
[Team] "1" *-- "*" [Player]
[Player] "1" *-- "1" [Inventory]
[Player] "1" *-- "1" [PlayerStats]
[Inventory] "1" *-- "*" [Weapon]
[Weapon] <|-- [Gun]
[Weapon] <|-- [Grenade]
[Round] "1" *-- "1" [Bomb]
[EventBus] "1" *-- "*" [GameEventListener]
[EventBus] ..> [GameEvent]
[DamageStrategy] <|-- [HeadshotStrategy]
[DamageStrategy] <|-- [BodyShotStrategy]

Class Details:
---------------------
1. GameManager (Facade)
   - Role: Entry point. Creates match, teams, players.
   - Methods: startMatch(), endMatch().

2. Match
   - Role: Orchestrates rounds. Tracks team scores.
   - Attributes: teams, rounds, state, maxRounds.
   - Methods: startRound(), endRound(), declareWinner().

3. Round
   - Role: Single round lifecycle.
   - Attributes: roundNumber, bomb, state, timerSeconds.
   - Methods: startBuyPhase(), startActive(), end().

4. Player
   - Role: Participant entity. Has inventory and stats.
   - Attributes: name, health, isAlive, team, inventory, stats.
   - Methods: takeDamage(), die(), shoot(), plant(), defuse().

5. Weapon (Abstract)
   - Role: Equipment entity.
   - Attributes: name, damage, price.
   - Impls: Gun (ammo, range), Grenade (radius, type).

6. WeaponFactory
   - Role: Creates weapons by type enum.

7. EventBus (Observer)
   - Role: Decoupled event propagation.
   - Methods: subscribe(), publish().

8. DamageStrategy (Strategy)
   - Role: Compute final damage.
   - Impls: HeadshotStrategy (2.5x), BodyShotStrategy (1.0x).
"""

# ==========================================
# Enums
# ==========================================

class TeamSide(Enum):
    TERRORIST = "TERRORIST"
    COUNTER_TERRORIST = "COUNTER_TERRORIST"

class MatchState(Enum):
    WAITING = "WAITING"
    BUY_PHASE = "BUY_PHASE"
    IN_PROGRESS = "IN_PROGRESS"
    ROUND_OVER = "ROUND_OVER"
    MATCH_OVER = "MATCH_OVER"

class WeaponType(Enum):
    PISTOL = "PISTOL"
    RIFLE = "RIFLE"
    SNIPER = "SNIPER"
    KNIFE = "KNIFE"
    GRENADE = "GRENADE"
    FLASHBANG = "FLASHBANG"
    SMOKE = "SMOKE"

class RoundEndReason(Enum):
    T_ELIMINATED = "T_ELIMINATED"
    CT_ELIMINATED = "CT_ELIMINATED"
    BOMB_EXPLODED = "BOMB_EXPLODED"
    BOMB_DEFUSED = "BOMB_DEFUSED"
    TIME_EXPIRED = "TIME_EXPIRED"

# ==========================================
# Events (Observer)
# ==========================================

class GameEvent:
    """Base event object published to the EventBus."""
    def __init__(self, event_type: str, data: dict):
        self.event_type = event_type
        self.data = data

class GameEventListener(ABC):
    """Observer interface for game events."""
    @abstractmethod
    def on_event(self, event: GameEvent):
        pass

class KillFeedListener(GameEventListener):
    """Prints kill-feed events to console."""
    def on_event(self, event: GameEvent):
        if event.event_type == "PLAYER_KILLED":
            print(f"  [KILLFEED] {event.data['killer']} killed {event.data['victim']} with {event.data['weapon']}")
        elif event.event_type == "BOMB_PLANTED":
            print(f"  [KILLFEED] *** BOMB PLANTED by {event.data['player']} ***")
        elif event.event_type == "BOMB_DEFUSED":
            print(f"  [KILLFEED] *** BOMB DEFUSED by {event.data['player']} ***")
        elif event.event_type == "ROUND_END":
            print(f"  [KILLFEED] Round ended: {event.data['reason']}")

class EventBus:
    """Decoupled event bus for game-wide event distribution."""
    def __init__(self):
        self._listeners: List[GameEventListener] = []
        self._lock = threading.Lock()

    def subscribe(self, listener: GameEventListener):
        with self._lock:
            self._listeners.append(listener)

    def publish(self, event: GameEvent):
        with self._lock:
            for listener in self._listeners:
                listener.on_event(event)

# ==========================================
# Damage Strategies
# ==========================================

class DamageStrategy(ABC):
    """Strategy for computing final damage dealt."""
    @abstractmethod
    def compute(self, base_damage: int) -> int:
        pass

class HeadshotStrategy(DamageStrategy):
    """2.5x damage multiplier for headshots."""
    def compute(self, base_damage: int) -> int:
        return int(base_damage * 2.5)

class BodyShotStrategy(DamageStrategy):
    """1.0x damage for standard body shots."""
    def compute(self, base_damage: int) -> int:
        return base_damage

# ==========================================
# Weapons
# ==========================================

class Weapon(ABC):
    """Abstract base class for all weapons."""
    def __init__(self, name: str, damage: int, price: int, weapon_type: WeaponType):
        self.name = name
        self.damage = damage
        self.price = price
        self.type = weapon_type

    @abstractmethod
    def use(self) -> bool:
        """Returns True if weapon can be used (ammo/charges available)."""
        pass

    def __repr__(self):
        return f"{self.name}"

class Gun(Weapon):
    """Ranged firearm with ammo."""
    def __init__(self, name: str, damage: int, price: int, weapon_type: WeaponType, ammo: int):
        super().__init__(name, damage, price, weapon_type)
        self.ammo = ammo
        self.max_ammo = ammo

    def use(self) -> bool:
        if self.ammo > 0:
            self.ammo -= 1
            return True
        print(f"  WARNING: {self.name} is out of ammo!")
        return False

    def reload(self):
        self.ammo = self.max_ammo
        print(f"  INFO: Reloaded {self.name}.")

class Grenade(Weapon):
    """Throwable explosive with a radius."""
    def __init__(self, name: str, damage: int, price: int, weapon_type: WeaponType, radius: int = 3):
        super().__init__(name, damage, price, weapon_type)
        self.radius = radius
        self._used = False

    def use(self) -> bool:
        if not self._used:
            self._used = True
            return True
        print(f"  WARNING: {self.name} already thrown!")
        return False

class WeaponFactory:
    """Factory to create weapons by WeaponType."""
    @staticmethod
    def create(weapon_type: WeaponType) -> Weapon:
        catalog = {
            WeaponType.KNIFE:     Gun("Knife",     26,    0,   WeaponType.KNIFE,    999),
            WeaponType.PISTOL:    Gun("Glock-18",  35,    200, WeaponType.PISTOL,   20),
            WeaponType.RIFLE:     Gun("AK-47",     100,   2700,WeaponType.RIFLE,    30),
            WeaponType.SNIPER:    Gun("AWP",       300,   4750,WeaponType.SNIPER,   5),
            WeaponType.GRENADE:   Grenade("HE Grenade",  57, 300,  WeaponType.GRENADE,  4),
            WeaponType.FLASHBANG: Grenade("Flashbang",    0, 200,  WeaponType.FLASHBANG,2),
            WeaponType.SMOKE:     Grenade("Smoke",         0, 300,  WeaponType.SMOKE,    4),
        }
        if weapon_type not in catalog:
            raise ValueError(f"Unknown weapon type: {weapon_type}")
        return catalog[weapon_type]

# ==========================================
# Inventory
# ==========================================

class Inventory:
    """Manages a player's weapons and economy."""
    def __init__(self):
        self.weapons: Dict[WeaponType, Weapon] = {
            WeaponType.KNIFE: WeaponFactory.create(WeaponType.KNIFE)
        }
        self.money: int = 800  # Starting money

    def buy(self, weapon_type: WeaponType) -> bool:
        weapon = WeaponFactory.create(weapon_type)
        if self.money >= weapon.price:
            self.money -= weapon.price
            self.weapons[weapon_type] = weapon
            return True
        print(f"  WARNING: Not enough money to buy {weapon.name} (need ${weapon.price}, have ${self.money})")
        return False

    def get_weapon(self, weapon_type: WeaponType) -> Optional[Weapon]:
        return self.weapons.get(weapon_type)

    def award_money(self, amount: int):
        self.money = min(self.money + amount, 16000)  # CS has a $16k cap

# ==========================================
# Player Stats
# ==========================================

class PlayerStats:
    """Tracks performance statistics per player."""
    def __init__(self):
        self.kills = 0
        self.deaths = 0
        self.assists = 0
        self._lock = threading.Lock()

    def add_kill(self):
        with self._lock:
            self.kills += 1

    def add_death(self):
        with self._lock:
            self.deaths += 1

    @property
    def kd_ratio(self) -> float:
        return self.kills / max(self.deaths, 1)

    def __repr__(self):
        return f"K:{self.kills} D:{self.deaths} KD:{self.kd_ratio:.2f}"

# ==========================================
# Player
# ==========================================

class Player:
    """Represents an individual game participant."""
    def __init__(self, name: str, team: 'Team'):
        self.id = str(uuid.uuid4())
        self.name = name
        self.team = team
        self.health = 100
        self.armor = 0
        self.is_alive = True
        self.inventory = Inventory()
        self.stats = PlayerStats()
        self._lock = threading.Lock()

    def buy_weapon(self, weapon_type: WeaponType) -> bool:
        return self.inventory.buy(weapon_type)

    def take_damage(self, damage: int, attacker: 'Player', weapon: Weapon, event_bus: EventBus):
        """Apply damage and handle death."""
        with self._lock:
            if not self.is_alive:
                return

            # Armor absorbs 50% of damage if equipped
            effective = damage // 2 if self.armor > 0 else damage
            self.health -= effective
            print(f"  INFO: {self.name} took {effective} damage. HP: {max(self.health, 0)}")

            if self.health <= 0:
                self._die(attacker, weapon, event_bus)

    def _die(self, killer: 'Player', weapon: Weapon, event_bus: EventBus):
        self.is_alive = False
        self.health = 0
        self.stats.add_death()
        killer.stats.add_kill()
        killer.inventory.award_money(300)  # Kill reward
        print(f"  INFO: {self.name} was eliminated by {killer.name}!")
        event_bus.publish(GameEvent("PLAYER_KILLED", {
            "killer": killer.name,
            "victim": self.name,
            "weapon": weapon.name
        }))

    def shoot(self, target: 'Player', weapon_type: WeaponType,
              damage_strategy: DamageStrategy, event_bus: EventBus):
        """Shoot at a target player."""
        if not self.is_alive:
            print(f"  WARNING: {self.name} is dead and cannot shoot.")
            return
        weapon = self.inventory.get_weapon(weapon_type)
        if not weapon:
            print(f"  WARNING: {self.name} doesn't have {weapon_type.name}")
            return
        if weapon.use():
            final_damage = damage_strategy.compute(weapon.damage)
            print(f"  INFO: {self.name} fires {weapon.name} at {target.name} for {final_damage} dmg")
            target.take_damage(final_damage, self, weapon, event_bus)

    def reset_for_round(self):
        """Called at the start of each round to reset player state."""
        self.health = 100
        self.armor = 0
        self.is_alive = True

    def __repr__(self):
        status = "ALIVE" if self.is_alive else "DEAD"
        return f"{self.name}({status}, HP:{self.health})"

# ==========================================
# Bomb
# ==========================================

class Bomb:
    """The bomb planted by Terrorists. CT must defuse it."""
    def __init__(self):
        self.is_planted = False
        self.is_defused = False
        self.is_exploded = False
        self.planted_by: Optional[Player] = None
        self.defused_by: Optional[Player] = None

    def plant(self, player: Player, event_bus: EventBus):
        if self.is_planted:
            print("  WARNING: Bomb is already planted!")
            return
        self.is_planted = True
        self.planted_by = player
        player.inventory.award_money(300)  # Plant bonus
        print(f"  INFO: Bomb planted by {player.name}!")
        event_bus.publish(GameEvent("BOMB_PLANTED", {"player": player.name}))

    def defuse(self, player: Player, event_bus: EventBus):
        if not self.is_planted or self.is_exploded:
            print("  WARNING: Cannot defuse at this time.")
            return
        self.is_defused = True
        self.defused_by = player
        player.inventory.award_money(300)  # Defuse bonus
        print(f"  INFO: Bomb defused by {player.name}!")
        event_bus.publish(GameEvent("BOMB_DEFUSED", {"player": player.name}))

    def explode(self, event_bus: EventBus):
        if not self.is_planted or self.is_defused:
            return
        self.is_exploded = True
        print("  INFO: *** BOMB HAS EXPLODED ***")
        event_bus.publish(GameEvent("BOMB_EXPLODED", {}))

# ==========================================
# Team
# ==========================================

class Team:
    """Represents one side (T or CT) with multiple players."""
    def __init__(self, side: TeamSide):
        self.side = side
        self.players: List[Player] = []
        self.round_wins = 0

    def add_player(self, player: Player):
        self.players.append(player)

    def alive_players(self) -> List[Player]:
        return [p for p in self.players if p.is_alive]

    def is_eliminated(self) -> bool:
        return len(self.alive_players()) == 0

    def reset_for_round(self):
        for p in self.players:
            p.reset_for_round()

    def __repr__(self):
        return f"Team({self.side.value}, wins={self.round_wins})"

# ==========================================
# Round
# ==========================================

class Round:
    """Encapsulates a single round's lifecycle."""
    def __init__(self, round_number: int):
        self.round_number = round_number
        self.bomb = Bomb()
        self.state = MatchState.WAITING
        self.winner_side: Optional[TeamSide] = None
        self.end_reason: Optional[RoundEndReason] = None

    def start(self):
        self.state = MatchState.IN_PROGRESS
        print(f"\n  [Round {self.round_number}] --- Started ---")

    def end(self, winner_side: TeamSide, reason: RoundEndReason, event_bus: EventBus):
        self.state = MatchState.ROUND_OVER
        self.winner_side = winner_side
        self.end_reason = reason
        event_bus.publish(GameEvent("ROUND_END", {
            "round": self.round_number,
            "winner": winner_side.value,
            "reason": reason.value
        }))
        print(f"  [Round {self.round_number}] Winner: {winner_side.value} | Reason: {reason.value}")

# ==========================================
# Match
# ==========================================

class Match:
    """Orchestrates the full match across multiple rounds."""
    MAX_ROUNDS = 30  # Win by reaching 16

    def __init__(self, t_team: Team, ct_team: Team, event_bus: EventBus):
        self.id = str(uuid.uuid4())
        self.t_team = t_team
        self.ct_team = ct_team
        self.event_bus = event_bus
        self.rounds: List[Round] = []
        self.state = MatchState.WAITING

    def _check_round_end(self, current_round: Round) -> bool:
        """Check if a round-ending condition has been met."""
        t_elim = self.t_team.is_eliminated()
        ct_elim = self.ct_team.is_eliminated()
        bomb = current_round.bomb

        if bomb.is_defused:
            current_round.end(TeamSide.COUNTER_TERRORIST, RoundEndReason.BOMB_DEFUSED, self.event_bus)
            return True
        if bomb.is_exploded:
            current_round.end(TeamSide.TERRORIST, RoundEndReason.BOMB_EXPLODED, self.event_bus)
            return True
        if t_elim:
            current_round.end(TeamSide.COUNTER_TERRORIST, RoundEndReason.T_ELIMINATED, self.event_bus)
            return True
        if ct_elim:
            current_round.end(TeamSide.TERRORIST, RoundEndReason.CT_ELIMINATED, self.event_bus)
            return True
        return False

    def play_round(self, simulate_fn=None):
        """
        Runs a single full round.
        simulate_fn(round, t_team, ct_team, event_bus): Optional callback to simulate actions.
        """
        if self.state == MatchState.MATCH_OVER:
            print("INFO: Match is already over.")
            return

        r = Round(len(self.rounds) + 1)
        self.rounds.append(r)
        self.state = MatchState.BUY_PHASE
        self.t_team.reset_for_round()
        self.ct_team.reset_for_round()

        print(f"\n=== ROUND {r.round_number} BUY PHASE ===")
        # Give round start money
        for p in self.t_team.players + self.ct_team.players:
            p.inventory.award_money(2400)

        r.start()
        self.state = MatchState.IN_PROGRESS

        if simulate_fn:
            simulate_fn(r, self.t_team, self.ct_team, self.event_bus)

        if not self._check_round_end(r):
            # Default: time expired -> CT win
            r.end(TeamSide.COUNTER_TERRORIST, RoundEndReason.TIME_EXPIRED, self.event_bus)

        if r.winner_side == TeamSide.TERRORIST:
            self.t_team.round_wins += 1
            for p in self.t_team.players:
                p.inventory.award_money(3250)  # T win reward
        else:
            self.ct_team.round_wins += 1
            for p in self.ct_team.players:
                p.inventory.award_money(3250)  # CT win reward

        if self._is_match_over():
            self.state = MatchState.MATCH_OVER
            self._print_scoreboard()

    def _is_match_over(self) -> bool:
        max_wins = self.MAX_ROUNDS // 2 + 1
        return self.t_team.round_wins >= max_wins or self.ct_team.round_wins >= max_wins

    def get_winner(self) -> Optional[Team]:
        max_wins = self.MAX_ROUNDS // 2 + 1
        if self.t_team.round_wins >= max_wins:
            return self.t_team
        if self.ct_team.round_wins >= max_wins:
            return self.ct_team
        return None

    def _print_scoreboard(self):
        print(f"\n{'='*50}")
        print(f"MATCH OVER | T: {self.t_team.round_wins} - CT: {self.ct_team.round_wins}")
        winner = self.get_winner()
        if winner:
            print(f"WINNER: {winner.side.value}")
        print(f"\n{'PLAYER':<15} {'SIDE':<20} {'K':>4} {'D':>4} {'KD':>6}")
        print("-" * 50)
        for p in self.t_team.players + self.ct_team.players:
            side = p.team.side.value[:3]
            print(f"{p.name:<15} {side:<20} {p.stats.kills:>4} {p.stats.deaths:>4} {p.stats.kd_ratio:>6.2f}")
        print('='*50)

# ==========================================
# Game Manager (Facade)
# ==========================================

class GameManager:
    """Facade for creating and managing a CS match."""
    def __init__(self):
        self.event_bus = EventBus()
        self.match: Optional[Match] = None
        print("INFO: GameManager initialized.")

    def create_match(self, t_names: List[str], ct_names: List[str]) -> Match:
        """Setup teams and create a match."""
        t_team = Team(TeamSide.TERRORIST)
        ct_team = Team(TeamSide.COUNTER_TERRORIST)

        for name in t_names:
            p = Player(name, t_team)
            t_team.add_player(p)

        for name in ct_names:
            p = Player(name, ct_team)
            ct_team.add_player(p)

        self.match = Match(t_team, ct_team, self.event_bus)
        print(f"INFO: Match created. T: {t_names} | CT: {ct_names}")
        return self.match

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Counter-Strike System Design Demo ---\n")

    gm = GameManager()
    gm.event_bus.subscribe(KillFeedListener())

    match = gm.create_match(
        t_names=["Ghost", "Reaper"],
        ct_names=["Shadow", "Forge"]
    )

    t_team = match.t_team
    ct_team = match.ct_team
    bus = match.event_bus

    # Helper strategies
    bodyshot = BodyShotStrategy()
    headshot = HeadshotStrategy()

    # =========================================
    # ROUND 1: CT wins by eliminating all Ts
    # =========================================
    def simulate_round1(r, t, ct, event_bus):
        print("\n--- Combat Phase ---")

        # Buy phase (Round 1 Money: $800 start + $2400 round = $3200 each)
        t.players[0].buy_weapon(WeaponType.RIFLE)   # Ghost: AK-47 ($2700)
        ct.players[0].buy_weapon(WeaponType.RIFLE)  # Shadow: AK-47 ($2700)
        ct.players[1].buy_weapon(WeaponType.RIFLE)  # Forge: AK-47 ($2700) - AWP needs $4750

        # Forge headshots Ghost with AK-47
        ct.players[1].shoot(t.players[0], WeaponType.RIFLE, headshot, event_bus)

        # Shadow shoots Reaper (bodyshot then headshot)
        ct.players[0].shoot(t.players[1], WeaponType.RIFLE, bodyshot, event_bus)
        ct.players[0].shoot(t.players[1], WeaponType.RIFLE, bodyshot, event_bus)

    match.play_round(simulate_round1)
    print(f"\nScore -> T: {t_team.round_wins} | CT: {ct_team.round_wins}")

    # =========================================
    # ROUND 2: T wins by bomb explosion
    # =========================================
    def simulate_round2(r, t, ct, event_bus):
        print("\n--- Combat Phase ---")

        t.players[0].buy_weapon(WeaponType.RIFLE)
        t.players[1].buy_weapon(WeaponType.GRENADE)
        ct.players[0].buy_weapon(WeaponType.PISTOL)

        # T side grenades Shadow
        t.players[1].shoot(ct.players[0], WeaponType.GRENADE, bodyshot, event_bus)
        t.players[1].shoot(ct.players[0], WeaponType.GRENADE, bodyshot, event_bus)  # Grenade can't be used twice

        # Ghost shoots Shadow
        t.players[0].shoot(ct.players[0], WeaponType.RIFLE, bodyshot, event_bus)

        # Forge is still alive - Ghost shoots Forge
        t.players[0].shoot(ct.players[1], WeaponType.RIFLE, headshot, event_bus)

        # Ghost plants the bomb (all CTs dead)
        r.bomb.plant(t.players[0], event_bus)
        r.bomb.explode(event_bus)  # No one to defuse

    match.play_round(simulate_round2)
    print(f"\nScore -> T: {t_team.round_wins} | CT: {ct_team.round_wins}")

    # =========================================
    # ROUND 3: T plants but CT defuses
    # =========================================
    def simulate_round3(r, t, ct, event_bus):
        print("\n--- Combat Phase ---")

        t.players[0].buy_weapon(WeaponType.RIFLE)
        ct.players[0].buy_weapon(WeaponType.RIFLE)

        # Ghost plants bomb while evading CTs
        r.bomb.plant(t.players[0], event_bus)

        # Shadow defuses bomb before explosion
        r.bomb.defuse(ct.players[0], event_bus)

    match.play_round(simulate_round3)
    print(f"\nScore -> T: {t_team.round_wins} | CT: {ct_team.round_wins}")

    print("\n--- Final Player Stats ---")
    for p in t_team.players + ct_team.players:
        print(f"  {p.name}: {p.stats}")
