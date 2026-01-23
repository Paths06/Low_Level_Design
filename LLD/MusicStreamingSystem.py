import threading
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Set, Optional

"""
==============================================================================================
MUSIC STREAMING SERVICE (SPOTIFY) LOW LEVEL DESIGN (PYTHON - PRODUCTION GRADE)
==============================================================================================

Key Features:
1. Catalog Management: Songs, Albums, Artists.
2. Playback: Player functionality (Play, Pause, queue).
3. User Interaction: Playlists, Following Artists.
4. Recommendation: Strategy-based recommendations (e.g., Genre-based).
5. Search: Find content by name or genre.
6. Production Standards: Logging, type hints, docstrings, thread-safety.

Design Patterns:
1. Singleton: StreamingService (Facade).
2. Strategy: RecommendationStrategy.
3. State: Handled via Player status.

Class Design Diagram:
---------------------
[StreamingService] "1" *-- "1" [Catalog]
[StreamingService] "1" *-- "*" [User]
[User] "1" *-- "1" [Player]
[User] "1" *-- "*" [Playlist]
[Catalog] "1" *-- "*" [Artist]
[Artist] "1" *-- "*" [Album]
[Album] "1" *-- "*" [Song]
[Player] ..> [Song]

Class Details:
---------------------
1. StreamingService
   - Role: Facade.
   - Methods: search(), recommend().

2. Player
   - Role: Controls audio playback.
   - Attributes: currentSong, queue, state.

3. Catalog
   - Role: Index of all music.

4. Song
   - Attributes: id, title, duration, genre.
"""

# ==========================================
# Enums
# ==========================================

class PlayerState(Enum):
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"

# ==========================================
# Domain Models
# ==========================================

class Song:
    """Represents a musical track."""
    def __init__(self, song_id: str, title: str, genre: str, duration_sec: int):
        self.id = song_id
        self.title = title
        self.genre = genre
        self.duration_sec = duration_sec

    def __repr__(self):
        return f"Song({self.title})"

class Album:
    """Represents a collection of songs by an artist."""
    def __init__(self, album_id: str, title: str):
        self.id = album_id
        self.title = title
        self.songs: List[Song] = []

    def add_song(self, song: Song):
        self.songs.append(song)

class Artist:
    """Represents a music creator."""
    def __init__(self, artist_id: str, name: str):
        self.id = artist_id
        self.name = name
        self.albums: List[Album] = []

    def add_album(self, album: Album):
        self.albums.append(album)

class Playlist:
    """User-created collection of songs."""
    def __init__(self, name: str):
        self.name = name
        self.songs: List[Song] = []

    def add_song(self, song: Song):
        self.songs.append(song)
        print(f"DEBUG: Added {song.title} to playlist {self.name}")

# ==========================================
# Player Component
# ==========================================

class Player:
    """Controls playback for a specific user."""
    def __init__(self, user_name: str):
        self.user_name = user_name
        self.current_song: Optional[Song] = None
        self.state = PlayerState.STOPPED
        self.seek_position = 0

    def play(self, song: Song):
        self.current_song = song
        self.state = PlayerState.PLAYING
        self.seek_position = 0
        print(f"INFO: [{self.user_name}] Playing: {song.title} ({song.duration_sec}s)")

    def pause(self):
        if self.state == PlayerState.PLAYING:
            self.state = PlayerState.PAUSED
            print(f"INFO: [{self.user_name}] Paused: {self.current_song.title}")

    def stop(self):
        self.state = PlayerState.STOPPED
        self.current_song = None
        print(f"INFO: [{self.user_name}] Stopped playback.")

# ==========================================
# User & Recommendation Logic
# ==========================================

class User:
    """Streaming service user."""
    def __init__(self, user_id: str, name: str):
        self.id = user_id
        self.name = name
        self.player = Player(name)
        self.playlists: Dict[str, Playlist] = {}
        self.history: List[Song] = []

    def create_playlist(self, name: str) -> Playlist:
        p = Playlist(name)
        self.playlists[name] = p
        return p

    def add_to_history(self, song: Song):
        self.history.append(song)

class RecommendationStrategy(ABC):
    @abstractmethod
    def recommend(self, user: User, catalog: 'Catalog') -> List[Song]:
        pass

class GenreRecommendation(RecommendationStrategy):
    """Recommends songs based on the user's most recently played genre."""
    def recommend(self, user: User, catalog: 'Catalog') -> List[Song]:
        if not user.history:
            return []
        
        last_played = user.history[-1]
        genre = last_played.genre
        
        # Simple Logic: Find all songs of same genre in catalog minus history
        history_ids = {s.id for s in user.history}
        recs = [s for s in catalog.songs.values() 
                if s.genre.lower() == genre.lower() and s.id not in history_ids]
        return recs

# ==========================================
# Catalog & Service
# ==========================================

class Catalog:
    """Index of all music content."""
    def __init__(self):
        self.artists: Dict[str, Artist] = {}
        self.songs: Dict[str, Song] = {}
        self._lock = threading.Lock()

    def add_artist(self, artist: Artist):
        with self._lock:
            self.artists[artist.id] = artist
            for album in artist.albums:
                for song in album.songs:
                    self.songs[song.id] = song
            print(f"DEBUG: Catalog updated with artist {artist.name}")

    def search_songs(self, query: str) -> List[Song]:
        return [s for s in self.songs.values() if query.lower() in s.title.lower()]

class StreamingService:
    """Facade for the Music Streaming System (Singleton)."""
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(StreamingService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.catalog = Catalog()
        self.users: Dict[str, User] = {}
        self.rec_strategy: RecommendationStrategy = GenreRecommendation()
        self._initialized = True
        print("INFO: StreamingService (Spotify Hook) initialized.")

    @classmethod
    def get_instance(cls):
        return cls()

    def register_user(self, user: User):
        self.users[user.id] = user
        print(f"INFO: User {user.name} registered.")

    def get_recommendations(self, user: User) -> List[Song]:
        print(f"INFO: Generating recommendations for {user.name}...")
        return self.rec_strategy.recommend(user, self.catalog)

# ==========================================
# Main Execution
# ==========================================

if __name__ == "__main__":
    print("--- Starting Music Streaming Demo ---")
    
    spotify = StreamingService.get_instance()

    # 1. Setup content
    artist1 = Artist("A1", "The Weeknd")
    s1 = Song("S1", "Blinding Lights", "Pop", 200)
    s2 = Song("S2", "Save Your Tears", "Pop", 215)
    s3 = Song("S3", "Starboy", "Electronic", 230)
    alb1 = Album("AL1", "After Hours")
    alb1.add_song(s1)
    alb1.add_song(s2)
    artist1.add_album(alb1)
    
    artist2 = Artist("A2", "Daft Punk")
    s4 = Song("S4", "Get Lucky", "Pop", 240)
    alb2 = Album("AL2", "Random Access Memories")
    alb2.add_song(s4)
    artist2.add_album(alb2)
    
    spotify.catalog.add_artist(artist1)
    spotify.catalog.add_artist(artist2)

    # 2. Setup User
    user1 = User("U1", "Saurabh")
    spotify.register_user(user1)

    # 3. Simulate Interactions
    playlist = user1.create_playlist("Chill Vibes")
    playlist.add_song(s1)
    
    print("[Action] User plays 'Blinding Lights'")
    user1.player.play(s1)
    user1.add_to_history(s1)
    
    print("[Action] User searches for 'Lucky'")
    search_results = spotify.catalog.search_songs("Lucky")
    if search_results:
        print(f"INFO: Search Results: {search_results}")

    # 4. Recommendations
    # User1 has played a 'Pop' song, so expect more Pop (s2, s4)
    recommendations = spotify.get_recommendations(user1)
    print(f"INFO: Recommendations for {user1.name}: {recommendations}")
