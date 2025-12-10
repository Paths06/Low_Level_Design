package com.spotify.lld;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/*
 * ==============================================================================================
 * MUSIC STREAMING SERVICE (SPOTIFY) LOW LEVEL DESIGN
 * ==============================================================================================
 * 
 * Key Features:
 * 1. Catalog Management: Songs, Albums, Artists.
 * 2. Playback: Player functionality (Play, Pause, queue).
 * 3. User Interaction: Playlists, Following Artists.
 * 4. Recommendation: Basic strategy based on Genre.
 * 5. Search: Find content by name.
 * 
 * Design Patterns:
 * 1. Singleton: StreamingService (Facade).
 * 2. Strategy: RecommendationStrategy.
 * 3. State: PlayerState (Playing, Paused).
 * 4. Composite: (Ideally Album contains Songs, Playlist contains Songs).
 * 
 * Class Design Diagram:
 * ---------------------
 * [StreamingService] "1" *-- "1" [Catalog]
 * [StreamingService] "1" *-- "*" [User]
 * [User] "1" *-- "1" [Player]
 * [User] "1" *-- "*" [Playlist]
 * [Catalog] "1" *-- "*" [Artist]
 * [Artist] "1" *-- "*" [Album]
 * [Album] "1" *-- "*" [Song]
 * [Player] ..> [Song]
 *
 * Class Details:
 * ---------------------
 * 1. StreamingService
 *    - Role: Facade.
 *    - Methods: search(), recommend().
 *
 * 2. Player
 *    - Role: Controls audio playback.
 *    - Attributes: currentSong, queue, state.
 *
 * 3. Catalog
 *    - Role: Index of all music.
 * 
 * 4. Song
 *    - Attributes: id, title, duration, genre.
 */

public class MusicStreamingSystem {
    public static void main(String[] args) {
        System.out.println("--- Spotify System Demo ---");
        
        StreamingService spotify = StreamingService.getInstance();

        // 1. Setup Catalog
        Artist a1 = new Artist("A1", "The Weeknd");
        Song s1 = new Song("S1", "Blinding Lights", "Pop", 200);
        Song s2 = new Song("S2", "Starboy", "Pop", 220);
        Album alb1 = new Album("AL1", "After Hours");
        
        alb1.addSong(s1); alb1.addSong(s2);
        a1.addAlbum(alb1);
        
        spotify.catalog.addArtist(a1); // Simplified adding

        // 2. User & Playlist
        User u1 = new User("U1", "Saurabh");
        spotify.registerUser(u1);
        
        Playlist p1 = u1.createPlaylist("Favorites");
        p1.addSong(s1);
        System.out.println("Playlist Created: " + p1.getName() + " Size: " + p1.getSongs().size());

        // 3. Playback
        System.out.println("\n[Action] User starts playing 'Blinding Lights'");
        u1.getPlayer().play(s1);
        u1.getPlayer().pause();

        // 4. Recommendation
        System.out.println("\n[Action] Recommendation for User based on 'Pop' history");
        // Simulate history
        u1.addToHistory(s1);
        List<Song> recs = spotify.getRecommendations(u1);
        System.out.println("Recommended Songs: " + recs.stream().map(Song::getTitle).collect(Collectors.toList()));
    }
}

// ==========================================
// Strategies
// ==========================================

interface RecommendationStrategy {
    List<Song> recommend(User user, Catalog catalog);
}

class GenreRecommendation implements RecommendationStrategy {
    @Override
    public List<Song> recommend(User user, Catalog catalog) {
        // Find most frequent genre in history
        // Simplified: Just pick genre of last played song
        if(user.getHistory().isEmpty()) return Collections.emptyList();
        
        Song lastPlayed = user.getHistory().get(user.getHistory().size()-1);
        String genre = lastPlayed.getGenre();
        
        return catalog.searchSongsByGenre(genre).stream()
                .filter(s -> !s.getId().equals(lastPlayed.getId())) // Don't recommend same song
                .collect(Collectors.toList());
    }
}

// ==========================================
// Domain Models
// ==========================================

class Song {
    String id, title, genre;
    int durationSec;
    public Song(String id, String t, String g, int d) {
        this.id = id; this.title = t; this.genre = g; this.durationSec = d;
    }
    public String getTitle() { return title; }
    public String getId() { return id; }
    public String getGenre() { return genre; }
}

class Album {
    String id, title;
    List<Song> songs;
    public Album(String id, String t) { 
        this.id = id; this.title = t; 
        this.songs = new ArrayList<>();
    }
    public void addSong(Song s) { songs.add(s); }
    public List<Song> getSongs() { return songs; }
}

class Artist {
    String id, name;
    List<Album> albums;
    public Artist(String id, String n) {
        this.id = id; this.name = n;
        this.albums = new ArrayList<>();
    }
    public void addAlbum(Album a) { albums.add(a); }
    public String getName() { return name; }
    public List<Album> getAlbums() { return albums; }
}

class Playlist {
    String name;
    List<Song> songs;
    public Playlist(String n) { this.name = n; this.songs = new ArrayList<>(); }
    public void addSong(Song s) { songs.add(s); }
    public List<Song> getSongs() { return songs; }
    public String getName() { return name; }
}

class Player {
    Song currentSong;
    boolean isPlaying;
    int currentSeekPosition;
    
    public void play(Song s) {
        this.currentSong = s;
        this.isPlaying = true;
        System.out.println("Playing: " + s.getTitle());
    }
    public void pause() {
        this.isPlaying = false;
        System.out.println("Paused: " + (currentSong!=null ? currentSong.getTitle() : "None"));
    }
    public void seek(int seconds) {
        this.currentSeekPosition = seconds;
    }
}

class User {
    String id, name;
    Player player;
    List<Playlist> playlists;
    List<Song> history;

    public User(String id, String name) {
        this.id = id; this.name = name;
        this.player = new Player();
        this.playlists = new ArrayList<>();
        this.history = new ArrayList<>();
    }
    
    public Playlist createPlaylist(String name) {
        Playlist p = new Playlist(name);
        playlists.add(p);
        return p;
    }
    
    public void addToHistory(Song s) { history.add(s); }
    public List<Song> getHistory() { return history; }
    public Player getPlayer() { return player; }
}

// ==========================================
// Catalog & System
// ==========================================

class Catalog {
    Map<String, Artist> artists = new ConcurrentHashMap<>();
    Map<String, Song> songs = new ConcurrentHashMap<>();
    
    public void addArtist(Artist a) {
        artists.put(a.id, a);
        for(Album alb : a.getAlbums()) {
            for(Song s : alb.getSongs()) {
                songs.put(s.id, s);
            }
        }
    }
    
    public List<Song> searchSongsByGenre(String genre) {
        return songs.values().stream()
                .filter(s -> s.getGenre().equalsIgnoreCase(genre))
                .collect(Collectors.toList());
    }
}

class StreamingService {
    private static StreamingService instance;
    public Catalog catalog;
    private Map<String, User> users;
    private RecommendationStrategy recStrategy;

    private StreamingService() {
        catalog = new Catalog();
        users = new HashMap<>();
        recStrategy = new GenreRecommendation();
    }

    public static synchronized StreamingService getInstance() {
        if(instance == null) instance = new StreamingService();
        return instance;
    }

    public void registerUser(User u) { users.put(u.id, u); }
    
    public List<Song> getRecommendations(User user) {
        return recStrategy.recommend(user, catalog);
    }
}
