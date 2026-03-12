# fmt: off
# ==============================================================================
#  MUSIC STREAMING SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                    MUSIC STREAMING SYSTEM (Spotify-like)                 │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌─────────────────────────┐    ┌─────────────────────────────────────┐
#  │    StreamingService     │    │             MusicCatalog            │
#  │       (Facade)          │    ├─────────────────────────────────────┤
#  ├─────────────────────────┤    │ + artists: Dict[str, Artist]        │
#  │ + catalog: MusicCatalog │───>│ + songs: Dict[str, Song]            │
#  │ + users: Dict           │    ├─────────────────────────────────────┤
#  ├─────────────────────────┤    │ + add_artist()                      │
#  │ + register_user()       │    │ + search(query): List[Song]         │
#  │ + play_song()           │    └──────────────────────────────────────┘
#  │ + get_recommendations() │
#  └─────────────────────────┘    ┌─────────────────────────────────────┐
#                                 │               Artist                │
#  ┌─────────────────────┐        ├─────────────────────────────────────┤
#  │       User          │        │ + id: str                           │
#  ├─────────────────────┤        │ + name: str                         │
#  │ + id: str           │        │ + songs: List[Song]                 │
#  │ + name: str         │        ├─────────────────────────────────────┤
#  │ + player: Player    │        │ + add_song()                        │
#  │ + playlists: Dict   │        └──────────────────────────────────────┘
#  └────────┬────────────┘
#           │ 1 owns              ┌─────────────────────────────────────┐
#           ▼                    │                Song                 │
#  ┌─────────────────────┐       ├─────────────────────────────────────┤
#  │       Player        │       │ + id: str                           │
#  ├─────────────────────┤       │ + title: str                        │
#  │ + current_song      │       │ + artist: Artist                    │
#  │ + history: List[]   │       │ + duration_secs: int                │
#  ├─────────────────────┤       └──────────────────────────────────────┘
#  │ + play(song)        │
#  │ + pause() / stop()  │
#  └─────────────────────┘    ┌─────────────────────────────────────┐
#                             │              Playlist               │
#  ┌───────────────────────┐  ├─────────────────────────────────────┤
#  │ RecommendationStrategy│  │ + id: str                           │
#  │    (ABC/Interface)    │  │ + name: str                         │
#  ├───────────────────────┤  │ + songs: List[Song]                 │
#  │ + recommend(user,     │  ├─────────────────────────────────────┤
#  │   catalog): List[Song]│  │ + add_song()                        │
#  └──────────┬────────────┘  │ + remove_song()                     │
#             │               └──────────────────────────────────────┘
#      ┌──────┴───────┐
#      │              │
#      ▼              ▼
#  ┌──────────────┐  ┌─────────────────────────────────┐
#  │HistoryBased  │  │    GenreBased (extendable)      │
#  │Recommendation│  │    Recommendation               │
#  ├──────────────┤  └─────────────────────────────────┘
#  │ returns songs│
#  │ from unheard │
#  │ artists      │
#  └──────────────┘
#
#  RELATIONSHIPS:
#  StreamingService ──1──> MusicCatalog          (central song/artist registry)
#  StreamingService ──*──> User                  (manages registered users)
#  User ──1──> Player                            (owns a media player)
#  User ──*──> Playlist                          (creates playlists)
#  MusicCatalog ──*──> Artist                    (indexes artists)
#  Artist ──*──> Song                            (owns songs)
#  Playlist ──*──> Song                          (references songs)
#  Player.history ──*──> Song                    (play history)
#  StreamingService uses RecommendationStrategy  (Strategy Pattern)
#  HistoryBasedRecommendation ──▷── RecommendationStrategy (implements)
# ==============================================================================
# fmt: on
import threading
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Optional

"""
==============================================================================================
MUSIC STREAMING SERVICE (SPOTIFY) LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features:
1. Catalog Management: Songs, Albums, Artists.
2. Playback: Player functionality (Play, Pause, Stop).
3. User Interaction: Playlists, Listening History.
4. Recommendation: Strategy-based recommendations (e.g., Genre-based).
5. Search: Find songs by name.

Design Patterns:
1. Facade: StreamingService (Central Controller).
2. Strategy: RecommendationStrategy.
3. State: Handled via PlayerState enum.

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
1. StreamingService (Facade)
   - Role: Facade.
   - Methods: registerUser(), search(), getRecommendations().

2. Player
   - Role: Controls audio playback.
   - Attributes: currentSong, state (PlayerState).
   - Methods: play(), pause(), stop().

3. Catalog
   - Role: Index of all music.
   - Methods: addArtist(), searchSongs().

4. Song
   - Attributes: id, title, genre, duration.
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
    def __init__(self, album_id: str, title: str):
        self.id = album_id
        self.title = title
        self.songs: List[Song] = []

    def add_song(self, song: Song):
        self.songs.append(song)

class Artist:
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
        print(f"INFO: Added '{song.title}' to playlist '{self.name}'")

# ==========================================
# Player Component
# ==========================================

class Player:
    """Controls playback for a specific user."""
    def __init__(self, user_name: str):
        self.user_name = user_name
        self.current_song: Optional[Song] = None
        self.state = PlayerState.STOPPED

    def play(self, song: Song):
        self.current_song = song
        self.state = PlayerState.PLAYING
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
        genre = user.history[-1].genre
        history_ids = {s.id for s in user.history}
        return [s for s in catalog.songs.values()
                if s.genre.lower() == genre.lower() and s.id not in history_ids]

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
            print(f"INFO: Catalog updated with artist {artist.name}")

    def search_songs(self, query: str) -> List[Song]:
        return [s for s in self.songs.values() if query.lower() in s.title.lower()]

class StreamingService:
    """Facade for the Music Streaming System."""
    def __init__(self):
        self.catalog = Catalog()
        self.users: Dict[str, User] = {}
        self.rec_strategy: RecommendationStrategy = GenreRecommendation()
        print("INFO: StreamingService initialized.")

    def register_user(self, user: User):
        self.users[user.id] = user
        print(f"INFO: User {user.name} registered.")

    def get_recommendations(self, user: User) -> List[Song]:
        print(f"INFO: Generating recommendations for {user.name}...")
        return self.rec_strategy.recommend(user, self.catalog)

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting Music Streaming Demo ---")

    spotify = StreamingService()

    # 1. Setup content
    s1 = Song("S1", "Blinding Lights", "Pop", 200)
    s2 = Song("S2", "Save Your Tears", "Pop", 215)
    s3 = Song("S3", "Starboy", "Electronic", 230)
    s4 = Song("S4", "Get Lucky", "Pop", 240)

    alb1 = Album("AL1", "After Hours")
    alb1.add_song(s1)
    alb1.add_song(s2)
    artist1 = Artist("A1", "The Weeknd")
    artist1.add_album(alb1)

    alb2 = Album("AL2", "Random Access Memories")
    alb2.add_song(s4)
    artist2 = Artist("A2", "Daft Punk")
    artist2.add_album(alb2)

    spotify.catalog.add_artist(artist1)
    spotify.catalog.add_artist(artist2)

    # 2. User Actions
    user1 = User("U1", "Saurabh")
    spotify.register_user(user1)

    playlist = user1.create_playlist("Chill Vibes")
    playlist.add_song(s1)

    print("[Action] User plays 'Blinding Lights'")
    user1.player.play(s1)
    user1.add_to_history(s1)

    print("[Action] User searches for 'Lucky'")
    results = spotify.catalog.search_songs("Lucky")
    print(f"INFO: Search Results: {results}")

    # Recommendations: user1 played Pop, so expect more Pop (s2, s4)
    recs = spotify.get_recommendations(user1)
    print(f"INFO: Recommendations for {user1.name}: {recs}")
