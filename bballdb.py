import re
import logging
import cgi
from google.appengine.ext import ndb
from google.appengine.api import mail
from google.appengine.ext.db import BadValueError

import bballoutmail
from ustz import *
from datetime import datetime, timedelta, date, time
import random
from bballconfig import *

OPEN_START_HOUR = 18      # Start time of the open period the day before
OPEN_END_HOUR = 11        # Time the list is posted

GAME_DAYS = (0,2,4)       # M, W, F

# The random window, right now 7:10-7:15
RANDOM_MINUTES_START = 7 * 60 + 10
RANDOM_MINUTES_END = RANDOM_MINUTES_START + 5

CUT_SCORE_INCREMENT = 3   # How much to inc priority by when cut
PRIORITY_TIMING = timedelta(hours=1)  # If you have the higher cut-score, how much time does that buy you

def isSignupOpen():
  '''True if signup is open'''
  # Any time the game is open, it's open
  status = getGameStatus()
  if status.inSignup:
    return True
    
  # Otherwise check the time
  now = datetime.utcnow()
  now = now + Eastern_tzinfo().utcoffset(now)
  # If it's a game day and we're before the signup list
  if now.hour < OPEN_END_HOUR and now.weekday() in GAME_DAYS:
    return True
  
  # If it's the day before a game day and we're after the start time
  elif now.hour >= OPEN_START_HOUR and ((now.weekday()+1) % 7) in GAME_DAYS:
    return True
  else:
    return False
  
            
class InvalidEmailException(Exception):
  pass

class NoGameStartedException(Exception):
  pass

prefMap = { "1x1":2,
            "2x2":4,
            "3x3":6,
            "4x4":8,
            "5x5":10 }

class GameStatus(ndb.Model):

    inSignup = ndb.BooleanProperty(required=True)
    timestamp = ndb.DateTimeProperty(auto_now=True)

class UseAList(ndb.Model):

    useAlist = ndb.BooleanProperty(required=True)

class GameProperties(ndb.Model):
    weekDay = ndb.IntegerProperty(required=True) # 0 = Monday
    minNumPlayers = ndb.IntegerProperty(required=True) # Game if we get at least this many players
    maxNumPlayers = ndb.IntegerProperty(required=True) # Absolute max
    
    # If this is different from maxNumPlayers then we will cut people above this
    # number *unless* we get at least maxNumPlayers
    provisionalNumPlayers = ndb.IntegerProperty(required=True) 
                          
class LastGameNumberPlayers(ndb.Model):

    numPlayers = ndb.IntegerProperty(required=True)

class Player(ndb.Model):

    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)
    preference = ndb.IntegerProperty(required=True)
    timestamp = ndb.DateTimeProperty(auto_now_add=True)
    priorityScore = ndb.IntegerProperty(required=False)
    isAlist = ndb.BooleanProperty(required=True)

class Subscriber(ndb.Model):
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)

class PlayerStatus(ndb.Model):
    email = ndb.StringProperty(required=True)
    numSignups = ndb.IntegerProperty(required=True)
    averageSignupTime = ndb.FloatProperty(required=True)
    lastSignup = ndb.DateProperty(required=True)
    
    gamesPlayed = ndb.IntegerProperty(required=True)
    gamesPlayedM = ndb.IntegerProperty(required=True)
    gamesPlayedW = ndb.IntegerProperty(required=True)
    gamesPlayedF = ndb.IntegerProperty(required=True)
    lastGame = ndb.DateProperty(required=False)

    gamesCut = ndb.IntegerProperty(required=True)
    lastCut = ndb.DateProperty(required=False)
    
    priorityScore = ndb.IntegerProperty(required=True)
    isAlist = ndb.BooleanProperty(required=True)
    
    
    def signup_time(self):
      '''signup time as a string'''
      return "{:2d}:{:02d}".format(int(self.averageSignupTime//60 + 7), int(self.averageSignupTime)%60)
    
def today():
  '''Return the day of the week in EST'''
  today = datetime.today()
  return today + Eastern_tzinfo().utcoffset(today)
   
def get_game_props():
  '''Return a GameProperties object for the current day of the week'''
  q = GameProperties.query(ancestor = ndb.Key('GameStatus','Bball'),
                              default_options = ndb.QueryOptions(keys_only = True))
  weekday = today().weekday()
  
  print weekday
    
  dayKeys = q.filter(GameProperties.weekDay == weekday)
  if dayKeys.count():
      for dayProp in dayKeys:
          try:
            day = dayProp.get()
          except BadValueError:
            continue
            
          return day
  else:
      print 'no properties for today, initializing to default'
      day = GameProperties(
        parent = ndb.Key('GameStatus','Bball'),
        weekDay = weekday,
        minNumPlayers = 8,
        maxNumPlayers = 12,
        provisionalNumPlayers = 12
      )
      day.put()
      return day
  
# Update the player status
def updatePlayerStatus(person, playing, signup_timestamp, overflow):
    '''Given an email/name, find an entry in the PlayerStatus database and update it'''
    q = PlayerStatus.query(ancestor = ndb.Key('GameStatus','Bball'),
                              default_options = ndb.QueryOptions(keys_only = True))
    # Sanitize
    name, email = emailParser(person)
    
    if (email == None):
      return False, None

    playerKeys = q.filter(PlayerStatus.email == email)
 
    if not playerKeys.count():
      player = PlayerStatus(parent = ndb.Key('GameStatus','Bball'),
                      email=email,
                      numSignups=0,
                      lastSignup = today(),
                      
                      gamesPlayed = 0,
                      gamesPlayedM = 0,
                      gamesPlayedW = 0,
                      gamesPlayedF = 0,
                      lastGame = None,
                      
                      gamesCut = 0,
                      lastCut = None,
                      
                      averageSignupTime = 0.0,
                      priorityScore = 0,
                      isAlist = False)

      update_player_status(player, playing, signup_timestamp, overflow)
      player.put()
    else:
      for playerKey in playerKeys:
          try:
            player = playerKey.get()
          except BadValueError:
            continue
            
          update_player_status(player, playing, signup_timestamp, overflow)
          player.put()
          break
          
def update_player_status(player, playing, signup_timestamp, overflow):
  '''Update a players status data'''
  ts = signup_timestamp + Eastern_tzinfo().utcoffset(signup_timestamp)
  minutes_7am = (ts.hour - 7) * 60 + ts.minute
    
  player.lastSignup = today()
  player.numSignups += 1
  
  # Compute the average signup time as minutes from 7AM
  alpha = 1.0/player.numSignups
  player.averageSignupTime = (minutes_7am * alpha) + player.averageSignupTime * (1.0 - alpha)
  
  if playing:
    player.lastGame = player.lastSignup
    player.gamesPlayed += 1
    mwf = player.lastGame.weekday()
    
    if mwf == 0:
      player.gamesPlayedM += 1
    elif mwf == 2:
      player.gamesPlayedW += 1
    elif mwf == 4:
      player.gamesPlayedF += 1

    if overflow and player.priorityScore > 0:
      player.priorityScore -= 1
  else:
    player.gamesCut += 1
    player.lastCut = player.lastSignup
    player.priorityScore += CUT_SCORE_INCREMENT
    
def getPlayerStatus():
    return PlayerStatus.query(ancestor = ndb.Key('GameStatus','Bball'))
  
 #class AutoListControl(ndb.Model):
#    mon = ndb.BooleanProperty(required=True)
#    tue = ndb.BooleanProperty(required=True)
#    wed = ndb.BooleanProperty(required=True)
#    thu = ndb.BooleanProperty(required=True)
#    fri = ndb.BooleanProperty(required=True)
    
# Returns a tuple of the full address, sanitized, and the raw email address
def emailParser(email):
    email = email.strip()
    reMatch = re.search(r'^(.*)\<([^\>]+)\>', email)
    
    if reMatch == None:
        atLoc = email.find("@")
        if (atLoc < 0):
            return None,None
        
        reMatch = re.match(r'(.*) (\S+)', email[0:atLoc])
        if (reMatch != None):
          name = reMatch.group(1).strip()
          addr = reMatch.group(2).strip() + email[atLoc:]
        else:
          name = ""
          addr = email

    else:
        name = reMatch.group(1).strip()
        addr = reMatch.group(2).strip()
    
    name = re.sub(r'[^\w ]',' ', name)
    name = name.strip()
    
    if len(name) == 0:
        name = None

    addr = re.sub(r'\s.*','',addr)
    if addr.count("@") != 1:
        return None, None
    
    if not re.match(r'''[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?''', addr, re.I):
        return None, None
    
    # Lower case the address
    if addr.lower() in ['your_email@your_domain.com', 'john@doe.net']:
        return None, None
        
    # Lower case the address
    if (name == None):
        return addr, addr.lower()
    else:
        return (name + " <" + addr + ">", addr.lower())
    
def playerIsAlist(email):
    return True
    email = email.strip()
    
    with open(ALIST_FILE, 'r') as alist:
      for line in alist:
        line = line.strip()
        for name in line.split():
            if email.lower() == name.lower():
                return True

    return False

def getPriorityScore(email):
    
    if (email == None):
      return 0
      
    q = PlayerStatus.query(ancestor = ndb.Key('GameStatus','Bball'),
                              default_options = ndb.QueryOptions(keys_only = True))

    playerKeys = q.filter(PlayerStatus.email == email)
 
    if not playerKeys.count():
      return 0
    else:
      for player in playerKeys:
        try:
          player = player.get()
        except:
          continue
        return player.priorityScore
  
def addPlayer(person,pref_str):
    class signupPlayer(object):
      def __init__(self, full_email, email_address, pref, newplayer):
        self.full_email = full_email
        self.email_address = email_address
        self.pref = pref
        self.newplayer = newplayer
    
    pref = prefMap[pref_str]
    
    players = Player.query(ancestor = ndb.Key('GameStatus','Bball'))
    
    # Sanitize
    name, email = emailParser(person)
    
    if (email == None):
      raise InvalidEmailException("Invalid email %s" % person)

    # Get whether the player is a-list
    if getUseAlist():
      isAlist = playerIsAlist(email)
    else:
      # If the alist is not being used, it's always false
      isAlist = False
      
    #JJG: turn this on for email validation
    #is_valid = validate_email(email)
    #if not is_valid:
    #  return False, "Email address is not valid: %s" % person, None

    priorityScore = getPriorityScore(email)
    
    if players.count():
        for player in players:
            if player.email == email:
                player.name = name
                player.preference = pref
                player.isAlist = isAlist
                player.priorityScore = priorityScore
                player.put()
                return signupPlayer(name, email, pref_str, False)
    player = Player(parent = ndb.Key('GameStatus','Bball'),
                    email=email,
                    name=name,
                    preference = pref,
                    priorityScore = priorityScore,
                    isAlist = isAlist)
    player.put()
    
    # # To stop a race to sign up right at the start, we randomize the start time
    # # for people who sign up before a pre-determine start time.
    # ts = player.timestamp
    # ts = ts + Eastern_tzinfo().utcoffset(ts)
    #
    # if ts.hour < OPEN_HOUR_RANDOM or (ts.hour == OPEN_HOUR_RANDOM and ts.minute < OPEN_MINUTES_RANDOM):
    #   time_since_start = ts.minute*60 + ts.second
    #   offset = random.randint(0, OPEN_MINUTES_RANDOM*60) # Pick a random integer in the N minute range
    #   offset -= time_since_start  # Offset by the current start time so that we end up uniform in 0...N mins
    #   offset += 3600 * (OPEN_HOUR_RANDOM-ts.hour)  # Offset by the extra hours to get after the open period
    #   player.timestamp += timedelta(seconds=offset)
    #   player.put() # add it back to the dB with the alternate timestamp
      
    return signupPlayer(name, email, pref_str, True)

rePref = re.compile(r'(([1-5])\s*[xX]\s*\2)')

# Be careful with cache...if you reload app...the datastore and cache can be
# out of sync...i.e. cache will say status is True but datastore says false
# especially if you just manually set datastore though admin console.  Always
# flush cache manually from console page in these situations

def addSignUpPlayer(sender,subject):
    reObj = rePref.search(subject)
    pref = "4x4" if not reObj else reObj.group(1).replace(" ","").lower() 
    if isSignupOpen():
        player = addPlayer(sender,pref)
        # bballoutmail.successSignUpMsg(sender,pref)
        #checkNoPlayers(test=False)
        return player
    else:
        # bballoutmail.failSignUpMsg(sender)
        raise NoGameStartedException("game not started")
    

# Remove a player from the signup list
def removePlayer(person):
    q = Player.query(ancestor = ndb.Key('GameStatus','Bball'),
                              default_options = ndb.QueryOptions(keys_only = True))
    # Sanitize
    name, email = emailParser(person)
    
    if (email == None):
      return False, None

    playerKeys = q.filter(Player.email == email)
    if playerKeys.count():
        ndb.delete_multi(playerKeys)
        return True, name
    return False, name

def removeSignUpPlayer(sender):
    retVal = False
    if isSignupOpen():
        retVal, sender = removePlayer(sender)
    if sender != None:
        pass
        # bballoutmail.signOffMsg(sender,retVal)
    return retVal, sender
    

def setLastGameNumPlayers(val):
    Akey = ndb.Key('LastGameNumberPlayers','Bball')
    try:
        status = Akey.get()
        if not status: raise Exception
    except:
        logging.info("LastGameNumberPlayers object entity does not exist -- creating...")
        status = LastGameNumberPlayers(key=Akey)

    status.numPlayers = val
    status.put()

    logging.info("setLastGameNumPlayers to %d" % status.numPlayers)
    return "Last game number of players is now %d" % val

def getLastGameNumPlayers():
    Akey = ndb.Key('LastGameNumberPlayers','Bball')
    try:
        status = Akey.get()
        if not status: raise Exception
    except:
        logging.info("LastGameNumberPlayers object entity does not exist -- creating...")
        status = LastGameNumberPlayers(key=Akey)
        status.numPlayers = 0
        status.put()


    return status.numPlayers
    
def setUseAlist(state):
    Akey = ndb.Key('UseAList','Bball')
    try:
        status = Akey.get()
        if not status: raise Exception
    except:
        logging.info("UseAList object entity does not exist -- creating...")
        status = UseAList(key=Akey)

    status.useAlist = state
    status.put()

    logging.info("setUseAlist to %s" % ("True - winter" if status.useAlist else "False - summer") )
    return "A-list mode is now %s" % str(state)

def getUseAlist():
    Akey = ndb.Key('UseAList','Bball')
    try:
        status = Akey.get()
        if not status: raise Exception
    except:
        logging.info("UseAList object entity does not exist -- creating...")
        status = UseAList(key=Akey)
        status.useAlist = IS_ALIST_ACTIVE
        status.put()


    return status.useAlist
    
# Set sign up mode - True enables sign up mode, False disables
def setGameStatus(state):

        
    GSkey = ndb.Key('GameStatus','Bball')
    try:
        status = GSkey.get()
        if not status: raise Exception
    except:
        logging.info("GameStatus object entity does not exist -- creating...")
        status = GameStatus(key=GSkey)

    #if not status:
        #status = GameStatus(inSignup = False, key_name='Bball')
        
    status.inSignup = state
      
    status.put()

    logging.info("setGameStatus to %s" % ("True - in signup mode" if status.inSignup else "False - signup is inactive") )
    return "Game Status is now %s" % str(state)

def getGameStatus():
      
  GSkey = ndb.Key('GameStatus','Bball')
  try:
      status = GSkey.get()
      if not status: raise Exception
  except:
      logging.info("GameStatus object entity does not exist -- creating...")
      status = GameStatus(key=GSkey)
      status.inSignup = False
      status.put()
      
  return status
  
# There are three states to the game:
#
#  1. Signup is open: players can signup
#  2. Email is sent: the email for the day has been sent

def isEmailSent():
  status = getGameStatus()
  return status.inSignup
  
# def getGameStatus():
#
#
#     GSkey = ndb.Key('GameStatus','Bball')
#     try:
#         status = GSkey.get()
#         if not status: raise Exception
#     except:
#         logging.info("GameStatus object entity does not exist -- creating...")
#         status = GameStatus(key=GSkey)
#         status.inSignup = False
#         status.put()
#
#
#     return status.inSignup

def getGameDateTime():

        
    GSkey = ndb.Key('GameStatus','Bball')
    try:
        status = GSkey.get()
        if not status: raise Exception
    except:
        status = GameStatus(key=GSkey)
        status.inSignup = False
        status.put()

    #return str(status.timestamp)[:-7]
    # timestamp is really a datetime object.  The following assumes that timestamp
    # is UTC time and that we always want Eastern time adjusted for Daylight Savings
    return (status.timestamp + Eastern_tzinfo().utcoffset(status.timestamp)).strftime("%a %b %d %Y %I:%M")

def removePlayers():
    playerKeys = Player.query(ancestor = ndb.Key('GameStatus','Bball'),
                              default_options = ndb.QueryOptions(keys_only = True))
    if playerKeys.count():
        ndb.delete_multi(playerKeys)
    setGameStatus(False)
    return True
    
def currentRoster():
    class roster(object):
      '''roster_list is the list of players playing. alt_roster_list is the list of alternate
      players who signed up but didn't make the cut'''
      def __init__(self, roster_list, alt_roster_list):
        self.roster_list = roster_list
        self.alt_roster_list = alt_roster_list

      def __str__(self):
        return 'roster_list=%s,alt_roster_list=%s' % (str(self.roster_list_str),str(self.alt_roster_list_str))

      @classmethod
      def table_row(cls, idx, player, cur_time=None):
        row_classes = []
        if cur_time is not None and player.isAlist:
          if player.timestamp < cur_time:
            row_classes.append('safe')
          else:
            row_classes.append('notsafe')
        row_classes.append({True: 'alist', False: 'blist'}[player.isAlist])
        return '''<tr class="{row}">
        <td>{idx}</td>
        <td>{name}</td>
        <td>{time}</td>
        <td>{score}</td>
        </tr>'''.format(
          row=' '.join(row_classes),
          idx=idx,
          name=cgi.escape(player.name),
          time=(player.timestamp - Eastern_tzinfo().utcoffset(player.timestamp)).strftime('%X'),
          score=player.priorityScore
        )
        
      @property
      def roster_list_str(self):
        return '\n'.join([x.name for x in self.roster_list])

      @property
      def alt_roster_list_str(self):
        return '\n'.join([x.name for x in self.alt_roster_list])

      @property
      def roster_list_html(self):
        cur_time = datetime.utcnow() - timedelta(hours=1)
        return '''<table class="playerlist" id="playing">
        <thead><tr><th>#</th><th class="widen">Player</th><th>Signup Time</th><th>Priority</th></tr></thead>
        <tbody>{body}</tbody>
        </table>'''.format(body='\n'.join(roster.table_row(idx, player, cur_time) for idx,player in enumerate(self.roster_list,start=1)))

      @property
      def alt_roster_list_html(self):
        return '''<table class="playerlist" id="cut">
        <thead><tr><th>#</th><th class="widen">Player</th><th>Signup Time</th><th>Priority</th></tr></thead>
        <tbody>{body}</tbody>
        </table>'''.format(body='\n'.join(roster.table_row(idx, player) for idx,player in enumerate(self.alt_roster_list,start=1)))

    playerKeys = Player.query(ancestor = ndb.Key('GameStatus','Bball'))
    if playerKeys.count():
      play_list, cut_list = sort_player_list(playerKeys)
      
      return roster(play_list, cut_list)

    return roster([],[])
    
def playerHasPriority(x,y):
  '''Sort cmp function. The return value is negative if x < y, zero if x == y and strictly positive if x > y.'''
  if x.priorityScore == y.priorityScore:
    return cmp(x.timestamp, y.timestamp)
    
  elif x.priorityScore > y.priorityScore:
    if x.timestamp - PRIORITY_TIMING <= y.timestamp:
      return -1
    else:
      return 1
      
  else: # y.priorityScore > x.priorityScore
    if y.timestamp - PRIORITY_TIMING <= x.timestamp:
      return 1
    else:
      return -1
  
def sort_player_list(playerKeys):
  '''Sort the player list'''
  # Load the properties for this game
  game_props = get_game_props()
  
  myPlayers = []
  for player in playerKeys:
      myPlayers.append( player )
        
  a_list = sorted([x for x in myPlayers if x.isAlist], cmp=playerHasPriority)
  b_list = sorted([x for x in myPlayers if not x.isAlist], cmp=playerHasPriority)
        
  full_list = a_list + b_list
        
  # Determine the number of players
  if (len(a_list) > game_props.provisionalNumPlayers and
      len(full_list) >= game_props.maxNumPlayers):
     # We have > PROISIONAL A-listers and more players than MAX, use MAX
     cutoff = game_props.maxNumPlayers
  else:
     cutoff = game_props.provisionalNumPlayers
            
  return full_list[:cutoff], full_list[cutoff:]
        
def pref2numPlayers( i ):
    return str(i/2) + 'x' + str(i/2)

    

def numPlayers2pref( s ):
    try:
        return prefMap[s]
    except:
        return 8
    
def finalizeEarlyRoster():
    '''Set the start times for the early roster spots'''
    players = Player.query(ancestor = ndb.Key('GameStatus','Bball'))

    # For players who start early, we randomize their time in some window
    # Get the time 
    ts = datetime.utcnow()
    ts = datetime(year=ts.year, month=ts.month, day=ts.day, hour=0, minute=0, second=0)
    et = Eastern_tzinfo().utcoffset(ts)
    
    for player in players:
      offset = random.randint(RANDOM_MINUTES_START*60, RANDOM_MINUTES_END*60) # Pick a random integer in the N minute range
      player.timestamp = ts + timedelta(seconds=offset) + et
      player.put() # add it back to the dB with the alternate timestamp
      
def startRoster(test, tues_thurs):
    finalizeEarlyRoster()
      
    if not isEmailSent():
        # # If today is tuesday or thursday and yesterday's game didn't get many people and we're using "summer"
        # # rules, then start a game. Otherwise exit
        # #logging.info('%s, %d, %s' % (str(tues_thurs), getLastGameNumPlayers(), str(getUseAlist())))
        # if tues_thurs and (getLastGameNumPlayers() > MAX_NUM_PLAYERS_TUES_THURS or getUseAlist()):
        #     logging.info("startRoster skipped - tuesday thursday")
        #     return False
            
        setGameStatus(True)
        if not test: bballoutmail.gameDayMsg()
        return True

    logging.info("startRoster failed - already in signup mode")        
    return False

# def checkNoPlayersWithEmailToEncourage(test):
#     if getGameStatus():
#         players = Player.query(ancestor = ndb.Key('GameStatus','Bball'))
#         cnt = players.count()
#         if cnt:
#             prefs = [player.preference for player in players]
#             if not isGame(prefs):
#                 # Number or players willing to play with 6 or less players
#                 nm = sum([(pref<=6)for pref in prefs])
#                 logging.info("No game yet:  Currently %d players willing to play at least 3x3" % nm)
#                 if nm == 5:
#                     logging.info("5 Players for at least 3x3 - sending message to encourage signup")
#                     if not test: bballoutmail.oneMorePlayerMsg()
#                     return True
#     return False


def isGame():
    
    players = Player.query(ancestor = ndb.Key('GameStatus','Bball'))

    game_props = get_game_props()
    if players.count() >= game_props.minNumPlayers:
      play_list, cut_list = sort_player_list(players)
      return play_list, cut_list
    else:
      return [],[]


    # Maybe too clever here, but this says out of the set of people
    # willing to play with i or more players, if the sum of willing players for i is greater
    # than i then add i to the list.  If the list is not empty we
    # we have a game.
    #
    # Returns the maximum number of players who must show up
    #
    # hasToPlay = [i for i in set(prefs) if i <= sum([x<=i for x in prefs])]
    # if hasToPlay:
    #     return max(hasToPlay)
    # else:
    #     return 0
    
    
def checkNoPlayers():
    class gameOnStatus(object):
      '''gameon is a boolean whether the game is on. numplayers is how many people
      signed up. obligation is the minimum number of players (a list with strings
      of the form '2x2') that need show up'''
      def __init__(self, gameon, numplayers, play_list, cut_list):
        self.gameon = gameon
        self.numplayers = numplayers
        self.play_list = play_list
        self.cut_list = cut_list
      
      def __str__(self):
        return 'gameon=%s,numplayers=%d,play_list=%d,cut_list=%d'%(str(self.gameon),self.numplayers,len(play_list), len(cut_list))
        
    play_list, cut_list = isGame()
    if play_list:
        return gameOnStatus(True, len(play_list), play_list, cut_list)
        
    # players = Player.query(ancestor = ndb.Key('GameStatus','Bball'))
   #  cnt = players.count()
   #  if cnt:
   #    prefs = [player.preference for player in players]
   #    numGamePlayers = isGame(prefs)
   #  else:
   #    numGamePlayers = 0
   #  if numGamePlayers > 0:
   #      numHasToPlay = sum([x<=numGamePlayers for x in prefs])
   #      if (cnt > numHasToPlay):
   #        obligation = ["%dx%d" % (x,x) for x in range(1,numGamePlayers/2+1) if (2*x) in prefs]
   #      else:
   #        obligation = []
   #
   #      return gameOnStatus(True, cnt, obligation)
    else:
      return gameOnStatus(False, cnt, [])

def savePlayerStatus(gamestat):
  '''Update everyone who signed-up's status'''
  if len(gamestat.cut_list):
    overflow = True
  else:
    overflow = False
    
  for player in gamestat.play_list:
    updatePlayerStatus(player.name, True, player.timestamp, overflow)
    
  for player in gamestat.cut_list:
    updatePlayerStatus(player.name, False, player.timestamp, overflow)
    
def postRoster(test):
    if isEmailSent():
        if not test: setGameStatus(False)
        gamestat = checkNoPlayers()
        
        # Log the number of players
        players = Player.query(ancestor = ndb.Key('GameStatus','Bball'))
        signup_cnt = players.count()
        setLastGameNumPlayers(signup_cnt)
        savePlayerStatus(gamestat)

        if gamestat.gameon:
            if not test: bballoutmail.gameRosterMsg(currentRoster())
            return (gamestat)
        else:
            if not test: bballoutmail.noGameMsg(gamestat.numplayers)
            return (gamestat)

    logging.info("postRoster failed - not in signup mode")
    return False
       
def addSubscriber(person):
    try:
      subscribers = Subscriber.query(ancestor = ndb.Key('Subscribers','Bball'))
    except:
      logging.info("Subscribers object entity does not exist -- creating...")
      status = SubscriberList(key=Subkey)
      status.put()
      subscribers = Subscriber.query(ancestor = ndb.Key('Subscribers','Bball'))
    
    # Sanitize
    name, email = emailParser(person)
    
    my_subscriber = [subscriber for subscriber in subscribers if subscriber.email == email]
    if my_subscriber:
      # already there, update name
      subscriber = my_subscriber[0]
      subscriber.name = name
    else:
      subscriber = Subscriber(parent = ndb.Key('Subscribers','Bball'),
                              email = email,
                              name = name)
    
    subscriber.put()
    return name, email

def removeSubscriber(email):
    try:
      q = Subscriber.query(ancestor = ndb.Key('Subscribers','Bball'),
                              default_options = ndb.QueryOptions(keys_only = True))
    except:
      return False
      
    # Sanitize
    name, email = emailParser(email)
    
    if (email == None):
      return False

    playerKeys = q.filter(Subscriber.email == email)
    if playerKeys.count():
        ndb.delete_multi(playerKeys)
        return True
    
    return False

def getAllSubscribers():
    try:
      subscribers = Subscriber.query(ancestor = ndb.Key('Subscribers','Bball'))
    except:
      logging.info("Subscribers object entity does not exist -- creating...")
      status = SubscriberList(key=Subkey)
      status.put()
      subscribers = Subscriber.query(ancestor = ndb.Key('Subscribers','Bball'))
 
    return [x.email for x in subscribers]

def validate_email(email):
    valid_emails = getAllSubscribers()
    if (email in valid_emails):
      return True
    else:
      raise InvalidEmailException()
      return False

    
def signupRandomPlayers():
  '''Debug tool - signup 15 random players'''
  for i in range(1,16):
    email = 'josh{}@nothing.com'.format(i)
    addPlayer(email, '4x4')
    
  players = Player.query(ancestor = ndb.Key('GameStatus','Bball'))
  
  ts = datetime.utcnow()
  ts = datetime(year=ts.year, month=ts.month, day=ts.day, hour=0, minute=0, second=0)
  et = Eastern_tzinfo().utcoffset(ts)
  
  for player in players:
    offset = random.randint(7*60*60, 8*60*60) # Pick a random integer in the N minute range
    player.timestamp = ts + timedelta(seconds=offset) + et
    player.isAlist = False if random.randint(0,2) == 0 else True
    player.put() # add it back to the dB with the alternate timestamp
