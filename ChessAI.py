# =============================================================================
# This is the computer brain, responsible for finding the best move possible and
# playing deadly, inhumane game of chess. (Still pretty stupid actually...)
# =============================================================================

# ----------------
# TO-DO
# -> Calculating phase of the game using numpy arrays,
# -> Transposition tables
# -> opening database & syzygy tables
# -> move ordering before pruning(checks, captures, threats)
# ----------------

import random

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

rookScores =  [[.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, .25],
               [0.5, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.5],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [.25, 0.25, 0.25, 0.50, 0.50, 0.25, 0.25, .25]]

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
    'R': lambda x: (x-4)*250,
    'P': lambda x: 0,
    'K': lambda x: 0
    }

staticPieceActivityScore = {'K': 0, 'Q': 10, 'R': 6, 'N': 4, 'B': 4, 'P': 1}

pieceScore = {'K':0, 'Q': 9, 'R':5, 'N':3, 'B': 3.15, 'P':1}
CHECKMATE = 1000
STALEMATE = 0
DEPTH = 3

""" Finds a random move if the AI cannot find the best move. """
def findRandomMove(validMoves):
    #randMove = validMoves[random.randint(0,len(validMoves)-1)]
    return random.choice(validMoves)


""" Helper Method to make the first recursive call. """
def findBestMove(gs, validMoves, returnQueue):
    global nextMove
    nextMove = None
    findMoveNegaMaxAlphaBeta(gs, validMoves, DEPTH, -CHECKMATE, CHECKMATE, 1 if gs.whiteToMove else -1)
    returnQueue.put(nextMove)


def findMoveNegaMaxAlphaBeta(gs, validMoves, depth, alpha, beta, turnMultiplier):
    global nextMove
    if depth == 0:
        return turnMultiplier * scoreBoard(gs, validMoves)
    
    #move ordering - implement later
    maxScore = -CHECKMATE
    for move in validMoves:
        gs.makeMove(move)
        nextMoves = gs.getValidMoves()
        score = -findMoveNegaMaxAlphaBeta(gs, nextMoves, depth-1, -beta, -alpha, -turnMultiplier)
        if score > maxScore:
            maxScore = score
            if depth == DEPTH:
                nextMove = move
                #print(move, score)
        gs.undoMove()
        if maxScore > alpha:
            alpha = maxScore
        if alpha >= beta:
            break
    return maxScore

            
""" Score the Gamestate based on Material and position(TBD) """        
def scoreBoard(gs, validMoves):
    
    if gs.checkmate:
        if gs.whiteToMove:
            return -CHECKMATE
        else:
            return CHECKMATE
    elif gs.stalemate:
        return STALEMATE
    score = 0
    for row in range(len(gs.board)):
        for col in range(len(gs.board[row])):
            square = gs.board[row][col]
            scoreMultiplier = 1 if square[0] == 'w' else -1 if square[0] == 'b' else 0
            if square != "--":
                # Positional scoring
                piecePositionScore = 0
                if square[1] != "K":
                    piecePositionScore = piecePositionScores[square][row][col]
                    
                # Mobility, Activity -> (AttackScore, DefenseScore)
                mobilityScore = 0
                activityScore = 0
                for move in validMoves:
                    noOfMoves = 0
                    activity = 0
                    if move.startRow == row and move.startCol == col:
                        noOfMoves += 1
                        endPiece = gs.board[move.endRow][move.endCol]
                        if endPiece[1] != '-' and (square[0] + 'K') != endPiece: # Not an empty square or own king.
                            # Activity -> It consists of defensive and attacking ability of a piece.
                            activity += staticPieceActivityScore[square[1]]
                mobilityScore = mobilityScores[square[1]](noOfMoves)
                print(mobilityScore, noOfMoves)
                activityScore = activity/10
                score += scoreMultiplier * (pieceScore[square[1]] + piecePositionScore + mobilityScore + activityScore)
    return score