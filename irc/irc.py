#!/usr/bin/env python

from twisted.internet import reactor

from user import UserFactory
from server import Server

def main():
    reactor.listenTCP(6667, UserFactory(Server("My Server")))
    reactor.run()

if __name__ == "__main__":
    main()
