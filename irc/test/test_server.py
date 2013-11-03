from server import Server
from mock import Mock, call
from codes import *

class FakeUser(object):
    def __init__(self):
        self.nick = '*'
        self.registered = False
        self.realname = None
        self.channels = []
        self.send = Mock()
        
class TestServer:
    def setup_method(self, method):
        self.server = Server("TestServer")
        self.user = FakeUser()
        self.user.nick = '*'
        self.user.registered = False
        self.user.realname = None
        
    def register_user(self, user, nick):
        self.server.msg_received(user, 'pass password')
        self.server.msg_received(user, 'nick {}'.format(nick))
        self.server.msg_received(user, 'user {0} 0 * :{0}'.format(nick))

    def setup_channel(self, chan, n):
        users = {}
        for name in ['foo'+str(u) for u in range(n)]:
            users[name] = FakeUser()
            self.register_user(users[name], name)
            self.server.msg_received(users[name], 'join ' + chan)
            users[name].send.reset_mock()
        return users

    # Server methods

    def test_parse(self):
        assert (self.server.parse_msg(':prefix command arg1 arg2 :trailing arg') ==
                ('prefix', 'command', ['arg1', 'arg2', 'trailing arg']))
        assert (self.server.parse_msg('command arg1 arg2 :trailing arg') ==
                ('', 'command', ['arg1', 'arg2', 'trailing arg']))
        assert (self.server.parse_msg(':prefix command :trailing arg') ==
                ('prefix', 'command', ['trailing arg']))
        assert (self.server.parse_msg(':prefix command') ==
                ('prefix', 'command', []))
        assert (self.server.parse_msg(':PREFIX COMMAND ARG1 :TRAILING arg') ==
                ('PREFIX', 'command', ['ARG1', 'TRAILING arg']))

    def test_valid_nick(self):
        assert self.server.valid_nick('s')
        assert self.server.valid_nick('abcdefghi')
        
        letters = map(chr, range(97, 123))
        letters.extend(map(chr, range(65, 91)))
        special = map(chr, range(0x5b, 0x61))
        special.extend(map(chr, range(0x7b, 0x7e)))
        
        non_initial = map(str, range(10))
        non_initial.append('-')

        for c in letters + special:
            assert self.server.valid_nick(c + 'a1[')

        for c in special + non_initial:
            assert self.server.valid_nick('a' + c)

        for c in non_initial:
            assert not self.server.valid_nick(c + 'a')

    def test_valid_chan(self):

        assert self.server.valid_chan('&chan')
        assert not self.server.valid_chan('#chan')
        assert not self.server.valid_chan('!chan')
        assert not self.server.valid_chan('+chan')
        assert not self.server.valid_chan('chan')
        assert not self.server.valid_chan('#')
        assert not self.server.valid_chan('&')
        assert not self.server.valid_chan('+')
        assert not self.server.valid_chan('!')

        assert self.server.valid_chan('&'+'A'*48)
        assert not self.server.valid_chan('&'+'A'*50)

        assert not self.server.valid_chan('&abc def')
        assert not self.server.valid_chan('&abc,def')
        assert not self.server.valid_chan('&abc:def')
        assert not self.server.valid_chan('&abc\x07def')

    # Nick command (before registration)

    def test_nick(self):
        self.server.msg_received(self.user, 'nick shira')
        assert self.user.nick == 'shira'
        assert not self.user.send.called

    def test_nick_alreadytaken(self):
        other = FakeUser()
        self.register_user(other, 'shira')
        
        self.server.msg_received(self.user, 'nick shira')
        assert self.user.nick == '*'
        self.user.send.assert_called_with(':{} {} * shira :Nickname is already '
            'in use'.format(self.server.host, ERR_NICKNAMEINUSE))

    def test_nick_noargs(self):
        self.server.msg_received(self.user, 'nick')
        assert self.user.nick == '*'
        self.user.send.assert_called_with(':{} {} * :No nickname '
            'given'.format(self.server.host, ERR_NONICKNAMEGIVEN))
                                                          
    def test_long_nick(self):
        self.server.msg_received(self.user, 'nick shira6789012345')
        assert self.user.nick == 'shira6789'
        
    def test_long_nick_alreadytaken(self):
        other = FakeUser()
        self.register_user(other, 'shira6789')
        
        self.server.msg_received(self.user, 'nick shira6789012345')
        assert self.user.nick == '*'
        self.user.send.assert_called_with(':{} {} * shira6789 :Nickname is '
            'already in use'.format(self.server.host, ERR_NICKNAMEINUSE))

    def test_invalid_nick(self):
        self.server.msg_received(self.user, 'nick -shira')
        assert self.user.nick == '*'
        self.user.send.assert_called_with(':{} {} * -shira :Erroneous '
            'nickname'.format(self.server.host, ERR_ERRONEUSNICKNAME))

    # Pass command

    def test_pass(self):
        self.server.msg_received(self.user, 'pass password')
        assert not self.user.send.called       

    def test_pass_noargs_before_registration(self):
        self.server.msg_received(self.user, 'pass')
        self.user.send.assert_called_with(':{} {} * PASS :Not enough '
            'parameters'.format(self.server.host, ERR_NEEDMOREPARAMS))

    def test_pass_noargs_after_registration(self):
        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()
        self.server.msg_received(self.user, 'pass')
        self.user.send.assert_called_with(':{} {} shira :You may not '
            'reregister'.format(self.server.host, ERR_ALREADYREGISTERED))

    def test_second_pass_before_registration(self):
        self.server.msg_received(self.user, 'pass password')
        self.server.msg_received(self.user, 'pass drowssap')
        assert not self.user.send.called
        
    def test_second_pass_after_registration(self):
        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()
        self.server.msg_received(self.user, 'pass drowsapp')
        self.user.send.assert_called_with(':{} {} shira :You may not '
            'reregister'.format(self.server.host, ERR_ALREADYREGISTERED))

    # User command

    def test_user(self):
        self.server.msg_received(self.user, 'user shira 0 * :Stacey')
        assert not self.user.send.called       

    def test_user_noargs_before_registration(self):
        self.server.msg_received(self.user, 'user')
        self.user.send.assert_called_with(':{} {} * USER :Not enough '
            'parameters'.format(self.server.host, ERR_NEEDMOREPARAMS))

    def test_user_noargs_after_registration(self):
        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()
        self.server.msg_received(self.user, 'user')
        self.user.send.assert_called_with(':{} {} shira :You may not '
            'reregister'.format(self.server.host, ERR_ALREADYREGISTERED))

    def test_user_1arg(self):
        self.server.msg_received(self.user, 'user shira')
        self.user.send.assert_called_with(':{} {} * USER :Not enough '
            'parameters'.format(self.server.host, ERR_NEEDMOREPARAMS))

    def test_user_2args(self):
        self.server.msg_received(self.user, 'user shira 0')
        self.user.send.assert_called_with(':{} {} * USER :Not enough '
            'parameters'.format(self.server.host, ERR_NEEDMOREPARAMS))

    def test_user_3args(self):
        self.server.msg_received(self.user, 'user shira 0 *')
        self.user.send.assert_called_with(':{} {} * USER :Not enough '
            'parameters'.format(self.server.host, ERR_NEEDMOREPARAMS))

    def test_second_user_before_registration(self):
        self.server.msg_received(self.user, 'user shira 0 * :Stacey')
        self.server.msg_received(self.user, 'user arihs 0 * :yecats')
        assert not self.user.send.called

    def test_second_user_after_registration(self):
        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()
        self.server.msg_received(self.user, 'user shira 0 * :Stacey')
        self.user.send.assert_called_with(':{} {} shira :You may not '
            'reregister'.format(self.server.host, ERR_ALREADYREGISTERED))

    # Registration

    def registration_assertions(self):
        calls = [call(':{} {} shira :Welcome to the IRC Chat Server '
                      'shira'.format(self.server.host, RPL_WELCOME)),
                 call(':{} {} shira :Your host is {}, running version '
                      '{}'.format(self.server.host, RPL_YOURHOST,
                                  self.server.host, self.server.version)),
                 call(':{} {} shira :This server was created '
                      '{}'.format(self.server.host, RPL_CREATED,
                                  self.server.createdate)),
                 call(':{} {} shira {} {}'.format(self.server.host, RPL_MYINFO,
                                                 self.server.host, 
                                                 self.server.version))]

        self.user.send.assert_has_calls(calls)

    def test_register(self):
        self.server.msg_received(self.user, 'nick shira')
        self.server.msg_received(self.user, 'user shira 0 * :Stacey')
        assert self.user.realname == 'Stacey'
                                 
    def test_register_pass_nick_user(self):
        self.server.msg_received(self.user, 'pass password')
        self.server.msg_received(self.user, 'nick shira')
        self.server.msg_received(self.user, 'user shira 0 * :Stacey')
        self.registration_assertions()

    def test_register_pass_user_nick(self):
        self.server.msg_received(self.user, 'pass password')
        self.server.msg_received(self.user, 'nick shira')
        self.server.msg_received(self.user, 'user shira 0 * :Stacey')
        self.registration_assertions()

    def test_register_nick_pass_user(self):
        self.server.msg_received(self.user, 'nick shira')
        self.server.msg_received(self.user, 'pass password')
        self.server.msg_received(self.user, 'user shira 0 * :Stacey')
        self.registration_assertions()

    def test_register_user_pass_nick(self):
        self.server.msg_received(self.user, 'user shira 0 * :Stacey')
        self.server.msg_received(self.user, 'pass password')
        self.server.msg_received(self.user, 'nick shira')
        self.registration_assertions()

    def test_register_nick_user(self):
        self.server.msg_received(self.user, 'nick shira')
        self.server.msg_received(self.user, 'user shira 0 * :Stacey')
        self.registration_assertions()

    def test_register_user_nick(self):
        self.server.msg_received(self.user, 'user shira 0 * :Stacey')
        self.server.msg_received(self.user, 'nick shira')
        self.registration_assertions()

    # Nick command (after registration)

    def test_change_nick(self):
        self.register_user(self.user, 'santa')
        self.server.msg_received(self.user, 'nick shira')
        assert self.user.nick == 'shira'
        self.user.send.assert_called_wth(':santa NICK shira')

    def test_change_nick_free_old(self):
        self.register_user(self.user, 'santa')
        self.server.msg_received(self.user, 'nick shira')
        self.server.msg_received(self.user, 'nick santa')
        assert self.user.nick == 'santa'

    def test_nick_multiple_channels(self):
        users = self.setup_channel('&chan1', 2).values()
        self.register_user(self.user, 'shira')
        self.server.msg_received(self.user, 'join &chan1')
        self.server.msg_received(self.user, 'join &chan2')
        for u in users:
            self.server.msg_received(u, 'join &chan2')
        for u in users:
            u.send.reset_mock()
        self.user.send.reset_mock()

        self.server.msg_received(self.user, 'nick santa')
        for u in users:
            assert u.send.call_count == 1

    def test_change_nick_alreadytaken(self):
        other = FakeUser()
        self.register_user(other, 'shira')

        self.register_user(self.user, 'santa')
        self.server.msg_received(self.user, 'nick shira')
        assert self.user.nick == 'santa'
        self.user.send.assert_called_with(':{} {} santa shira :Nickname is '
            'already in use'.format(self.server.host, ERR_NICKNAMEINUSE))

    def test_change_nick_noargs(self):
        self.register_user(self.user, 'santa')
        self.server.msg_received(self.user, 'nick')
        assert self.user.nick == 'santa'
        self.user.send.assert_called_with(':{} {} santa :No nickname '
            'given'.format(self.server.host, ERR_NONICKNAMEGIVEN))
                                                          
    def test_change_long_nick(self):
        self.register_user(self.user, 'santa')
        self.server.msg_received(self.user, 'nick shira6789012345')
        assert self.user.nick == 'shira6789'
        
    def test_change_long_nick_alreadytaken(self):
        other = FakeUser()
        self.register_user(other, 'shira6789')
        
        self.register_user(self.user, 'santa')
        self.server.msg_received(self.user, 'nick shira6789012345')
        assert self.user.nick == 'santa'
        self.user.send.assert_called_with(':{} {} santa shira6789 :Nickname is '
            'already in use'.format(self.server.host, ERR_NICKNAMEINUSE))

    def test_change_invalid_nick(self):
        self.register_user(self.user, 'santa')
        self.server.msg_received(self.user, 'nick -shira')
        assert self.user.nick == 'santa'
        self.user.send.assert_called_with(':{} {} santa -shira :Erroneous '
            'nickname'.format(self.server.host, ERR_ERRONEUSNICKNAME))
        
    # Join command

    def test_join_not_registered(self):
        self.server.msg_received(self.user, 'join &chan')
        self.user.send.assert_called_with(':{} {} * :You have not '
            'registered'.format(self.server.host, ERR_NOTREGISTERED))
    
    def test_join(self):
        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()

        self.server.msg_received(self.user, 'join &chan')
        assert '&chan' in self.server.channels
        assert self.user in self.server.channels['&chan'].users 
        assert self.server.channels['&chan'] in self.user.channels

        calls = [call(':shira JOIN &chan'),
                 call(':{} {} shira @ &chan '
                      ':shira'.format(self.server.host, RPL_NAMREPLY)),
                 call(':{} {} shira &chan :End of NAMES '
                      'list'.format(self.server.host, RPL_ENDOFNAMES))]
        
        self.user.send.assert_has_calls(calls)

        # verify that topic is not being sent
        assert self.user.send.call_count == 3

    def test_join_noargs(self):
        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()
        self.server.msg_received(self.user, 'join')
        self.user.send.assert_called_with(':{} {} shira JOIN :Not enough '
            'parameters'.format(self.server.host, ERR_NEEDMOREPARAMS))

    def test_invalid_chan(self):
        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()
        self.server.msg_received(self.user, 'join chan')
        self.user.send.assert_called_with(':{} {} shira chan :No such '
            'channel'.format(self.server.host, ERR_NOSUCHCHANNEL))

    def test_join_notification(self):
        users = self.setup_channel('&chan', 2)
        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()

        self.server.msg_received(self.user, 'join &chan')

        names = users.keys()
        names.append('shira')
        names.sort()
        calls = [call(':shira JOIN &chan'),
                 call(':{} {} shira @ &chan :{} {} '
                      '{}'.format(self.server.host, RPL_NAMREPLY,
                                  names[0], names[1], names[2])),
                 call(':{} {} shira &chan :End of NAMES '
                      'list'.format(self.server.host, RPL_ENDOFNAMES))]
        self.user.send.assert_has_calls(calls)

        for user in users.values():
            user.send.assert_called_with(':shira JOIN &chan')

    def test_join_twice(self):
        users = self.setup_channel('&chan', 2)
        self.register_user(self.user, 'shira')
        self.server.msg_received(self.user, 'join &chan')
        self.user.send.reset_mock()

        self.server.msg_received(self.user, 'join &chan')
        assert not self.user.send.called
        for user in users:
            assert not self.user.send.called
 
    # Part command

    def test_part_not_registered(self):
        self.server.msg_received(self.user, 'part &chan')
        self.user.send.assert_called_with(':{} {} * :You have not '
            'registered'.format(self.server.host, ERR_NOTREGISTERED))

    def test_part(self):
        users = self.setup_channel('&chan', 2).values()
        self.register_user(self.user, 'shira')
        self.server.msg_received(self.user, 'join &chan')
        self.user.send.reset_mock()

        self.server.msg_received(self.user, 'part &chan')
        self.user.send.assert_called_with(':shira PART &chan')
        assert not self.user in self.server.channels['&chan'].users
        assert not self.server.channels['&chan'] in self.user.channels
        for user in users:
            assert self.server.channels['&chan'] in user.channels
            user.send.assert_called_with(':shira PART &chan')

    def test_part_last(self):
        self.register_user(self.user, 'shira')
        self.server.msg_received(self.user, 'join &chan')
        self.user.send.reset_mock()

        self.server.msg_received(self.user, 'part &chan')
        assert '&chan' in self.server.channels

    def test_part_noargs(self):
        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()
        self.server.msg_received(self.user, 'part')
        self.user.send.assert_called_with(':{} {} shira PART :Not enough '
            'parameters'.format(self.server.host, ERR_NEEDMOREPARAMS))

    def test_part_non_existent_channel(self):
        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()
        self.server.msg_received(self.user, 'part &chan')
        self.user.send.assert_called_with(":{} {} shira &chan :No "
            'such channel'.format(self.server.host, ERR_NOSUCHCHANNEL))

    def test_part_not_in_channel(self):
        other = FakeUser()
        self.register_user(other,'santa')
        self.server.msg_received(other, 'join &chan')

        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()
        self.server.msg_received(self.user, 'part &chan')
        self.user.send.assert_called_with(":{} {} shira &chan :You're not "
            'on that channel'.format(self.server.host, ERR_NOTONCHANNEL))

    def test_part_one_of_multiple_channels(self):
        users = self.setup_channel('&chan1', 2).values()
        self.register_user(self.user, 'shira')
        self.server.msg_received(self.user, 'join &chan1')
        self.server.msg_received(self.user, 'join &chan2')
        for u in users:
            self.server.msg_received(u, 'join &chan2')
        for u in users:
            u.send.reset_mock()
        self.user.send.reset_mock()

        self.server.msg_received(self.user, 'part &chan1')
        assert self.user in self.server.channels['&chan2'].users
        assert self.server.channels['&chan2'] in self.user.channels
        for u in users:
            assert u.send.call_count == 1

    def test_join_0(self):
        self.setup_channel('&chan1', 2)
        self.setup_channel('&chan2', 2)
        self.register_user(self.user, 'shira')
        self.server.msg_received(self.user, 'join &chan1')
        self.server.msg_received(self.user, 'join &chan2')
        self.user.send.reset_mock()

        self.server.msg_received(self.user, 'join 0')
        assert not self.user in self.server.channels['&chan1'].users
        assert not self.user in self.server.channels['&chan2'].users
        assert not self.server.channels['&chan1'] in self.user.channels
        assert not self.server.channels['&chan2'] in self.user.channels

    # Privmsg command

    def test_privmsg_not_registered(self):
        self.server.msg_received(self.user, 'privmsg shira :hi')
        self.user.send.assert_called_with(':{} {} * :You have not '
            'registered'.format(self.server.host, ERR_NOTREGISTERED))
    
    def test_privmsg_to_nick(self):
        other = FakeUser()
        self.register_user(other, 'santa')
        other.send.reset_mock()

        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()

        self.server.msg_received(self.user, 'privmsg santa :hi')
        other.send.assert_called_with(':shira PRIVMSG santa :hi')

    def test_privmsg_noargs(self):
        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()
        
        self.server.msg_received(self.user, 'privmsg')
        self.user.send.assert_called_with(':{} {} shira :No recipient '
            'given (PRIVMSG)'.format(self.server.host, ERR_NORECIPIENT))

    def test_privmsg_1args(self):
        other = FakeUser()
        self.register_user(other, 'santa')
        other.send.reset_mock()

        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()
        
        self.server.msg_received(self.user, 'privmsg santa')
        self.user.send.assert_called_with(':{} {} shira :No text to '
            'send'.format(self.server.host, ERR_NOTEXTTOSEND))

        assert not other.send.called

    def test_privmsg_non_existent(self):
        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()
        self.server.msg_received(self.user, 'privmsg foo :hi')

        self.user.send.assert_called_with(':{} {} shira foo :No such '
            'nick/channel'.format(self.server.host, ERR_NOSUCHNICK))

    def test_privmsg_to_channel(self):
        users = self.setup_channel('&chan', 2)
        self.register_user(self.user, 'shira')

        self.server.msg_received(self.user, 'join &chan')
        self.user.send.reset_mock()

        for user in users.values():
            user.send.reset_mock()

        self.server.msg_received(self.user, 'privmsg &chan :hi')
        
        for (name, user) in users.items():
            user.send.assert_called_with(':shira PRIVMSG &chan :hi')

        assert not self.user.send.called
 
    # Miscellaneous tests

    def test_invalid_command_before_registration(self):
        self.server.msg_received(self.user, 'qwerty')
        assert not self.user.send.called

    def test_invalid_command_after_registration(self):
        self.register_user(self.user, 'shira')
        self.user.send.reset_mock()

        self.server.msg_received(self.user, 'qwerty')
        assert not self.user.send.called


