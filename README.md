# Chess

## Demonstration

https://github.com/user-attachments/assets/84103de9-5a55-41f6-8db8-69a17702313a

## Overview

A desktop chess game built with Python and Pygame. Supports human-vs-human, human-vs-AI, and AI-vs-AI play. Features full chess rule enforcement, move animation, game clocks, and an AI opponent that plays at a competitive amateur level.

The project started as a follow-along of [Eddie Sharick's YouTube series](https://www.youtube.com/channel/UCaEohRz5bPHywGBwmR18Qww) and has since been significantly extended with a much stronger AI engine, draw detection, time controls, and a polished UI.

## AI Engine

The AI is the heart of this project. It's a from-scratch chess engine written in pure Python — no external chess libraries, no neural networks, no borrowed evaluation code.

### Search

- **NegaMax with alpha-beta pruning** — the core search algorithm. Explores the game tree efficiently by pruning branches that can't possibly affect the result.
- **Iterative deepening** — searches depth 1, then 2, then 3... up to the configured max (default 5). This gives better move ordering from shallower searches and ensures the AI always has a move ready even if time runs out.
- **Transposition table** — caches previously evaluated positions using Zobrist hashing. When the same position is reached via different move orders, the cached result is reused instead of re-searching. Stores exact scores, lower bounds (beta cutoffs), and upper bounds (failed low).
- **Quiescence search** — extends the search on capture sequences to avoid the "horizon effect" where the AI stops searching right before a big capture happens. Searches captures up to 6 plies deep beyond the main search.
- **Opening book** — a hand-curated database of ~80 opening lines covering the Italian Game, Ruy Lopez, Sicilian, French, Caro-Kann, Queen's Gambit, Indian defenses, and more. The AI plays book moves instantly with some randomization for variety.

### Evaluation

The evaluation function scores positions from white's perspective using:

- **Material counting** — standard piece values (Q=9, R=5, B=3.15, N=3, P=1)
- **Piece-square tables** — positional bonuses/penalties for each piece type on each square. Knights are rewarded for central placement, rooks for the 7th rank, pawns for advancement.
- **Pawn structure** — penalties for doubled pawns and isolated pawns; bonuses for passed pawns scaled by how far advanced they are.
- **King safety** — pawn shield detection around the king, penalties for open/semi-open files near the king. Scales down in endgames when king safety matters less.
- **Piece coordination** — bishop pair bonus, connected rooks bonus, knight outpost detection (knight supported by pawn, can't be attacked by enemy pawns).
- **Mobility** — small bonus per legal move to encourage active piece play.
- **Center control** — bonus for moves targeting the central squares (d4, d5, e4, e5).
- **Rook activity** — bonuses for rooks on open and semi-open files.

### Performance

The engine is pure Python, so raw speed can't compete with C/C++ engines. Instead, it relies on smart pruning and caching:

- **Zobrist hashing** — O(1) incremental position hashing. Instead of converting the entire board to a tuple every time (O(64)), the hash is updated with a few XOR operations on each move/unmove. This eliminated one of the biggest bottlenecks in the search.
- **Move ordering** — TT best move first, then captures, then quiet moves. Good move ordering makes alpha-beta pruning cut off more branches.
- **`__slots__` on Move class** — reduces memory overhead for the millions of Move objects created during search.
- **Optimized evaluation** — single board scan collects all piece positions, pawn columns, and material counts in one pass. No redundant loops.

At depth 5 with quiescence, the AI typically takes 2-8 seconds per move in the middlegame on a modern machine.

### Debug Tooling

When `AI_DEBUG = True` in the config, the AI writes detailed JSON logs to `ai_debug.json` after each move, including:
- Score at each iterative deepening level
- Top 10 candidate moves with scores
- Search time per depth iteration
- Transposition table size
- Full board state

This enables post-game analysis to understand why the AI made specific decisions.

## Features

- Full chess rule enforcement: castling, en passant, pawn promotion, check/checkmate/stalemate
- Draw detection: insufficient material, threefold repetition, 50-move rule
- Pawn promotion UI with piece selection (Q/R/B/N)
- Move animation with lightning-trail effect
- Move highlighting (last move, selected piece, valid destinations, check)
- Move log panel with algebraic notation
- Per-side game clocks (default 10 minutes)
- Sound effects on moves
- Undo with `Z`, reset with `Esc`

## Project Structure

```
├── src/
│   ├── ChessDriver.py    # Entry point, Pygame UI, rendering, animation, game loop
│   ├── ChessEngine.py    # Game state, move generation, validation, Zobrist hashing
│   └── ChessAI.py        # AI search, evaluation, opening book, debug logging
├── assets/
│   ├── images/gioco/     # Piece sprites ({color}{piece}.png)
│   └── sounds/           # Move sound effects
├── requirements.txt
└── README.md
```

## Configuration

All key settings are at the top of `src/ChessDriver.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `PLAYER_ONE` | `True` | `True` = human plays white, `False` = AI plays white |
| `PLAYER_TWO` | `False` | `True` = human plays black, `False` = AI plays black |
| `AI_SEARCH_DEPTH` | `5` | Main search depth (higher = stronger but slower) |
| `AI_QUIESCENCE_DEPTH` | `6` | Extra depth for capture-only search |
| `AI_DEBUG` | `True` | Write AI decision logs to `ai_debug.json` |
| `CLOCK_TIME_SECONDS` | `600` | Time per side in seconds (600 = 10 min) |

## Installation

```sh
git clone https://github.com/shyamdr/Chess.git
cd Chess
pip install -r requirements.txt
```

## Usage

```sh
python src/ChessDriver.py
```

### Controls

| Key | Action |
|-----|--------|
| `Z` | Undo move (undoes 2 moves in human-vs-AI mode) |
| `Esc` | Reset board and clocks |
| `T` | Load debug test position (dev only) |

## Acknowledgements

- Original tutorial by [Eddie Sharick](https://www.youtube.com/channel/UCaEohRz5bPHywGBwmR18Qww)
- UI inspired by [lichess.org](https://lichess.org) and [chess.com](https://chess.com)
- Piece sprites from the Gioco set

## License

MIT License. See [LICENSE](LICENSE) for details.
