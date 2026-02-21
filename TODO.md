# Chess Project — TODO

## Completed
- [x] Bug: Remove dead `Move.pgn` class variable
- [x] Bug: Remove stray `print()` in AI `scoreBoard`
- [x] Bug: Fix rook mobility score typo (250 → 0.25) — was already fixed
- [x] Bug: Fix black rook castling rights checking wrong row (7 → 0)
- [x] Bug: Fix mobility/activity accumulation in `scoreBoard`
- [x] Code quality: Remove dead `moveOrdering` method and no-op inline ordering
- [x] Code quality: Extract magic numbers into named constants
- [x] Code quality: Convert triple-quote comments to proper docstrings
- [x] Code quality: Add type hints to all method signatures
- [x] Perf: Replace `squareUnderAttack` with targeted piece-type detection
- [x] Perf: Add iterative deepening search (depth 1→5)
- [x] Perf: Add transposition table for caching evaluated positions
- [x] Perf: Add move ordering (TT best move → captures → quiet moves)

## Remaining — Ordered by Difficulty

### Easy
- [x] Pawn promotion UI — let player choose Q/R/B/N instead of auto-queen
- [x] Draw by insufficient material (K vs K, K+B vs K, K+N vs K)

### Medium
- [x] Threefold repetition detection — track position history, declare draw
- [x] 50-move rule — count half-moves since last pawn move or capture
- [x] Game clock / timer — add configurable time controls per side
- [x] Improve AI evaluation — king safety, pawn structure, piece coordination
- [x] Better rook piece-square tables — penalize edge/corner squares more

### Hard
- [x] Opening book — load and follow known opening lines from a database
- [ ] Endgame tablebases (Syzygy) — perfect play with ≤6 pieces remaining
- [x] Quiescence search — extend search on captures to avoid horizon effect
