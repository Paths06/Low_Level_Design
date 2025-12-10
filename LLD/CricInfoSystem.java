package com.cricinfo.lld;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.stream.Collectors;

/*
 * ==============================================================================================
 * CRICINFO (CRICKET INFORMATION SYSTEM) LOW LEVEL DESIGN
 * ==============================================================================================
 * 
 * Key Requirements:
 * 1. Match Management: Live scores, upcoming schedule, completed results.
 * 2. Search: Teams, Players, Matches.
 * 3. Live Updates: Observer Pattern for real-time score updates.
 * 4. Statistics: detailed Scorecards and Player stats.
 * 
 * Design Patterns:
 * 1. Singleton: CricInfoSystem (Facade).
 * 2. Observer: For notifying subscribers (UI/Users) of live match events/score updates.
 * 3. Strategy: (Implicit) could be used for different Match Types (T20, ODI, Test) rules.
 * 4. Factory: Creating Match objects.
 *
 * Class Design Diagram:
 * ---------------------
 * [CricInfoSystem] "1" *-- "*" [Match]
 * [CricInfoSystem] "1" *-- "*" [Team]
 * [CricInfoSystem] "1" *-- "*" [Player]
 * [Match] "1" *-- "2" [Team]
 * [Match] "1" *-- "1" [Scorecard]
 * [Match] "1" *-- "*" [Commentary]
 * [Match] ..|> [Observable]
 * [Scorecard] "1" *-- "2" [Innings]
 * [Innings] "1" *-- "*" [BattingStats]
 * [Innings] "1" *-- "*" [BowlingStats]
 * [User/Display] ..|> [Observer]
 *
 * Class Details:
 * ---------------------
 * 1. CricInfoSystem (Singleton)
 *    - Role: Main controller. Finds matches, players.
 *    - Methods: searchMatches(), getLiveMatches().
 * 
 * 2. Match
 *    - Role: Represents a single game.
 *    - Attributes: id, teams, status (LIVE, COMPLETED), scorecard.
 *    - Methods: updateScore(), addCommentary() [Notify Observers].
 *
 * 3. Scorecard
 *    - Role: Container for innings and stats.
 *
 * 4. Observer (Interface)
 *    - Role: Real-time update receiver.
 *    - Impl: LiveMatchDisplay.
 */

public class CricInfoSystem {
    public static void main(String[] args) {
        System.out.println("--- CricInfo System Demo ---");
        
        CricInfoManager manager = CricInfoManager.getInstance();

        // 1. Setup Teams and Players
        Player p1 = new Player("P1", "Virat Kohli", "Batsman");
        Player p2 = new Player("P2", "Jasprit Bumrah", "Bowler");
        Player p3 = new Player("P3", "Steve Smith", "Batsman");
        
        Team india = new Team("IND", "India");
        india.addPlayer(p1); india.addPlayer(p2);
        
        Team aus = new Team("AUS", "Australia");
        aus.addPlayer(p3);
        
        manager.addTeam(india);
        manager.addTeam(aus);

        // 2. Create Match
        Match match = new Match("M001", india, aus, new Date(), MatchFormat.T20);
        manager.addMatch(match);

        // 3. User subscribes to Live Updates
        LiveMatchDisplay userDisplay = new LiveMatchDisplay("User1");
        match.addObserver(userDisplay);

        // 4. Simulate Live Match Updates
        System.out.println("\n[System] Match Started: IND vs AUS");
        match.startMatch(); // This initializes innings and current players
        
        match.updateScore(0, false, "0.1", "Bumrah to Kohli, no run");
        match.updateScore(4, false, "0.2", "Bumrah to Kohli, FOUR runs!");
        match.updateScore(6, false, "0.3", "Bumrah to Kohli, SIX runs!");
        match.updateScore(0, true, "0.4", "Bumrah to Kohli, OUT! Caught by Smith");
        
        // 5. Search Functionality
        System.out.println("\n[System] Searching for 'India'...");
        List<Team> teams = manager.searchTeams("India");
        System.out.println("Found Teams: " + teams.size());
        
        // 6. View Scorecard (Snapshot)
        System.out.println("\n[System] Match Scorecard Summary:");
        System.out.println(match.getScorecard());
    }
}

// ==========================================
// Enums & Observers
// ==========================================

enum MatchStatus { SCHEDULED, LIVE, COMPLETED, ABANDONED }
enum MatchFormat { T20, ODI, TEST }

interface MatchObserver {
    void update(Match match, String commentary);
}

class LiveMatchDisplay implements MatchObserver {
    String userId;
    public LiveMatchDisplay(String id) { this.userId = id; }
    
    @Override
    public void update(Match match, String commentary) {
        System.out.println(">> [Notification to " + userId + "] " + match.getTeams() + ": " + commentary);
        // In real app, this would push scores via WebSocket
    }
}

// ==========================================
// Domain Models
// ==========================================

class Player {
    String id;
    String name;
    String role;
    // Stats could be complex object
    
    public Player(String id, String name, String role) {
        this.id = id; this.name = name; this.role = role;
    }
    public String getName() { return name; }
}

class Team {
    String id;
    String name;
    List<Player> players;

    public Team(String id, String name) {
        this.id = id; this.name = name;
        this.players = new ArrayList<>();
    }
    public void addPlayer(Player p) { players.add(p); }
    public String getName() { return name; }
    public List<Player> getPlayers() { return players; }
}

class Match {
    String matchId;
    Team team1;
    Team team2;
    Date startTime;
    MatchFormat format;
    MatchStatus status;
    Scorecard scorecard;
    
    // Observer List (Thread Safe)
    private List<MatchObserver> observers = new CopyOnWriteArrayList<>();
    
    // Tracking current state (Demo simplification)
    private Player currentStriker;
    private Player currentBowler;

    public Match(String id, Team t1, Team t2, Date date, MatchFormat fmt) {
        this.matchId = id; this.team1 = t1; this.team2 = t2;
        this.startTime = date; this.format = fmt;
        this.status = MatchStatus.SCHEDULED;
        this.scorecard = new Scorecard();
    }
    
    public void startMatch() {
        this.status = MatchStatus.LIVE;
        // Demo Init: Assume Team 1 bat first. 
        // Real logic would involve toss.
        this.scorecard.startInnings(new Innings(1, team1));
        
        // Pick first 2 players as batsmen and last as bowler from T2 just for demo
        if(!team1.getPlayers().isEmpty()) this.currentStriker = team1.getPlayers().get(0);
        if(!team2.getPlayers().isEmpty()) this.currentBowler = team2.getPlayers().get(0); 
    }

    public void addObserver(MatchObserver o) { observers.add(o); }
    public void removeObserver(MatchObserver o) { observers.remove(o); }
    
    private void notifyObservers(String commentary) {
        for(MatchObserver o : observers) {
            o.update(this, commentary);
        }
    }

    // Core Logic
    public void setStatus(MatchStatus s) { this.status = s; }
    
    // Updated to handle detailed stats
    public void updateScore(int runs, boolean isWicket, String overBall, String commText) {
        if(currentStriker == null || currentBowler == null) return;

        // Update Internal State
        scorecard.recordBall(currentStriker, currentBowler, runs, isWicket, overBall + ": " + commText);
        
        // Notify
        Innings inns = scorecard.getCurrentInnings();
        notifyObservers(commText + " (Score: " + inns.totalRuns + "/" + inns.totalWickets + ")");
        
        // If out, rotate strike? (Simplified for demo, just keep same)
    }
    
    public String getTeams() { return team1.getName() + " vs " + team2.getName(); }
    public Scorecard getScorecard() { return scorecard; }
    public MatchStatus getStatus() { return status; }
}

// ==========================================
// Detailed Scorecard Domain
// ==========================================

class BattingStats {
    Player player;
    int runs;
    int ballsFaced;
    int fours;
    int sixes;
    boolean isOut;

    public BattingStats(Player p) { this.player = p; }
    public void addRuns(int r) {
        this.runs += r;
        this.ballsFaced++;
        if(r == 4) fours++;
        if(r == 6) sixes++;
    }
    public void setOut() { this.isOut = true; ballsFaced++; } // counting the out ball
    
    @Override
    public String toString() {
        return String.format("%-15s %3d (%d)", player.getName(), runs, ballsFaced);
    }
}

class BowlingStats {
    Player player;
    int overs;
    int ballsBowled;
    int runsConceded;
    int wickets;

    public BowlingStats(Player p) { this.player = p; }
    public void addBall(int runs, boolean isWicket) {
        this.ballsBowled++;
        this.runsConceded += runs;
        if(isWicket) this.wickets++;
        if(ballsBowled % 6 == 0) overs++;
    }
    
    @Override
    public String toString() {
        return String.format("%-15s %d-%d (Overs: %d.%d)", player.getName(), wickets, runsConceded, overs, ballsBowled%6);
    }
}

class Innings {
    int id;
    Team battingTeam;
    Map<String, BattingStats> battingStats = new LinkedHashMap<>();
    Map<String, BowlingStats> bowlingStats = new LinkedHashMap<>();
    int totalRuns;
    int totalWickets;
    
    // In a real system, we would track current Striker and Non-Striker
    
    public Innings(int id, Team battingTeam) {
        this.id = id;
        this.battingTeam = battingTeam;
        // Init stats for all players
        for(Player p : battingTeam.getPlayers()) {
            battingStats.put(p.id, new BattingStats(p));
        }
    }
    
    public void update(Player batsman, Player bowler, int runs, boolean isWicket) {
        totalRuns += runs;
        
        // Update Batsman
        BattingStats bs = battingStats.get(batsman.id);
        if(bs == null) { // Fallback if player not in list
             bs = new BattingStats(batsman);
             battingStats.put(batsman.id, bs);
        }
        
        if (isWicket) {
            bs.setOut();
            totalWickets++;
        } else {
            bs.addRuns(runs);
        }
        
        // Update Bowler
        BowlingStats bo = bowlingStats.get(bowler.id);
        if(bo == null) {
            bo = new BowlingStats(bowler);
            bowlingStats.put(bowler.id, bo);
        }
        bo.addBall(runs, isWicket);
    }
    
    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("Innings ").append(id).append(": ").append(battingTeam.getName()).append("\n");
        sb.append("Total: ").append(totalRuns).append("/").append(totalWickets).append("\n");
        sb.append("Batting:\n");
        battingStats.values().stream().filter(b -> b.ballsFaced > 0 || b.runs > 0).forEach(b -> sb.append(b).append("\n"));
        sb.append("Bowling:\n");
        bowlingStats.values().forEach(b -> sb.append(b).append("\n"));
        return sb.toString();
    }
}

class Scorecard {
    private List<Innings> inningsList = new ArrayList<>();
    private List<String> commentaryList = new ArrayList<>();
    private Innings currentInnings;

    public void startInnings(Innings innings) {
        inningsList.add(innings);
        currentInnings = innings;
    }

    public void recordBall(Player batsman, Player bowler, int runs, boolean isWicket, String comm) {
        if(currentInnings != null) {
            currentInnings.update(batsman, bowler, runs, isWicket);
            commentaryList.add(comm);
        }
    }

    public Innings getCurrentInnings() { return currentInnings; }

    @Override
    public String toString() {
        if(currentInnings == null) return "Match not started";
        return currentInnings.toString() + 
               "\nRecent Commentary: " + 
               (commentaryList.isEmpty()? "" : commentaryList.get(commentaryList.size()-1));
    }
}

// ==========================================
// System Manager (Singleton)
// ==========================================

class CricInfoManager {
    private static CricInfoManager instance;
    private Map<String, Match> matches;
    private Map<String, Team> teams;
    private Map<String, Player> players;

    private CricInfoManager() {
        matches = new ConcurrentHashMap<>();
        teams = new ConcurrentHashMap<>();
        players = new ConcurrentHashMap<>();
    }

    public static synchronized CricInfoManager getInstance() {
        if(instance == null) instance = new CricInfoManager();
        return instance;
    }

    public void addMatch(Match m) { matches.put(m.matchId, m); }
    public void addTeam(Team t) { 
        teams.put(t.id, t); 
        for(Player p : t.getPlayers()) players.put(p.id, p);
    }
    
    // Search Methods
    public List<Match> getLiveMatches() {
        return matches.values().stream()
                .filter(m -> m.getStatus() == MatchStatus.LIVE)
                .collect(Collectors.toList());
    }

    public List<Team> searchTeams(String name) {
        return teams.values().stream()
                .filter(t -> t.getName().toLowerCase().contains(name.toLowerCase()))
                .collect(Collectors.toList());
    }
    
    public Player searchPlayer(String name) {
        return players.values().stream()
                .filter(p -> p.getName().equalsIgnoreCase(name))
                .findFirst().orElse(null);
    }
}
