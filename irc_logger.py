#!/usr/bin/env python
"Implements a IRC logger for Twitch"



# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

# system imports
import time, sys
import psycopg2

# import secrets (mainly to hide from github
from ..secrets import *


DB_CONN = psycopg2.connect(
	host=db_config['host'],
	user=db_config['user'],
	password=db_config['password'],
	database=db_config['db']
)

# Code borrow heavily from Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

class DBLogger:
    "A seperate function to write the comments to the DB."


    def __init__(self, db, channel):
	"Takes the cursor for the DB as the only arguement"
        self.db = db
        cur = self.db.cursor()
        cur.execute("""SELECT id
                       FROM channels
                       WHERE channel = %s;""", (channel, ))
        self.channel = cur.fetchone()
        if not self.channel:
            cur.execute("""INSERT INTO channels(channel)
                           VALUES (%s)
                           RETURNING (id);""", (channel, ))
            self.channel = cur.fetchone()
            self.db.commit()
        cur.close()
        print("[init] Got Channel id {} for {}".format(self.channel, channel))


    def log(self, user, comment):
        """Write a message to the DB"""
        cur = self.db.cursor()
        if user == 'twitchnotify':
            return False
        # get user id
	try:
	    cur.execute("""SELECT id
			    FROM users
			    WHERE name = %s;""", (user, ))
	    u_id = cur.fetchone()
            if not u_id:
                print("[log][user] New user: {}".format(user))
                cur.execute("""INSERT INTO users(name)
                               VALUES (%s)
                               RETURNING (id);""", (user, ))
                u_id = cur.fetchone()
                self.db.commit()
        except Exception as e:
            print("[log][user] Encountered error {}".format(e))
            return False
	try:
	    cur.execute("""SELECT id
			    FROM comments
			    WHERE comment = %s;""", (comment, ))
	    c_id = cur.fetchone()
            if not c_id:
                print("[log][comment] New comment: {}".format(comment[:40]))
                cur.execute("""INSERT INTO comments(comment)
                               VALUES (%s)
                               RETURNING (id);""", (comment, ))
                c_id = cur.fetchone()
                self.db.commit()
        except Exception as e:
            print("[log][comment] Encountered error {}".format(e))
            return False
        print("[log][log] {} said {}".format(user, comment[:40]))
        cur.execute("""INSERT INTO log(user_id, comment_id, channel_id)
                       VALUES (%s, %s, %s)""", (u_id, c_id, self.channel))
        self.db.commit()
	cur.close()


    def close(self):
        self.db.close()




class TwitchLogger(irc.IRCClient):
    """A bot to log Twitch Channels"""


    nickname = twitch['name']
    password = twitch['pw']


    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        print("[irc] Connection Made")
        self.logger = DBLogger(DB_CONN, self.factory.channel)


    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        print("[irc] Connection Lost")
        self.logger.close()


    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        self.logger.log(user, msg)





class LogBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, channel):
        self.channel = channel

    def buildProtocol(self, addr):
        p = TwitchLogger()
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()


if __name__ == '__main__':
    # initialize logging
    log.startLogging(sys.stdout)
    
    # create factory protocol and application
    f = LogBotFactory(sys.argv[1])

    # connect factory to this host and port
    reactor.connectTCP("irc.twitch.tv", 6667, f)

    # run bot
    reactor.run()
	
