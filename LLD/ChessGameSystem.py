# fmt: off
# ==============================================================================
#  CHESS GAME SYSTEM — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌─────────────────────────────────────────────────────────────────────────┐
#  │                            CHESS GAME SYSTEM                            │
#  └─────────────────────────────────────────────────────────────────────────┘
#
#  ┌─────────────────────────┐
#  │       ChessGame         │  ← Facade / Controller
#  ├─────────────────────────┤
#  │ + board: Board          │
#  │ + players: Player[2]    │
#  │ + current_turn: Player  │
#  │ + status: GameStatus    │
#  │ + moves_list: List[Move]│
#  ├─────────────────────────┤
#  │ + player_move()         │
#  │ + end_game()            │
#  │ - _is_checkmate()       │
#  └─────────────────────────┘
#            │          │
#        ....│..........│....
#        .   ▼          ▼   .
#  ┌──────────────┐  ┌─────────────────────────┐
#  │    Board     │  │         Player          │
#  ├──────────────┤  ├─────────────────────────┤
#  │ + boxes:     │  │ + account: Account      │
#  │   Box[8][8]  │  │ + color: Color          │
#  ├──────────────┤  ├─────────────────────────┤
#  │ + reset()    │  │ + make_move()           │
#  │ + get_box()  │  └─────────────────────────┘
#  └──────────────┘               │
#           │                     ▼
#           ▼             ┌──────────────┐
#  ┌──────────────┐       │     Move     │  ← Command Pattern
#  │     Box      │       ├──────────────┤
#  ├──────────────┤       │ + start: Box │
#  │ + x: int     │       │ + end: Box   │
#  │ + y: int     │       │ + piece_moved│
#  │ + piece:Piece│       │ + piece_killed
#  └──────────────┘       └──────────────┘
#           │
#           ▼
#  ┌─────────────────────────┐
#  │       Piece (ABC)       │
#  ├─────────────────────────┤
#  │ + killed: bool          │
#  │ + white: bool           │
#  ├─────────────────────────┤
#  │ + can_move(board, start,│
#  │            end): bool   │
#  └─┬──┬──┬──┬──┬───────────┘
#    │  │  │  │  │
#    ▼  ▼  ▼  ▼  ▼ (Subclasses)
#   King, Queen, Knight, Bishop, Rook, Pawn
#
#  RELATIONSHIPS:
#  ChessGame ──1──> Board                 (manages the board)
#  ChessGame ──*──> Move                  (keeps track of move history)
#  Board ──8x8──> Box                     (contains 64 boxes)
#  Box ──1──> Piece                       (can hold 1 or 0 piece)
#  Move ──2──> Box                        (stores start and end box)
#  King/Queen/etc ──▷── Piece             (implements abstract movement rules)
# ==============================================================================
# fmt: on

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional

"""
==============================================================================================
CHESS GAME SYSTEM LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features Implemented:
1. Core Board & Box: 8x8 grid of Boxes, each potentially holding a Piece.
2. Pieces & Movement Rules: Strategy/Template method pattern where `Piece` is an ABC 
   and each specific piece (Knight, King, etc.) implements its own `can_move` logic.
3. Move History: Command-like pattern capturing `Move` objects (Start Box, End Box, 
   Piece moved, Piece killed). Makes it easy to implement undo/redo or replay games.
4. Game Lifecycle & Players: Facade coordinating turns and game states (Active, Checkmate, etc.).

Design Patterns:
1. Facade / Controller: `ChessGame` coordinates between the Player, Board, and Moves.
2. Factory/Template Method: Specific initialization of pieces on the `Board.reset_board()`.
3. Command Pattern (Data Structure): `Move` encapsulates all data to execute or record a move.

"""

# ==========================================
# Enums & Models
# ==========================================

class Color(Enum):
    WHITE = "WHITE"
    BLACK = "BLACK"


class GameStatus(Enum):
    ACTIVE = "ACTIVE"
    BLACK_WIN = "BLACK_WIN"
    WHITE_WIN = "WHITE_WIN"
    FORFEIT = "FORFEIT"
    STALEMATE = "STALEMATE"
    RESIGNATION = "RESIGNATION"


# ==========================================
# Domain Entities: Person & Player
# ==========================================

class Account:
    def __init__(self, username: str, email: str):
        self.username = username
        self.email = email


class Player:
    def __init__(self, account: Account, color: Color):
        self.account = account
        self.color = color


# ==========================================
# Core Mechanisms: Pieces
# ==========================================

class Piece(ABC):
    def __init__(self, is_white: bool):
        self.is_white = is_white
        self.is_killed = False

    @abstractmethod
    def can_move(self, board: 'Board', start: 'Box', end: 'Box') -> bool:
        """
        Abstract method. Each concrete piece will dictate if a move from 'start' to 'end' is logically valid 
        based on how that specific piece moves (e.g. Knight in L-shape).
        """
        pass

    def __repr__(self):
        return f"{'W' if self.is_white else 'B'}_{self.__class__.__name__[:2]}"


class King(Piece):
    def __init__(self, is_white: bool):
        super().__init__(is_white)
        self.castling_done = False

    def can_move(self, board: 'Board', start: 'Box', end: 'Box') -> bool:
        # Basic logical movement for a King (1 square in any direction)
        if end.piece and end.piece.is_white == self.is_white:
            return False

        x_diff = abs(start.x - end.x)
        y_diff = abs(start.y - end.y)

        if x_diff + y_diff == 1 or (x_diff == 1 and y_diff == 1):
            return True

        # Validation for castling would go here...
        return False


class Knight(Piece):
    def __init__(self, is_white: bool):
        super().__init__(is_white)

    def can_move(self, board: 'Board', start: 'Box', end: 'Box') -> bool:
        if end.piece and end.piece.is_white == self.is_white:
            return False

        x_diff = abs(start.x - end.x)
        y_diff = abs(start.y - end.y)

        # L shaped movement: 2 in one direction and 1 in another
        return (x_diff == 2 and y_diff == 1) or (x_diff == 1 and y_diff == 2)


# (Other pieces: Queen, Bishop, Rook, Pawn would be implemented similarly)

# ==========================================
# Core Mechanisms: Board & Move
# ==========================================

class Box:
    def __init__(self, x: int, y: int, piece: Optional[Piece]):
        self.x = x
        self.y = y
        self.piece = piece

    def __repr__(self):
        return f"[{self.piece if self.piece else '    '}]"


class Move:
    def __init__(self, player: Player, start: Box, end: Box):
        self.player = player
        self.start = start
        self.end = end
        self.piece_moved = start.piece
        self.piece_killed = end.piece


class Board:
    def __init__(self):
        # 8 x 8 Grid
        self.boxes: List[List[Optional[Box]]] = [[None for _ in range(8)] for _ in range(8)]
        self.reset_board()

    def get_box(self, x: int, y: int) -> Box:
        if x < 0 or x > 7 or y < 0 or y > 7:
            raise Exception("Index out of bound")
        return self.boxes[x][y]

    def reset_board(self):
        # Initialize White Pieces
        self.boxes[0][0] = Box(0, 0, None)  # Should put White Rook
        self.boxes[0][1] = Box(0, 1, Knight(True))
        # ... Init rest of the board exactly like standard chess setup...

        # Dummy initialization for rest of boxes to prevent NoneType errors in the demo
        for i in range(8):
            for j in range(8):
                if self.boxes[i][j] is None:
                    self.boxes[i][j] = Box(i, j, None)
                    
        # Initialize Black Pieces
        self.boxes[7][1] = Box(7, 1, Knight(False))
        self.boxes[7][4] = Box(7, 4, King(False))

    def print_board(self):
        print("\n   0     1     2     3     4     5     6     7")
        print("  " + "-" * 49)
        for i in range(8):
            row_str = f"{i} |"
            for j in range(8):
                box = self.boxes[i][j]
                piece_str = str(box.piece) if box.piece else "    "
                row_str += f"{piece_str}|"
            print(row_str)
            print("  " + "-" * 49)
        print()


# ==========================================
# Facade: Game Controller
# ==========================================

class ChessGame:
    def __init__(self, p1: Player, p2: Player):
        self.players = [p1, p2]
        self.board = Board()
        self.current_turn: Player = p1 if p1.color == Color.WHITE else p2
        self.status = GameStatus.ACTIVE
        self.moves_played: List[Move] = []

    def is_end(self) -> bool:
        return self.status != GameStatus.ACTIVE

    def player_move(self, player: Player, start_x: int, start_y: int, end_x: int, end_y: int) -> bool:
        if self.is_end():
            print("Game has already ended.")
            return False

        if player != self.current_turn:
            print("Not your turn!")
            return False

        start_box = self.board.get_box(start_x, start_y)
        end_box = self.board.get_box(end_x, end_y)
        source_piece = start_box.piece

        if not source_piece:
            print("Source piece is empty.")
            return False

        # Check if the piece matches the color of the player
        is_player_white = player.color == Color.WHITE
        if source_piece.is_white != is_player_white:
            print("You cannot move the opponent's pieces.")
            return False

        # Validate piece-specific movement logic
        if not source_piece.can_move(self.board, start_box, end_box):
            print("Invalid move for this piece.")
            return False

        # Create move command
        move = Move(player, start_box, end_box)

        # Execute move
        dest_piece = end_box.piece
        if dest_piece:
            dest_piece.is_killed = True
            print(f">>> {player.account.username} killed {dest_piece}!")
            
            # End game if King killed
            if isinstance(dest_piece, King):
                self.status = GameStatus.WHITE_WIN if is_player_white else GameStatus.BLACK_WIN
                print(f"🎉 {player.account.username} has won by Checkmate!")

        # Update board
        self.moves_played.append(move)
        end_box.piece = source_piece
        start_box.piece = None

        # Next turn
        self.current_turn = self.players[0] if self.current_turn == self.players[1] else self.players[1]
        return True


# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Starting Chess System Demo ---")

    # Create players
    p1 = Player(Account("Alice", "alice@example.com"), Color.WHITE)
    p2 = Player(Account("Bob", "bob@example.com"), Color.BLACK)

    # Init game
    game = ChessGame(p1, p2)
    game.board.print_board()

    # Bob's White Knight attempts a move (Fails, not Bob's turn)
    print("\n[Action] Bob tries to move White Knight.")
    game.player_move(p2, 0, 1, 2, 2)

    # Alice's White Knight makes a valid L valid move
    print("\n[Action] Alice moves White Knight to (2, 2).")
    success = game.player_move(p1, 0, 1, 2, 2)
    if success:
        game.board.print_board()

    # Bob's Black Knight tries an invalid move (Straight line)
    print("\n[Action] Bob tries invalid move with Black Knight to (7, 2).")
    game.player_move(p2, 7, 1, 7, 2)

    # Bob's Black Knight makes valid L move
    print("\n[Action] Bob moves Black Knight to (5, 2).")
    game.player_move(p2, 7, 1, 5, 2)
    game.board.print_board()

