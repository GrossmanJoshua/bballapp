import logging, email, cgi
from google.appengine.api import mail
from bballconfig import *
import bballdb
import datetime


def emailFromAdmin(recipient, sub, content, wholelist=False):

    if not bballdb.getSendEmails():
        logging.info("Emails are disabled; not seding email To: %s Subject: %s" % (recipient, sub) )
        logging.info(content)
        return

    logging.info("Sent email To: %s Subject: %s" % (recipient, sub) )
    logging.info(content)

    if recipient is not None:
      to = [recipient]
    else:
      to = []

    if wholelist:
      # Add the A List recipients
      to.extend(email.split()[0] for name,email in bballdb.loadAList(onlySendEmail=True)) # only use first name on a line
      # Add the B List recipients
      to.extend(email.split()[0] for name,email in bballdb.loadBList(onlySendEmail=True)) # only use first name on a line

    # Only unique entries, sorted
    to = list(sorted(set([i.lower() for i in to])))

    if not to:
        logging.warning('No recipients, not sending email')
        return

    mail.send_mail(sender=ADMIN_EMAIL,
                       to=to,
                       subject=sub,
                       body=content)

def emailAlert(sub, content):
    logging.warning("Sent ALERT email To: %s Subject: %s" % (ALERT_EMAIL, sub) )
    mail.send_mail(sender=ADMIN_EMAIL,
                       to=ALERT_EMAIL,
                       subject=sub,
                       body=content)

def emailBballGroup(sub, content, wholelist=False):
    emailFromAdmin( None, sub, content, wholelist=wholelist)
#  for subscriber in bballdb.getAllSubscribers():
#    content += "\n\nTo unsubscribe from this mailing list click the following link:\n\n" + \
#               " http://%s.appspot.com/unsubscribe?email=%s\n" % (APP_NAME, subscriber)
#    emailFromAdmin( subscriber, sub, content)

# def subscribeEmail():
    # mail.send_mail(sender=ADMIN_EMAIL,
                       # to=SUBSCRIBE_EMAIL,
                       # subject="",
                       # body="")
    # return SUBSCRIBE_EMAIL

def forwardMailToAdmin(inmsg):
     # log this msg for kicks
     # download the logs to dev machine using:
     # appcfg.py --severity=0 request_logs <appname> <file_to_dump>
     if not hasattr(inmsg, 'subject'):
       inmsg.subject = "####No subject####"

     logging.info("Received a message from: " + inmsg.sender +
                    ", to " + inmsg.to + ", subject: " + inmsg.subject)

     # now make a message object that can be submitted to GAE
     oumsg = mail.EmailMessage()

     # GAE doesn't allow setting the From address to arbitary
     # values. Workaround: Set the sender as the mail redirector
     # and specify the original sender in the body of the email.
     oumsg.sender = REDIRECT_EMAIL

     # is incoming message from the address from which we send? if so,
     # somebody spoofed the address, or GAE encountered an
     # error sending the email and sent an err msg back.
     # for now, just log the event and ignore it. TODO
     # distinguish between error messages and potential loop/spoof.
     inmsg_email_address = email.utils.parseaddr(inmsg.sender)[1]
     my_email_address = email.utils.parseaddr(REDIRECT_EMAIL)[1]
     if inmsg_email_address == my_email_address:
       logging.error("Oops. loop/err/spoof? sender: " + inmsg.sender +
           "subject: " + inmsg.subject + " at date: " + inmsg.date)
       return

     # compute the address to forward to
     oumsg.to = ALERT_EMAIL

     # at least we are allowed to set an arbitrary subject :)
     oumsg.subject = "[FW BBALL APP] " + inmsg.subject

     # gather up the plain text parts of the incoming email
     # and cat them together. Add original sender as body text prefix
     # since we can't set the sender to anything we please.
     # InboundMailMessage can handle multiple plaintext parts
     # but outbound requires a single body field. Hence no option
     # but to cat the multiple parts if present.
     body = None
     for plaintext in inmsg.bodies(content_type='text/plain'):
       if body == None:
         body = "####Original sender: " + inmsg.sender + \
                " and recipient: " + inmsg.to + " #####\n\n"
       body = body + plaintext[1].decode()
       # the above is a bit obscure: bodies is a generator, so can't
       # index into it without a loop. Each iteration returns a tuple
       # (content_type, content). Get to content via [1]. But the the
       # content is of type EmailPayload. Need to call decode() to
       # convert it to Python string. See docs in GAE src for why this is
       # reqd.

     if body == None:
       # corner case: if no body, oumsg.send() will fail. This is
       # a GAE limitation: no emails without body. Set a special
       # string as body.
       oumsg.body = "####Original email had no body text.####"
     else:
       oumsg.body = body

     # do similar things as plaintext for the html parts.
     html = None
     for htmlpart in inmsg.bodies(content_type='text/html'):
       if html == None:
         html = "<P style=\"color: red\">Original sender: " + cgi.escape(inmsg.sender) + \
                " and recipient: " + cgi.escape(inmsg.to) + "<br></br><br></br></p>"
       html = html + htmlpart[1].decode()

     # corner case: if no html in original, dont put one in new
     if html != None:
       oumsg.html = html

     # TODO: attach the attachments.

     logging.info("Sending message to: " + oumsg.to)

     # queue it for sending
     oumsg.send()

     return

def gameDayMsg():
#You can specify your preference to play 2x2, 3x3, 4x4 by
#selecting the appropriate value from the drop-down box.
#
#PLEASE NOTE THAT FOR 2X2 OR 3X3 GAMES EVERYONE WHO SIGNED UP
#(EVEN THOSE WHO DIDN'T SPECIFY 2X2 OR 3x3) WILL SHOW UP ON
#THE FINAL ROSTER.  THOSE INDIVIDUALS WHO DID NOT SIGNUP FOR
#2x2 OR 3x3 ARE NOT OBLIGATED TO SHOW UP.

    emailBballGroup(
"Game Day - %s" % datetime.datetime.today().strftime("%a %b %d %Y"),
"""
To sign-up for Today's game simply click the following link
and enter your email address in the box.

http://%s.appspot.com/signup

You'll get a message back from the mail server acknowledging
your sign-up.

You can see who has signed up so far by browsing the
sign-up list at http://%s.appspot.com/roster

If, for whatever reason after signing up, you wish to
remove yourself from the sign-up list, click the following
linnk and enter your email address in the box:

http://%s.appspot.com/quit

You should receive an acknowledgement email.

Sometime around 11:00 am,the final roster will be emailed to
everyone on the mailing lists.

More details on Concord Basketball can be found at:

http://%s.appspot.com/
"""  % (APP_NAME, APP_NAME, APP_NAME, APP_NAME), wholelist=True )


def gameRosterMsg(roster):
    dt = datetime.datetime.today().strftime("%a %b %d %Y")

    # Get the alternate roster, if any
    if roster.alt_roster_list:
      alt_roster = '''The following players are NOT in the game, but are
alternates in case someone can't make it. If you are on the game list (above)
and cannot make the game, please offer your spot to these players:

%(roster)s

''' % { 'roster': roster.alt_roster_list_str }
    else:
      alt_roster = ''

    emailBballGroup(
"Game Roster - %s" % dt,
'''
%(time)s

%(nump)d players - 1 Game at Noon today

%(roster)s

%(alt_roster)s
''' % {
    'time':dt.split('.')[0],
    'nump':len(roster.roster_list),
    'roster':roster.roster_list_str,
    'alt_roster': alt_roster
  }, wholelist=True)

def noGameMsg(count):
    emailBballGroup(
"No Game - %s" % datetime.datetime.today().strftime("%a %b %d %Y"),
"No game today...%s signed up" % ["no one",
                                  "only 1 person",
                                  "only %d people" % count][count if count < 2 else 2], wholelist=True)

def successSignUpMsg(sdr,pref):

    sub = "Added to B-Ball Game %s - Final list at 11:10 AM" % pref
    content = """

You have been added (at your request) to the basketball sign-up list.
The final roster will be published ~11:00 am.

The current list of people signed up to play today can be found
at http://%s.appspot.com/roster

You can remove yourself from today's sign-up list using the website above.

HOWEVER: Once the final roster comes out at 11:00, there is no convienent
way to add or remove people.  Instead you can state your intentions to
play or quit by hitting "Reply All" to the email.
""" % (APP_NAME)

    emailFromAdmin(sdr, sub, content)

def failSignUpMsg(sdr):

    sub = "Sign up for the Basketball Game is Over/Inactive"
    content = ""
    emailFromAdmin(sdr, sub, content)

def oneMorePlayerMsg():
    emailBballGroup(
"Need One More Bball Player",
"""
We have 5 people signed up for at least 3x3.  Can we get one more
person to sign up (or change their preference)?

The current list of people signed up to play today can be found
at http://%s.appspot.com/roster
""" % APP_NAME )


def signOffMsg(sdr,status):

    if status:
        sub = "You were removed from the Basketball Roster"
        content = "You have been removed the Basketball Roster\nhttp://%s.appspot.com/roster\n" % APP_NAME
    else:
        sub = "Unable to remove you from the Basketball Roster"
        content = "Either you were not signed up as %s or sign up is over and the roster is frozen." % sdr

    emailFromAdmin(sdr, sub, content)

def notifyNewSubscriber(email):
    content = ("You have validated that you are a real person. You may now sign-up for basketball games.\n" + \
              "Go to the following link to sign-up for today's game:\n\n" + \
              " http://%s.appspot.com/signup\n\n" + \
              "To remove yourself from this database, click the following link:\n\n" + \
              " http://%s.appspot.com/unsubscribe?email=%s\n") % (APP_NAME, APP_NAME, email)
    emailFromAdmin( email, "You have been added to the %(title)s Basketball list"% {'title':PAGE_TITLE}, content)
