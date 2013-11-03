class Channel(object):
    def __init__(self, name):
        self.name = name
        self.users = []
        self._topic = ''

    def set_topic(self, topic):
        self._topic = topic

    def get_topic(self):
        return self._topic

