#!/usr/bin/env python3
"""
ELO Benchmark: Play the Dragon chess engine against Stockfish at various
strength levels under proper time controls and estimate Dragon's ELO.

Usage:
    venv/bin/python tools/benchmark.py                     # Full benchmark
    venv/bin/python tools/benchmark.py --elo 1200          # Single game vs SF-1200
    venv/bin/python tools/benchmark.py --elo 1200 --black  # Single game, Dragon plays black

Results are saved to benchmark_results/<timestamp>_<commit>/ with one JSON
file per game (moves, clocks, PGN) and a summary.json for the full run.
"""

import sys
import os
import json
import time
import datetime
import subprocess
import argparse

sys.path.insert(0, "src")

import chess
import chess.engine
import chess.pgn
import ChessEngine
import ChessAI
from multiprocessing import Queue


# =============================================================================
# Configuration
# =============================================================================
ENGINE_NAME = "Dragon"
STOCKFISH_PATH = "/opt/homebrew/bin/stockfish"
SEARCH_DEPTH = 5
QUIESCENCE_DEPTH = 6
MAX_MOVES_PER_GAME = 200
TIME_PER_SIDE = 600.0  # 10+0 rapid

# Stockfish Skill Levels to test against.
# Skill 0 ≈ 1300, Skill 3 ≈ 1500, Skill 5 ≈ 1700, Skill 8 ≈ 1900,
# Skill 10 ≈ 2000, Skill 12 ≈ 2100, Skill 15 ≈ 2300, Skill 18 ≈ 2600, Skill 20 = full.
SKILL_LEVELS = [
    {"skill": 0,  "approx_elo": 1300},
    {"skill": 3,  "approx_elo": 1500},
    {"skill": 5,  "approx_elo": 1700},
    {"skill": 8,  "approx_elo": 1900},
    {"skill": 10, "approx_elo": 2000},
]
SF_MOVE_TIME = 6.0  # Seconds per move for Stockfish in Skill Level mode.
GAMES_PER_LEVEL = 2  # 1 as white, 1 as black.


def get_git_info() -> dict:
    """Get current git commit hash and branch."""
    info = {"commit": "unknown", "branch": "unknown", "dirty": False}
    try:
        info["commit"] = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
        info["branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], text=True
        ).strip()
        info["dirty"] = len(status) > 0
    except Exception:
        pass
    return info


# =============================================================================
# Bridge: Convert between Dragon's representation and python-chess
# =============================================================================

_COL_TO_FILE = {0: "a", 1: "b", 2: "c", 3: "d", 4: "e", 5: "f", 6: "g", 7: "h"}
_ROW_TO_RANK = {0: "8", 1: "7", 2: "6", 3: "5", 4: "4", 5: "3", 6: "2", 7: "1"}
_FILE_TO_COL = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6, "h": 7}
_RANK_TO_ROW = {"1": 7, "2": 6, "3": 5, "4": 4, "5": 3, "6": 2, "7": 1, "8": 0}


def our_move_to_uci(move: ChessEngine.Move) -> str:
    """Convert a Dragon Move to UCI string (e.g. 'e2e4', 'a7a8q')."""
    uci = (
        _COL_TO_FILE[move.startCol] + _ROW_TO_RANK[move.startRow] +
        _COL_TO_FILE[move.endCol] + _ROW_TO_RANK[move.endRow]
    )
    if move.isPawnPromotionMove:
        uci += "q"
    return uci


def uci_to_our_move(uci_str: str, valid_moves: list) -> ChessEngine.Move | None:
    """Find the matching Move in valid_moves for a UCI string."""
    start_col = _FILE_TO_COL[uci_str[0]]
    start_row = _RANK_TO_ROW[uci_str[1]]
    end_col = _FILE_TO_COL[uci_str[2]]
    end_row = _RANK_TO_ROW[uci_str[3]]
    target_id = start_row * 1000 + start_col * 100 + end_row * 10 + end_col
    for m in valid_moves:
        if m.moveID == target_id:
            return m
    return None


def get_dragon_move(gs: ChessEngine.GameState, valid_moves: list, time_left: float = 0.0) -> ChessEngine.Move | None:
    """Run Dragon's AI search and return the best move.
    
    time_left: Dragon's remaining clock time. Used to calculate time budget per move.
    0 means unlimited (no time management).
    """
    q = Queue()
    # Time management: allocate remaining_time / 30, min 1s, max 15s.
    budget = 0.0
    if time_left > 0:
        budget = max(1.0, min(15.0, time_left / 30.0))
    ChessAI.findBestMove(gs, valid_moves, q, searchDepth=SEARCH_DEPTH, qDepth=QUIESCENCE_DEPTH, debug=False, timeBudget=budget)
    return q.get()


# =============================================================================
# Play one game — prints every move live, saves detailed JSON result file
# =============================================================================

def play_game(stockfish_elo: int, our_color: str, engine: chess.engine.SimpleEngine,
              output_dir: str, game_num: int, skill_level: int | None = None) -> dict:
    """Play one game with move-by-move live output. Saves a detailed JSON per game."""
    if skill_level is not None:
        engine.configure({"UCI_LimitStrength": False, "Skill Level": skill_level})
    else:
        engine.configure({"UCI_LimitStrength": True, "UCI_Elo": stockfish_elo})

    gs = ChessEngine.GameState()
    pc_board = chess.Board()

    # PGN setup.
    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = "ELO Benchmark"
    pgn_game.headers["Site"] = "Local"
    pgn_game.headers["Date"] = datetime.date.today().isoformat()
    pgn_game.headers["Round"] = str(game_num)
    sf_label = f"SF-skill{skill_level}" if skill_level is not None else f"SF-{stockfish_elo}"
    pgn_game.headers["White"] = f"{ENGINE_NAME} (depth {SEARCH_DEPTH})" if our_color == "white" else sf_label
    pgn_game.headers["Black"] = f"{ENGINE_NAME} (depth {SEARCH_DEPTH})" if our_color == "black" else sf_label
    pgn_game.headers["TimeControl"] = f"{int(TIME_PER_SIDE)}+0"
    pgn_node = pgn_game

    dragon_clock = TIME_PER_SIDE
    sf_clock = TIME_PER_SIDE
    dragon_total_think = 0.0
    dragon_moves_count = 0
    move_count = 0
    result = None
    move_log = []  # Detailed per-move log.

    white_name = f"{ENGINE_NAME}" if our_color == "white" else sf_label
    black_name = f"{ENGINE_NAME}" if our_color == "black" else sf_label
    game_path = os.path.join(output_dir, f"game_{game_num:02d}.json")

    def _flush_game_file(status="in_progress", final_result=None):
        """Write current game state to file after every move."""
        game_data = {
            "game_num": game_num,
            "status": status,
            "stockfish_elo": stockfish_elo,
            "dragon_color": our_color,
            "white": white_name,
            "black": black_name,
            "result": final_result or "ongoing",
            "config": {
                "search_depth": SEARCH_DEPTH,
                "quiescence_depth": QUIESCENCE_DEPTH,
                "time_control": f"{int(TIME_PER_SIDE)}+0",
            },
            "dragon_clock": round(dragon_clock, 1),
            "sf_clock": round(sf_clock, 1),
            "total_plies": move_count,
            "moves": move_log,
        }
        if status == "complete":
            game_data["dragon_avg_time"] = round(dragon_total_think / max(dragon_moves_count, 1), 2)
            game_data["dragon_score"] = our_score if final_result else None
            game_data["pgn"] = str(pgn_game)
        with open(game_path, "w") as f:
            json.dump(game_data, f, indent=2)

    _flush_game_file()
    print(f"\n  Game {game_num}: {white_name} vs {black_name} | Writing to {game_path}")
    sys.stdout.flush()

    while move_count < MAX_MOVES_PER_GAME:
        valid_moves = gs.getValidMoves()

        if gs.checkmate:
            result = "0-1" if gs.whiteToMove else "1-0"
            break
        if gs.stalemate or gs.threefoldRepetition or gs.fiftyMoveRule or gs.insufficientMaterial:
            result = "1/2-1/2"
            break
        if not valid_moves:
            result = "1/2-1/2"
            break

        is_dragon_turn = (
            (our_color == "white" and gs.whiteToMove) or
            (our_color == "black" and not gs.whiteToMove)
        )
        full_move_num = move_count // 2 + 1
        side_label = "w" if gs.whiteToMove else "b"

        if is_dragon_turn:
            if dragon_clock <= 0:
                result = "0-1" if our_color == "white" else "1-0"
                print(f"  >>> Dragon lost on time")
                break

            t0 = time.time()
            our_move = get_dragon_move(gs, valid_moves, time_left=dragon_clock)
            elapsed = time.time() - t0
            dragon_clock -= elapsed
            dragon_total_think += elapsed
            dragon_moves_count += 1

            if our_move is None:
                our_move = ChessAI.findRandomMove(valid_moves)

            uci_str = our_move_to_uci(our_move)
            pc_move = chess.Move.from_uci(uci_str)

            if our_move.isPawnPromotionMove:
                gs.makeMove(our_move, "Q")
            else:
                gs.makeMove(our_move)
            pc_board.push(pc_move)
            pgn_node = pgn_node.add_variation(pc_move)
            pgn_node.comment = f"Dragon {dragon_clock:.0f}s"

            move_log.append({
                "ply": move_count + 1, "move_num": full_move_num, "side": side_label,
                "player": "Dragon", "uci": uci_str, "time": round(elapsed, 2),
                "clock": round(dragon_clock, 1),
            })
            _flush_game_file()
            print(f"    {full_move_num}.{'  ' if side_label == 'w' else '..'} {uci_str:<7} Dragon  {elapsed:>5.1f}s  (clock {dragon_clock:>5.0f}s)")
            sys.stdout.flush()

        else:
            if our_color == "white":
                wtime, btime = dragon_clock, sf_clock
            else:
                wtime, btime = sf_clock, dragon_clock

            t0 = time.time()
            if skill_level is not None:
                # Skill Level mode: cap SF thinking to play fast.
                sf_result = engine.play(pc_board, chess.engine.Limit(time=6.0))
            else:
                sf_result = engine.play(
                    pc_board,
                    chess.engine.Limit(white_clock=wtime, black_clock=btime),
                )
            sf_elapsed = time.time() - t0
            sf_clock -= sf_elapsed

            sf_move = sf_result.move
            uci_str = sf_move.uci()

            our_move = uci_to_our_move(uci_str, valid_moves)
            if our_move is None:
                our_move = uci_to_our_move(uci_str[:4], valid_moves)
            if our_move is None:
                print(f"  ERROR: Could not map Stockfish move {uci_str}")
                result = "error"
                break

            if our_move.isPawnPromotionMove:
                promo = uci_str[4].upper() if len(uci_str) > 4 else "Q"
                gs.makeMove(our_move, promo)
            else:
                gs.makeMove(our_move)
            pc_board.push(sf_move)
            pgn_node = pgn_node.add_variation(sf_move)
            pgn_node.comment = f"SF {sf_clock:.0f}s"

            move_log.append({
                "ply": move_count + 1, "move_num": full_move_num, "side": side_label,
                "player": sf_label, "uci": uci_str, "time": round(sf_elapsed, 2),
                "clock": round(sf_clock, 1),
            })
            _flush_game_file()
            print(f"    {full_move_num}.{'  ' if side_label == 'w' else '..'} {uci_str:<7} SF      {sf_elapsed:>5.1f}s  (clock {sf_clock:>5.0f}s)")
            sys.stdout.flush()

        move_count += 1

    if result is None:
        result = "1/2-1/2"

    pgn_game.headers["Result"] = result

    # Score from Dragon's perspective.
    if result == "1-0":
        our_score = 1.0 if our_color == "white" else 0.0
    elif result == "0-1":
        our_score = 0.0 if our_color == "white" else 1.0
    else:
        our_score = 0.5

    tag = {1.0: "WIN", 0.0: "LOSS", 0.5: "DRAW"}[our_score]
    print(f"  Result: {tag} ({result}) in {move_count} plies")
    sys.stdout.flush()

    # Final write with complete data.
    _flush_game_file(status="complete", final_result=result)

    return {
        "game_num": game_num,
        "stockfish_elo": stockfish_elo,
        "dragon_color": our_color,
        "result": result,
        "dragon_score": our_score,
        "total_plies": move_count,
        "dragon_avg_time": round(dragon_total_think / max(dragon_moves_count, 1), 2),
        "dragon_time_left": round(dragon_clock, 1),
        "sf_time_left": round(sf_clock, 1),
        "dragon_moves": dragon_moves_count,
        "game_file": f"game_{game_num:02d}.json",
    }


# =============================================================================
# ELO Estimation
# =============================================================================

def expected_score(our_elo: float, opp_elo: float) -> float:
    return 1.0 / (1.0 + 10 ** ((opp_elo - our_elo) / 400.0))


def estimate_elo(results: list[dict]) -> int:
    if not results:
        return 0
    best_elo, best_error = 800, float("inf")
    for candidate in range(600, 3000):
        total_expected = sum(expected_score(candidate, r["stockfish_elo"]) for r in results)
        total_actual = sum(r["dragon_score"] for r in results)
        error = (total_expected - total_actual) ** 2
        if error < best_error:
            best_error = error
            best_elo = candidate
    return best_elo


def write_summary(run_dir: str, all_results: list[dict], git: dict) -> int:
    """Write/update the JSON summary. Returns estimated ELO."""
    estimated = estimate_elo(all_results)
    summary = {
        "engine": ENGINE_NAME,
        "git": git,
        "timestamp": datetime.datetime.now().isoformat(),
        "config": {
            "search_depth": SEARCH_DEPTH,
            "quiescence_depth": QUIESCENCE_DEPTH,
            "time_control": f"{int(TIME_PER_SIDE)}+0",
            "games_per_level": GAMES_PER_LEVEL,
        },
        "estimated_elo": estimated,
        "overall": {
            "total_games": len(all_results),
            "wins": sum(1 for r in all_results if r["dragon_score"] == 1.0),
            "draws": sum(1 for r in all_results if r["dragon_score"] == 0.5),
            "losses": sum(1 for r in all_results if r["dragon_score"] == 0.0),
            "total_score": sum(r["dragon_score"] for r in all_results),
        },
        "games": [{k: v for k, v in r.items() if k != "moves" and k != "pgn"} for r in all_results],
    }
    with open(os.path.join(run_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    return estimated


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description=f"{ENGINE_NAME} ELO Benchmark")
    parser.add_argument("--elo", type=int, help="Run single game vs this Stockfish ELO (uses UCI_LimitStrength)")
    parser.add_argument("--skill", type=int, help="Run single game at this Skill Level (0-20)")
    parser.add_argument("--black", action="store_true", help="Dragon plays black (default: white)")
    parser.add_argument("--resume", type=str, help="Resume a previous run from its directory path")
    args = parser.parse_args()

    git = get_git_info()

    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

    if args.elo or args.skill is not None:
        # Single game mode.
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join("benchmark_results", f"{timestamp}_{git['commit']}")
        os.makedirs(run_dir, exist_ok=True)

        elo_val = args.elo or 1320
        skill_val = args.skill
        label = f"Skill Level {args.skill}" if args.skill is not None else f"ELO {elo_val}"
        print("=" * 60)
        print(f"  {ENGINE_NAME} vs Stockfish ({label}) — single game")
        print(f"  Git: {git['branch']}@{git['commit']}" + (" (dirty)" if git["dirty"] else ""))
        print(f"  Depth: {SEARCH_DEPTH}, Time: {int(TIME_PER_SIDE)}+0")
        print(f"  Output: {run_dir}/")
        print("=" * 60)

        our_color = "black" if args.black else "white"
        try:
            result = play_game(elo_val, our_color, engine, run_dir, 1, skill_level=skill_val)
        except Exception as e:
            print(f"  ERROR: {e}")
            result = {
                "game_num": 1, "stockfish_elo": elo_val, "dragon_color": our_color,
                "result": "error", "dragon_score": 0.5, "total_plies": 0,
                "dragon_avg_time": 0, "dragon_time_left": 0, "sf_time_left": 0,
                "dragon_moves": 0, "moves": [], "pgn": "",
            }
        all_results = [result]
        write_summary(run_dir, all_results, git)

    else:
        # Full benchmark mode — with optional resume.
        all_results = []
        skip_levels = set()
        game_num = 0

        if args.resume:
            run_dir = args.resume
            # Load completed games from previous run.
            summary_path = os.path.join(run_dir, "summary.json")
            if os.path.exists(summary_path):
                with open(summary_path) as f:
                    prev = json.load(f)
                for g in prev.get("games", []):
                    all_results.append(g)
                    game_num = max(game_num, g["game_num"])
                # Figure out which levels are fully done (2 games each).
                for level_info in SKILL_LEVELS:
                    elo = level_info["approx_elo"]
                    done = [r for r in all_results if r["stockfish_elo"] == elo]
                    if len(done) >= GAMES_PER_LEVEL:
                        skip_levels.add(elo)
                print(f"  Resuming from {run_dir} — {len(all_results)} games loaded, skipping ELOs {skip_levels}")
            # Remove any incomplete game files.
            for fname in os.listdir(run_dir):
                if fname.startswith("game_") and fname.endswith(".json"):
                    fpath = os.path.join(run_dir, fname)
                    with open(fpath) as f:
                        gdata = json.load(f)
                    if gdata.get("status") != "complete":
                        os.remove(fpath)
                        print(f"  Removed incomplete {fname}")
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            run_dir = os.path.join("benchmark_results", f"{timestamp}_{git['commit']}")
            os.makedirs(run_dir, exist_ok=True)

        print("=" * 60)
        print(f"  {ENGINE_NAME} ELO Benchmark")
        print(f"  Git: {git['branch']}@{git['commit']}" + (" (dirty)" if git["dirty"] else ""))
        print(f"  Search: depth {SEARCH_DEPTH}, quiescence {QUIESCENCE_DEPTH}")
        print(f"  Time control: {int(TIME_PER_SIDE)}+0 (rapid)")
        print(f"  SF move time: {SF_MOVE_TIME}s/move")
        print(f"  Levels: {[s['skill'] for s in SKILL_LEVELS]} (approx ELO {[s['approx_elo'] for s in SKILL_LEVELS]})")
        print(f"  Games per level: {GAMES_PER_LEVEL}")
        print(f"  Output: {run_dir}/")
        print("=" * 60)

        for level_info in SKILL_LEVELS:
            skill = level_info["skill"]
            approx_elo = level_info["approx_elo"]

            if approx_elo in skip_levels:
                done = [r for r in all_results if r["stockfish_elo"] == approx_elo]
                score = sum(r["dragon_score"] for r in done)
                print(f"\n  Skill {skill} (~{approx_elo}): already done — {score}/{len(done)}")
                continue

            print(f"\n{'='*60}")
            print(f"  vs Stockfish Skill {skill} (~{approx_elo} ELO)")
            print(f"{'='*60}")

            level_results = []
            for i in range(GAMES_PER_LEVEL):
                our_color = "white" if i % 2 == 0 else "black"
                game_num += 1

                try:
                    result = play_game(approx_elo, our_color, engine, run_dir, game_num, skill_level=skill)
                except Exception as e:
                    print(f"  ERROR: {e}")
                    result = {
                        "game_num": game_num, "stockfish_elo": approx_elo, "dragon_color": our_color,
                        "result": "error", "dragon_score": 0.5, "total_plies": 0,
                        "dragon_avg_time": 0, "dragon_time_left": 0, "sf_time_left": 0,
                        "dragon_moves": 0, "moves": [], "pgn": "",
                    }

                level_results.append(result)
                all_results.append(result)
                write_summary(run_dir, all_results, git)

            score = sum(r["dragon_score"] for r in level_results)
            print(f"\n  Score vs Skill {skill} (~{approx_elo}): {score}/{len(level_results)}")

    engine.quit()

    estimated = write_summary(run_dir, all_results, git)

    print(f"\n{'='*60}")
    print(f"  ESTIMATED ELO: {estimated}")
    w = sum(1 for r in all_results if r["dragon_score"] == 1.0)
    d = sum(1 for r in all_results if r["dragon_score"] == 0.5)
    l = sum(1 for r in all_results if r["dragon_score"] == 0.0)
    print(f"  Total: {w}W / {d}D / {l}L  ({sum(r['dragon_score'] for r in all_results)}/{len(all_results)})")
    print(f"  Results: {run_dir}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
