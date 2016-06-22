import re
import logging
import cgi
from google.appengine.ext import ndb
from google.appengine.api import mail
from google.appengine.ext.db import BadValueError

import bballoutmail
from ustz import *
from datetime import datetime
from bballconfig import *

def isTimeBeforeListPost():
  now = datetime.now()
  hour = (now + Eastern_tzinfo().utcoffset(now)).hour
  if hour < 11:
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

class LastGameNumberPlayers(ndb.Model):

    numPlayers = ndb.IntegerProperty(required=True)

class Player(ndb.Model):

    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)
    preference = ndb.IntegerProperty(required=True)
    timestamp = ndb.DateTimeProperty(auto_now=True)
    isAlist = ndb.BooleanProperty(required=True)

class Subscriber(ndb.Model):
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)

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
    email = email.strip()
    
    with open(ALIST_FILE, 'r') as alist:
      for line in alist:
        line = line.strip()
        for name in line.split():
            if email.lower() == name.lower():
                return True

    return False

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

    if players.count():
        for player in players:
            if player.email == email:
                player.name = name
                player.preference = pref
                player.isAlist = isAlist
                player.put()
                return signupPlayer(name, email, pref_str, False)
    player = Player(parent = ndb.Key('GameStatus','Bball'),
                    email=email,
                    name=name,
                    preference = pref,
                    isAlist = isAlist)
    player.put()
    return signupPlayer(name, email, pref_str, True)

rePref = re.compile(r'(([1-5])\s*[xX]\s*\2)')

# Be careful with cache...if you reload app...the datastore and cache can be
# out of sync...i.e. cache will say status is True but datastore says false
# especially if you just manually set datastore though admin console.  Always
# flush cache manually from console page in these situations

def addSignUpPlayer(sender,subject):
    reObj = rePref.search(subject)
    pref = "4x4" if not reObj else reObj.group(1).replace(" ","").lower() 
    if getGameStatus():
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
    if getGameStatus():
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


    return status.inSignup

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
        return 'roster_list=%s,alt_roster_list=%s' % (str(self.roster_list),str(self.alt_roster_list))

      @property
      def roster_list_str(self):
        return '\n'.join([x[0] for x in self.roster_list])

      @property
      def alt_roster_list_str(self):
        return '\n'.join([x[0] for x in self.alt_roster_list])

      @property
      def roster_list_html(self):
        return '\n'.join(['<span %(alist)s>%(name)s</span><br/>' % {'alist':'id="alist"' if x[3] else '', 'name':cgi.escape(x[0])} for x in self.roster_list])

      @property
      def alt_roster_list_html(self):
        return '\n'.join(['<span %(alist)s>%(name)s</span><br/>' % {'alist':'id="alist"' if x[3] else '', 'name':cgi.escape(x[0])} for x in self.alt_roster_list])

    playerKeys = Player.query(ancestor = ndb.Key('GameStatus','Bball'),
                              default_options = ndb.QueryOptions(keys_only = True))
    if playerKeys.count():
        myPlayers = []
        for playerKey in playerKeys:
            try:
              player = playerKey.get()
            except BadValueError:
              playerKey.delete()
              continue
            myPlayers.append((player.name, player.preference, player.timestamp, player.isAlist))
        
        a_list = sorted([x for x in myPlayers if x[3]], cmp=lambda x,y: cmp(x[2],y[2]) or cmp(x[0],y[0]))
        b_list = sorted([x for x in myPlayers if not x[3]], cmp=lambda x,y: cmp(x[2],y[2]) or cmp(x[0],y[0]))
        
        full_list = a_list + b_list
        
        cutoff = MAXIMUM_NUMBER_OF_PLAYERS
        return roster(full_list[:cutoff], full_list[cutoff:])

    return roster([],[])
    
def pref2numPlayers( i ):
    return str(i/2) + 'x' + str(i/2)

    

def numPlayers2pref( s ):
    try:
        return prefMap[s]
    except:
        return 8
    

def startRoster(test, tues_thurs):
    if not getGameStatus():
        removePlayers()
        
        # If today is tuesday or thursday and yesterday's game didn't get many people and we're using "summer"
        # rules, then start a game. Otherwise exit
        #logging.info('%s, %d, %s' % (str(tues_thurs), getLastGameNumPlayers(), str(getUseAlist())))
        if tues_thurs and (getLastGameNumPlayers() > MAX_NUM_PLAYERS_TUES_THURS or getUseAlist()):
            logging.info("startRoster skipped - tuesday thursday")        
            return False
            
        setGameStatus(True)
        if not test: bballoutmail.gameDayMsg()
        return True

    logging.info("startRoster failed - already in signup mode")        
    return False

def checkNoPlayersWithEmailToEncourage(test):
    if getGameStatus():
        players = Player.query(ancestor = ndb.Key('GameStatus','Bball'))
        cnt = players.count()
        if cnt:
            prefs = [player.preference for player in players]
            if not isGame(prefs):
                # Number or players willing to play with 6 or less players
                nm = sum([(pref<=6)for pref in prefs])
                logging.info("No game yet:  Currently %d players willing to play at least 3x3" % nm)
                if nm == 5:
                    logging.info("5 Players for at least 3x3 - sending message to encourage signup")
                    if not test: bballoutmail.oneMorePlayerMsg()
                    return True
    return False


def isGame(prefs):
    
    # Maybe too clever here, but this says out of the set of people
    # willing to play with i or more players, if the sum of willing players for i is greater
    # than i then add i to the list.  If the list is not empty we
    # we have a game.
    #
    # Returns the maximum number of players who must show up

    hasToPlay = [i for i in set(prefs) if i <= sum([x<=i for x in prefs])]
    if hasToPlay:
        return max(hasToPlay)
    else:
        return 0
    
    
def checkNoPlayers():
    class gameOnStatus(object):
      '''gameon is a boolean whether the game is on. numplayers is how many people
      signed up. obligation is the minimum number of players (a list with strings
      of the form '2x2') that need show up'''
      def __init__(self, gameon, numplayers, obligation):
        self.gameon = gameon
        self.numplayers = numplayers
        self.obligation = obligation
      
      def __str__(self):
        return 'gameon=%s,numplayers=%d,obligation=%s'%(str(self.gameon),self.numplayers,str(self.obligation))
        
    players = Player.query(ancestor = ndb.Key('GameStatus','Bball'))
    cnt = players.count()
    if cnt:
      prefs = [player.preference for player in players]
      numGamePlayers = isGame(prefs)
    else:
      numGamePlayers = 0
    if numGamePlayers > 0:
        numHasToPlay = sum([x<=numGamePlayers for x in prefs])
        if (cnt > numHasToPlay):
          obligation = ["%dx%d" % (x,x) for x in range(1,numGamePlayers/2+1) if (2*x) in prefs]
        else:
          obligation = []

        return gameOnStatus(True, cnt, obligation)
    else:
      return gameOnStatus(False, cnt, [])

        
    
def postRoster(test):
    if getGameStatus():
        if not test: setGameStatus(False)
        gamestat = checkNoPlayers()
        
        # Log the number of players
        players = Player.query(ancestor = ndb.Key('GameStatus','Bball'))
        signup_cnt = players.count()
        setLastGameNumPlayers(signup_cnt)

        if gamestat.gameon:
            if not test: bballoutmail.gameRosterMsg(currentRoster(),gamestat.obligation)
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

    