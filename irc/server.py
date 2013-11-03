from user import UserFactory, UNSET_NICK
from channel import Channel
from codes import *

import re
import socket

MAX_NICK_LEN = 9

class Server(object):
    def __init__(self, name):
        self.name = name[:64]
        self.users = {}
        self.channels = {}

        self.host = socket.getfqdn()
        self.version = "irc-sds-0.1"
        self.createdate = "Thu Oct 24 2013 at 07:23:58 EST"

        self.reg_required = ['join', 'part', 'privmsg']

        self.nick_re = re.compile('[a-zA-Z\[\]\\\`_^{|}]'
                                  '[a-zA-Z0-9\[\]\\\`_^{|}-]{0,8}')
        self.chan_re = re.compile('[&][\x01-\x06\x08-\x09\x0B-\x0C\x0E-\x1F'
                                  '\x21-\x2B\x2D-\x39\x3B-\xFF]{1,49}$')

    def valid_nick(self, nick):
        return bool(self.nick_re.match(nick))

    def valid_chan(self, chan):
        return bool(self.chan_re.match(chan))

    def parse_msg(self, msg):
        string = msg
        prefix = ''
        if string[0] == ':':
            prefix, string = string[1:].split(' ', 1)
        if string.find(':') != -1:
            string, trailing = string.rsplit(':', 1)
            parts = string.split()
            parts.append(trailing)
        else:
            parts = string.split()
        return prefix, parts[0].lower(), parts[1:]

    def msg_received(self, user, msg):
        print "received from {}: {}".format(user.nick, msg)
        self.command(user, *self.parse_msg(msg))

    def command(self, user, prefix, command, args):
        if not user.registered and command in self.reg_required:
            self.respond(user, self.host, ERR_NOTREGISTERED,
                         [':You have not registered'])
        else:
            try:
                getattr(self, "cmd_{}".format(command.lower()))(user, args)
            except AttributeError:
                print "Unsupported IRC command: {} {}".format(command, args)

    def register(self, user, nick):
        self.users[nick] = user
        user.registered = True

        self.respond(user, self.host, RPL_WELCOME, 
                     [':Welcome to the IRC Chat Server '
                      '{}'.format(user.nick)])
        self.respond(user, self.host, RPL_YOURHOST,
                     [':Your host is {}, running version '
                      '{}'.format(self.host, self.version)])
        self.respond(user, self.host, RPL_CREATED, 
                     [':This server was created {}'.format(self.createdate)])
        self.respond(user, self.host, RPL_MYINFO,
                     ['{} {}'.format(self.host, self.version)])

    def notify_set(self, user):
        notify = []
        for chan in user.channels:
            notify.extend(chan.users)
        return set(notify)
        
    def send_names(self, user, chan):
        # don't worry about length of message for now
        names = []
        for u in chan.users:
            names.append(u.nick)
        names.sort()
        
        self.respond(user, self.host, RPL_NAMREPLY,
                     ['@ {} :{}'.format(chan.name, ' '.join(names))])
        self.respond(user, self.host, RPL_ENDOFNAMES,
                     ['{} :End of NAMES list'.format(chan.name)])

    def cmd_pass(self, user, args):
        if user.registered:
            self.respond(user, self.host, ERR_ALREADYREGISTERED,
                         [':You may not reregister'])
        elif args == []:
                     self.respond(user, self.host, ERR_NEEDMOREPARAMS,
                                  ['PASS :Not enough parameters'])
        else:
            # Ignore the password
            pass

    def cmd_nick(self, user, args):
        if args == []:
            self.respond(user, self.host, ERR_NONICKNAMEGIVEN, 
                         [':No nickname given'])
        else:
            nick = args[0][:MAX_NICK_LEN]

            if not self.valid_nick(nick):
                self.respond(user, self.host, ERR_ERRONEUSNICKNAME, 
                             [nick, ':Erroneous nickname'])
            elif nick in self.users:
                    self.respond(user, self.host, ERR_NICKNAMEINUSE,
                                 [nick, ':Nickname is already in use'])
            elif not user.registered:
                user.nick = nick

                if user.realname:
                    self.register(user, nick)
            else:
                old = user.nick
                del self.users[old]
                
                user.nick = nick
                self.users[nick] = user

                for u in self.notify_set(user):
                    self.respond(u, old, 'NICK', [])                 

    def cmd_user(self, user, args):
        if user.registered:
            self.respond(user, self.host, ERR_ALREADYREGISTERED,
                         [':You may not reregister'])
        elif len(args) < 4:
            self.respond(user, self.host, ERR_NEEDMOREPARAMS, 
                         ['USER :Not enough parameters'])
        else:
            user.realname = args[3]
            if not user.nick == UNSET_NICK:
                self.register(user, user.nick)
    
    def cmd_quit(self, user, args):
        pass

    def cmd_join(self, user, args):
        if args == []:
            self.respond(user, self.host, ERR_NEEDMOREPARAMS, 
                         ['JOIN :Not enough parameters'])
        else:
            name = args[0]

            if name == '0':
                for u in self.notify_set(user):
                    self.respond_without_nick(u, user.nick, 'PART', ['{}'.format(name)])

                for c in user.channels:
                    c.users.remove(user)

                user.channels = []

            elif not self.valid_chan(name):
                self.respond(user, self.host, ERR_NOSUCHCHANNEL,
                             [name, ':No such channel'])
            else:
                if not name in self.channels:
                    self.channels[name] = Channel(name)

                chan = self.channels[name]
                if not chan in user.channels:
                    user.channels.append(chan)
                    chan.users.append(user)

                    for u in chan.users:
                        self.respond_without_nick(u, user.nick, 'JOIN', ['{}'.format(name)])

                    self.send_names(user, chan)
                else:
                    # ignore a user's attempt to join a channel of
                    # which they are already a part
                    pass

    def cmd_part(self, user, args):
        if args == []:
            self.respond(user, self.host, ERR_NEEDMOREPARAMS, 
                         ['PART :Not enough parameters'])
        else:
            name = args[0]

            if not name in self.channels:
                self.respond(user, self.host, ERR_NOSUCHCHANNEL,
                             ['{} :No such channel'.format(name)])
            else:
                chan = self.channels[name]
                if chan in user.channels:
                    user.channels.remove(chan)

                    for u in chan.users:
                        self.respond_without_nick(u, user.nick, 'PART', ['{}'.format(name)])
                    chan.users.remove(user)
                else:
                    self.respond(user, self.host, ERR_NOTONCHANNEL,
                                 [name, ":You're not on that channel"])

    def cmd_list(self, user, args):
        pass
        
    def cmd_kick(self, user, args):
        pass
    
    def cmd_privmsg(self, user, args):
        if args == []:
            self.respond(user, self.host, ERR_NORECIPIENT, 
                         [':No recipient given (PRIVMSG)'])
        elif len(args) == 1:
            self.respond(user, self.host, ERR_NOTEXTTOSEND,
                         [':No text to send'])
        else:
            target = args[0]
            message = args[1]

            if not target in self.users and not target in self.channels:
                self.respond(user, self.host, ERR_NOSUCHNICK,
                             [target, ':No such nick/channel'])
            else:
                if target in self.users:
                    self.respond(self.users[target], user.nick, 'PRIVMSG',
                                 [':{}'.format(message)])
                else:
                    for u in self.channels[target].users:
                        if not user == u:
                            self.respond_without_nick(u, user.nick, 'PRIVMSG',
                                                      [target,
                                                       ':{}'.format(message)])
                            
    def cmd_notice(self, user, args):
        pass

    def cmd_topic(self, user, args):
        pass

    def respond(self, user, prefix, command, args):
        message = ':{} {} {}'.format(prefix, command, user.nick)
        if not args == []:
            message = message + ' ' + ' '.join(args)

        user.send(message)
        print "send to {}: {}".format(user.nick, message)

    def respond_without_nick(self, user, prefix, command, args):
        message = ':{} {}'.format(prefix, command)
        if not args == []:
            message = message + ' ' + ' '.join(args)

        user.send(message)
        print "send to {}: {}".format(user.nick, message)


