from codes import *
from twisted.protocols.basic import LineReceiver

from twisted.internet.protocol import ServerFactory

UNSET_NICK = '*'

class User(LineReceiver):
    def __init__(self, server, addr):
        self.server = server
        self.addr = addr
        self.registered = False
        self.nick = UNSET_NICK
        self.realname = None
        self.channels = []
        
    def connectionMade(self):
        pass

    def connectionLost(self, reason):
        pass

    def lineReceived(self, line):
        self.server.msg_received(self, line)

    def send(self, line):
        self.sendLine(line)

class UserFactory(ServerFactory):
    def __init__(self, server):
        self.server = server

    def buildProtocol(self, addr):
        return User(self.server, addr)


