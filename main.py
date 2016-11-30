#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from os import path
from tictac import tic_tac_toe_board as tic_tac_toe_board
from tictac import tic_tac_toe_AI as tic_tac_toe_AI
import random 
from google.appengine.ext.webapp import template
from google.appengine.ext import db
import webapp2, logging, math
import cPickle as pickle

     
     
class TicTacToeGame(db.Model):  
    ai = db.StringProperty()
    board_object = db.BlobProperty()
        
    def save_board(self, board_object):
        self.board_object = pickle.dumps(board_object)
        self.put()
        
    def load_board(self):
        unpickled = pickle.loads(self.board_object)
        return unpickled
        
            
    
class ActiveGrade(webapp2.RequestHandler):
    def get(self):
        context = {}
        tmpl = path.join(path.dirname(__file__), 'templates/activegrade.html')
        self.response.out.write(template.render(tmpl, context))   

    def post(self):
        
        numbers = []
        error = ''
        number = self.request.get('number')
        if not number:
            error = 'Please enter an input.'
        else:
            try:
                number = int(float(number))
            except:
                try:
                    number = int(number)
                except:
                    fail = True
            try:                
                if number < 0:
                    numbers = [-x for x in range(abs(number)+1)[1:]] 
                    numbers = [1,0]+numbers                 
                else:   
                    if number == 0:
                        numbers = [1,0] 
                    else:
                        number = int(number)
                        numbers = range(number+1)[1:]
            except:
                error = 'Please enter a number.'
        context = {
                   'numbers':numbers,
                   'error':error
                   }
        
        tmpl = path.join(path.dirname(__file__), 'templates/activegrade.html')
        self.response.out.write(template.render(tmpl, context)) 

class Design(webapp2.RequestHandler):
    def get(self):
        context = {}
        tmpl = path.join(path.dirname(__file__), 'templates/design.html')   
        self.response.out.write(template.render(tmpl, context))

class Home(webapp2.RequestHandler):
    def get(self):
        context = {}
        tmpl = path.join(path.dirname(__file__), 'templates/home.html')   
        self.response.out.write(template.render(tmpl, context))
        
class Programming(webapp2.RequestHandler):
    def get(self):
        context = {}
        tmpl = path.join(path.dirname(__file__), 'templates/programming.html')   
        self.response.out.write(template.render(tmpl, context)) 
        
class Grapher(webapp2.RequestHandler):
    def get(self):
        context = {}
        tmpl = path.join(path.dirname(__file__), 'templates/grapher.html')   
        self.response.out.write(template.render(tmpl, context)) 
        
class Resume(webapp2.RequestHandler):
    def get(self):
        context = {}
        tmpl = path.join(path.dirname(__file__), 'templates/resume.html')   
        self.response.out.write(template.render(tmpl, context))
        
class TicTacToe(webapp2.RequestHandler):
    def get(self):   
        ai=random.choice(['x','o'])     
        self.board_object = tic_tac_toe_board()   
        self.game_model = TicTacToeGame()
        self.game_model.ai = ai
        self.game_model.save_board(self.board_object)            
        self.render()
        
    def post(self):
        game_key = self.request.get('game_key')
        self.game_model = db.get(game_key)
        self.board_object= self.game_model.load_board()
        move = self.request.get('move')
        self.board_object.move([int(move[0]),int(move[1])])
        self.render()
    
    def render(self):
        self.check_ai()
        self.game_model.save_board(self.board_object)
        context = {
                   'game':self.board_object,
                   'game_model':self.game_model
                   }
        tmpl = path.join(path.dirname(__file__), 'templates/tic_tac_toe.html')   
        self.response.out.write(template.render(tmpl, context))  
        
    def check_ai(self):
        if self.board_object.turn in self.game_model.ai and not self.board_object.is_game_over():
            ai = tic_tac_toe_AI(self.board_object)
            self.board_object.move(ai.move())
            
class Tasks(webapp2.RequestHandler):
    def get(self, request):
        if request == 'tictac':
            self.tictac()
        
    def tictac(self):
        weekAgo = datetime.datetime.now()-datetime.timedelta(weeks=1)
        expired = TicTacToeGame.all().filter('date <=',weekAgo).fetch(10000) 
        for game in expired:
            game.delete()

            
            
class Udacity(webapp2.RequestHandler):
    def get(self):
        context = {}
        tmpl = path.join(path.dirname(__file__), 'templates/udacity.html')
        self.response.out.write(template.render(tmpl, context))
        
app = webapp2.WSGIApplication([
                               ('/activegrade/',ActiveGrade),
                               ('/design/', Design),
                               ('/grapher/',Grapher),
                               ('/programming/', Programming),
                               ('/programming/udacity/',Udacity),
                               ('/programming/tic-tac-toe/',TicTacToe),
                               ('/resume/',Resume),
                               ('/tasks/(.*)/',Tasks),
                               ('.*', Home)
                               ], debug=True)
