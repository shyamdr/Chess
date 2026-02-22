# =============================================================================
# Chess AI Engine
#
# NegaMax search with alpha-beta pruning, iterative deepening, transposition
# tables (Zobrist hashing), quiescence search, and an opening book.
#
# Evaluation: material, piece-square tables, pawn structure, king safety,
# piece coordination (bishop pair, connected rooks, knight outposts),
# mobility, center control, rook activity.
#
# See TODO.md for remaining improvements (null move pruning, LMR, etc.)
# =============================================================================

from __future__ import annotations
from multiprocessing import Queue
import json
import os
import time as _time
import random

# =============================================================================
# Debug Logging
# =============================================================================
# Set AI_DEBUG = True in ChessDriver.py config to enable logging.
# Logs are written to ai_debug.json in the project root after each AI move.
AI_DEBUG_LOG_FILE = "ai_debug.json"
_debugLog: list[dict] = []



def _logMove(entry: dict) -> None:
    """Append a debug entry to the log file, preserving previous entries."""
    # Read existing log (survives across multiprocessing calls).
    existing = []
    if os.path.exists(AI_DEBUG_LOG_FILE):
        try:
            with open(AI_DEBUG_LOG_FILE, 'r') as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = []
    existing.append(entry)
    try:
        with open(AI_DEBUG_LOG_FILE, 'w') as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass  # Don't crash the AI over logging



def _boardToStr(gs: object) -> list[list[str]]:
    """Snapshot the board as a simple 2D list for logging."""
    return [row[:] for row in gs.board]
# =============================================================================
# Maps move sequences (as tuples of algebraic move strings) to a list of
# candidate reply moves. The AI picks randomly from candidates for variety.
# Notation: "e2e4" means startFile startRank -> endFile endRank.

_FILE_TO_COL = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6, "h": 7}
_RANK_TO_ROW = {"1": 7, "2": 6, "3": 5, "4": 4, "5": 3, "6": 2, "7": 1, "8": 0}


def _algebraicToMoveID(notation: str) -> int:
    """Convert a 4-char algebraic move like 'e2e4' to a moveID."""
    startCol = _FILE_TO_COL[notation[0]]
    startRow = _RANK_TO_ROW[notation[1]]
    endCol = _FILE_TO_COL[notation[2]]
    endRow = _RANK_TO_ROW[notation[3]]
    return startRow * 1000 + startCol * 100 + endRow * 10 + endCol


# Opening book: keyed by tuple of move notations played so far.
# Values are lists of candidate reply notations.
OPENING_BOOK: dict[tuple[str, ...], list[str]] = {
    # === White's first move ===
    (): ["e2e4", "d2d4", "c2c4", "g1f3"],

    # === Responses to 1.e4 ===
    ("e2e4",): ["e7e5", "c7c5", "e7e6", "c7c6", "d7d5"],

    # -- 1.e4 e5 (Open Game) --
    ("e2e4", "e7e5"): ["g1f3"],
    ("e2e4", "e7e5", "g1f3"): ["b8c6", "g8f6"],
    # Italian Game
    ("e2e4", "e7e5", "g1f3", "b8c6"): ["f1c4", "f1b5", "d2d4"],
    ("e2e4", "e7e5", "g1f3", "b8c6", "f1c4"): ["f8c5", "g8f6"],
    ("e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5"): ["c2c3", "d2d3", "b2b4"],
    # Ruy Lopez
    ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5"): ["a7a6", "g8f6", "f8c5"],
    ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6"): ["b5a4", "b5c6"],
    ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5a4"): ["g8f6", "d7d6"],
    # Scotch Game
    ("e2e4", "e7e5", "g1f3", "b8c6", "d2d4"): ["e5d4"],
    ("e2e4", "e7e5", "g1f3", "b8c6", "d2d4", "e5d4"): ["f3d4"],
    # Petrov Defense
    ("e2e4", "e7e5", "g1f3", "g8f6"): ["f3e5", "b1c3", "d2d4"],

    # -- 1.e4 c5 (Sicilian Defense) --
    ("e2e4", "c7c5"): ["g1f3", "b1c3", "c2c3"],
    ("e2e4", "c7c5", "g1f3"): ["d7d6", "b8c6", "e7e6"],
    # Open Sicilian
    ("e2e4", "c7c5", "g1f3", "d7d6"): ["d2d4"],
    ("e2e4", "c7c5", "g1f3", "d7d6", "d2d4"): ["c5d4"],
    ("e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4"): ["f3d4"],
    ("e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4"): ["g8f6"],
    ("e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4", "g8f6"): ["b1c3"],
    ("e2e4", "c7c5", "g1f3", "b8c6"): ["d2d4", "f1b5"],
    ("e2e4", "c7c5", "g1f3", "e7e6"): ["d2d4"],

    # -- 1.e4 e6 (French Defense) --
    ("e2e4", "e7e6"): ["d2d4"],
    ("e2e4", "e7e6", "d2d4"): ["d7d5"],
    ("e2e4", "e7e6", "d2d4", "d7d5"): ["b1c3", "b1d2", "e4e5"],
    ("e2e4", "e7e6", "d2d4", "d7d5", "b1c3"): ["f8b4", "g8f6", "d5e4"],
    ("e2e4", "e7e6", "d2d4", "d7d5", "e4e5"): ["c7c5"],

    # -- 1.e4 c6 (Caro-Kann) --
    ("e2e4", "c7c6"): ["d2d4"],
    ("e2e4", "c7c6", "d2d4"): ["d7d5"],
    ("e2e4", "c7c6", "d2d4", "d7d5"): ["b1c3", "e4e5", "b1d2"],
    ("e2e4", "c7c6", "d2d4", "d7d5", "b1c3"): ["d5e4"],
    ("e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4"): ["c3e4"],
    # Advance Variation
    ("e2e4", "c7c6", "d2d4", "d7d5", "e4e5"): ["c8f5", "c7c5", "e7e6"],
    ("e2e4", "c7c6", "d2d4", "d7d5", "e4e5", "c8f5"): ["g1f3", "b1c3"],
    ("e2e4", "c7c6", "d2d4", "d7d5", "e4e5", "c7c5"): ["d4c5", "c2c3"],

    # -- 1.e4 d5 (Scandinavian) --
    ("e2e4", "d7d5"): ["e4d5"],
    ("e2e4", "d7d5", "e4d5"): ["d8d5", "g8f6"],
    ("e2e4", "d7d5", "e4d5", "d8d5"): ["b1c3"],

    # === Responses to 1.d4 ===
    ("d2d4",): ["d7d5", "g8f6", "e7e6"],

    # -- 1.d4 d5 (Queen's Gambit) --
    ("d2d4", "d7d5"): ["c2c4", "g1f3"],
    ("d2d4", "d7d5", "c2c4"): ["e7e6", "c7c6", "d5c4"],
    # QGD
    ("d2d4", "d7d5", "c2c4", "e7e6"): ["b1c3", "g1f3"],
    ("d2d4", "d7d5", "c2c4", "e7e6", "b1c3"): ["g8f6"],
    ("d2d4", "d7d5", "c2c4", "e7e6", "b1c3", "g8f6"): ["c1g5", "g1f3"],
    # Slav
    ("d2d4", "d7d5", "c2c4", "c7c6"): ["g1f3", "b1c3"],
    ("d2d4", "d7d5", "c2c4", "c7c6", "g1f3"): ["g8f6"],
    # QGA
    ("d2d4", "d7d5", "c2c4", "d5c4"): ["e2e4", "g1f3"],

    # -- 1.d4 Nf6 (Indian Defenses) --
    ("d2d4", "g8f6"): ["c2c4"],
    ("d2d4", "g8f6", "c2c4"): ["e7e6", "g7g6", "c7c5"],
    # Nimzo-Indian
    ("d2d4", "g8f6", "c2c4", "e7e6"): ["b1c3", "g1f3"],
    ("d2d4", "g8f6", "c2c4", "e7e6", "b1c3"): ["f8b4"],
    # King's Indian
    ("d2d4", "g8f6", "c2c4", "g7g6"): ["b1c3"],
    ("d2d4", "g8f6", "c2c4", "g7g6", "b1c3"): ["f8g7"],
    ("d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "f8g7"): ["e2e4"],

    # === Responses to 1.c4 (English) ===
    ("c2c4",): ["e7e5", "g8f6", "c7c5"],
    ("c2c4", "e7e5"): ["b1c3", "g1f3"],
    ("c2c4", "g8f6"): ["b1c3", "g1f3"],

    # === Responses to 1.Nf3 (Reti) ===
    ("g1f3",): ["d7d5", "g8f6", "c7c5"],
    ("g1f3", "d7d5"): ["c2c4", "g2g3"],
    ("g1f3", "g8f6"): ["c2c4", "g2g3", "d2d4"],
}


def _getBookMove(gs: object, validMoves: list) -> object | None:
    """Look up the current position in the opening book. Returns a matching valid Move or None."""
    # Build the move sequence from the game's move log.
    moveSequence = tuple(
        m.getChessNotation() for m in gs.moveLog
    )
    if moveSequence not in OPENING_BOOK:
        return None
    candidates = OPENING_BOOK[moveSequence]
    # Shuffle candidates for variety, then find the first one that's legal.
    random.shuffle(candidates)
    for notation in candidates:
        targetID = _algebraicToMoveID(notation)
        for move in validMoves:
            if move.moveID == targetID:
                return move
    return None


knightScores = [[ -1, -1,-.5, -.5, -.5,-.5, -1, -1],
                [ -1,-.5,  0,   0,   0,  0,-.5, -1],
                [-.5,  0,.75, .75, .75,.75,  0,-.5],
                [  0, .5,.75,1.25,1.25,.75, .5,  0],
                [  0, .5,.75,1.25,1.25,.75, .5,  0],
                [-.5,  0,.75, .75, .75,.75,  0,-.5],
                [ -1,-.5,  0,   0,   0,  0,-.5, -1],
                [ -1, -1,-.5, -.5, -.5,-.5, -1, -1]]

bishopScores =  [[0.0, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.0],
                 [0.2, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.2],
                 [0.2, 0.4, 0.5, 0.6, 0.6, 0.5, 0.4, 0.2],
                 [0.2, 0.5, 0.5, 0.6, 0.6, 0.5, 0.5, 0.2],
                 [0.2, 0.4, 0.6, 0.6, 0.6, 0.6, 0.4, 0.2],
                 [0.2, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.2],
                 [0.2, 0.5, 0.4, 0.4, 0.4, 0.4, 0.5, 0.2],
                 [0.0, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.0]]

rookScores =  [[ 0.0, 0.1, 0.2, 0.3, 0.3, 0.2, 0.1, 0.0],
               [ 0.5, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.5],
               [-0.1, 0.1, 0.2, 0.2, 0.2, 0.2, 0.1,-0.1],
               [-0.1, 0.1, 0.2, 0.2, 0.2, 0.2, 0.1,-0.1],
               [-0.1, 0.1, 0.2, 0.2, 0.2, 0.2, 0.1,-0.1],
               [-0.1, 0.1, 0.2, 0.2, 0.2, 0.2, 0.1,-0.1],
               [-0.1, 0.0, 0.1, 0.1, 0.1, 0.1, 0.0,-0.1],
               [-0.1, 0.0, 0.1, 0.4, 0.4, 0.1, 0.0,-0.1]]

queenScores = [[0.0, 0.2, 0.2, 0.3, 0.3, 0.2, 0.2, 0.0],
                [0.2, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.2],
                [0.2, 0.4, 0.5, 0.5, 0.5, 0.5, 0.4, 0.2],
                [0.3, 0.4, 0.5, 0.5, 0.5, 0.5, 0.4, 0.3],
                [0.4, 0.4, 0.5, 0.5, 0.5, 0.5, 0.4, 0.3],
                [0.2, 0.5, 0.5, 0.5, 0.5, 0.5, 0.4, 0.2],
                [0.2, 0.4, 0.5, 0.4, 0.4, 0.4, 0.4, 0.2],
                [0.0, 0.2, 0.2, 0.3, 0.3, 0.2, 0.2, 0.0]]

pawnScores =  [[0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8],
               [0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7],
               [0.3, 0.3, 0.4, 0.5, 0.5, 0.4, 0.3, 0.3],
               [.25, .25, 0.3, .45, .45, 0.3, 0.25,.25],
               [0.2, 0.2, 0.2, 0.4, 0.4, 0.2, 0.2, 0.2],
               [.25, .15, 0.1, 0.2, 0.2, 0.1, .15, .25],
               [.25, 0.3, 0.3, 0.0, 0.0, 0.3, 0.3, .25],
               [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]]

piecePositionScores = {"wN": knightScores,
                         "bN": knightScores[::-1],
                         "wB": bishopScores,
                         "bB": bishopScores[::-1],
                         "wQ": queenScores,
                         "bQ": queenScores[::-1],
                         "wR": rookScores,
                         "bR": rookScores[::-1],
                         "wP": pawnScores,
                         "bP": pawnScores[::-1]}


mobilityScores = {
    'N': lambda x: (x-5)*0.3,
    'B': lambda x: (x-8)*0.15,
    'Q': lambda x: (x-12)*0.25,
    'R': lambda x: (x-4)*0.25,
    'P': lambda x: 0,
    'K': lambda x: 0
    }

staticPieceActivityScore = {'K': 0, 'Q': 10, 'R': 6, 'N': 4, 'B': 4, 'P': 1}

pieceScore = {'K':0, 'Q': 9, 'R':5, 'N':3, 'B': 3.15, 'P':1}
CHECKMATE = 1000
STALEMATE = 0

# Pawn structure penalties/bonuses
DOUBLED_PAWN_PENALTY = 0.3
ISOLATED_PAWN_PENALTY = 0.35
PASSED_PAWN_BONUS = [0, 0.1, 0.15, 0.3, 0.5, 0.8, 1.2, 0]  # By rank advancement (index 0/7 unused)

# King safety
PAWN_SHIELD_BONUS = 0.25  # Per pawn in the shield
OPEN_FILE_NEAR_KING_PENALTY = 0.4
SEMI_OPEN_FILE_NEAR_KING_PENALTY = 0.2

# Piece coordination
BISHOP_PAIR_BONUS = 0.5
ROOK_OPEN_FILE_BONUS = 0.3
ROOK_SEMI_OPEN_FILE_BONUS = 0.15

# Evaluation granularity: small bonuses to differentiate "equal" positions
CENTER_CONTROL_BONUS = 0.03  # Per piece/pawn attacking central squares (d4,d5,e4,e5)
KNIGHT_OUTPOST_BONUS = 0.25  # Knight on rank 4-6 supported by pawn, no enemy pawn can attack
ROOK_SEVENTH_RANK_BONUS = 0.3  # Rook on 7th rank (2nd for black)
CONNECTED_ROOKS_BONUS = 0.15   # Both rooks on same rank/file with nothing between

# Transposition table: maps board state -> (depth, score, flag, best_move)
# Flag types for transposition table entries:
TT_EXACT = 0      # Score is exact (no cutoff occurred)
TT_LOWERBOUND = 1 # Score is a lower bound (beta cutoff)
TT_UPPERBOUND = 2 # Score is an upper bound (failed low)
transpositionTable = {}

def getBoardKey(gs: object) -> int:
    """Return the Zobrist hash as the board key (O(1) — maintained incrementally in GameState)."""
    return gs.zobristHash

def findRandomMove(validMoves: list) -> object:
    """Finds a random move as a fallback when the AI cannot determine the best move."""
    return random.choice(validMoves)





def findBestMove(gs: object, validMoves: list, returnQueue: Queue, searchDepth: int = 5, qDepth: int = 6, debug: bool = False) -> None:
    """Entry point for AI search. Checks opening book first, then uses iterative deepening."""
    global nextMove, transpositionTable, _rootMoveScores
    nextMove = None
    _rootMoveScores = {}
    moveNumber = len(gs.moveLog) // 2 + 1
    side = "white" if gs.whiteToMove else "black"

    # Try the opening book before searching.
    bookMove = _getBookMove(gs, validMoves)
    if bookMove is not None:
        if debug:
            _logMove({
                "moveNumber": moveNumber,
                "side": side,
                "source": "book",
                "chosenMove": bookMove.getChessNotation(),
                "board": _boardToStr(gs),
            })
        returnQueue.put(bookMove)
        return

    transpositionTable = {}
    iterationResults = []
    startTime = _time.time()

    # Iterative deepening: search depth 1, 2, ... up to searchDepth.
    for currentDepth in range(1, searchDepth + 1):
        _rootMoveScores = {}
        iterStart = _time.time()
        score = findMoveNegaMaxAlphaBeta(gs, validMoves, currentDepth, currentDepth, -CHECKMATE, CHECKMATE, 1 if gs.whiteToMove else -1, qDepth)
        iterTime = _time.time() - iterStart
        if debug:
            iterationResults.append({
                "depth": currentDepth,
                "bestMove": nextMove.getChessNotation() if nextMove else None,
                "score": round(score, 3),
                "timeSeconds": round(iterTime, 3),
            })

    totalTime = _time.time() - startTime

    if debug:
        # Build top moves from actual root search scores (not TT lookups).
        topMoves = []
        for move in validMoves:
            moveKey = move.getChessNotation()
            moveScore = _rootMoveScores.get(move.moveID)
            topMoves.append({
                "move": moveKey,
                "piece": move.pieceMoved,
                "capture": move.pieceCaptured if move.isCapture else None,
                "score": round(moveScore, 3) if moveScore is not None else "pruned",
            })
        # Sort by score descending (best first).
        topMoves.sort(key=lambda x: x["score"] if isinstance(x["score"], (int, float)) else -9999, reverse=True)

        _logMove({
            "moveNumber": moveNumber,
            "side": side,
            "source": "search",
            "chosenMove": nextMove.getChessNotation() if nextMove else None,
            "chosenPiece": nextMove.pieceMoved if nextMove else None,
            "finalScore": round(score, 3),
            "searchDepth": searchDepth,
            "qDepth": qDepth,
            "totalTimeSeconds": round(totalTime, 3),
            "iterations": iterationResults,
            "topMoves": topMoves[:10],
            "totalMovesConsidered": len(validMoves),
            "ttSize": len(transpositionTable),
            "board": _boardToStr(gs),
        })

    returnQueue.put(nextMove)







def findMoveNegaMaxAlphaBeta(gs: object, validMoves: list, depth: int, maxDepth: int, alpha: float, beta: float, turnMultiplier: int, qDepth: int = 6) -> float:
    """NegaMax search with alpha-beta pruning and transposition table lookup."""
    global nextMove, _rootMoveScores

    isRoot = (depth == maxDepth)

    boardKey = getBoardKey(gs)
    # Skip TT cutoffs at root so every root move gets a real score for debug/selection.
    if not isRoot and boardKey in transpositionTable:
        ttDepth, ttScore, ttFlag, ttMove = transpositionTable[boardKey]
        if ttDepth >= depth:
            if ttFlag == TT_EXACT:
                return ttScore
            elif ttFlag == TT_LOWERBOUND:
                if ttScore >= beta:
                    return ttScore
                if ttScore > alpha:
                    alpha = ttScore
            elif ttFlag == TT_UPPERBOUND:
                if ttScore <= alpha:
                    return ttScore
                if ttScore < beta:
                    beta = ttScore

    if depth == 0:
        return quiescenceSearch(gs, validMoves, alpha, beta, turnMultiplier, qDepth)

    # Order moves: TT best move first, then captures (MVV-LVA), then quiet moves.
    ttEntry = transpositionTable.get(boardKey)
    ttBestMoveID = ttEntry[3].moveID if ttEntry and ttEntry[3] is not None else -1
    orderedMoves = sorted(validMoves,
                          key=lambda m: (0 if m.moveID == ttBestMoveID else (1 if m.isCapture else 2)))

    origAlpha = alpha
    maxScore = -CHECKMATE
    bestMove = None
    for move in orderedMoves:
        gs.makeMove(move)
        nextMoves = gs.getValidMoves()
        score = -findMoveNegaMaxAlphaBeta(gs, nextMoves, depth-1, maxDepth, -beta, -alpha, -turnMultiplier, qDepth)
        if score > maxScore:
            maxScore = score
            bestMove = move
            if isRoot:
                nextMove = move
        gs.undoMove()
        # Record actual score for each root move (for debug logging).
        if isRoot:
            _rootMoveScores[move.moveID] = score
        if maxScore > alpha:
            alpha = maxScore
        if alpha >= beta:
            break

    # Determine bound type for TT storage.
    if maxScore <= origAlpha:
        ttFlag = TT_UPPERBOUND
    elif maxScore >= beta:
        ttFlag = TT_LOWERBOUND
    else:
        ttFlag = TT_EXACT

    transpositionTable[boardKey] = (depth, maxScore, ttFlag, bestMove)
    return maxScore



            




def scoreBoard(gs: object, validMoves: list) -> float:
    """Score the board from white's perspective. Positive = white advantage."""

    if gs.checkmate:
        return -CHECKMATE if gs.whiteToMove else CHECKMATE
    elif gs.stalemate or gs.threefoldRepetition or gs.fiftyMoveRule or gs.insufficientMaterial:
        return STALEMATE

    score = 0.0
    board = gs.board  # Local reference for speed.

    # Single board scan: collect everything we need.
    whitePawnCols = []
    blackPawnCols = []
    whitePawns = []
    blackPawns = []
    whitePawnSet: set[tuple[int, int]] = set()
    blackPawnSet: set[tuple[int, int]] = set()
    totalMaterial = 0
    whiteRooks: list[tuple[int, int]] = []
    blackRooks: list[tuple[int, int]] = []
    whiteKnights: list[tuple[int, int]] = []
    blackKnights: list[tuple[int, int]] = []
    whiteBishops = 0
    blackBishops = 0

    for row in range(8):
        for col in range(8):
            sq = board[row][col]
            if sq == "--":
                continue
            color = sq[0]
            piece = sq[1]

            if piece == 'P':
                if color == 'w':
                    whitePawnCols.append(col)
                    whitePawns.append((row, col))
                    whitePawnSet.add((row, col))
                else:
                    blackPawnCols.append(col)
                    blackPawns.append((row, col))
                    blackPawnSet.add((row, col))
            elif piece == 'R':
                if color == 'w':
                    whiteRooks.append((row, col))
                else:
                    blackRooks.append((row, col))
            elif piece == 'N':
                if color == 'w':
                    whiteKnights.append((row, col))
                else:
                    blackKnights.append((row, col))
            elif piece == 'B':
                if color == 'w':
                    whiteBishops += 1
                else:
                    blackBishops += 1

            if piece not in ('K', 'P'):
                totalMaterial += pieceScore[piece]

            # Material + positional scoring.
            scoreMultiplier = 1 if color == 'w' else -1
            piecePositionScore = 0
            if piece != "K":
                piecePositionScore = piecePositionScores[sq][row][col]
            score += scoreMultiplier * (pieceScore[piece] + piecePositionScore)

    # Mobility (small bonus to avoid one-sided bias).
    mobilityMultiplier = 1 if gs.whiteToMove else -1
    numMoves = len(validMoves)
    score += mobilityMultiplier * numMoves * 0.01

    # Center control.
    centerCount = 0
    for m in validMoves:
        er, ec = m.endRow, m.endCol
        if 3 <= er <= 4 and 3 <= ec <= 4:
            centerCount += 1
    score += mobilityMultiplier * centerCount * CENTER_CONTROL_BONUS

    # Pawn structure scoring.
    score += _scorePawnStructure(whitePawns, whitePawnCols, blackPawnCols, 1)
    score += _scorePawnStructure(blackPawns, blackPawnCols, whitePawnCols, -1)

    # King safety scoring.
    score += _scoreKingSafety(gs, gs.whiteKingLocation, 'w', whitePawns, blackPawns, totalMaterial)
    score -= _scoreKingSafety(gs, gs.blackKingLocation, 'b', blackPawns, whitePawns, totalMaterial)

    # Bishop pair bonus.
    if whiteBishops >= 2:
        score += BISHOP_PAIR_BONUS
    if blackBishops >= 2:
        score -= BISHOP_PAIR_BONUS

    # Rook on open/semi-open file bonus (using already-collected rook positions).
    whiteColSet = set(whitePawnCols)
    blackColSet = set(blackPawnCols)
    for _, c in whiteRooks:
        if c not in whiteColSet:
            score += ROOK_OPEN_FILE_BONUS if c not in blackColSet else ROOK_SEMI_OPEN_FILE_BONUS
    for _, c in blackRooks:
        if c not in blackColSet:
            score -= ROOK_OPEN_FILE_BONUS if c not in whiteColSet else ROOK_SEMI_OPEN_FILE_BONUS

    # Knight outposts.
    for r, c in whiteKnights:
        if 2 <= r <= 4:
            supported = (r + 1, c - 1) in whitePawnSet or (r + 1, c + 1) in whitePawnSet
            if supported:
                canBeAttacked = any(abs(ec - c) == 1 and er > r for er, ec in blackPawns)
                if not canBeAttacked:
                    score += KNIGHT_OUTPOST_BONUS
    for r, c in blackKnights:
        if 3 <= r <= 5:
            supported = (r - 1, c - 1) in blackPawnSet or (r - 1, c + 1) in blackPawnSet
            if supported:
                canBeAttacked = any(abs(ec - c) == 1 and er < r for er, ec in whitePawns)
                if not canBeAttacked:
                    score -= KNIGHT_OUTPOST_BONUS

    # Rook on 7th rank bonus.
    for r, _ in whiteRooks:
        if r == 1:
            score += ROOK_SEVENTH_RANK_BONUS
    for r, _ in blackRooks:
        if r == 6:
            score -= ROOK_SEVENTH_RANK_BONUS

    # Connected rooks bonus.
    if len(whiteRooks) == 2:
        score += _connectedRooksBonus(board, whiteRooks[0], whiteRooks[1])
    if len(blackRooks) == 2:
        score -= _connectedRooksBonus(board, blackRooks[0], blackRooks[1])

    # Hash-based tiebreaker.
    score += (gs.zobristHash % 10000) * 0.00001

    return score




def quiescenceSearch(gs: object, validMoves: list, alpha: float, beta: float, turnMultiplier: int, depthLeft: int) -> float:
    """Continue searching capture moves until the position is quiet, avoiding horizon effect."""
    standPat = turnMultiplier * scoreBoard(gs, validMoves)

    if depthLeft == 0:
        return standPat

    if standPat >= beta:
        return beta
    if standPat > alpha:
        alpha = standPat

    # Only search captures, ordered by MVV-LVA (most valuable victim - least valuable attacker).
    captureMoves = [m for m in validMoves if m.isCapture]
    captureMoves.sort(key=lambda m: pieceScore.get(gs.board[m.endRow][m.endCol][1], 0) - pieceScore.get(m.pieceMoved[1], 0), reverse=True)

    for move in captureMoves:
        gs.makeMove(move)
        nextMoves = gs.getValidMoves()
        score = -quiescenceSearch(gs, nextMoves, -beta, -alpha, -turnMultiplier, depthLeft - 1)
        gs.undoMove()

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha





def _scorePawnStructure(pawns: list[tuple[int, int]], pawnCols: list[int], enemyPawnCols: list[int], multiplier: int) -> float:
    """Evaluate pawn structure: doubled pawns, isolated pawns, passed pawns."""
    score = 0.0
    colCounts = [0] * 8
    for col in pawnCols:
        colCounts[col] += 1

    enemyColSet = set(enemyPawnCols)

    # Doubled pawns: penalize each extra pawn on the same file.
    for count in colCounts:
        if count > 1:
            score -= DOUBLED_PAWN_PENALTY * (count - 1)

    for row, col in pawns:
        # Isolated pawns: no friendly pawns on adjacent files.
        hasNeighbor = (col > 0 and colCounts[col - 1] > 0) or (col < 7 and colCounts[col + 1] > 0)
        if not hasNeighbor:
            score -= ISOLATED_PAWN_PENALTY

        # Passed pawns: no enemy pawns on same or adjacent files.
        isPassed = col not in enemyColSet
        if isPassed and col > 0:
            isPassed = (col - 1) not in enemyColSet
        if isPassed and col < 7:
            isPassed = (col + 1) not in enemyColSet
        if isPassed:
            advancement = (7 - row) if multiplier == 1 else row
            score += PASSED_PAWN_BONUS[advancement]

    return score * multiplier





def _scoreKingSafety(gs: object, kingPos: tuple[int, int], color: str,
                     friendlyPawns: list[tuple[int, int]], enemyPawns: list[tuple[int, int]],
                     totalMaterial: float) -> float:
    """Evaluate king safety based on pawn shield and open files near the king."""
    if totalMaterial < 12:
        return 0.0

    kr, kc = kingPos
    score = 0.0

    # Build set for O(1) pawn lookups.
    friendlyPawnSet = set(friendlyPawns)

    # Pawn shield: check the 2-3 squares directly in front of the king.
    shieldDir = -1 if color == 'w' else 1
    shieldCols = [c for c in (kc - 1, kc, kc + 1) if 0 <= c <= 7]
    for col in shieldCols:
        shieldRow = kr + shieldDir
        shieldRow2 = kr + 2 * shieldDir
        if (shieldRow, col) in friendlyPawnSet or (shieldRow2, col) in friendlyPawnSet:
            score += PAWN_SHIELD_BONUS

    # Penalize open/semi-open files near the king.
    friendlyCols = set(pc for _, pc in friendlyPawns)
    enemyCols = set(pc for _, pc in enemyPawns)
    for col in shieldCols:
        if col not in friendlyCols and col not in enemyCols:
            score -= OPEN_FILE_NEAR_KING_PENALTY
        elif col not in friendlyCols:
            score -= SEMI_OPEN_FILE_NEAR_KING_PENALTY

    return score




def _connectedRooksBonus(board: list[list[str]], rook1: tuple[int, int], rook2: tuple[int, int]) -> float:
    """Return CONNECTED_ROOKS_BONUS if two rooks are on the same rank/file with nothing between."""
    r1, c1 = rook1
    r2, c2 = rook2
    if r1 == r2:
        # Same rank — check columns between.
        minC, maxC = min(c1, c2), max(c1, c2)
        for c in range(minC + 1, maxC):
            if board[r1][c] != "--":
                return 0.0
        return CONNECTED_ROOKS_BONUS
    elif c1 == c2:
        # Same file — check rows between.
        minR, maxR = min(r1, r2), max(r1, r2)
        for r in range(minR + 1, maxR):
            if board[r][c1] != "--":
                return 0.0
        return CONNECTED_ROOKS_BONUS
    return 0.0




