from __future__ import annotations
import random as _random

# =============================================================================
# Zobrist Hashing — O(1) incremental position hashing
# =============================================================================
_ZOBRIST_RNG = _random.Random(42)  # Fixed seed for reproducibility across processes.

# One random 64-bit int per (piece, square) combination.
_PIECE_KEYS: list[str] = ['wP','wN','wB','wR','wQ','wK','bP','bN','bB','bR','bQ','bK']
_PIECE_INDEX: dict[str, int] = {p: i for i, p in enumerate(_PIECE_KEYS)}
# zobristPiece[pieceIndex][row][col]
zobristPiece: list[list[list[int]]] = [
    [[_ZOBRIST_RNG.getrandbits(64) for _ in range(8)] for _ in range(8)]
    for _ in range(12)
]
zobristSide: int = _ZOBRIST_RNG.getrandbits(64)  # XOR when it's black to move.
zobristCastle: list[int] = [_ZOBRIST_RNG.getrandbits(64) for _ in range(4)]  # wks, wqs, bks, bqs
zobristEnPassant: list[int] = [_ZOBRIST_RNG.getrandbits(64) for _ in range(8)]  # One per file.


def _zobristSquare(piece: str, row: int, col: int) -> int:
    """Return the Zobrist key component for a piece on a square."""
    idx = _PIECE_INDEX.get(piece)
    if idx is None:
        return 0
    return zobristPiece[idx][row][col]


class GameState():
    
    def __init__(self) -> None:
        self.board = [
            ["bR","bN","bB","bQ","bK","bB","bN","bR"],
            ["bP","bP","bP","bP","bP","bP","bP","bP"],
            ["--","--","--","--","--","--","--","--"],
            ["--","--","--","--","--","--","--","--"],
            ["--","--","--","--","--","--","--","--"],
            ["--","--","--","--","--","--","--","--"],
            ["wP","wP","wP","wP","wP","wP","wP","wP"],
            ["wR","wN","wB","wQ","wK","wB","wN","wR"]]

        self.moveFunctions = {'P':self.getPawnMoves, 
                              'R':self.getRookMoves,
                              'N':self.getKnightMoves,
                              'B':self.getBishopMoves,
                              'Q':self.getQueenMoves,
                              'K':self.getKingMoves}
        self.whiteToMove = True
        self.moveLog = []
        self.whiteKingLocation = (7,4)
        self.blackKingLocation = (0,4)
        self.inCheck = False
        self.pins = []
        self.checks = []        
        self.checkmate = False
        self.stalemate = False
        self.insufficientMaterial = False
        self.threefoldRepetition = False
        self.fiftyMoveRule = False
        self.halfMoveClock = 0
        self.halfMoveClockLog = [0]
        self.positionHistory = {}
        self.enPassantPossible = ()
        self.enPassantPossibleLog = [self.enPassantPossible]
        # Castling rights.
        self.currentCastlingRights = CastleRights(True,True,True,True)
        self.castleRightsLog = [CastleRights(self.currentCastlingRights.wks, self.currentCastlingRights.wqs,
                                             self.currentCastlingRights.bks, self.currentCastlingRights.bqs)]
        # Zobrist hash — computed from scratch once, then updated incrementally.
        self.zobristHash = self._computeZobristHash()
        self.zobristLog: list[int] = [self.zobristHash]
        # Record starting position for threefold repetition tracking.
        self.positionHistory[self._getPositionKey()] = 1
    
        
    def makeMove(self, move: Move, promotionChoice: str = 'Q') -> None:
        """Makes the move that is passed as a parameter."""
        h = self.zobristHash

        # --- Remove old en passant from hash ---
        if self.enPassantPossible:
            h ^= zobristEnPassant[self.enPassantPossible[1]]

        # --- Remove old castling rights from hash ---
        cr = self.currentCastlingRights
        if cr.wks: h ^= zobristCastle[0]
        if cr.wqs: h ^= zobristCastle[1]
        if cr.bks: h ^= zobristCastle[2]
        if cr.bqs: h ^= zobristCastle[3]

        # --- Move the piece on the board ---
        # Remove piece from start square.
        h ^= _zobristSquare(move.pieceMoved, move.startRow, move.startCol)
        # Remove captured piece from end square (if any — but NOT for en passant, handled below).
        if not move.isEnPassantMove and move.pieceCaptured != "--":
            h ^= _zobristSquare(move.pieceCaptured, move.endRow, move.endCol)

        self.board[move.startRow][move.startCol] = "--"
        self.board[move.endRow][move.endCol] = move.pieceMoved
        self.moveLog.append(move)
        self.whiteToMove = not self.whiteToMove
        h ^= zobristSide  # Toggle side.

        # Update king's position.
        if move.pieceMoved == 'wK':
            self.whiteKingLocation = (move.endRow, move.endCol)
        elif move.pieceMoved == 'bK':
            self.blackKingLocation = (move.endRow, move.endCol)

        # En passant: if pawn moves twice, next move can capture en passant.
        if move.pieceMoved[1] == 'P' and abs(move.startRow - move.endRow) == 2:
            self.enPassantPossible = ((move.endRow + move.startRow) // 2, move.endCol)
        else:
            self.enPassantPossible = ()

        # En passant capture.
        if move.isEnPassantMove:
            self.board[move.startRow][move.endCol] = "--"
            # Remove the captured pawn from hash (it was on startRow, endCol).
            capturedPawn = 'bP' if move.pieceMoved == 'wP' else 'wP'
            h ^= _zobristSquare(capturedPawn, move.startRow, move.endCol)

        # Pawn promotion.
        if move.isPawnPromotionMove:
            promotedPiece = move.pieceMoved[0] + promotionChoice
            self.board[move.endRow][move.endCol] = promotedPiece
            # Add the promoted piece (not the pawn) to the end square.
            h ^= _zobristSquare(promotedPiece, move.endRow, move.endCol)
        else:
            # Add piece to end square.
            h ^= _zobristSquare(move.pieceMoved, move.endRow, move.endCol)

        # Castling — move the rook.
        if move.isCastleMove:
            if move.endCol - move.startCol == 2:  # King side.
                rook = self.board[move.endRow][move.endCol + 1]
                h ^= _zobristSquare(rook, move.endRow, move.endCol + 1)
                self.board[move.endRow][move.endCol - 1] = rook
                self.board[move.endRow][move.endCol + 1] = "--"
                h ^= _zobristSquare(rook, move.endRow, move.endCol - 1)
            else:  # Queen side.
                rook = self.board[move.endRow][move.endCol - 2]
                h ^= _zobristSquare(rook, move.endRow, move.endCol - 2)
                self.board[move.endRow][move.endCol + 1] = rook
                self.board[move.endRow][move.endCol - 2] = "--"
                h ^= _zobristSquare(rook, move.endRow, move.endCol + 1)

        # Update en passant log.
        self.enPassantPossibleLog.append(self.enPassantPossible)
        # Update castling rights.
        self.updateCastleRights(move)
        self.castleRightsLog.append(CastleRights(self.currentCastlingRights.wks, self.currentCastlingRights.wqs,
                                                  self.currentCastlingRights.bks, self.currentCastlingRights.bqs))

        # --- Add new castling rights to hash ---
        cr = self.currentCastlingRights
        if cr.wks: h ^= zobristCastle[0]
        if cr.wqs: h ^= zobristCastle[1]
        if cr.bks: h ^= zobristCastle[2]
        if cr.bqs: h ^= zobristCastle[3]

        # --- Add new en passant to hash ---
        if self.enPassantPossible:
            h ^= zobristEnPassant[self.enPassantPossible[1]]

        self.zobristHash = h
        self.zobristLog.append(h)

        # Update half-move clock (reset on pawn move or capture).
        if move.pieceMoved[1] == 'P' or move.pieceCaptured != '--':
            self.halfMoveClock = 0
        else:
            self.halfMoveClock += 1
        self.halfMoveClockLog.append(self.halfMoveClock)
        # Track position for threefold repetition.
        posKey = self._getPositionKey()
        self.positionHistory[posKey] = self.positionHistory.get(posKey, 0) + 1
        # Check draw conditions.
        if self.halfMoveClock >= 100:
            self.fiftyMoveRule = True
        if self.positionHistory[posKey] >= 3:
            self.threefoldRepetition = True
                
            
    def undoMove(self) -> None:
        """Undo the last move made."""    
        if len(self.moveLog) != 0:
            # Undo position history FIRST (while zobristHash still matches the position we're undoing).
            posKey = self._getPositionKey()
            self.positionHistory[posKey] = self.positionHistory.get(posKey, 1) - 1
            if self.positionHistory[posKey] <= 0:
                del self.positionHistory[posKey]

            move = self.moveLog.pop()
            self.board[move.startRow][move.startCol] = move.pieceMoved
            self.board[move.endRow][move.endCol] = move.pieceCaptured
            self.whiteToMove = not self.whiteToMove

            # Update king's position.
            if move.pieceMoved == 'wK':
                self.whiteKingLocation = (move.startRow, move.startCol)
            elif move.pieceMoved == 'bK':
                self.blackKingLocation = (move.startRow, move.startCol)
            # Undo en-passant.
            if move.isEnPassantMove:
                self.board[move.endRow][move.endCol] = "--"
                self.board[move.startRow][move.endCol] = move.pieceCaptured
            self.enPassantPossibleLog.pop()
            self.enPassantPossible = self.enPassantPossibleLog[-1]
            # Undo castling rights.
            self.castleRightsLog.pop()
            newRights = self.castleRightsLog[-1]
            self.currentCastlingRights = CastleRights(newRights.wks, newRights.wqs, newRights.bks, newRights.bqs)
            # Undo castle move.
            if move.isCastleMove:
                if move.endCol - move.startCol == 2:  # King side.
                    self.board[move.endRow][move.endCol + 1] = self.board[move.endRow][move.endCol - 1]
                    self.board[move.endRow][move.endCol - 1] = "--"
                else:  # Queen side.
                    self.board[move.endRow][move.endCol - 2] = self.board[move.endRow][move.endCol + 1]
                    self.board[move.endRow][move.endCol + 1] = "--"
            self.checkmate = False
            self.stalemate = False
            self.insufficientMaterial = False
            self.threefoldRepetition = False
            self.fiftyMoveRule = False
            # Restore Zobrist hash from log.
            self.zobristLog.pop()
            self.zobristHash = self.zobristLog[-1]
            # Undo half-move clock.
            self.halfMoveClockLog.pop()
            self.halfMoveClock = self.halfMoveClockLog[-1]
                    
                
               
    def updateCastleRights(self, move: Move) -> None:
        if move.pieceMoved == 'wK':
            self.currentCastlingRights.wks = False
            self.currentCastlingRights.wqs = False
        elif move.pieceMoved == 'bK':
            self.currentCastlingRights.bks = False
            self.currentCastlingRights.bqs = False
        elif move.pieceMoved == 'wR':
            if move.startRow == 7:
                if move.startCol == 0:
                    self.currentCastlingRights.wqs = False
                elif move.startCol == 7:
                    self.currentCastlingRights.wks = False
        elif move.pieceMoved == 'bR':
            if move.startRow == 0:
                if move.startCol == 0:
                    self.currentCastlingRights.bqs = False
                elif move.startCol == 7:
                    self.currentCastlingRights.bks = False
        
        if move.pieceMoved == 'wR':
            if move.endRow == 7:
                if move.endCol == 0:
                    self.currentCastlingRights.wqs = False
                elif move.endCol == 7:
                    self.currentCastlingRights.wks = False
            elif move.endRow == 0:
                if move.endCol == 0:
                    self.currentCastlingRights.bqs = False
                elif move.endCol == 7:
                    self.currentCastlingRights.bks = False        
    
    def getValidMoves(self) -> list[Move]:
        """Returns all moves considering checks."""
        tempCastleRights = CastleRights(self.currentCastlingRights.wks, self.currentCastlingRights.wqs,
                                        self.currentCastlingRights.bks, self.currentCastlingRights.bqs)                
        moves = []
        self.inCheck, self.pins, self.checks = self.checkForPinsAndChecks()
        if self.whiteToMove:
            kingRow = self.whiteKingLocation[0]
            kingCol = self.whiteKingLocation[1]
        else:
            kingRow = self.blackKingLocation[0]
            kingCol = self.blackKingLocation[1]            
        if self.inCheck:
            if len(self.checks) == 1: # Only 1 check - block/move king.
                moves = self.getAllPossibleMoves()
                # To block a check, you must move a piece into one of the squares between the enemy piece and the king.
                check = self.checks[0] # Check information.
                checkRow = check[0]
                checkCol = check[1]
                pieceChecking = self.board[checkRow][checkCol] # Enemy piece causing the check.
                validSquares = [] # Squares that the pieces can move to.
                # Knight can't be blocked, must be captured/move king.
                if pieceChecking[1] == 'N':
                    validSquares = [(checkRow,checkCol)]
                else:
                    for i in range(1,8):
                        validSquare = (kingRow + check[2]*i, kingCol + check[3]*i) # check[2] and check[3] are check directions.
                        validSquares.append(validSquare)
                        if validSquare[0] == checkRow and validSquare[1] == checkCol: # Once you get to piece end checks.
                            break
                # Filter moves: keep king moves and moves that block/capture.
                validSquareSet = set(validSquares)
                moves = [m for m in moves if m.pieceMoved[1] == 'K' or (m.endRow, m.endCol) in validSquareSet]
            else: # DOUBLE CHECK! king has to move.
                self.getKingMoves(kingRow, kingCol, moves)
        else: # Not in check, so all the moves are valid.
            moves = self.getAllPossibleMoves()        
        
        if self.whiteToMove:
            self.getCastleMoves(self.whiteKingLocation[0], self.whiteKingLocation[1], moves)
        else:
            self.getCastleMoves(self.blackKingLocation[0], self.blackKingLocation[1], moves)
        self.currentCastlingRights = tempCastleRights
        
        if len(moves) == 0: # Either checkmate or stalemate.
            if self.InCheck():
                self.checkmate = True
            else:
                self.stalemate = True
        elif self.isInsufficientMaterial():
            self.insufficientMaterial = True
        elif self.fiftyMoveRule:
            pass  # Already set in makeMove.
        elif self.threefoldRepetition:
            pass  # Already set in makeMove.
    
        return moves
    
    def isInsufficientMaterial(self) -> bool:
        """Check if neither side has enough material to checkmate."""
        # Quick scan: count non-king, non-pawn pieces. Bail early if any pawn/queen/rook found.
        minors = []  # (color, pieceType, row, col)
        for row in range(8):
            for col in range(8):
                sq = self.board[row][col]
                if sq == "--" or sq[1] == 'K':
                    continue
                piece = sq[1]
                if piece in ('P', 'Q', 'R'):
                    return False  # Enough material exists.
                minors.append((sq[0], piece, row, col))
                if len(minors) > 2:
                    return False  # More than 2 minors — sufficient.
        # K vs K
        if len(minors) == 0:
            return True
        # K+minor vs K
        if len(minors) == 1:
            return True
        # K+B vs K+B with bishops on same color square
        if len(minors) == 2:
            c0, p0, r0, co0 = minors[0]
            c1, p1, r1, co1 = minors[1]
            if p0 == 'B' and p1 == 'B' and c0 != c1:
                if (r0 + co0) % 2 == (r1 + co1) % 2:
                    return True
        return False
    def _computeZobristHash(self) -> int:
        """Compute the full Zobrist hash from scratch. Called once at init/reset."""
        h = 0
        for r in range(8):
            for c in range(8):
                sq = self.board[r][c]
                if sq != "--":
                    h ^= _zobristSquare(sq, r, c)
        if not self.whiteToMove:
            h ^= zobristSide
        cr = self.currentCastlingRights
        if cr.wks: h ^= zobristCastle[0]
        if cr.wqs: h ^= zobristCastle[1]
        if cr.bks: h ^= zobristCastle[2]
        if cr.bqs: h ^= zobristCastle[3]
        if self.enPassantPossible:
            h ^= zobristEnPassant[self.enPassantPossible[1]]
        return h

    def _getPositionKey(self) -> int:
        """Returns the Zobrist hash as the position key (O(1) — already maintained incrementally)."""
        return self.zobristHash

    
    def InCheck(self) -> bool:
        """Determine if the current player is in check."""
        if self.whiteToMove:
            return self.squareUnderAttack(self.whiteKingLocation[0], self.whiteKingLocation[1])
        else:
            return self.squareUnderAttack(self.blackKingLocation[0], self.blackKingLocation[1])
        
    def squareUnderAttack(self, row: int, col: int) -> bool:
        """Determine if the enemy can attack the square at (row, col) using targeted detection."""
        enemyColor = 'b' if self.whiteToMove else 'w'

        # Check for knight attacks
        knightMoves = ((-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1))
        for m in knightMoves:
            endRow, endCol = row + m[0], col + m[1]
            if 0 <= endRow < 8 and 0 <= endCol < 8:
                piece = self.board[endRow][endCol]
                if piece[0] == enemyColor and piece[1] == 'N':
                    return True

        # Check for pawn attacks
        if enemyColor == 'b':
            pawnAttacks = ((-1, -1), (-1, 1))  # Black pawns attack downward
        else:
            pawnAttacks = ((1, -1), (1, 1))  # White pawns attack upward
        for m in pawnAttacks:
            endRow, endCol = row + m[0], col + m[1]
            if 0 <= endRow < 8 and 0 <= endCol < 8:
                piece = self.board[endRow][endCol]
                if piece[0] == enemyColor and piece[1] == 'P':
                    return True

        # Check for king attacks (1 square in any direction)
        kingMoves = ((-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1))
        for m in kingMoves:
            endRow, endCol = row + m[0], col + m[1]
            if 0 <= endRow < 8 and 0 <= endCol < 8:
                piece = self.board[endRow][endCol]
                if piece[0] == enemyColor and piece[1] == 'K':
                    return True

        # Check for rook/queen attacks (orthogonal lines)
        rookDirections = ((-1,0), (1,0), (0,-1), (0,1))
        for d in rookDirections:
            for step in range(1, 8):
                endRow, endCol = row + d[0]*step, col + d[1]*step
                if 0 <= endRow < 8 and 0 <= endCol < 8:
                    piece = self.board[endRow][endCol]
                    if piece == "--":
                        continue
                    if piece[0] == enemyColor and piece[1] in ('R', 'Q'):
                        return True
                    break  # Blocked by any piece
                else:
                    break

        # Check for bishop/queen attacks (diagonal lines)
        bishopDirections = ((-1,-1), (-1,1), (1,-1), (1,1))
        for d in bishopDirections:
            for step in range(1, 8):
                endRow, endCol = row + d[0]*step, col + d[1]*step
                if 0 <= endRow < 8 and 0 <= endCol < 8:
                    piece = self.board[endRow][endCol]
                    if piece == "--":
                        continue
                    if piece[0] == enemyColor and piece[1] in ('B', 'Q'):
                        return True
                    break  # Blocked by any piece
                else:
                    break

        return False  
    
    def getAllPossibleMoves(self) -> list[Move]:
        """Get all moves without considering checks (pseudo-legal moves)."""
        moves = []
        for r in range(len(self.board)):
            for c in range(len(self.board[r])):
                pieceColor = self.board[r][c][0]
                if (pieceColor == 'w' and self.whiteToMove == True) or (pieceColor == 'b' and self.whiteToMove != True):
                    # We have found a the right colored piece at this location (r,c) on board.
                    piece = self.board[r][c][1]
                    self.moveFunctions[piece](r,c,moves) # calls the appropriate move function based on piece.
        return moves

                        
    def getPawnMoves(self, r: int, c: int, moves: list[Move]) -> None:
        """Get all pawn moves from position (r, c) and add them to moves."""
        piecePinned = False
        pinDirection = ()
        for i in range(len(self.pins)-1, -1, -1):
            if self.pins[i][0] == r and self.pins[i][1] == c:
                piecePinned = True
                pinDirection = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break
        
        if self.whiteToMove:
            moveAmount = -1
            startRow = 6
            backRow = 0
            enemyColor = 'b'
            kingRow, kingCol = self.whiteKingLocation
        else:
            moveAmount = 1
            startRow = 1
            backRow = 7
            enemyColor = 'w'
            kingRow, kingCol = self.blackKingLocation
        isPawnPromotionMove = False
        
        if self.board[r+moveAmount][c] == "--": # 1 square move
            if not piecePinned or pinDirection == (moveAmount, 0):
                if r+moveAmount == backRow: # if piece gets to back rank then it is pawn promotion.
                    isPawnPromotionMove = True
                moves.append(Move((r,c), (r+moveAmount, c), self.board, isPawnPromotionMove = isPawnPromotionMove))
                if r == startRow and self.board[r+2*moveAmount][c] == "--": # 2 square moves.
                    moves.append(Move((r,c), (r+2*moveAmount,c), self.board))
        
        if c>=1: # Capture left.
            if not piecePinned or pinDirection == (moveAmount, -1):
                if self.board[r+moveAmount][c-1][0] == enemyColor:
                    if r+moveAmount == backRow:
                        isPawnPromotionMove = True
                    moves.append(Move((r,c), (r+moveAmount, c-1), self.board, isPawnPromotionMove = isPawnPromotionMove))
                if (r+moveAmount, c-1) == self.enPassantPossible:
                    attackingPiece = blockingPiece = False
                    if kingRow == r:
                        if kingCol < c: # King is left of the pawn.
                            # inside -> between king and pawn, outside -> range between pawn border
                            insideRange = range(kingCol+1, c-1)
                            outsideRange = range(c+1, 8)
                        else: # King is right of pawn.
                            insideRange = range(kingCol-1, c, -1)
                            outsideRange = range(c-2, -1, -1)
                        for i in insideRange:
                            if self.board[r][i] != "--": # some other piece besdes en-passant pawn blocks.
                                blockingPiece = True
                        for i in outsideRange:
                            square = self.board[r][i]
                            if square[0] == enemyColor and (square[1] == 'R' or square[1] == 'Q'):
                                attackingPiece = True
                            elif square != "--":
                                blockingPiece = True
                    if not attackingPiece or blockingPiece:
                        moves.append(Move((r,c), (r+moveAmount, c-1), self.board, isEnPassantMove = True))
        
        if c<=6: # Capture right.
            if not piecePinned or pinDirection == (moveAmount, 1):
                if self.board[r+moveAmount][c+1][0] == enemyColor:
                    if r+moveAmount == backRow:
                        isPawnPromotionMove = True
                    moves.append(Move((r,c), (r+moveAmount, c+1), self.board, isPawnPromotionMove = isPawnPromotionMove))
                if (r+moveAmount, c+1) == self.enPassantPossible:
                    attackingPiece = blockingPiece = False
                    if kingRow == r:
                        if kingCol < c: # King is left of the pawn.
                            # inside -> between king and pawn, outside -> range between pawn border
                            insideRange = range(kingCol+1, c)
                            outsideRange = range(c+2, 8)
                        else: # King is right of pawn.
                            insideRange = range(kingCol-1, c+1, -1)
                            outsideRange = range(c-1, -1, -1)
                        for i in insideRange:
                            if self.board[r][i] != "--": # some other piece besdes en-passant pawn blocks.
                                blockingPiece = True
                        for i in outsideRange:
                            square = self.board[r][i]
                            if square[0] == enemyColor and (square[1] == 'R' or square[1] == 'Q'):
                                attackingPiece = True
                            elif square != "--":
                                blockingPiece = True
                    if not attackingPiece or blockingPiece:
                        moves.append(Move((r,c), (r+moveAmount, c+1), self.board, isEnPassantMove = True))                
                    
                  
    def getKnightMoves(self, r: int, c: int, moves: list[Move]) -> None:
        """Get all knight moves from position (r, c) and add them to moves."""
        piecePinned = False
        for i in range(len(self.pins)-1, -1, -1):
            if self.pins[i][0] == r and self.pins[i][1] == c:
                piecePinned = True
                self.pins.remove(self.pins[i])
                break        
        
        directions = ((-2,-1),(-2,1),(-1,-2),(-1,2),(2,-1),(2,1),(1,-2),(1,2)) 
        friendlyColor = "w" if self.whiteToMove else "b"
        for d in directions:
            endRow = r+d[0]
            endCol = c+d[1]
            if 8>endRow>=0 and 8>endCol>=0: #On-board
                if not piecePinned:
                    endPiece = self.board[endRow][endCol]
                    if endPiece[0] != friendlyColor: # Enemy piece / Empty square  - Valid
                        moves.append(Move((r,c), (endRow,endCol), self.board))
                    
    def getBishopMoves(self, r: int, c: int, moves: list[Move]) -> None:
        """Get all bishop moves from position (r, c) and add them to moves."""
        piecePinned = False
        pinDirection = ()
        for i in range(len(self.pins)-1, -1, -1):
            if self.pins[i][0] == r and self.pins[i][1] == c:
                piecePinned = True
                pinDirection = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break        
        
        directions = ((-1,-1), (-1,1), (1,-1), (1,1)) 
        # Vayavya(North-West), Ishanya(North-East), Nairtya(South-West), Agneya(South-East) 
        enemyColor = "b" if self.whiteToMove else "w"
        for d in directions:
            for step in range(1,8):
                endRow = r+d[0]*step
                endCol = c+d[1]*step
                if 8>endRow>=0 and 8>endCol>=0: #On-board
                    if not piecePinned or pinDirection == d or pinDirection == (-d[0], -d[1]):
                        endPiece = self.board[endRow][endCol]
                        if endPiece == "--": # Empty square - Valid
                            moves.append(Move((r,c), (endRow,endCol), self.board))
                        elif endPiece[0] == enemyColor: # Enemy piece - Valid
                            moves.append(Move((r,c), (endRow,endCol), self.board))
                            break
                        else: # Friendly piece - Invalid
                            break
                else:
                    break
                              
    def getRookMoves(self, r: int, c: int, moves: list[Move]) -> None:
        """Get all rook moves from position (r, c) and add them to moves."""
        piecePinned = False
        pinDirection = ()
        for i in range(len(self.pins)-1, -1, -1):
            if self.pins[i][0] == r and self.pins[i][1] == c:
                piecePinned = True
                pinDirection = (self.pins[i][2], self.pins[i][3])
                if self.board[r][c][1] != 'Q': # Can't remove queen from pin on rook moves, only remove it on bishop moves.
                    self.pins.remove(self.pins[i])
                break
        
        directions = ((-1,0), (0,-1), (1,0), (0,1)) # Up, Left, Down, Right
        enemyColor = "b" if self.whiteToMove else "w"
        for d in directions:
            for step in range(1,8):
                endRow = r + d[0]*step
                endCol = c + d[1]*step
                if 8>endRow>=0 and 8>endCol>=0:
                    if not piecePinned or pinDirection == d or pinDirection == (-d[0], -d[1]):
                        endPiece = self.board[endRow][endCol]
                        if endPiece == "--": # Empty square - Valid
                            moves.append(Move((r,c), (endRow,endCol), self.board))
                        elif endPiece[0] == enemyColor: # Enemy piece - Valid
                            moves.append(Move((r,c), (endRow,endCol), self.board))
                            break
                        else: # Friendly piece - Invalid
                            break
                else: # Off-board
                    break
                
    def getQueenMoves(self, r: int, c: int, moves: list[Move]) -> None:
        """Get all queen moves from position (r, c) and add them to moves."""
        self.getRookMoves(r, c, moves)
        self.getBishopMoves(r, c, moves)
        
    def getKingMoves(self, r: int, c: int, moves: list[Move]) -> None:
        """Get all king moves from position (r, c) and add them to moves."""
        rowMoves = (-1, -1, -1,  0, 0,  1, 1, 1)
        colMoves = (-1,  0,  1, -1, 1, -1, 0, 1)
        friendlyColor = "w" if self.whiteToMove else "b"
        for i in range(8):
            endRow = r+rowMoves[i]
            endCol = c+colMoves[i]
            if 8>endRow>=0 and 8>endCol>=0: #On-board
                endPiece = self.board[endRow][endCol]
                if endPiece[0] != friendlyColor: # Enemy piece / Empty square - Valid
                    # Place king on end square and check for checks.
                    if friendlyColor == 'w':
                        self.whiteKingLocation = (endRow, endCol)
                    else:
                        self.blackKingLocation = (endRow, endCol)
                    inCheck, pins,checks = self.checkForPinsAndChecks()
                    if not inCheck:
                        moves.append(Move((r,c), (endRow,endCol), self.board))
                    # Place king back on original location.
                    if friendlyColor == 'w':
                        self.whiteKingLocation = (r,c)
                    else:
                        self.blackKingLocation = (r,c)
    
    def checkForPinsAndChecks(self) -> tuple[bool, list, list]:
        """Returns (inCheck, pins, checks) for the current player's king."""
        pins = [] # Squares where the friendly pinned piece is and direction pinned from.
        checks = [] # Squares where enemy is applying a check.
        inCheck = False
        if self.whiteToMove:
            enemyColor = "b"
            friendlyColor = "w"
            startRow = self.whiteKingLocation[0]
            startCol = self.whiteKingLocation[1]
        else:
            enemyColor = "w"
            friendlyColor = "b"
            startRow = self.blackKingLocation[0]
            startCol = self.blackKingLocation[1]
        # Check outward from king for pins and checks, keep track of pins.
        directions = ((-1,0), (0,-1), (1,0), (0,1), (-1,-1), (-1,1), (1,-1), (1,1))
        for j in range(len(directions)):
            d = directions[j]
            possiblePin = () # Reset possible pins.
            for i in range(1,8):
                endRow = startRow + d[0]*i
                endCol = startCol + d[1]*i
                if 8>endRow>=0 and 8>endCol>=0:
                    endPiece = self.board[endRow][endCol]
                    if endPiece[0] == friendlyColor and endPiece[1] != 'K':
                        if possiblePin == (): # 1st friendly piece could be pinned.
                            possiblePin = (endRow, endCol, d[0], d[1])
                        else: # 2nd friendy piece, so pin/check not possible in this direction.
                            break
                    elif endPiece[0] == enemyColor:
                        type = endPiece[1]
                        '''
                        There are 5 Possibilities here in this complex conditional
                        1) Orthogonally away from king and piece is a rook.
                        2) Diagonally away from king and piece is a bishop.
                        3) 1 square away diagonally from king and piece is a pawn.
                        4) any direction and piece is a queen.
                        5) any direction 1 square away and piece is a king.This is necessary
                           to prevent a king move to a square controlled by another king.
                        '''
                        if (3 >= j >= 0 and type == 'R') or \
                           (7 >= j >= 4 and type == 'B') or \
                           (i == 1 and type == 'P' and ((enemyColor == 'w' and 7 >= j >= 6) or (enemyColor == 'b' and 5 >= j >= 4))) or \
                           (type == 'Q') or \
                           (i == 1 and type == 'K'):
                               if possiblePin == (): # No piece blocking, hence CHECK!
                                   inCheck = True
                                   checks.append((endRow, endCol, d[0], d[1]))
                                   break
                               else: # Piece blocking, hence Pin.
                                   pins.append(possiblePin)
                                   break
                        else: # Enemy piece not applying checks.
                            break
        # Check for knight checks
        knightMoves = ((-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1))
        for m in knightMoves:
            endRow = startRow + m[0]
            endCol = startCol + m[1]
            if 8>endRow>=0 and 8>endCol>=0:
                endPiece = self.board[endRow][endCol]
                if endPiece[0] == enemyColor and endPiece[1] == 'N':
                    inCheck = True
                    checks.append((endRow, endCol, m[0], m[1]))
        return inCheck, pins, checks
    
    def getCastleMoves(self, r: int, c: int, moves: list[Move]) -> None:
        if self.squareUnderAttack(r,c):
            return # Can't castle while in check.
        if (self.whiteToMove and self.currentCastlingRights.wks) or (not self.whiteToMove and self.currentCastlingRights.bks):
            self.getKingSideCastleMoves(r,c,moves)
        if (self.whiteToMove and self.currentCastlingRights.wqs) or (not self.whiteToMove and self.currentCastlingRights.bqs):
            self.getQueenSideCastleMoves(r,c,moves)
        
    def getKingSideCastleMoves(self, r: int, c: int, moves: list[Move]) -> None:
        if self.board[r][c+1] == "--" and self.board[r][c+2] == "--":
            if not self.squareUnderAttack(r,c+1) and not self.squareUnderAttack(r,c+2):
                moves.append(Move((r,c), (r,c+2), self.board, isCastleMove = True))
                
    def getQueenSideCastleMoves(self, r: int, c: int, moves: list[Move]) -> None:
        if self.board[r][c-1] == '--' and self.board[r][c-2] == '--' and self.board[r][c-3] == '--':
            if not self.squareUnderAttack(r, c-1) and not self.squareUnderAttack(r, c-2):
                moves.append(Move((r, c), (r, c-2), self.board, isCastleMove=True))
        
    

class CastleRights():
    def __init__(self, wks: bool, wqs: bool, bks: bool, bqs: bool) -> None:
        self.wks = wks
        self.wqs = wqs
        self.bks = bks
        self.bqs = bqs

                                  
class Move():
    
    __slots__ = ('startRow', 'startCol', 'endRow', 'endCol', 'pieceMoved',
                 'pieceCaptured', 'isEnPassantMove', 'isPawnPromotionMove',
                 'isCastleMove', 'isCapture', 'moveID')
    
    # Maps Keys to Values
    ranksToRows = {"1":7, "2":6, "3":5, "4":4, "5":3, "6":2, "7":1, "8":0}
    rowsToRanks = {v: k for k,v in ranksToRows.items()}
    
    filesToCols = {"a":0, "b":1, "c":2, "d":3, "e":4, "f":5, "g":6, "h":7}
    colsToFiles = {v: k for k,v in filesToCols.items()}
    
    def __init__(self, startSq: tuple[int, int], endSq: tuple[int, int], board: list[list[str]],
                 isEnPassantMove: bool = False, isPawnPromotionMove: bool = False, isCastleMove: bool = False) -> None:
        self.startRow = startSq[0]
        self.startCol = startSq[1]
        self.endRow = endSq[0]
        self.endCol = endSq[1]
        self.pieceMoved = board[self.startRow][self.startCol]
        self.pieceCaptured = board[self.endRow][self.endCol]
        self.isEnPassantMove = isEnPassantMove
        self.isPawnPromotionMove = isPawnPromotionMove
        self.isCastleMove = isCastleMove
        self.isCapture = self.pieceCaptured != "--"
        #print(self.isCapture,self.isCastleMove,self.isEnPassantMove,self.isPawnPromotionMove)

        if self.isEnPassantMove:
            self.pieceCaptured = 'bP' if self.pieceMoved == 'wP' else 'wP' # En-passant captures opposite colored pawn.
        
        self.moveID = self.startRow*1000 + self.startCol*100 + self.endRow*10 + self.endCol
        
    def __eq__(self, other: object) -> bool:
        """Check equality by comparing move IDs (start/end square encoding)."""
        if isinstance(other, Move):
            return self.moveID == other.moveID
        return False
    
    def __hash__(self) -> int:
        return self.moveID
    
    def getChessNotation(self) -> str:
        """Return the move in long algebraic notation (e.g. 'e2e4')."""
        return self.getRankFile(self.startRow, self.startCol) + self.getRankFile(self.endRow, self.endCol)
    
    def getRankFile(self, r: int, c: int) -> str:
        """Convert row, col to chess notation (e.g. 'e4')."""
        return self.colsToFiles[c] + self.rowsToRanks[r]
     
    def __str__(self) -> str:
        if self.isCastleMove:
            return "0-0" if self.endCol == 6 else "0-0-0"
        
        endSquare = self.getRankFile(self.endRow, self.endCol)
        if self.pieceMoved[1] == "P":
            if self.isCapture:
                return self.colsToFiles[self.startCol] + "x" + endSquare
            else:
                return endSquare + "Q" if self.isPawnPromotionMove else endSquare
        moveString = self.pieceMoved[1]
        if self.isCapture:
            moveString += "x"
        return moveString + endSquare