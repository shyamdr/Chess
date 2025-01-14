import math
import pygame as p
import ChessEngine, ChessAI
from sys import exit
from multiprocessing import Process, Queue

"""
Color codes:
    black -> (255,255,255)
    white -> (0,0,0)
    red -> (255,0,0)
    bright cherry red -> (225,6,0)
    cyan -> (0,255,255)
    muave -> (224, 176, 255)
    Chess.com color palette:
        piece select blue -> (60,186,169)
        light squares -> (237,238,209)
        Dark squares -> (119,153,82)
"""
BOARD_WIDTH = BOARD_HEIGHT = 512
MLP_WIDTH = 300
MLP_HEIGHT = 512
DIMENSION = 8
SQ_SIZE = BOARD_HEIGHT//DIMENSION
MAX_FPS = 15
IMAGES = {}

# Load Images, perform this action only once.
def load_Files():
    pieces = ['bR','bN','bB','bQ','bK','bP',
              'wR','wN','wB','wQ','wK','wP']
    for piece in pieces:
        IMAGES[piece] = p.transform.smoothscale(p.image.load("assets/images/gioco/"+piece+".png"), (SQ_SIZE,SQ_SIZE))
        #IMAGES[piece] = p.transform.scale(p.image.load("images/Default/"+piece+".png"), (SQ_SIZE,SQ_SIZE))
        
    p.mixer.music.load('assets/sounds/Move-standard.mp3')
          
# Main block of code responsible for all functions to call and event to operate.    
def main():
    p.init()
    screen = p.display.set_mode((BOARD_WIDTH + MLP_WIDTH,BOARD_HEIGHT))
    clock = p.time.Clock()
    screen.fill(p.Color("white"))
    moveLogFont = p.font.SysFont("Consolas", 18, False, False)
    gs = ChessEngine.GameState()
    validMoves = gs.getValidMoves()
    moveMade = False # Flag variable for when a move is made.
    animate = False # Flag variable for when to animate a move.
    gameOver = False
    load_Files()
    running = True
    sqSelected = ()
    playerClicks = []
    AIThinking = False
    moveFinderProcess = None
    moveUndone = False
    
    playerOne = True # If white is played by human then true, else false.
    playerTwo = True # If black is played by human then true, else false.    
    while running:
        humanTurn = (playerOne and gs.whiteToMove) or (playerTwo and not gs.whiteToMove)
        for e in p.event.get():
            if e.type == p.QUIT:
                running = False
                # new addition of code
                p.quit()
                exit() 
            # mouse handler
            elif e.type == p.MOUSEBUTTONDOWN:
                if not gameOver:
                    location = p.mouse.get_pos() #(x,y) location of the mouse.
                    col = location[0]//SQ_SIZE
                    row = location[1]//SQ_SIZE
                    if sqSelected == (row,col) or col > 7:
                        sqSelected = ()
                        playerClicks = []
                    else:
                        sqSelected = (row,col)
                        playerClicks.append(sqSelected) #append for both clicks
                    if len(playerClicks) == 2 and humanTurn: #after 2nd click.
                        move = ChessEngine.Move(playerClicks[0], playerClicks[1], gs.board)
                        #print(move.getChessNotation())
                        for i in range(len(validMoves)):    
                            if move == validMoves[i]:
                                gs.makeMove(validMoves[i])
                                p.mixer.music.play()
                                moveMade = True
                                animate = True
                                sqSelected = ()
                                playerClicks = []
                        if not moveMade:
                            playerClicks = [sqSelected]
            # key handler         
            elif e.type == p.KEYDOWN:
                
                # Press 'Z' to undo a move.
                if e.key == p.K_z:
                    if not(playerOne and playerTwo):
                        gs.undoMove()
                    gs.undoMove()
                    moveMade = True
                    animate = False
                    gameOver = False
                    if AIThinking:
                        moveFinderProcess.terminate()
                        AIThinking = False
                    moveUndone = True
                        
                # Press 'Esc' to reset the board    
                if e.key == p.K_ESCAPE:
                    gs = ChessEngine.GameState()
                    validMoves = gs.getValidMoves()
                    sqSelected = ()
                    playerClicks = []
                    moveMade = False
                    animate = False
                    gameOver = False
                    if AIThinking:
                        moveFinderProcess.terminate()
                        AIThinking = False
                    moveUndone = True
                    
        # AI Logic goes here.
        if not(gameOver or humanTurn or moveUndone):
            if not AIThinking:
                AIThinking = True
                #print("Thinking .... \n")
                returnQueue = Queue() # used to pass data betwee threads.
                moveFinderProcess = Process(target = ChessAI.findBestMove, args = (gs,validMoves,returnQueue))
                moveFinderProcess.start() # calls the findBestMove function.
                
            if not moveFinderProcess.is_alive():
                #print("Done thinking.")
                AIMove = returnQueue.get()
                if AIMove is None:
                    AIMove = ChessAI.findRandomMove(validMoves)
                gs.makeMove(AIMove)
                moveMade = True
                animate = True
                AIThinking = False
                
        if moveMade:
            if animate:
                animateMove(gs.moveLog[-1], screen, gs.board, clock)
            validMoves = gs.getValidMoves()
            moveMade = False
            animate = False
            moveUndone = False
            
        drawGameState(screen,gs, validMoves, sqSelected, moveLogFont)
        
        if gs.checkmate or gs.stalemate:
            gameOver = True
            drawEndGameText(screen, 'Stalemate!' if gs.stalemate else 'Black wins by Checkmate!' if gs.whiteToMove else 'White wins by Checkmate!')
                    
        clock.tick(MAX_FPS)
        p.display.flip()
        
# Performs the building of board and pieces at the start.    
def drawGameState(screen, gs, validMoves, sqSelected, moveLogFont):
    drawBoard(screen) # draw the squares on the board.
    highlightSquares(screen, gs, sqSelected) # Highlighting squares on the board.
    drawPieces(screen, gs.board) # add the pieces on the squares. 
    highlightMoves(screen, gs, validMoves, sqSelected) # Highlighting possible moves.
    drawMoveLog(screen, gs, moveLogFont)
    
def drawBoard(screen):
    global colors
    colors = [p.Color((237,238,209)),p.Color((119,153,82))]
    for row in range(DIMENSION):
        for column in range(DIMENSION):
            color = colors[((row+column)%2)]
            p.draw.rect(screen,color,p.Rect(row*SQ_SIZE, column*SQ_SIZE, SQ_SIZE, SQ_SIZE))
    
def highlightSquares(screen,gs,sqSelected):
    # Highlights the last move squares.
    if (len(gs.moveLog)) > 0:
        lastMove = gs.moveLog[-1]        
        s = p.Surface((SQ_SIZE+DIMENSION,SQ_SIZE+DIMENSION))
        s.set_alpha(100)
        s.fill(p.Color((0,255,255)))
        screen.blit(s, (lastMove.endCol*SQ_SIZE-DIMENSION/2, lastMove.endRow*SQ_SIZE-DIMENSION/2))
        screen.blit(s, (lastMove.startCol*SQ_SIZE-DIMENSION/2, lastMove.startRow*SQ_SIZE-DIMENSION/2))
    # Highlights the selected squares.
    if sqSelected != ():
        r,c = sqSelected
        if gs.board[r][c][0] == ('w' if gs.whiteToMove else 'b'):
            s = p.Surface((SQ_SIZE+DIMENSION,SQ_SIZE+DIMENSION))
            s.set_alpha(150) # Make the selected square transparent. Range between (0,255->opaque)
            s.fill(p.Color('yellow'))
            screen.blit(s,(c*SQ_SIZE-DIMENSION/2, r*SQ_SIZE-DIMENSION/2))
    if gs.inCheck:
        r,c = gs.whiteKingLocation if gs.whiteToMove else gs.blackKingLocation
        s = p.Surface((SQ_SIZE,SQ_SIZE))
        s.set_alpha(100)
        s.fill(p.Color('red'))
        screen.blit(s, (c*SQ_SIZE, r*SQ_SIZE))
        
            
def drawPieces(screen,board):
    for row in range(DIMENSION):
        for column in range(DIMENSION):
            piece = board[row][column]
            if piece != "--":
                screen.blit(IMAGES[piece], p.Rect(column*SQ_SIZE, row*SQ_SIZE, SQ_SIZE, SQ_SIZE))
            
def highlightMoves(screen,gs,validMoves,sqSelected):
    if sqSelected != ():
        r,c = sqSelected
        if gs.board[r][c][0] == ('w' if gs.whiteToMove else 'b'):
            s = p.Surface((SQ_SIZE+DIMENSION,SQ_SIZE+DIMENSION))
            s.set_alpha(150) # Make the selected square transparent. Range between (0,255->opaque)
            #s.fill(p.Color('yellow'))
            
            # Highlight moves from the piece on the selected square.
            for move in validMoves:
                 if move.startRow == r and move.startCol == c:
                    p.draw.circle(screen, p.Color((225,6,0)), (move.endCol*SQ_SIZE + SQ_SIZE/2, move.endRow*SQ_SIZE + SQ_SIZE/2), 8)
                    p.draw.circle(screen, p.Color('orange'), (move.endCol*SQ_SIZE + SQ_SIZE/2, move.endRow*SQ_SIZE + SQ_SIZE/2), 8,2)
                    #screen.blit(s, (move.endCol*SQ_SIZE, move.endRow*SQ_SIZE))
                    
def drawMoveLog(screen, gs, font):
    moveLogRect = p.Rect(BOARD_WIDTH, 0, MLP_WIDTH, MLP_HEIGHT)
    p.draw.rect(screen, p.Color(("#464646")), moveLogRect)
    moveLog = gs.moveLog
    moveTexts = []
    for i in range(0, len(moveLog), 2):
        moveString = str(i//2 + 1) + ". " + str(moveLog[i]) + " "
        if i+1 < len(moveLog): #make sure black made a move
            moveString += str(moveLog[i+1]) + "  "
        moveTexts.append(moveString)
    movesPerRow = 2
    padding = 5
    textY = padding
    lineSpacing = 3
    for i in range(0,len(moveTexts), movesPerRow):
        text = ""
        for j in range(movesPerRow):
            if i+j < len(moveTexts):
                text += moveTexts[i+j]
        textObject = font.render(text, True, p.Color('white'))
        textLocation = moveLogRect.move(padding, textY)
        screen.blit(textObject, textLocation)
        textY += textObject.get_height() + lineSpacing
    
def animateMove(move,screen,board,clock):
    global colors
    dR = move.endRow - move.startRow
    dC = move.endCol - move.startCol
    #Slow animations.
    #fps = 10
    #frameCount = round(fps * (math.sqrt(dR**2 + dC**2)))
    frameCount = 5 + round((math.sqrt(dR**2 + dC**2))//2)
    
    for frame in range(frameCount +1):
        r,c = (move.startRow + dR*frame/frameCount, move.startCol + dC*frame/frameCount)
        drawBoard(screen)
        drawPieces(screen, board)
        # Erase the piece moved from its ending square.
        color = colors[(move.endRow + move.endCol)%2]
        endSquare = p.Rect(move.endCol*SQ_SIZE, move.endRow*SQ_SIZE, SQ_SIZE, SQ_SIZE)
        p.draw.rect(screen,color,endSquare)
        # Lightning effect lines.                        
        p.draw.lines(screen,p.Color((187,194,204)),True,[
            (move.startCol*SQ_SIZE + (DIMENSION-2)*4, move.startRow*SQ_SIZE + (DIMENSION+0)*4)
            ,(((move.startCol + 1/3*dC*frame/frameCount)*SQ_SIZE + (DIMENSION+2)*4), ((move.startRow + 1/3*dR*frame/frameCount)*SQ_SIZE + (DIMENSION+2)*4))            
            ,(((move.startCol + 2/3*dC*frame/frameCount)*SQ_SIZE + (DIMENSION+0)*4), ((move.startRow + 2/3*dR*frame/frameCount)*SQ_SIZE + (DIMENSION+4)*4))
            ,(((move.startCol + 3/3*dC*frame/frameCount)*SQ_SIZE + (DIMENSION+0)*4), ((move.startRow + 3/3*dR*frame/frameCount)*SQ_SIZE + (DIMENSION+6)*4))],2)
        
        p.draw.lines(screen,p.Color((187,194,204)),False,[
            (move.startCol*SQ_SIZE + (DIMENSION+0)*4, move.startRow*SQ_SIZE + (DIMENSION+0)*4)
            ,(((move.startCol + 1/3*dC*frame/frameCount)*SQ_SIZE + (DIMENSION-3)*4), ((move.startRow + 1/3*dR*frame/frameCount)*SQ_SIZE + (DIMENSION+2)*4))            
            ,(((move.startCol + 2/3*dC*frame/frameCount)*SQ_SIZE + (DIMENSION+3)*4), ((move.startRow + 2/3*dR*frame/frameCount)*SQ_SIZE + (DIMENSION+4)*4))
            ,(((move.startCol + 3/3*dC*frame/frameCount)*SQ_SIZE + (DIMENSION-3)*4), ((move.startRow + 3/3*dR*frame/frameCount)*SQ_SIZE + (DIMENSION+6)*4))],2)
        
        # Draw captured piece into the rectangle
        if move.pieceCaptured != "--":
            if move.isEnPassantMove:
                enPassantRow = move.endRow+1 if move.pieceCaptured[0] == 'b' else move.endRow-1
                endSquare = p.Rect(move.endCol*SQ_SIZE, enPassantRow*SQ_SIZE, SQ_SIZE, SQ_SIZE)
            screen.blit(IMAGES[move.pieceCaptured], endSquare)
        # Draw moving piece.
        screen.blit(IMAGES[move.pieceMoved], p.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))
        p.display.flip()
        clock.tick(60)

def drawEndGameText(screen, text):
    font = p.font.SysFont("Helvitca", 40, True, False)    
    textObject = font.render(text, 0, p.Color('Gray'))
    textLocation = p.Rect(0, 0, BOARD_WIDTH, BOARD_HEIGHT).move(BOARD_WIDTH/2 - textObject.get_width()/2, BOARD_HEIGHT/2 - textObject.get_height()/2)
    screen.blit(textObject, textLocation)
    textObject = font.render(text, 0, p.Color('Black'))
    screen.blit(textObject, textLocation.move(3,3))
        

if __name__ == "__main__":
    main()