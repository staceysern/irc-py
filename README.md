IRC Server
===============

This is an IRC server written in Python.  It runs on localhost:6667 and supports a subset of the IRC protocol.  It's a first attempt and needs quite a bit of refactoring.  In particular, the IRC messages should be abstracted into a class.

Server Invocation
-----------------

python irc.py

Unit Tests
----------
 
py.test is used for unit testing.  From the test directory run: 
 
PYTHONPATH=..:${PYTHONPATH} py.test


