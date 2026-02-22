#!/usr/bin/env python3
"""
Replay a benchmark game visually using Pygame.

Usage:
    venv/bin/python tools/replay_game.py benchmark_results/<run>/game_01.json

Controls:
    RIGHT / SPACE  — Next move
    LEFT           — Previous move
    HOME           — Go to start
    END            — Go to end
    A              — Auto-play (toggle, 1 move/sec)
    Q / ESC        — Quit
"""

import sys
import os
import json
import pygame as p

sys.path.insert(0, "src")
import ChessEngine

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BOARD_SIZE = 512
DIMENSION = 8
SQ_SIZE = BOARD_SIZE // DIMENSION
INFO_WIDTH = 300
WINDOW_WIDTH = BOARD_SIZE + INFO_WIDTH
WINDOW_HEIGHT = BOARD_SIZE
FPS = 30
AUTO_PLAY_INTERVAL = 1000  # ms between moves in auto-play

COLOR_LIGHT = (237, 238, 209)
COLOR_DARK = (119, 153, 82)
COLOR_LAST_MOVE = (0, 255, 255)
COLOR_INFO_BG = (70, 70, 70)
COLOR_TEXT = (220, 220, 220)
COLOR_ACTIVE_MOVE = (100, 180, 255)
HIGHLIGHT_ALPHA = 100

IMAGES: dict = {}
FILE_TO_COL = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6, "h": 7}
RANK_TO_ROW = {"1": 7, "2": 6, "3": 5, "4": 4, "5": 3, "6": 2, "7": 1, "8": 0}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_images():
    """Load piece images (same assets as ChessDriver)."""
    pieces = ["bR", "bN", "bB", "bQ", "bK", "bP",
              "wR", "wN", "wB", "wQ", "wK", "wP"]
    for piece in pieces:
        IMAGES[piece] = p.transform.smoothscale(
            p.image.load(f"assets/images/gioco/{piece}.png"),
            (SQ_SIZE, SQ_SIZE),
        )


def uci_to_engine_move(uci_str: str, valid_moves: list) -> "ChessEngine.Move | None":
    """Convert a UCI string like 'e2e4' to a matching ChessEngine.Move."""
    if len(uci_str) < 4:
        return None
    start_col = FILE_TO_COL.get(uci_str[0])
    start_row = RANK_TO_ROW.get(uci_str[1])
    end_col = FILE_TO_COL.get(uci_str[2])
    end_row = RANK_TO_ROW.get(uci_str[3])
    if None in (start_col, start_row, end_col, end_row):
        return None
    target_id = start_row * 1000 + start_col * 100 + end_row * 10 + end_col
    for m in valid_moves:
        if m.moveID == target_id:
            return m
    return None


def draw_board(screen: p.Surface):
    """Draw the 8x8 board squares."""
    colors = [p.Color(COLOR_LIGHT), p.Color(COLOR_DARK)]
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            color = colors[(r + c) % 2]
            p.draw.rect(screen, color, p.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))


def draw_pieces(screen: p.Surface, board: list):
    """Draw pieces on the board."""
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            piece = board[r][c]
            if piece != "--":
                screen.blit(IMAGES[piece], p.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))


def highlight_last_move(screen: p.Surface, gs: "ChessEngine.GameState"):
    """Highlight the last move's start and end squares in cyan."""
    if len(gs.moveLog) > 0:
        last = gs.moveLog[-1]
        s = p.Surface((SQ_SIZE, SQ_SIZE))
        s.set_alpha(HIGHLIGHT_ALPHA)
        s.fill(p.Color(COLOR_LAST_MOVE))
        screen.blit(s, (last.startCol * SQ_SIZE, last.startRow * SQ_SIZE))
        screen.blit(s, (last.endCol * SQ_SIZE, last.endRow * SQ_SIZE))


def draw_info_panel(screen: p.Surface, game_data: dict, moves: list, current_ply: int, auto_play: bool):
    """Draw the info panel to the right of the board with game info and move list."""
    panel_rect = p.Rect(BOARD_SIZE, 0, INFO_WIDTH, WINDOW_HEIGHT)
    p.draw.rect(screen, p.Color(COLOR_INFO_BG), panel_rect)

    font_title = p.font.SysFont("Consolas", 16, bold=True)
    font_small = p.font.SysFont("Consolas", 13)
    font_move = p.font.SysFont("Consolas", 14)

    y = 10
    # Header
    white_name = game_data.get("white", "?")
    black_name = game_data.get("black", "?")
    result = game_data.get("result", "?")
    total = game_data.get("total_plies", len(moves))

    lines = [
        f"White: {white_name}",
        f"Black: {black_name}",
        f"Result: {result}  ({total} plies)",
        f"Ply: {current_ply}/{len(moves)}",
        f"Auto: {'ON' if auto_play else 'OFF (A to toggle)'}",
        "",
        "RIGHT/SPACE = next   LEFT = prev",
        "HOME = start  END = end  Q = quit",
        "",
    ]
    for line in lines:
        txt = font_small.render(line, True, p.Color(COLOR_TEXT))
        screen.blit(txt, (BOARD_SIZE + 8, y))
        y += 18

    # Move list (scrollable region)
    move_area_top = y
    move_area_height = WINDOW_HEIGHT - move_area_top - 5
    # Two columns: move_num. white_uci  black_uci
    col_w = 8
    line_h = 18
    max_visible = move_area_height // line_h

    # Group moves into full moves (pairs)
    full_moves = []
    i = 0
    while i < len(moves):
        entry = {"num": moves[i].get("move_num", i // 2 + 1)}
        entry["white"] = moves[i] if moves[i]["side"] == "w" else None
        entry["black"] = None
        if moves[i]["side"] == "w" and i + 1 < len(moves) and moves[i + 1]["side"] == "b":
            entry["black"] = moves[i + 1]
            i += 2
        elif moves[i]["side"] == "b":
            entry["white"] = None
            entry["black"] = moves[i]
            i += 1
        else:
            i += 1
        full_moves.append(entry)

    # Scroll so current move is visible
    current_full_idx = 0
    for idx, fm in enumerate(full_moves):
        if fm["white"] and fm["white"]["ply"] <= current_ply:
            current_full_idx = idx
        if fm["black"] and fm["black"]["ply"] <= current_ply:
            current_full_idx = idx

    scroll_start = max(0, current_full_idx - max_visible + 3)

    for idx in range(scroll_start, min(len(full_moves), scroll_start + max_visible)):
        fm = full_moves[idx]
        row_y = move_area_top + (idx - scroll_start) * line_h

        num_txt = font_move.render(f"{fm['num']:>3}.", True, p.Color(COLOR_TEXT))
        screen.blit(num_txt, (BOARD_SIZE + col_w, row_y))

        if fm["white"]:
            is_current = fm["white"]["ply"] == current_ply
            color = p.Color(COLOR_ACTIVE_MOVE) if is_current else p.Color(COLOR_TEXT)
            w_time = f" {fm['white']['time']:.1f}s" if fm["white"].get("time") else ""
            w_txt = font_move.render(f"{fm['white']['uci']}{w_time}", True, color)
            screen.blit(w_txt, (BOARD_SIZE + col_w + 40, row_y))

        if fm["black"]:
            is_current = fm["black"]["ply"] == current_ply
            color = p.Color(COLOR_ACTIVE_MOVE) if is_current else p.Color(COLOR_TEXT)
            b_time = f" {fm['black']['time']:.1f}s" if fm["black"].get("time") else ""
            b_txt = font_move.render(f"{fm['black']['uci']}{b_time}", True, color)
            screen.blit(b_txt, (BOARD_SIZE + col_w + 150, row_y))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def replay(game_path: str):
    """Load a game JSON and replay it interactively."""
    with open(game_path) as f:
        game_data = json.load(f)

    moves = game_data.get("moves", [])
    if not moves:
        print(f"No moves found in {game_path}")
        return

    p.init()
    screen = p.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    p.display.set_caption(f"Replay — {os.path.basename(game_path)}")
    clock = p.time.Clock()
    load_images()

    # Pre-build game states for each ply so we can jump freely.
    # states[0] = starting position, states[i] = position after ply i.
    states: list[ChessEngine.GameState] = []
    gs = ChessEngine.GameState()
    states.append(_clone_state(gs))

    for move_data in moves:
        uci = move_data["uci"]
        valid = gs.getValidMoves()
        engine_move = uci_to_engine_move(uci, valid)
        if engine_move is None:
            print(f"  WARNING: Could not map move {uci} at ply {move_data['ply']}, stopping.")
            break
        if engine_move.isPawnPromotionMove:
            promo = uci[4].upper() if len(uci) > 4 else "Q"
            gs.makeMove(engine_move, promo)
        else:
            gs.makeMove(engine_move)
        states.append(_clone_state(gs))

    total_plies = len(states) - 1  # states[0] is start
    current_ply = 0
    auto_play = False
    last_auto_tick = p.time.get_ticks()

    running = True
    while running:
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False
            elif event.type == p.KEYDOWN:
                if event.key in (p.K_q, p.K_ESCAPE):
                    running = False
                elif event.key in (p.K_RIGHT, p.K_SPACE):
                    if current_ply < total_plies:
                        current_ply += 1
                elif event.key == p.K_LEFT:
                    if current_ply > 0:
                        current_ply -= 1
                elif event.key == p.K_HOME:
                    current_ply = 0
                elif event.key == p.K_END:
                    current_ply = total_plies
                elif event.key == p.K_a:
                    auto_play = not auto_play
                    last_auto_tick = p.time.get_ticks()

        # Auto-play
        if auto_play and current_ply < total_plies:
            now = p.time.get_ticks()
            if now - last_auto_tick >= AUTO_PLAY_INTERVAL:
                current_ply += 1
                last_auto_tick = now
            if current_ply >= total_plies:
                auto_play = False

        # Draw
        _draw_state(screen, states[current_ply], game_data, moves, current_ply, auto_play)
        p.display.flip()
        clock.tick(FPS)

    p.quit()


def _clone_state(gs: "ChessEngine.GameState") -> "ChessEngine.GameState":
    """Create a lightweight snapshot of the game state for replay navigation."""
    import copy
    clone = ChessEngine.GameState.__new__(ChessEngine.GameState)
    clone.board = [row[:] for row in gs.board]
    clone.whiteToMove = gs.whiteToMove
    clone.moveLog = list(gs.moveLog)
    clone.inCheck = gs.inCheck
    clone.whiteKingLocation = gs.whiteKingLocation
    clone.blackKingLocation = gs.blackKingLocation
    clone.checkmate = gs.checkmate
    clone.stalemate = gs.stalemate
    return clone


def _draw_state(screen, gs, game_data, moves, current_ply, auto_play):
    """Render one frame: board + pieces + highlights + info panel."""
    draw_board(screen)
    highlight_last_move(screen, gs)
    draw_pieces(screen, gs.board)
    draw_info_panel(screen, game_data, moves, current_ply, auto_play)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: venv/bin/python tools/replay_game.py <game_file.json>")
        print("  e.g. venv/bin/python tools/replay_game.py benchmark_results/20260222_122435_f955386/game_01.json")
        sys.exit(1)
    replay(sys.argv[1])
