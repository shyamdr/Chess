class GameState():
    
    def __init__(self):
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
        self.enPassantPossible = ()
        self.enPassantPossibleLog = [self.enPassantPossible]
        # Castling rights.
        self.currentCastlingRights = CastleRights(True,True,True,True)
        self.castleRightsLog = [CastleRights(self.currentCastlingRights.wks, self.currentCastlingRights.wqs,
                                             self.currentCastlingRights.bks, self.currentCastlingRights.bqs)]
    
        
    ''' Makes the move that is passed as a parameter. '''    
    def makeMove(self,move):
        self.board[move.startRow][move.startCol] = "--"
        self.board[move.endRow][move.endCol] = move.pieceMoved
        self.moveLog.append(move)
        self.whiteToMove = not self.whiteToMove # Switch turns.
        # Update king's position
        if move.pieceMoved == 'wK':
            self.whiteKingLocation = (move.endRow,move.endCol)
        elif move.pieceMoved == 'bK':
            self.blackKingLocation = (move.endRow,move.endCol)  
        
        # If pawn moves twice, next move can capture en passant.
        if move.pieceMoved[1] == 'P' and abs(move.startRow - move.endRow) == 2:
            self.enPassantPossible = ((move.endRow + move.startRow)//2, move.endCol)
        else:
            self.enPassantPossible = ()
        # If en-Passant move, must update the board to capture the pawn
        if move.isEnPassantMove:
            self.board[move.startRow][move.endCol] = "--"
            
        # Pawn promotion.
        if move.isPawnPromotionMove:
            #promotedPiece = input("Promote to Q,R,B or N:")
            self.board[move.endRow][move.endCol] = move.pieceMoved[0] + "Q"
            
        #Castling
        if move.isCastleMove:
            if move.endCol - move.startCol == 2: # King's side castling.
                self.board[move.endRow][move.endCol-1] = self.board[move.endRow][move.endCol+1] # Moves rook beside king.
                self.board[move.endRow][move.endCol+1] = "--"
            else: # Queen's side castling.
                self.board[move.endRow][move.endCol+1] = self.board[move.endRow][move.endCol-2] # Moves rook beside king.
                self.board[move.endRow][move.endCol-2] = "--"
        # Update enPassant rights.
        self.enPassantPossibleLog.append(self.enPassantPossible)
        # Update Castle rights - whenever it is a rook or king move.
        self.updateCastleRights(move)
        self.castleRightsLog.append(CastleRights(self.currentCastlingRights.wks, self.currentCastlingRights.wqs,
                                                  self.currentCastlingRights.bks, self.currentCastlingRights.bqs))
                
            
    ''' Undo the last move made. '''    
    def undoMove(self):    
        if len(self.moveLog) != 0:
            move = self.moveLog.pop()
            self.board[move.startRow][move.startCol] = move.pieceMoved # Put piece on starting square.
            self.board[move.endRow][move.endCol] = move.pieceCaptured # Put back captured piece. 
            self.whiteToMove = not self.whiteToMove # Switch turns back.
            #move.pgn.pop() # Delete the move from PGN
            # Update king's position.
            if move.pieceMoved == 'wK':
                self.whiteKingLocation = (move.startRow, move.startCol)
            elif move.pieceMoved == 'bK':
                self.blackKingLocation = (move.startRow, move.startCol)
            # Undo en-passant.
            if move.isEnPassantMove:
                self.board[move.endRow][move.endCol] = "--" # Removes the pawn that was added on the wrong square.
                self.board[move.startRow][move.endCol] = move.pieceCaptured # puts the pawn back on the correct square it was captured from.
            self.enPassantPossibleLog.pop()
            self.enPassantPossible = self.enPassantPossibleLog[-1]
            # Undo castling rights.
            self.castleRightsLog.pop()
            newRights = self.castleRightsLog[-1]
            self.currentCastlingRights = CastleRights(newRights.wks, newRights.wqs, newRights.bks, newRights.bqs)
            # Undo castle move.
            if move.isCastleMove:
                if move.endCol - move.startCol == 2: # King side.
                    self.board[move.endRow][move.endCol+1] = self.board[move.endRow][move.endCol-1]
                    self.board[move.endRow][move.endCol-1] = "--"
                else: # Queen side.
                    self.board[move.endRow][move.endCol-2] = self.board[move.endRow][move.endCol+1]
                    self.board[move.endRow][move.endCol+1] = "--" 
            self.checkmate = False
            self.stalemate = False
                    
                
               
    def updateCastleRights(self,move):
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
            if move.startRow == 7:
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
    
    ''' All moves considering checks. '''
    def getValidMoves(self):
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
                # Get rid of any moves that don't block checks or move king
                for i in range(len(moves)-1, -1, -1): # Traversing list backwards when removing elements.
                    if moves[i].pieceMoved[1] != 'K': # Move doesn't move king, so it must block/capture.  
                        if not (moves[i].endRow, moves[i].endCol) in validSquares: # Move doesn't block check or capture piece.
                            moves.remove(moves[i])
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
    
        orderedMoves = []
        for i in range(len(moves)-1, -1, -1):
            if self.inCheck:
                orderedMoves.append(moves[i])
                #moves.remove(moves[i])
            elif self.board[moves[i].endRow][moves[i].endCol] != "--" and self.board[moves[i].endRow][moves[i].endCol][0] != self.whiteToMove:
                orderedMoves.append(moves[i])
                #moves.remove(moves[i])
            else:
                orderedMoves.append(moves[i])
                #moves.remove(moves[i])       
        return orderedMoves
    
    def moveOrdering(self,moves):
        orderedMoves = []
        for i in range(len(moves)-1, -1, -1):
            if self.inCheck:
                orderedMoves.append(moves[i])
                moves.remove(moves[i])
            elif self.board[moves[i].endRow][moves[i].endCol] != "--" and self.board[moves[i].endRow][moves[i].endCol][0] != self.whiteToMove:
                orderedMoves.append(moves[i])
                moves.remove(moves[i])
            else:
                orderedMoves.append(moves[i])
                moves.remove(moves[i])
                
        return orderedMoves
    
    '''Determine if a current player is in check'''
    def InCheck(self):
        if self.whiteToMove:
            return self.squareUnderAttack(self.whiteKingLocation[0], self.whiteKingLocation[1])
        else:
            return self.squareUnderAttack(self.blackKingLocation[0], self.blackKingLocation[1])
        
    '''Determine if enemy can attack the square row col'''    
    def squareUnderAttack(self, row, col):
        self.whiteToMove = not self.whiteToMove  # switch to opponent's point of view
        opponents_moves = self.getAllPossibleMoves()
        self.whiteToMove = not self.whiteToMove
        for move in opponents_moves:
            if move.endRow == row and move.endCol == col:  # square is under attack
                return True
        return False  
    
    # All moves not considering checks.
    def getAllPossibleMoves(self):
        moves = []
        for r in range(len(self.board)):
            for c in range(len(self.board[r])):
                pieceColor = self.board[r][c][0]
                if (pieceColor == 'w' and self.whiteToMove == True) or (pieceColor == 'b' and self.whiteToMove != True):
                    # We have found a the right colored piece at this location (r,c) on board.
                    piece = self.board[r][c][1]
                    self.moveFunctions[piece](r,c,moves) # calls the appropriate move function based on piece.
        return moves

                        
    '''Get all piece moves for Pawns located on the location (r,c).'''    
    def getPawnMoves(self,r,c,moves):
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
                    
                  
    '''Get all piece moves for Knights located on the location (r,c).'''                          
    def getKnightMoves(self,r,c,moves):
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
                    
    '''Get all piece moves for Bishops located on the location (r,c).''' 
    def getBishopMoves(self,r,c,moves):
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
                              
    '''Get all piece moves for Rooks located on the location (r,c).'''   
    def getRookMoves(self,r,c,moves):
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
                
    '''Get all piece moves for Queens located on the location (r,c).'''                
    def getQueenMoves(self,r,c,moves):
        self.getRookMoves(r, c, moves)
        self.getBishopMoves(r, c, moves)
        
    '''Get all piece moves for Kings located on the location (r,c).'''
    def getKingMoves(self,r,c,moves):
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
    
    ''' Returns if the player is in check, a list of pins and a list of checks. '''
    def checkForPinsAndChecks(self):
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
    
    def getCastleMoves(self, r, c, moves):
        if self.squareUnderAttack(r,c):
            return # Can't castle while in check.
        if (self.whiteToMove and self.currentCastlingRights.wks) or (not self.whiteToMove and self.currentCastlingRights.bks):
            self.getKingSideCastleMoves(r,c,moves)
        if (self.whiteToMove and self.currentCastlingRights.wqs) or (not self.whiteToMove and self.currentCastlingRights.bqs):
            self.getQueenSideCastleMoves(r,c,moves)
        
    def getKingSideCastleMoves(self,r,c,moves):
        if self.board[r][c+1] == "--" and self.board[r][c+2] == "--":
            if not self.squareUnderAttack(r,c+1) and not self.squareUnderAttack(r,c+2):
                moves.append(Move((r,c), (r,c+2), self.board, isCastleMove = True))
                
    def getQueenSideCastleMoves(self, r, c, moves):
        if self.board[r][c-1] == '--' and self.board[r][c-2] == '--' and self.board[r][c-3] == '--':
            if not self.squareUnderAttack(r, c-1) and not self.squareUnderAttack(r, c-2):
                moves.append(Move((r, c), (r, c-2), self.board, isCastleMove=True))
        
    

class CastleRights():
    def __init__(self,wks,wqs,bks,bqs):
        self.wks = wks
        self.wqs = wqs
        self.bks = bks
        self.bqs = bqs

                                  
class Move():
    
    # Maps Keys to Values
    ranksToRows = {"1":7, "2":6, "3":5, "4":4, "5":3, "6":2, "7":1, "8":0}
    rowsToRanks = {v: k for k,v in ranksToRows.items()}
    
    filesToCols = {"a":0, "b":1, "c":2, "d":3, "e":4, "f":5, "g":6, "h":7}
    colsToFiles = {v: k for k,v in filesToCols.items()}
    
    pgn = []
    
    def __init__(self, startSq, endSq, board, isEnPassantMove = False, isPawnPromotionMove = False, isCastleMove = False):
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
        
    '''
    Overriding the equals method. 
    The computer isnt able to recognize if the move hard coded in "moves"  in "getAllPossibleMoves"
    function is same as that played on the screen, so in case of using classes, we need to explicitly
    tell that both moves are same known as overriding the equals method.
    '''    
    def __eq__(self,other):
        if isinstance(other, Move):
            return self.moveID == other.moveID
        return False
    
    def getChessNotation(self):
        # originl code:
        return self.getRankFile(self.startRow, self.startCol) + self.getRankFile(self.endRow, self.endCol)
    
    def getRankFile(self,r,c):
        return self.colsToFiles[c] + self.rowsToRanks[r]
     
    def __str__(self):
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