
import random, time, re, itertools

##############################################
# UTILITIES                                  #
##############################################

def flatten_list(x):
    """Turns nested lists of any depth and returns a flat list. I understand that recursion
    is slow and limited (particularly in Python). But it will never be used on a large list.
    Ditto for merge."""
    if not isinstance(x,list):
        return [x]
    else:
        if not x:
            return x
        else:
            return flatten_list(x[0])+flatten_list(x[1:])        

def merge(x,y):
    """Takes two lists with identical dimensions and returns a new list with those
    dimensions in which corresponding elements have been matched in paired lists."""
    if not isinstance(x,list):
        return [x,y]
    if not x:
        return x
    else:
        return [merge(x[0],y[0])]+merge(x[1:],y[1:])

def restring(list_of_strings):
    """The inverse of list(string). Concatenates a list of strings. Accepts non-string values."""
    return ''.join([str(item) for item in list_of_strings])

def vector_sum(a,b):
    return [i+j for i,j in zip(a,b)]

##############################################
# BOARD LOGIC                                #
##############################################

class tic_tac_toe_board(object):
    """ Represent the state of the board. Registers moves. Can determine if a win
    or stalemate has occured. Offers some functions that process board data for
    external consumption (by AIs say)."""
    toggle = {'x':'o','o':'x'}
    turn = 'x'
    winning_line = []
    def __init__(self,board=None,turn=None):
        if not board:
            self.board = [['','',''],['','',''],['','','']]
        else:
            self.board = board
        if turn:
            self.turn = turn
        if not self.is_valid_board():
            raise ValueError('tic_tac_toe_board intialized with invalid board, requires 3x3 list of "x","o",""')
        self.parse_board()
        self.get_line_status()
        self.line_defs = self.line_definitions()
        self.move_keys = [[str(i)+str(j) for j in range(3)] for i in range(3)]
        self.available = self.get_available()

    def line_definitions(self,size=3):
        """Defines the 11 lines of the board as 'ij' indices."""
        lines = []
        # rows and columns
        for i in range(size):
            row = []
            column = []
            for j in range(size):
                row.append('%s%s'%(i,j))
                column.append('%s%s'%(j,i))
            lines += [row,column]
        # diagonals
        diagonals = [[],[]]
        for i in range(size):
            diagonals[0].append('%s%s'%(i,i))
            diagonals[1].append('%s%s'%(i,size-i-1))
        lines += diagonals
        return lines
                
    def parse_board(self):
        """Creates an attribute containing the 11 lines in their actual states (e.g. ['x','','o']). """
        self.lines = [[self.board[int(i)][int(j)] for i,j in line] for line in self.line_definitions()]     
        
    def get_available(self):
        """Returns a list of available move represented as 'ij' strings. Useful when a board is loaded
        with an intermediate state."""
        available = []
        for i in range(3):
            for j in range(3):
                if not self.board[i][j]:
                    available += [str(i)+str(j)]   
        return available       

    def get_line_status(self):
        """Line status returns counts of the 'x's and 'o's in each of the eleven lines of the board_object. It
        makes it easy to talk about state of those lines."""
        line_status = []
        for line in self.lines:
            line_status.append([line.count('x'),line.count('o')])
        self.line_status = line_status
        
    def move(self,location):
        """Performs all of the actions associated with a move. Fails silently with state unchanged if 
        the move is not possible."""
        if not self.board[location[0]][location[1]]:
            # perform move
            self.board[location[0]][location[1]] = self.turn
            # remove location from available move list
            self.available.remove(str(location[0])+str(location[1]))
            # update parse and line status, useful logical correlates
            self.parse_board()
            self.get_line_status()
            # end moving player's turn
            self.turn = self.toggle[self.turn]
 
    def is_game_over(self):
        if self.get_winner():
            return True
        if self.is_stalemate():
            return True
        return False
        
    def get_winner(self):
        """Returns winner if one exists."""
        for line in self.line_status:
            if 3 in line:
                if line[0]:
                    return 'x'
                else:
                    return 'o'
        return ''                       
                
    def is_stalemate(self):
        """Returns True if a stalemate has occured. My game terminates when this occurs 
        rather than requiring players to play out futile late moves."""
        for line in self.lines:
            if not ('x' in line and 'o' in line):
                return False
        if self.get_winner():
            return False
        return True

    def is_valid_board(self):
        """Checks for 3x3 array of strings either 'x' or 'o' or ''."""
        valid = True
        if not isinstance(self.board,list):
            valid = False
        if not len(self.board)==3:
            valid = False
        for row in self.board:
            if not isinstance(row,list):
                valid = False
                if not len(row)==3:
                    valid = False
            for element in row:
                if not element in ['x','o','']:
                    valid = False
        return valid

    def print_board(self):
        """Useful for text-based game as well as debugging."""
        out = '\n'
        out += '    1 2 3 \n'
        i = 1
        for row in self.board:         
            out += '\n   -------\n'
            row_string = str(i)+'  |'
            i+=1
            for cell in row:
                if not cell:
                    cell=' '
                row_string += cell+'|'
            out += row_string
        out += '\n   -------'
        return out

##############################################
# GAME CONTROLLER                            #
##############################################

# text version
class tic_tac_toe_game(object):
    fast = False
    def __init__(self,board=None,turn=None, ai_players='o'):
        if not turn:
            print 'Welcome to the tic-tac-toe game!'
            print 'Play online at www.henrybissonnette.com/programming/tic-tac-toe/'
            print 'type help for help'
            print 'type exit to leave\n\n'
            print 'consulting the oracle'
            self.pause(1)
            turn = random.choice(['x','o'])
            print turn + ' goes first.\n'
        self.board_object = tic_tac_toe_board(board=board,turn=turn)
        self.ai_players=ai_players
        if self.ai_players:
            self.ai = tic_tac_toe_AI(self.board_object)
        self.play_round()

    def check_tokens(self, string):
        """ These tokens allow the user to interupt the game with special commands. """
        string = string.strip()
        if 'exit' in string or 'quit' in string:
            self.quit_game()
            return 'exit'
        if 'help' in string or 'info' in string:
            self.print_help()
            return 'help'
        if 'fast' in string:
            self.fast = not self.fast
            if self.fast:
                setting = 'on'
            else:
                setting = 'off'
            print 'fast is set to '+setting
            return 'fast'
        return False

    def parse_move(self, move):
        """Validates move and give prompts to correct inputs."""
        reg=r'[0-9]'
        numbers = re.findall(reg,move)
        if len(numbers)!= 2:
            print """Moves must consist of two integers indicating the row
and column of the cell you want to play (e.g. (1,1))"""
            
        else:
            numbers = [int(i)-1 for i in numbers ]
            if min(numbers)>=0 and max(numbers)<=2:
                if restring(numbers) in  self.board_object.available:
                    return numbers
                else:
                    print 'Move taken, choose a different cell.'
            else:
                print numbers
                print 'rows and columns are numbered 1 through 3'

    def play_game(self,*args):
        self.__init__(args)
        
    def play_round(self):
        if self.board_object.get_winner() or self.board_object.is_stalemate():
            self.game_over()
            return
        else:
            if self.board_object.turn in self.ai_players:
                print 'computer is taking it\'s turn'
                print 'AI '+ self.board_object.turn+': hmmm....'
                print self.board_object.print_board()
                self.pause(1)
                current = self.board_object.move(self.ai.move())
            else:
                print 'player '+ self.board_object.turn
                print 'it\'s your turn'
                print self.board_object.print_board()
                move = None
                while not move:
                    move = raw_input('enter move (row,column) e.g. 1,1 or 11:')
                    token = self.check_tokens(move)
                    if token:
                        move = ''
                        if token == 'exit':
                            return
                    else:
                        move = self.parse_move(move)
                current = self.board_object.move(move)
        print '\n'
        self.play_round()

    def print_help(self):
        print """
tic-tac-toe help
------------------
Tic-Tac-Toe: To win this game you need to get three of your symbol, 'x's or 'o's in a
row. This can be done vertically, horizontally, or diagonally. The AI never loses.
Good luck! 

Moving: The move function will accept any input that includes two and only two numbers
between one and three. [3:;3], 21, row 1 column 1, would all be acceptable inputs. If
you're confused by what the numbers mean look at the numbers around the edge of the board
to identify row and column numbers.
v   1 2 3 <<<
v
v  -------
1  | | | |
   -------
2  | | | |
   -------
3  | | | |
   -------

AI: When you start additional games you are given the option to choose the numer of AI
opponents. You can choose 0-2 with the results: 0 AI players (PvP), 1 AI player (PvC),
or 2 AI players (CvC: simulation).

Speed: In order to add interest and give users time to read outputs this game sometimes
inserts pauses between lines. If you find this irritating, you can turn these pauses off
at any time by typing: fast. If you change your mind you can turn them back on by typing
fast again.

If you would like to leave the game you can type 'quit' or 'exit' at any time.

If you want to return to this screen just type 'help' or 'info'.

"""
        raw_input('press enter to continue')

    def game_over(self):
        """Upon completion of a game ask if user wants to play another.
        User has the option of choosing 0 AI players (PvP), 1 AI player (PvC),
        or 2 AI players (CvC: simulation)."""
        print self.board_object.print_board()
        if self.board_object.get_winner():
            print self.board_object.get_winner() + ' wins!'
        if self.board_object.is_stalemate():
            print 'draw'
            for useless in range(3):
                self.pause(.5)
                print '.'
            print 'weeeee...'
        self.pause(1)
        repeat=''
        while not repeat:
            repeat = raw_input('Play again? (y/n)')
            token = self.check_tokens(repeat)
            if token:
                repeat = ''
                if token == 'exit':
                    return
            else:
                if repeat:       
                    if repeat.strip()[0] in ['y','Y']:
                        players = ''
                        while not players:
                            players = raw_input('How mant AI players should join?')
                            token = self.check_tokens(players)
                            if token:
                                players = ''
                                if token == 'exit':
                                    return
                            else:
                                reg = r'[0-9]'
                                players = re.findall(reg,players)
                                if players:
                                    players = int(players[0])
                                self.__init__(ai_players='ox'[0:players])
                                break
                    else:
                        self.quit_game()

    def pause(self, duration):
        if not self.fast:
            time.sleep(duration)
            
    def quit_game(self):
        print 'Don\'t feel bad...'
        self.pause(.75)
        print 'You probably just need to practice more...'
        self.pause(1)
        print 'Have a nice day!'
        self.pause(2)
        print 'Don\'t forget to visit www.henrybissonnette.com/programming/tic-tac-toe/ !'
        print 'To play more enter: tictac.play_game()'
        

##############################################
# AI PLAYER                                  #
##############################################
    
class tic_tac_toe_AI(object):

    def __init__(self, board_object):
        self.board_object = board_object

    def update_board(self,board):
        self.board_object = board_object
        
    def get_move_ranks(self):
        """Move ranks returns a list of data structures that represent the quality
        of each possible move. The structures look like [string,integer] eg. ['110',-1]. The string 
        always represents an integer such as '210' or '1100' where each number represents 
        a winnable line (a line occupied by only one player) that the cell being evaluated 
        is a part of, and the numeral is the number of moves already on that line.
        So '210' means that that cell is a winning move for one of the players and
        would create 2-on-a-line for one of the player (perhaps the same perhaps different).
        The integer value in the rank structure represents the difference between xs and os
        in lines that include the present cell (postive if more are the player's own). This tends
        to bias the computer toward winning or building it's own lines over blocking it's opponent.

        In theory then, the lexigraphic max of the ranks would yield the best (or at least a good) move.
        ['210',1] > ['210',-1] #the move on the left represents a win, that on the right blocks a win
        ['110',2] > ['10',1] #the move on the left represents fork, that on the right makes a single two-in-a-row 
        The scheme works great in the late game. I discovered however that there were early game cases that the
        ranks got wrong. So, with regret, I kludged in a special case. 

        It's still not the most winning of all possible algorithms, but I really wanted to come
        up with one clean rule that would make decisions for my ai, rather than use lots of
        special cases.
        """
        # move keys is for mapping cells into moves
        move_keys = [[str(i)+str(j) for j in range(3)] for i in range(3)]
        # first element in rank
        move_scores = [[[] for i in range(3)] for j in range(3)]
        # second element in rank, lexigraphically inferior
        differentials = [[0 for i in range(3)] for j in range(3)]
        # both of these measures rely on counts along the lines that intersect each cell
        for line in self.board_object.line_definitions():
            # didn't grab from board_object.parse_board because I wanted 'ij's for later
            actual = [self.board_object.board[int(i)][int(j)] for i,j in line]
            xs = actual.count('x')
            os = actual.count('o')
            if not os or not xs: # contested lines are useless and don't contribute to ranks
                if self.board_object.turn is 'x': # which player am I
                    diff = xs - os
                else:
                    diff = os - xs
                for location in line:
                    if location in self.board_object.available: # taken moves get null rank ['',0]
                        move_scores[int(location[0])][int(location[1])] += [xs + os]
                        differentials[int(location[0])][int(location[1])] += diff
        move_scores = [[restring(sorted(item,reverse=True)) for item in row] for row in move_scores]
        move_ranks = merge(move_scores,differentials)
        return move_ranks        
            
    def move(self):
        """in most cases move returns the highest ranked move..."""
        max = []
        ties = []
        if len(self.board_object.available)==6:
            corner = self.is_corner_start()
            if corner:
                ties = corner
        if not ties: # if a special case was applied don't run rankings
            ranks = self.get_move_ranks()
            for i in range(3):
                for j in range(3):
                    if ranks[i][j] > max:
                        max = ranks[i][j]
                        ties = [str(i)+str(j)]
                    if ranks[i][j] == max:
                        ties += [str(i)+str(j)]

        return [int(item) for item in list(random.choice(ties))]

    def is_corner_start(self):
        "detects corner starts and returns counter move"
        turn = self.board_object.turn
        off = {'x':'o','o':'x'}[turn]
        if [off,turn,off] in self.board_object.lines[-2:]:
            return ['01','10','12','21']
        return None
                
        


##############################################
# TEST FUNCTIONS                              #
##############################################

class AI_arena(object):
    """Allows AI's to play each other for statistical glory."""
    def __init__(self,ai_1,ai_2=None,turn='x'):
        self.board_object = tic_tac_toe_board(turn = turn)
        self.ai_x = eval(ai_1+'(self.board)')
        if ai_2:
            self.ai_o = eval(ai_2+'(self.board)')
        else:
            self.ai_o = wind_up_AI(self.board_object)

    def super_test(self):
        """Pits an AI against every possible tic-tac-toe strategy
        and returns the results. This takes a while. My AI typically
        scores something like [679402, 0, 46358]. Due to it's use of
        random to select between moves the tie number fluctuates by a
        few hundred each time.
        """
        win_loss_tie = [0,0,0]
        for script in self.ai_o.generate_all_scripts():
            self.ai_o.set_script(script)
            self.new_game()
            win_loss_tie = vector_sum(self.play_round(),win_loss_tie)
            self.new_game(turn='o')
            win_loss_tie = vector_sum(self.play_round(),win_loss_tie)
        return win_loss_tie

    def new_game(self, turn='x'):
        self.board_object.__init__(turn=turn)
        

    def play_round(self):
        if self.board_object.get_winner() or self.board_object.is_stalemate():
            return self.game_over()
        else:
            if self.board_object.turn is 'x':
                self.board_object.move(self.ai_x.move())
            else:
                self.board_object.move(self.ai_o.move())
        return self.play_round()

    def game_over(self):
        winner = self.board_object.get_winner()
        if winner:
            if winner is 'x':
                return [1,0,0]
            else:
                return [0,1,0]
        else:
            return [0,0,1]
        

class wind_up_AI(object):
    """Wind up AI play a script. They strictly prefer moves that occur ealier in
    their script list."""
    def __init__(self, board):
        self.board = board

    def update_board(self,board):
        self.board = board

    def set_script(self, script):
        self.script = script

    def generate_all_scripts(self):
        moves = flatten_list([[str(i)+str(j) for j in range(3)] for i in range(3)])
        return itertools.permutations(moves)

    def move(self):
        for move in self.script:
            if move in self.board_object.available:
                return [int(move[0]),int(move[1])]
            


def test_tic_tac_toe_board(verbose=False):
    """Rudimentary test of board_objects."""

    def set_board(move_list,**kwargs):
        """ Take a list of move then cycles a board through them to get to
        the state we want to test."""
        board_object = tic_tac_toe_board(**kwargs)
        for move in move_list[:-1]:
            board_object.move(move)
        final_state = board_object.move(move_list[-1])
        if verbose:
            print board_object.print_board()
        return board_object
    
    def test_moves(move_list, final_state,**kwargs):
        result = set_board(move_list,**kwargs)
        try:
            current = None
            for item in final_state.iteritems():
                current = item
                actual_result = eval('result.'+item[0])
                assert actual_result == item[1]
            if verbose:
                print 'passed'
        except AssertionError:
            if verbose:
                print 'failed!\n\n'
                final_string = str(current)
                result_string = str((current[0],actual_result))
                message = 'move_list: %s\nand board_args: %s\ndid not give expected result:'
                message += '\n%s\ninstead returned:\n%s' 
                print message % (str(move_list),str(kwargs),final_string,result_string)
            else:
                raise
        
    if verbose:        
        print 'TEST 1'
    move_list = [[0,0],[0,1],[1,1],[0,2],[2,2]]
    final_state = {
        'board':[['x','o','o'],['','x',''],['','','x']],
        'is_game_over()':True,
        'get_winner()':'x',
        'turn':'o'
        }   
    test_moves(move_list,final_state)

    if verbose:
        print 'TEST 2'
    board_args = {'turn':'o'}
    move_list = [[0,0],[1,0],[0,1],[1,1],[0,2]]
    final_state = {
        'board':[['o','o','o'],['x','x',''],['','','']],
        'is_game_over()':True,
        'get_winner()':'o',
        'turn':'x'
        }
    test_moves(move_list,final_state,**board_args)

    if verbose:
        print 'TEST 3'
    board = [['x','o','x',],['o','x','',],['o','x','',]]
    board_args = {'board':board,'turn':'o'}
    move_list = [[2,2]]
    final_state = {
        'board':[['x','o','x',],['o','x','',],['o','x','o',]],
        'is_game_over()':True,
        'get_winner()':'',
        'turn':'x'
        }
    
    test_moves(move_list,final_state,**board_args)

##############################################
# MAIN                                       #
############################################## 
#test_tic_tac_toe_board()
#arena = AI_arena('tic_tac_toe_AI')
#result = arena.super_test() # beware, this takes a while
#print result
#tictac = tic_tac_toe_game()



