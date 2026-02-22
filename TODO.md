# Chess Project — TODO

## Completed
- [x] Bug: Remove dead `Move.pgn` class variable
- [x] Bug: Remove stray `print()` in AI `scoreBoard`
- [x] Bug: Fix rook mobility score typo (250 → 0.25)
- [x] Bug: Fix black rook castling rights checking wrong row (7 → 0)
- [x] Bug: Fix mobility/activity accumulation in `scoreBoard`
- [x] Bug: Fix AI evaluation bias — mobility scoring gave ~1.0 point swing to side-to-move
- [x] Bug: Fix AI draw blindness — AI ignored threefold repetition, 50-move rule, insufficient material in search
- [x] Bug: Fix `_connectedRooksBonus` signature mismatch (was passing board but function expected gs)
- [x] Code quality: Remove dead `moveOrdering` method and no-op inline ordering
- [x] Code quality: Extract magic numbers into named constants
- [x] Code quality: Convert triple-quote comments to proper docstrings
- [x] Code quality: Add type hints to all method signatures
- [x] Code quality: Remove dead `_scoreRooksOnFiles` function (inlined into scoreBoard)
- [x] Code quality: Remove dead `return moves` after `return False` in `isInsufficientMaterial`
- [x] Perf: Replace `squareUnderAttack` with targeted piece-type detection
- [x] Perf: Add iterative deepening search (depth 1→5)
- [x] Perf: Add transposition table for caching evaluated positions
- [x] Perf: Add move ordering (TT best move → captures → quiet moves)
- [x] Perf: Add `__slots__` and `__hash__` to Move class
- [x] Perf: Replace list.remove loop with set-based filter in getValidMoves
- [x] Perf: Merge bishop counting and rook scoring into single board scan in scoreBoard
- [x] Perf: Implement Zobrist hashing for O(1) incremental position keys
- [x] Perf: Optimize isInsufficientMaterial with early exits (bail on pawns/queens/rooks)
- [x] Perf: Optimize move ordering — extract TT best move ID once instead of per-move dict lookup
- [x] Perf: Optimize _scoreKingSafety — set lookups for pawn shield instead of list iteration
- [x] Perf: Optimize _scorePawnStructure — eliminate set creation per pawn
- [x] Feature: Pawn promotion UI — let player choose Q/R/B/N instead of auto-queen
- [x] Feature: Draw by insufficient material (K vs K, K+B vs K, K+N vs K, same-color bishops)
- [x] Feature: Threefold repetition detection
- [x] Feature: 50-move rule
- [x] Feature: Game clock / timer with configurable time controls
- [x] Feature: Opening book (~80 lines covering major openings)
- [x] Feature: Quiescence search (captures-only extension to avoid horizon effect)
- [x] Feature: AI debug logging (JSON log with scores, top moves, timing per depth)
- [x] AI: King safety evaluation (pawn shield, open files near king)
- [x] AI: Pawn structure evaluation (doubled, isolated, passed pawns)
- [x] AI: Piece coordination (bishop pair, connected rooks, knight outposts)
- [x] AI: Center control bonus
- [x] AI: Rook on 7th rank bonus
- [x] AI: Rook on open/semi-open file bonus
- [x] AI: Hash-based position tiebreaker for score differentiation
- [x] AI: Skip TT cutoffs at root to ensure all root moves get real scores

## Remaining — Known Issues

- [ ] Identical scores at root — many moves evaluate to the same score in quiet positions (moves 3-7 in typical games). The AI effectively picks randomly among "equal" moves in the early middlegame. Needs deeper search or better eval differentiation.
- [ ] `isPawnPromotionMove` flag in `getPawnMoves` not reset between capture branches — can cause false promotion detection in rare cases.
- [ ] AI evaluation counts mobility only from the current side's valid moves, not both sides.

## Remaining — Performance

- [ ] Null move pruning — skip a move and do a shallow search; if the opponent still can't beat beta, prune. Typically 2-3x node reduction.
- [ ] Late move reductions (LMR) — search moves ordered late at reduced depth first, only re-search at full depth if promising.
- [ ] Killer move heuristic — remember moves that caused beta cutoffs at each depth, try them early in sibling nodes.
- [ ] History heuristic — track which moves cause cutoffs globally, use for move ordering.
- [ ] Principal variation search (PVS) — search the first move with full window, remaining moves with null window, re-search if they beat alpha.

## Remaining — Features

- [ ] ELO benchmarking — automated games against Stockfish at various strength levels to estimate engine rating.
- [ ] Post-game analysis — compare AI moves against Stockfish to calculate average centipawn loss.
- [ ] Endgame tablebases (Syzygy) — perfect play with ≤6 pieces remaining.
- [ ] Time management — allocate more time for complex positions, less for forced/book moves.
- [ ] Pondering — think on opponent's time.
