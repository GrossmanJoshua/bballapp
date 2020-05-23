import re
import logging, email
import bballdb
import bballoutmail
from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.ext.webapp.util import run_wsgi_app




class BballMailHandler(InboundMailHandler):
    def receive(self, mail_message):
        m = mail_message
        
        try:
            sub = m.subject
        except AttributeError:
            logging.info("Received email from:" + m.sender + " date: " + m.date + " with no subject")
            return
                         
        logging.info("Received email from: " + m.sender + " subject: " + m.subject + " date: " + m.date)
        
        ###################################################################################################
        # Strip quotes around send name (if any).  This will avoid situation where someone REPLY to all
        # with the game day message and the  mailing list is included, where admin receives one email
        # directly with quotes and a second copy via mailing list (since admin must be a mailing list
        # member) without quotes.
        ###################################################################################################
        
        #sender = m.sender.replace('"','')
        
        ######################################################################
        # Check to see if incoming msg is an intellicast weather report
        # Parse out weather details for today and start roster if appropriate
        ######################################################################

        if 'admin@' in m.sender:
            bballoutmail.forwardMailToAdmin(m)
        
        #if "weather e-mail" in m.subject.lower():
        #    #msg_body = m.bodies('text/plain')
        #    msg_body = m.body.decode()
        #    # need DOTALL for . to include NEWLINES in pattern
        #    forecastRE = re.compile(r'5-Day.+Today:\s+([^,]+),\s+High:\s+([-0-9]+) ?F,',re.DOTALL)
        #    searchObj = forecastRE.search(msg_body)
        #    if not searchObj:
        #        bballoutmail.emailAlert("Bad Weather Message Format", msg_body)
        #    else:
        #        desc = searchObj.group(1)
        #        temp = int(searchObj.group(2))
        #        if ("Sunny"  in desc and temp > 64) or ("Cloudy" in desc and temp > 69):
        #            if bballdb.startRoster(test=False):
        #                logging.info("Started roster based on weather report today: %s, High: %d" % (desc,temp))
        #        else:
        #            logging.info("Weather report not good enough today: %s, High: %d" % (desc,temp))
        
        # Add to the list
        #elif "subscribe" in mail_message.subject.lower():
        #    name,email = bballdb.addSubscriber(sender)
        #    if (email != None):
        #      bballoutmail.notifyNewSubscriber(email)
            
        #  quit order is important.  must be before game day since quit often includes the game day subject
        #elif "quit" in mail_message.subject.lower():
        #    bballdb.removeSignUpPlayer(sender)
        #elif "re: game day" in mail_message.subject.lower():
        #    bballdb.addSignUpPlayer(sender,mail_message.subject)

        # now check for roster commands    
        #elif mail_message.subject.lower().startswith("startroster"):
        #    if not bballdb.startRoster(test=False):
        #        bballoutmail.emailFromAdmin(m.sender,"startRoster Failed", "Start Roster failed...already in sign up mode")
        #elif mail_message.subject.lower().startswith("postroster"):
        #    if not bballdb.postRoster(test=False):
        #        bballoutmail.emailFromAdmin(m.sender,"postRoster Failed", "Post Roster failed...not in sign up mode")
        
application = webapp.WSGIApplication([BballMailHandler.mapping()], debug=True)

def main(): 
    run_wsgi_app(application) 

if __name__ == "__main__": 
    main()
