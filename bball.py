
'''
bball app implements a basketball signup list.
Email for this app is of the form <*>@bball.appspotmail.com
This app belongs to bball@gmail.com
You need a mailing list address .  And the appspotmail.com
address needs to be able use the mailing list.
'''

import cgi
import logging
import bballdb
import webapp2
import bballoutmail
import string
from datetime import datetime
from bballconfig import *

####################################################################################
# To call these functions via webapp URL:
# http://<appname>.appspot.com/control?function=<func>&arg1=<arg>&arg2=<arg> etc...
#####################################################################################


funcMap = { "setGameStatus" : (1,"bballdb"),
            "setUseAlist"   : (1,"bballdb"),
            "addPlayer"     : (2,"bballdb"),
            "removePlayer"  : (1,"bballdb"),
            "startRoster"   : (2,"bballdb"),
            "startEarlyRoster" : (0, "bballdb"),
            "postRoster"    : (1,"bballdb"),
            "removePlayers" : (0,"bballdb"),
            "currentRoster" : (0,"bballdb"),
            "checkNoPlayers": (0,"bballdb"),
            "signupRandomPlayers": (0, "bballdb")}

def htmlHead():
  return '''
   <link rel="shortcut icon" href="static/favicon.ico" />
   <link rel="stylesheet" type="text/css" href="static/bball.css"/>
   <!--<link href='http://fonts.googleapis.com/css?family=Vollkorn:400italic,400' rel='stylesheet' type='text/css'>-->
   <link href='http://fonts.googleapis.com/css?family=Varela' rel='stylesheet' type='text/css'>
   <!-- <link href='http://fonts.googleapis.com/css?family=Raleway' rel='stylesheet' type='text/css'>-->
   <link href='http://fonts.googleapis.com/css?family=Open+Sans+Condensed:300' rel='stylesheet' type='text/css'>
   <meta name="viewport" content="width=device-width"/>'''

class MainPage(webapp2.RequestHandler):
    def get(self):
        return webapp2.redirect("/static/index.html")


class DirectionsPage(webapp2.RequestHandler):
    def get(self):
        self.response.out.write('''
        <html>
        <head>
           <link href='http://fonts.googleapis.com/css?family=Varela' rel='stylesheet' type='text/css'>
           <link href='http://fonts.googleapis.com/css?family=Open+Sans+Condensed:300' rel='stylesheet' type='text/css'>
           <meta name="viewport" content="width=device-width"/>
           <link rel="stylesheet" type="text/css" href="static/bball.css" />
        </head>
        <body>
        ''')
        if bballdb.getUseAlist():
            self.response.out.write('''<p class="block">Hunt Recreation Center</p>
                <a href="https://goo.gl/maps/tN72M" target="_blank"><p class="block">90 Stow St</p>
                <p class="block">Concord, MA 01742</p></a>

                <p></p>

                <iframe class="optional_mobile" src="https://www.google.com/maps/embed?pb=!1m14!1m8!1m3!1d2943.632630738138!2d-71.350981!3d42.456832!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x89e39a471eb5ee4d%3A0x8d9659de078ed235!2sHunt+Recreation+Center%2C+90+Stow+St%2C+Concord%2C+MA+01742!5e0!3m2!1sen!2sus!4v1411135520200" width="95%" height="450" frameborder="0" style="border:0"></iframe>
               ''')
        else:
            self.response.out.write('''<p class="block">Percy Rideout Playground</p>
                <a href="http://goo.gl/maps/LH5GZ" target="_blank"><p class="block">Intersection of Laws Brook Road and Conant St</p>
                <p class="block">West Concord, MA 01742</p></a>
 
                <p>Courts are on the Laws Brook Road side of the park.</p>

                <iframe src="https://www.google.com/maps/embed?pb=!1m14!1m8!1m3!1d3081.5904116212882!2d-71.399879!3d42.457339999999995!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x89e3908e05aced69%3A0xdb622158aef8cecc!2sRideout+Playground!5e1!3m2!1sen!2sus!4v1411135681769" width="95%" height="450" frameborder="0" style="border:0"></iframe>
                ''')
        self.response.out.write('''
        </body>
        </html>
        ''')

class PlayersListPage(webapp2.RequestHandler):
    def get(self):
      self.response.out.write('''<html>
       <head><title>Player List</title>
       <link rel="shortcut icon" href="static/favicon.ico" />
       <link rel="stylesheet" type="text/css" href="static/bball.css"/>
       <meta name="viewport" content="width=640"/>
       </head>
       <body class="wide">
       <div class="rosterbox">
       <table class="playerlist" id="player_list_table">
       <thead>
         <tr>
         <th></th>
         <th></th>
         <th colspan="4">Signups</th>
         <th colspan="5">Games Played</th>
         <th colspan="2">Missed Cut</th>
         <tr>
         <th class="widen">Email</th>
         <th>Priority</th>
         <th>Total</th><th>Last</th><th>Avg Signup Time</th><th>Early</th>
         <th>Total</th><th>M</th><th>W</th><th>F</th><th>Last</th>
         <th>Total</th><th>Last</th>
       </thead><tbody>
       ''')
      
      # email = ndb.StringProperty(required=True)
      # numSignups = ndb.IntegerProperty(required=True)
      # gamesPlayedM = ndb.IntegerProperty(required=True)
      # gamesPlayedW = ndb.IntegerProperty(required=True)
      # gamesPlayedF = ndb.IntegerProperty(required=True)
      # gamesCut = ndb.IntegerProperty(required=True)
      # lastGame = ndb.DateProperty(required=True)
      # lastSignup = ndb.DateProperty(required=True)
      # averageSignupTime = ndb.FloatProperty(required=True)
      # priorityScore = ndb.IntegerProperty(required=True)
      # isAlist = ndb.BooleanProperty(required=True)

      players = bballdb.getPlayerStatus()
      
      def email_subst(email):
        email = email.replace('@','-at-')
        email = email.replace('.','-dot-')
        return email
        
      for player in sorted(players, key=lambda i: i.email):
        self.response.out.write('''
        <tr><td>{email}</td><td>{prio}</td>
        <td>{sups}</td><td>{lastsup}</td><td>{suptime}</td><td>{early}</td>
        <td>{totp}</td><td>{m}</td><td>{w}</td><td>{f}</td><td>{lastp}</td>
        <td>{cut}</td><td>{lastcut}</td></tr>
        '''.format(
          email=email_subst(player.email),
          sups=player.numSignups,
          lastsup=player.lastSignup,
          suptime=player.signup_time(),
          early=player.numEarlySignups,
          totp=player.gamesPlayed,
          m=player.gamesPlayedM,
          w=player.gamesPlayedW,
          f=player.gamesPlayedF,
          lastp=player.lastGame,
          cut=player.gamesCut,
          lastcut=player.lastCut,
          prio=player.priorityScore
        ))
      self.response.out.write('''</tbody></table></div>
      <p class="block"><a href="/graphs">[Graphs]</a></p></body></html>\n''')

class AlistPage(webapp2.RequestHandler):
    def get(self):
      self.response.out.write('''<html>
               <head><title>Player List "A"</title>
               <link rel="shortcut icon" href="static/favicon.ico" />
               <link rel="stylesheet" type="text/css" href="static/bball.css"/>
               <meta name="viewport" content="width=640"/>
               </head>
               <body>
               <h1>"A" list</h1>
               <div class="rosterbox">
               ''')
      alist_list = []
      with open(ALIST_FILE, 'r') as alist:
        for line in alist:
          line = line.strip()
          if line:
            alist_list.append(line.lower())
      for line in sorted(alist_list):
        self.response.out.write('<span id="alist">%s</span></br>\n' % cgi.escape(line))
      self.response.out.write('''</div></body></html>\n''')

class BlistPage(webapp2.RequestHandler):
    def get(self):
      self.response.out.write('''<html>
               <head><title>Player List "B"</title>
               <link rel="shortcut icon" href="static/favicon.ico" />
               <link rel="stylesheet" type="text/css" href="static/bball.css"/>
               <meta name="viewport" content="width=640"/>
               </head>
               <body>
               <h1>"B" list</h1>
               <div class="rosterbox">
               ''')
      blist_list = []
      with open(BLIST_FILE, 'r') as blist:
        for line in blist:
          line = line.strip()
          if line:
            blist_list.append(line.lower())
      for line in sorted(blist_list):
        self.response.out.write('<span id="blist">%s</span></br>\n' % cgi.escape(line))
      self.response.out.write('''</div></body></html>\n''')

def getRosterStr(current_user=None):
    roster = bballdb.currentRoster(current_user=current_user)
    #logging.info("getInprogressPage %s" % (str(roster))) 
    retstr = '''
          <h1>Signup Roster</h1>
          <p style="text-align:center">%(time)s</p>
          <p class="emph" style="text-align:center">The following %(nump)d player%(s)s currently signed up</p>
          <div class="rosterbox">%(roster)s</div>
          <p class="content_desktop"><span class="alist">Highlighted players</span> are on the "A-list" and will not be bumped by players who are not on the A-list. You
          may be bumped for up to 1 hour after your signup if another player with higher priority signs up (a player gets higher priority if
          they have been recently cut from games due to too many players). A name will be shaded <span style="color:#FC002D">red</span>,
          until that happens. Non-A-list players will be cut from the team from the bottom of this list
          up as "A-list" players sign-up. An asterisk denotes a player who used early signup.</p>
          <p class="content_mobile"><span class="alist">Highlighted players</span> are on the "A-list". A name shaded 
          <span style="color:#FC002D">red</span> can be bumped by a player with higher priority. This lasts
          until an hour after signup.</p>
          ''' % {
            'time':cgi.escape(bballdb.getGameDateTime()),
            'nump':len(roster.roster_list),
            's':'s are' if len(roster.roster_list)>1 else ' is',
            'roster':roster.roster_list_html
          }
    if roster.alt_roster_list:
        retstr += '''
          <h2>Currently missing the cut</h2>
          <p class="content_desktop">The following %(nump)d player%(s)s signed up but aren't in the final game
          at this time. If someone on the game roster (above) drops out, the first person from this list will be added
          to the game. After the final roster goes out, if you are on the game roster but for any reason can't make the game, please offer your spot to these players.</p>
          <p class="content_mobile emph">The following %(nump)d player%(s)s have missed the cut
          at this time:</p>
          <div class="rosterbox">%(roster)s</div>
          ''' % {
            'nump':len(roster.alt_roster_list),
            's':'s' if len(roster.alt_roster_list)>1 else '',
            'roster':roster.alt_roster_list_html
          }
    return retstr

class AddName(webapp2.RequestHandler):
    def get(self):


        if bballdb.isSignupOpen(): # Game sign-up is open
            #logging.info(repr(self.request.headers['Cookie']))
            try:
              defaultUserName = self.request.cookies['emailAddress']
              js_focus = ''
            except KeyError:
              defaultUserName = 'John Doe <john@doe.net>'
              js_focus = '''onfocus="if(this.value=='%s') this.value='';"''' % defaultUserName
            
            js_focus += ''' onblur="if(this.value=='') this.value='%s';" ''' % defaultUserName
            
            defaultUserName = defaultUserName.replace('"', '')
            self.response.out.write('''
             <html>
               <head><title>%(title)s Basketball Sign-up</title>
               %(head)s
               </head>
               <body>
                  <h1>Sign up for %(title)s Basketball</h1>
                  <form action="/signup" method="post">
                    <div>Your name &amp; email address (please enter your <b>real</b> email address!!). If you are signing up for multiple people, please use one email address per person:
                    <input id="text" type="text" %(focus)s name="player" value="%(name)s" size="100"/></div>
                    <div id="note">
                    You may also put your real name before the address with the<br/>
                    email address in angle brackets (e.g. "John Doe &lt;john@doe.net&gt;").
                    </div>
                    <!--
                    <div>Minimum number of players:
                    <select name="pref">
                    <option value="1x1">1x1</option>
                    <option value="2x2">2x2</option>
                    <option value="3x3" selected="selected">3x3</option>
                    <option value="4x4">4x4</option>
                    </div>
                    -->
                    <div><input type="submit" value="I wanna play today!"></div>
                  </form>
                </body>
              </html>''' % {'title':PAGE_TITLE,'name':defaultUserName, 'focus':js_focus, 'head':htmlHead()})
        # elif bballdb.isTimeBeforeListPost(): # Signup is off, but early enough that someone could start the list
        #     self.response.out.write('''
        #      <html>
        #        <head><title>%(title)s Basketball - Start Sign-up</title>
        #        %(head)s
        #        </head>
        #        <body>
        #           <h1>Start the Signup for %(title)s Basketball</h1>
        #           <p>The signup list has not been started yet. If you would like to start
        #           the sign-up list (i.e. send out an email asking for players, etc.), click
        #           the <i>Start Sign-up List</i> button below.</p>
        #           <p><a class="a_button" href="/startSignup">Start Sign-up List</a></p>
        #         </body>
        #       </html>''' % {'title':PAGE_TITLE, 'head':htmlHead()})
        else: # After the game, frozen
            self.response.out.write('''
              <html>
               <head><title>%(title)s Basketball - Roster Frozen</title>
               %(head)s
               </head>
               <body>
                  <h2>Posted roster is frozen until sign up starts again</h2>
                </body>
               </html>   
             ''' % {'title':PAGE_TITLE, 'head':htmlHead()})            

    def post(self):
        
        player = self.request.get('player')
        #pref   = self.request.get('pref')
        pref = "4x4"
        try:
          newPlayer = bballdb.addSignUpPlayer(player,pref)
        except bballdb.InvalidEmailException: # Error - unknown user tried to sign up
          self.response.out.write('''
            <html>
              <head><title>Error! Sign-up</title>
              %(head)s
              </head>
              <body>
              <!--
              <p class="status">You could not be added to the roster because your email
              address is not known to the system.</p>
              <p>Please send an email with the word "subscribe" in the subject from your
              email account to the following address:</p>
              <p class="indented"><a href="mailto:%(email)s?subject=subscribe">%(emailesc)s</a></p>
              <p>After you have recieved confirmation, sign up again with the same address you
              sent the email from, and you should be fine.</p>
              -->
              <p class="status">You could not be added to the roster because your email address is invalid.</p>
              <p>Back to the <a href="/">%(title)s Basketball home page</a></p>
              </body>
            </html>''' % {'title':PAGE_TITLE, 'email':ADMIN_EMAIL,'emailesc':cgi.escape(ADMIN_EMAIL), 'head':htmlHead()})
          return
        except bballdb.NoGameStartedException as e:
            self.response.out.write('''
            <html>
              <head><title>Error! Sign-up</title>
              %(head)s
              </head>
              <body><p class="status">You could not be added to the roster: %(details)s</p>
              <p>Back to the <a href="/">%(title)s Basketball home page</a></p>
              </body>
            </html>''' % {'title':PAGE_TITLE,'details':str(e), 'head':htmlHead()})
            return

        # Save the current address to the cookie  
        self.response.set_cookie('emailAddress', player, max_age=31536000, secure=False)
        
        self.redirect("/roster")
        
        # # Get the roster pane
        # rosterstr = getRosterStr()
        #
        # roster = bballdb.currentRoster()
        # matches_email = [x for x in roster.roster_list if x.name == newPlayer.full_email]
        # if matches_email or bballdb.isEarlySignup():
        #   tag = '<p class="status">You have been added to the roster as "%(player)s"</p>' % {'player':cgi.escape(player)}
        # else:
        #   tag = '<p class="status" style="background-color:red">Your name has been registered but you are not currently on the active roster because too many people have signed up before you</p>'
        #
        # self.response.out.write('''
        # <html>
        #   <head><title>%(title)s Basketball Sign-up</title>
        #       %(head)s
        #   </head>
        #   <body>
        #   %(tag)s
        #   %(roster)s
        #   <table style="width:100%%"><tr>
        #   <td class="td_button" style="width:50%%;"><a class="a_button full_height" href="/roster">Roster</a></td>
        #   <td class="td_button" style="width:50%%;"><a class="a_button full_height" href="/">Home Page</a></td>
        #   </tr>
        #   </table>
        #   <!--<p><i>[click <a href="/roster">here</a> to view the roster at any time]</i></p>-->
        #   <!--<p>Back to the <a href="/">%(title)s Basketball home page</a></p>-->
        #   </body>
        # </html>''' % {'title':PAGE_TITLE, 'tag':tag, 'roster':rosterstr, 'head':htmlHead()})

class Graphs(webapp2.RequestHandler):
  def get(self):
    email_split = lambda x: x.split('@')[0]
    
    with open('graphs.html') as f:
      data = f.read()
      
    templ = string.Template(data)

    # players = list(sorted(bballdb.getPlayerStatus(), key=lambda x: (x.gamesPlayedM+x.gamesPlayedW+x.gamesPlayedF+x.gamesCut), reverse=True))
    players = list(sorted(bballdb.getPlayerStatus(), key=lambda x: (x.gamesPlayed+x.gamesCut), reverse=True))
    
    mapping = {}
    mapping['bar_data_m'] = '[{}]'.format(','.join(str(i.gamesPlayedM) for i in players))
    mapping['bar_data_w'] = '[{}]'.format(','.join(str(i.gamesPlayedW) for i in players))
    mapping['bar_data_f'] = '[{}]'.format(','.join(str(i.gamesPlayedF) for i in players))
    mapping['bar_data_cut'] = '[{}]'.format(','.join(str(i.gamesCut) for i in players))
    mapping['names'] = '[{}]'.format(','.join("'{}'".format(email_split(i.email)) for i in players))
    mapping['signup_time_data'] = '[]'

    self.response.out.write(templ.safe_substitute(mapping))

class RemoveName(webapp2.RequestHandler):
    def get(self):


        if bballdb.isSignupOpen():
            #logging.info(repr(self.request.headers['Cookie']))
            try:
              defaultUserName = self.request.cookies['emailAddress']
              js_focus = ''
            except KeyError:
              defaultUserName = 'John Doe <john@doe.net>'
              js_focus = '''onfocus="if(this.value=='%s') this.value='';"''' % defaultUserName
            
            js_focus += ''' onblur="if(this.value=='') this.value='%s';" ''' % defaultUserName
            defaultUserName = defaultUserName.replace('"', '')
            self.response.out.write('''
             <html>
               <head><title>Quit today's game</title>
               %(head)s
               </head>

               <body>
                  <h1>Quit today's game</h1>
                  <form action="/quit" method="post">
                    <div>Your name & email address: <input id="text" type="text" %(focus)s name="player" value="%(name)s" size="100"/></div>
                    </div>
                    <div><input type="submit" value="I can't play today"></div>
                  </form>
                </body>
              </html>''' % {'head':htmlHead(),'focus':js_focus,'name':defaultUserName})
        else:
            self.response.out.write('''
             <html><body><h2>Posted roster is frozen until sign up starts again</h2></body></html>   
             ''')            

    def post(self):
        
        player = self.request.get('player')
        status, player = bballdb.removeSignUpPlayer(player)
        self.response.set_cookie('emailAddress', player, max_age=31536000, secure=False)
        if status:
            self.response.out.write('''
            <html>
              <head><title>%(title)s Basketball Un-Sign-up</title>
              %(head)s
              </head>
              <body><p class="status">You have been removed from the game</p>
              <h1>Signup Roster</h1>
              <div class="rosterbox">%(roster)s</div>
              <table style="width:100%%"><tr>
              <td class="td_button" style="width:50%%;"><a class="a_button full_height" href="/roster">Roster</a></td>
              <td class="td_button" style="width:50%%;"><a class="a_button full_height" href="/">Home Page</a></td>
              </tr>
              </table>
              </body>
            </html>''' % {'title':PAGE_TITLE,'roster':bballdb.currentRoster().roster_list_html, 'head':htmlHead()})
        else:
            self.response.out.write('''
            <html>
              <head><title>Error! Un-Sign-up</title>
              %(head)s
              </head>
              <body><p class="status">You could not be removed from the game</p>
              <p>Back to the <a href="/">%(title)s Basketball home page</a></p>
              </body>
            </html>'''% {'title':PAGE_TITLE, 'head':htmlHead()})

class AddSubscriber(webapp2.RequestHandler):
    def get(self):
        self.response.out.write('''
         <html>
           <head><title>%(title)s Basketball - Subscribe</title>
              %(head)s
           </head>
           <body>
              <h1>Subscribe for %(title)s Basketball emails</h1>
              <form action="/subscribe" method="post">
                <div>Your name & email address: <input id="text" type="text" onClick="this.select();" name="email" value="your name <you@domain.com>" size="50"/></div>
                </div>
                <div><input type="submit" value="Add to email list"></div>
              </form>
            </body>
          </html>'''% {'title':PAGE_TITLE, 'head':htmlHead()})

    def post(self):
        email = self.request.get('email')
        name,email = bballdb.addSubscriber(email)
        if (email != None):
          title = "%(title)s Basketball - Subscribe" % {'title':PAGE_TITLE}
          content = '"%s" has been added to the mailing list' % cgi.escape(email)
          bballoutmail.notifyNewSubscriber(email)
        else:
          title = "Error! Subscribe"
          content = "You could not be subscribed to the mailing list"
        
        logging.info(repr(bballdb.getAllSubscribers()))
        self.response.out.write('''
            <html>
              <head><title>%s</title>
              %(head)s
              </head>
              <body><p class="status">%s</p>
              <div class="rosterbox">%s</div>
              </body>
            </html>''' % (title, htmlHead(), content, "\n".join([cgi.escape(x) for x in bballdb.getAllSubscribers()])))

class RemoveSubscriber(webapp2.RequestHandler):
    def get(self):
        email = self.request.get('email')
        status = bballdb.removeSubscriber(email)

        self.response.out.write('''
         <html>
           <head><title>%(title)s Basketball - Unsubscribe</title>
              %(head)s
           </head>
           <body>''' % {'title':PAGE_TITLE, 'head':htmlHead()})
        if (status):
          self.response.out.write('''<p class="status">%(email)s has been unsubscribed from the %(title)s Basketball emails</p>'''% {'title':PAGE_TITLE,'email': email})
        else:
          self.response.out.write('''<p class="status">Error! could not unsubscribe %(email)s from the %(title)s Basketball emails</p>'''% {'title':PAGE_TITLE,'email': email})
        self.response.out.write('''
          </html>''')

class Roster(webapp2.RequestHandler):

    def getInprogressPage(self):
      try:
        current_user = self.request.cookies['emailAddress']
      except:
        print('no cookie')
        current_user = None
        
      retstr = getRosterStr(current_user=current_user)
      retstr += '''            <table style="width:100%%"><tr>
            <td class="td_button" style="width:50%%"><a class="a_button full_height" href="/signup">Sign up for today's game</a></td>
            <td class="td_button" style="width:50%%"><a class="a_button full_height" href="/quit">Quit today's game</a></td>
            </tr></table>
      '''
      return retstr
      
    def getGameDecisionPage(self):
      gamestat = bballdb.checkNoPlayers()
      gametime = cgi.escape(bballdb.getGameDateTime())
      try:
        current_user = self.request.cookies['emailAddress']
      except:
        current_user = None
      roster = bballdb.currentRoster(current_user=current_user, nocolor=True)
      if not gamestat.gameon: # no game, no one signed up
          if gamestat.numplayers == 0:
              return '''
              <h1>No Game</h1>
              <p style="text-align:center">%s</p>
              ''' % (gametime)
          else: # No game, not enough people signed up
              return '''
              <h1>No Game Today</h1>
              <p style="text-align:center">%(time)s</p>
              <p class="emph" style="text-align:center">Only %(nump)d player%(s)s signed up</p>
              <div class="rosterbox">%(roster)s</div>
              ''' % {
                'time':gametime, 
                'nump':gamestat.numplayers,
                's':'s' if gamestat.numplayers>1 else '',
                'roster':roster.roster_list_html
              }
      else: # Game on!
          retstr = '''
            <h1>Final Game Roster - Game On!</h1>
            <p style="text-align:center">%(time)s</p>
            <p class="emph" style="text-align:center">%(nump)d players - game at noon</p>
            <div class="rosterbox">%(roster)s</div>
            ''' % {
              'time':gametime, 
              'nump':len(roster.roster_list),
              'roster':roster.roster_list_html
            }
          if roster.alt_roster_list:
            retstr += '''
              <h2>Missed the cut</h2>
              <p>The following %(nump)d player%(s)s signed up but didn't make the final game.
              If you are on the game roster (above) and for any reason can't make the game, please offer your spot to these
              players.</p>
              <div class="rosterbox">%(roster)s</div>
              ''' % {
                'nump':len(roster.alt_roster_list),
                's':'s' if len(roster.alt_roster_list)>1 else '',
                'roster':roster.alt_roster_list_html
              }
          # elif gamestat.obligation:
          #     obligation = "Only people who specified %s when they signed up are obliged to play." + \
          #                  "Others may play if they like." % (' or '.join(gamestat.obligation))
          #
          #     retstr += '''<p><i>%(obligation)s</i></p>\n''' % {
          #         'obligation':obligation.strip()
          #     }
          return retstr

    def get(self):
        if bballdb.isSignupOpen(): # sign-up is in progress, no game decision yet
          content = self.getInprogressPage()
        else: # final decisino has been made
          content = self.getGameDecisionPage()

        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write('''
            <html>
            <head>
            <title>%(title)s Basketball Roster</title>
              %(head)s
            </head>
            <body>
            %(content)s
            </body>
            </html>
            ''' % {'title':PAGE_TITLE,'content':content, 'head':htmlHead()})

# class SubscribeToGroup(webapp2.RequestHandler):

    # def get(self):
        
        # self.response.headers['Content-Type'] = 'text/html'
        # self.response.out.write('''
            # <html>
            # <head>
            # <title>Subscribing to Group</title>
              # %(head)s
            # </head>
            # <body>
            # <p>Sending subscribe email to</p>
            # <div id="rosterbox">%(message)s</div>
            # </body>
            # </html>
            # ''' % {'message':bballoutmail.subscribeEmail(), 'head':htmlHead()})

####################################################################################        
# Handler to test and control major app functions listed in funcMap avove
# url is http://bball@appspot.com/control?function=<func>&arg1=<arg>&arg2=....
####################################################################################

class Control(webapp2.RequestHandler):

    # Method to build a string from URL that can be evaled to
    # to run a python function with arguments 
    def funcString(self):

        #try:
        func = self.request.get('function')
        (numArgs,module) = funcMap[func]
        retStr = "%s.%s(" % (module,func)
        if numArgs:
            retStr += self.funcArg('arg1')
        if numArgs > 1:
            for n in range(2,numArgs+1):
                retStr += ',' + self.funcArg('arg'+str(n))
        retStr += ')'
        return retStr
        #except:
            #return ""

    # Method to parse and correctly type argments in URL
    def funcArg(self, argName):
        arg = self.request.get(argName)
        
        # See if arg evals as a valid object e.g. bool or int. WARNING
        # this will also eval strings that happen to be valid objects!!!
        try:
            eval(arg)
            return arg
        
        # If not assume arg is a string
        except:
            return '"%s"' % arg
    
    def get(self):
        
        fstr = self.funcString()
        if not fstr:
            
            # If unable to parse function from URL then ERROR
            self.response.headers['Content-Type'] = 'text/html'
            self.response.out.write('<html><body>ERROR</body></html>')

        else:
            
            # Run Function and display result
            funcRet = eval(fstr)
            logging.info("Executed %s and it returned %s" % (fstr, str(funcRet)))
            self.response.headers['Content-Type'] = 'text/html'
            self.response.out.write('<html><body>Executed <pre>')
            self.response.out.write(cgi.escape(fstr))
            self.response.out.write('</pre>and returned<pre>')
            self.response.out.write(cgi.escape(str(funcRet)))
            self.response.out.write('</body></html>')

                                
        
class StartSignup(webapp2.RequestHandler):
    def get(self):
        # Run Function and display result
        funcRet = bballdb.startRoster(False, False)
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write('''
            <html>
            <head>
            <title>Signup List Started</title>
              %(head)s
            </head>
            <body>
            <p>The signup list has been started. You have not been added to the signup list.
            Would you like to sign up?</p>
            <p><a class="a_button" href="/signup">Yes, I wanna play today!</a></p>
            <p><a class="a_button" href="/">No, thanks. I'm just starting the list.</a></p>
            </body>
            </html>
            '''% {'head':htmlHead()})

                                
        
# Web page mappings - each page maps to a Handler above
app = webapp2.WSGIApplication([(r'/', MainPage),
                               (r'/directions', DirectionsPage),
                               (r'/alist', AlistPage),
                               (r'/blist', BlistPage),
                               (r'/roster',Roster),
                               (r'/control',Control),
                               (r'/signup',AddName),
                               (r'/startSignup',StartSignup),
                               (r'/quit',RemoveName),
                               (r'/players',PlayersListPage),
                               (r'/graphs',Graphs),
                               (r'/subscribe',AddSubscriber),
                               (r'/unsubscribe',RemoveSubscriber)],debug=True)
