# fmt: off
# ==============================================================================
#  TIC TAC TOE SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌─────────────────────────────────────────────────────────────────────────┐
#  │                         TIC TAC TOE GAME SYSTEM                         │
#  └─────────────────────────────────────────────────────────────────────────┘
#
#  ┌─────────────────────────┐
#  │     TicTacToeGame       │  ← Facade / Controller
#  ├─────────────────────────┤
#  │ + board: Board          │
#  │ + players: Deque[Player]│
#  │ + status: GameState     │
#  ├─────────────────────────┤
#  │ + initialize()          │
#  │ + start_game()          │
#  │ + make_move()           │
#  │ - _check_winner()       │
#  └─────────────────────────┘
#            │          │
#        ....│..........│....
#        .   ▼          ▼   .
#  ┌──────────────┐  ┌─────────────────────────┐
#  │    Board     │  │         Player          │
#  ├──────────────┤  ├─────────────────────────┤
#  │ + size: int  │  │ + id: str               │
#  │ + grid: P[][]│  │ + name: str             │
#  ├──────────────┤  │ + piece: PlayingPiece   │
#  │ + add_piece()│  └─────────────────────────┘
#  │ + is_full()  │               │
#  │ + print()    │               ▼
#  └──────────────┘  ┌─────────────────────────┐
#           │        │      PlayingPiece       │
#           ▼        ├─────────────────────────┤
#  ┌──────────────┐  │ + type: PieceType (Enum)│
#  │  PieceType   │  └────────────┬────────────┘
#  ├──────────────┤               │
#  │  X / O       │     ┌─────────┴─────────┐
#  └──────────────┘     ▼                   ▼
#                 ┌────────────┐      ┌────────────┐
#                 │   PieceX   │      │   PieceO   │
#                 │ (type = X) │      │ (type = O) │
#                 └────────────┘      └────────────┘
#
#  RELATIONSHIPS:
#  TicTacToeGame ──1──> Board                  (manages one board)
#  TicTacToeGame ──*──> Player                 (plays the players in a queue)
#  Player ──1──> PlayingPiece                  (has a chosen piece)
#  Board ──*──> PlayingPiece                   (contains pieces on grid)
#  PieceX / PieceO ──▷── PlayingPiece          (inheritance)
# ==============================================================================
# fmt: on

from abc import ABC
from enum import Enum
from collections import deque
from typing import List, Optional, Tuple

"""
==============================================================================================
TIC TAC TOE SYSTEM LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features Implemented:
1. Dynamic Board Size: N x N grid support.
2. Players & Pieces: Supports extensible playing piece types (X, O).
3. Game Lifecycle: Manages player turns using a queue (Deque) for a Round-Robin pattern.
4. Extensibility: Clean separation between Board, Player, and Game Logic.

Design Patterns:
1. Facade / Controller: TicTacToeGame acts as the central coordinator.
2. Template or Factory (Partial): The PlayingPiece subclasses allow for easy extension 
   if a 3rd piece (e.g. 'Y') were to be added for larger boards.
3. Queue (Data Structure): Uses a double-ended queue to naturally rotate player turns.

Class Design Summary:
---------------------
1. TicTacToeGame (Facade/Controller)
   - Role: Controls game flow, evaluates win/draw conditions after each turn.
2. Board
   - Role: Manages a 2D matrix, tracks free spots, and validates move boundaries.
3. Player
   - Role: POJO containing user details and assigned playing piece.
4. PlayingPiece & Subclasses
   - Role: Represents the token placed on the board.
"""

# ==========================================
# Enums
# ==========================================

class PieceType(Enum):
    X = "X"
    O = "O"


class GameState(Enum):
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"
    DRAW = "DRAW"


# ==========================================
# Pieces / Domain Entities
# ==========================================

class PlayingPiece(ABC):
    def __init__(self, target_type: PieceType):
        self.piece_type = target_type


class PlayingPieceX(PlayingPiece):
    def __init__(self):
        super().__init__(PieceType.X)


class PlayingPieceO(PlayingPiece):
    def __init__(self):
        super().__init__(PieceType.O)


class Player:
    def __init__(self, player_id: str, name: str, playing_piece: PlayingPiece):
        self.player_id = player_id
        self.name = name
        self.playing_piece = playing_piece

    def __repr__(self):
        return f"{self.name} ({self.playing_piece.piece_type.value})"


# ==========================================
# Board System
# ==========================================

class Board:
    def __init__(self, size: int):
        self.size = size
        # 2D Grid initialized with None (representing empty cells)
        self.grid: List[List[Optional[PlayingPiece]]] = [[None for _ in range(size)] for _ in range(size)]

    def add_piece(self, row: int, col: int, piece: PlayingPiece) -> bool:
        """Adds a piece to the board. Returns True if successful, False if invalid/occupied."""
        if row < 0 or row >= self.size or col < 0 or col >= self.size:
            print("ERROR: Move out of bounds.")
            return False

        if self.grid[row][col] is not None:
            print("ERROR: Cell is already occupied.")
            return False

        self.grid[row][col] = piece
        return True

    def get_free_cells(self) -> List[Tuple[int, int]]:
        free_cells = []
        for i in range(self.size):
            for j in range(self.size):
                if self.grid[i][j] is None:
                    free_cells.append((i, j))
        return free_cells

    def print_board(self):
        print("\n--- Current Board ---")
        for i in range(self.size):
            row_str = " | ".join(
                [self.grid[i][j].piece_type.value if self.grid[i][j] else " " for j in range(self.size)]
            )
            print(" " + row_str)
            if i < self.size - 1:
                print("-" * (self.size * 4 - 1))
        print("---------------------\n")


# ==========================================
# Game Controller / Facade
# ==========================================

class TicTacToeGame:
    def __init__(self):
        self.board: Optional[Board] = None
        self.players: deque = deque()
        self.status = GameState.IN_PROGRESS

    def initialize_game(self, p1: Player, p2: Player, board_size: int = 3):
        self.board = Board(board_size)
        self.players.append(p1)
        self.players.append(p2)
        print("INFO: Game Initialized.")

    def play_turn(self, row: int, col: int) -> bool:
        """
        Executes a turn for the current player. Automatically handles queue rotation.
        Returns False if the game is over or move is invalid.
        """
        if self.status != GameState.IN_PROGRESS:
            print(f"INFO: Game is already {self.status.name}")
            return False

        current_player = self.players[0]
        print(f"INFO: Turn -> {current_player.name}")

        success = self.board.add_piece(row, col, current_player.playing_piece)
        if not success:
            return False

        self.board.print_board()

        # Check Win Conditions
        is_winner = self._check_winner(row, col, current_player.playing_piece.piece_type)
        if is_winner:
            print(f"🎉 WINNER: {current_player.name} has won the game!")
            self.status = GameState.FINISHED
            return True

        # Check Draw Condition
        if not self.board.get_free_cells():
            print("🤝 DRAW: No more spaces left.")
            self.status = GameState.DRAW
            return True

        # Rotate the queue logically by popping left and pushing right
        self.players.append(self.players.popleft())
        return True

    def _check_winner(self, row: int, col: int, piece_type: PieceType) -> bool:
        """
        Checks O(1) row/col/diag starting from the latest move to see if someone won.
        """
        row_match = True
        col_match = True
        diag_match = True
        anti_diag_match = True
        n = self.board.size

        for i in range(n):
            # Check Row
            if self.board.grid[row][i] is None or self.board.grid[row][i].piece_type != piece_type:
                row_match = False
            # Check Col
            if self.board.grid[i][col] is None or self.board.grid[i][col].piece_type != piece_type:
                col_match = False
            # Check Main Diagonal
            if self.board.grid[i][i] is None or self.board.grid[i][i].piece_type != piece_type:
                diag_match = False
            # Check Anti-Diagonal
            if self.board.grid[i][n - i - 1] is None or self.board.grid[i][n - i - 1].piece_type != piece_type:
                anti_diag_match = False

        return row_match or col_match or diag_match or anti_diag_match


# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting Tic Tac Toe System Demo ---")

    game = TicTacToeGame()

    # Create pieces
    px = PlayingPieceX()
    po = PlayingPieceO()

    # Create players
    player_1 = Player("P1", "Alice", px)
    player_2 = Player("P2", "Bob", po)

    # Initialize 3x3 board
    game.initialize_game(player_1, player_2, board_size=3)
    game.board.print_board()

    # Simulate Moves
    # Alice places X
    game.play_turn(0, 0)
    # Bob places O
    game.play_turn(1, 1)
    # Alice places X
    game.play_turn(0, 1)
    # Bob places O
    game.play_turn(2, 2)
    # Alice places X
    game.play_turn(0, 2)

    # Output should declare Alice the winner right after she places x at (0,2)!
