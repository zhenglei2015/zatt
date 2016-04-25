import collections
from .abstractClient import AbstractClient


class DistributedDict(collections.UserDict, AbstractClient):
    def __init__(self, addr, port):
        super().__init__()
        self.target = (addr, port)
        self.data = self.get_state()

    def __getitem__(self, key):
        self.data = self.get_state()
        return self.data[key]

    def __setitem__(self, key, value):
        if type(key) != str:
            raise ValueError('Json allows only for key of type "str"')
        self.data[self.__keytransform__(key)] = value
        self.append_log({'action': 'change', 'key': key, 'value': value})

    def __delitem__(self, key):
        del self.data[self.__keytransform__(key)]
        self.append_log({'action': 'delete', 'key': key})

    def __keytransform__(self, key):
        return key


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3:
        d = DistributedDict('127.0.0.1', 9111)
        d[sys.argv[1]] = sys.argv[2]
