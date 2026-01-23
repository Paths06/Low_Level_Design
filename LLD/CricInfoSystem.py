import threading
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List, Dict, Set, Optional

"""
==============================================================================================
CRICINFO (CRICKET INFORMATION SYSTEM) LOW LEVEL DESIGN (PYTHON - PRODUCTION GRADE)
==============================================================================================

Key Requirements:
1. Match Management: Live scores, upcoming schedule, completed results.
2. Search: Teams, Players, Matches.
3. Live Updates: Observer Pattern for real-time score updates.
4. Statistics: Detailed scorecards and player stats.

Design Patterns:
1. Singleton: CricInfoManager (Facade).
2. Observer: For notifying subscribers of live match events.
3. Production Standards: Logging, thread-safety, type hints, and docstrings.

Class Design Diagram:
---------------------
[CricInfoSystem] "1" *-- "*" [Match]
[CricInfoSystem] "1" *-- "*" [Team]
[CricInfoSystem] "1" *-- "*" [Player]
[Match] "1" *-- "2" [Team]
[Match] "1" *-- "1" [Scorecard]
[Match] "1" *-- "*" [Commentary]
[Match] ..|> [Observable]
[Scorecard] "1" *-- "2" [Innings]
[Innings] "1" *-- "*" [BattingStats]
[Innings] "1" *-- "*" [BowlingStats]
[User/Display] ..|> [Observer]

Class Details:
---------------------
1. CricInfoSystem (Singleton)
   - Role: Main controller. Finds matches, players.
   - Methods: searchMatches(), getLiveMatches().

2. Match
   - Role: Represents a single game.
   - Attributes: id, teams, status (LIVE, COMPLETED), scorecard.
   - Methods: updateScore(), addCommentary() [Notify Observers].

3. Scorecard
   - Role: Container for innings and stats.

4. Observer (Interface)
   - Role: Real-time update receiver.
   - Impl: LiveMatchDisplay.
"""

# ==========================================
# Enums & Interfaces
# ==========================================

class MatchStatus(Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"

class MatchFormat(Enum):
    T20 = "T20"
    ODI = "ODI"
    TEST = "TEST"

class MatchObserver(ABC):
    @abstractmethod
    def update(self, match: 'Match', commentary: str):
        pass

class LiveMatchDisplay(MatchObserver):
    """Implementation of MatchObserver for user displays."""
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    def update(self, match: 'Match', commentary: str):
        print(f"INFO: >> [Notification to {self.user_id}] {match.get_teams()}: {commentary}")

# ==========================================
# Domain Models
# ==========================================

class Player:
    def __init__(self, player_id: str, name: str, role: str):
        self.id = player_id
        self.name = name
        self.role = role

class Team:
    def __init__(self, team_id: str, name: str):
        self.id = team_id
        self.name = name
        self.players: List[Player] = []

    def add_player(self, player: Player):
        self.players.append(player)

class BattingStats:
    def __init__(self, player: Player):
        self.player = player
        self.runs = 0
        self.balls_faced = 0
        self.fours = 0
        self.sixes = 0
        self.is_out = False

    def add_runs(self, r: int):
        self.runs += r
        self.balls_faced += 1
        if r == 4: self.fours += 1
        if r == 6: self.sixes += 1

    def set_out(self):
        self.is_out = True
        self.balls_faced += 1

    def __str__(self):
        return f"{self.player.name:<15} {self.runs:>3} ({self.balls_faced})"

class BowlingStats:
    def __init__(self, player: Player):
        self.player = player
        self.overs = 0
        self.balls_bowled = 0
        self.runs_conceded = 0
        self.wickets = 0

    def add_ball(self, runs: int, is_wicket: bool):
        self.balls_bowled += 1
        self.runs_conceded += runs
        if is_wicket: self.wickets += 1
        if self.balls_bowled % 6 == 0:
            self.overs += 1

    def __str__(self):
        return f"{self.player.name:<15} {self.wickets}-{self.runs_conceded} (Overs: {self.overs}.{self.balls_bowled % 6})"

class Innings:
    def __init__(self, innings_id: int, batting_team: Team):
        self.id = innings_id
        self.batting_team = batting_team
        self.batting_stats: Dict[str, BattingStats] = {p.id: BattingStats(p) for p in batting_team.players}
        self.bowling_stats: Dict[str, BowlingStats] = {}
        self.total_runs = 0
        self.total_wickets = 0

    def update(self, batsman: Player, bowler: Player, runs: int, is_wicket: bool):
        self.total_runs += runs
        
        # Update Batsman
        bs = self.batting_stats.get(batsman.id)
        if not bs:
            bs = BattingStats(batsman)
            self.batting_stats[batsman.id] = bs
        
        if is_wicket:
            bs.set_out()
            self.total_wickets += 1
        else:
            bs.add_runs(runs)
        
        # Update Bowler
        bo = self.bowling_stats.get(bowler.id)
        if not bo:
            bo = BowlingStats(bowler)
            self.bowling_stats[bowler.id] = bo
        bo.add_ball(runs, is_wicket)

    def __str__(self):
        lines = [f"\nInnings {self.id}: {self.batting_team.name}",
                 f"Total: {self.total_runs}/{self.total_wickets}",
                 "Batting:"]
        for bs in self.batting_stats.values():
            if bs.balls_faced > 0 or bs.runs > 0:
                lines.append(str(bs))
        lines.append("Bowling:")
        for bo in self.bowling_stats.values():
            lines.append(str(bo))
        return "\n".join(lines)

class Scorecard:
    def __init__(self):
        self.innings_list: List[Innings] = []
        self.commentary_list: List[str] = []
        self.current_innings: Optional[Innings] = None

    def start_innings(self, innings: Innings):
        self.innings_list.append(innings)
        self.current_innings = innings

    def record_ball(self, batsman: Player, bowler: Player, runs: int, is_wicket: bool, comm: str):
        if self.current_innings:
            self.current_innings.update(batsman, bowler, runs, is_wicket)
            self.commentary_list.append(comm)

    def __str__(self):
        if not self.current_innings:
            return "Match not started"
        summary = str(self.current_innings)
        recent = f"\nRecent Commentary: {self.commentary_list[-1]}" if self.commentary_list else ""
        return summary + recent

class Match:
    def __init__(self, match_id: str, team1: Team, team2: Team, start_time: datetime, match_format: MatchFormat):
        self.match_id = match_id
        self.team1 = team1
        self.team2 = team2
        self.start_time = start_time
        self.format = match_format
        self.status = MatchStatus.SCHEDULED
        self.scorecard = Scorecard()
        self.observers: List[MatchObserver] = []
        self.current_striker: Optional[Player] = None
        self.current_bowler: Optional[Player] = None
        self._lock = threading.Lock()

    def start_match(self):
        """Initializes the match state."""
        self.status = MatchStatus.LIVE
        innings = Innings(1, self.team1)
        self.scorecard.start_innings(innings)
        if self.team1.players: self.current_striker = self.team1.players[0]
        if self.team2.players: self.current_bowler = self.team2.players[0]
        print(f"INFO: Match {self.match_id} started: {self.get_teams()}")

    def add_observer(self, observer: MatchObserver):
        with self._lock:
            self.observers.append(observer)

    def notify_observers(self, commentary: str):
        """Thread-safe notification to all subscribers."""
        with self._lock:
            for o in self.observers:
                o.update(self, commentary)

    def update_score(self, runs: int, is_wicket: bool, over_ball: str, comm_text: str):
        """Update scores and notify observers."""
        if not self.current_striker or not self.current_bowler:
            return
        
        self.scorecard.record_ball(self.current_striker, self.current_bowler, runs, is_wicket, f"{over_ball}: {comm_text}")
        
        if self.scorecard.current_innings:
            inns = self.scorecard.current_innings
            score_info = f" (Score: {inns.total_runs}/{inns.total_wickets})"
            self.notify_observers(comm_text + score_info)

    def get_teams(self) -> str:
        return f"{self.team1.name} vs {self.team2.name}"

# ==========================================
# Service Manager (Singleton)
# ==========================================

class CricInfoManager:
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(CricInfoManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.matches: Dict[str, Match] = {}
        self.teams: Dict[str, Team] = {}
        self.players: Dict[str, Player] = {}
        self._initialized = True
        print("INFO: CricInfo Manager initialized.")

    @classmethod
    def get_instance(cls):
        return cls()

    def add_match(self, match: Match):
        self.matches[match.match_id] = match

    def add_team(self, team: Team):
        self.teams[team.id] = team
        for p in team.players:
            self.players[p.id] = p

    def get_live_matches(self) -> List[Match]:
        return [m for m in self.matches.values() if m.status == MatchStatus.LIVE]

    def search_teams(self, name: str) -> List[Team]:
        return [t for t in self.teams.values() if name.lower() in t.name.lower()]

# ==========================================
# Main Execution
# ==========================================

if __name__ == "__main__":
    print("--- Starting CricInfo System Demo ---")
    
    manager = CricInfoManager.get_instance()

    # 1. Setup Data
    p1 = Player("P1", "Virat Kohli", "Batsman")
    p2 = Player("P2", "Jasprit Bumrah", "Bowler")
    p3 = Player("P3", "Steve Smith", "Batsman")
    
    india = Team("IND", "India")
    india.add_player(p1)
    india.add_player(p2)
    
    aus = Team("AUS", "Australia")
    aus.add_player(p3)
    
    manager.add_team(india)
    manager.add_team(aus)

    match = Match("M001", india, aus, datetime.now(), MatchFormat.T20)
    manager.add_match(match)

    # 2. Subscribe Users
    user_display = LiveMatchDisplay("Fan_1")
    match.add_observer(user_display)

    # 3. Simulation
    match.start_match()
    
    match.update_score(0, False, "0.1", "Bumrah to Kohli, no run")
    match.update_score(4, False, "0.2", "Bumrah to Kohli, FOUR runs!")
    match.update_score(6, False, "0.3", "Bumrah to Kohli, SIX runs!")
    match.update_score(0, True, "0.4", "Bumrah to Kohli, OUT! Caught by Smith")
    
    # 4. Search
    print("[System] Searching for 'India'...")
    found_teams = manager.search_teams("India")
    print(f"INFO: Found Teams: {[t.name for t in found_teams]}")
    
    # 5. Result Card
    print("\n[System] Final Match Scorecard Summary:")
    print(match.scorecard)
