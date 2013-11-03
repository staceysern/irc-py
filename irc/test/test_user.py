from user import User
from mock import Mock

from twisted.test.proto_helpers import StringTransport


class TestUser:
    def setup_method(self, method):
        self.server = Mock()
        self.user = User(self.server, "localhost")
        self.transport = StringTransport()
        self.user.makeConnection(self.transport)
        self.line = "cmd arg1 arg2 :trailing"

    def test_lineReceived(self):
        self.user.lineReceived(self.line)
        self.server.msg_received.assert_called_once_with(self.user, self.line)

    def test_send(self):
        self.user.send(self.line)
        assert self.transport.value() == self.line + '\r\n'
