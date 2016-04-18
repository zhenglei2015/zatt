import collections
import socket
import json


class DistributedDict(collections.MutableMapping):
    def __init__(self, addr, port):
        self.target = (addr, port)
        self.store = dict()
        self._get()

    def __getitem__(self, key):
        self._get()
        return self.store[self.__keytransform__(key)]

    def __setitem__(self, key, val):
        if type(key) != str:
            print('Json allows only for key of type "str".')
            return
        self._get()
        self.store[self.__keytransform__(key)] = val
        payload = {'type': 'append',
                   'data': {'key': key, 'value': val, 'action': 'change'}}
        self._put(payload)

    def __delitem__(self, key):
        self._get()
        del self.store[self.__keytransform__(key)]
        payload = {'type': 'append',
                   'data': {'key': key, 'action': 'delete'}}
        self._put(payload)

    def __iter__(self):
        self._get()
        return iter(self.store)

    def __len__(self):
        self._get()
        return len(self.store)

    def __keytransform__(self, key):
        self._get()
        return key

    def __repr__(self):
        self._get()
        return self.store.__repr__()

    def _put(self, payload):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(self.target)
        sock.send(str(json.dumps(payload)).encode())

        buff = bytes()
        while True:
            block = sock.recv(128)
            if not block:
                break
            buff += block
        resp = json.loads(buff.decode('utf-8'))
        if resp['type'] == 'redirect':
            self.target = tuple(resp['leader'])
            print('redirected to', self.target)
        sock.close()
        if resp['type'] == 'redirect':
            self._put(payload)

    def _get(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(self.target)
        sock.send(str(json.dumps({'type': 'get'})).encode())

        buff = bytes()
        while True:
            block = sock.recv(128)
            if not block:
                break
            buff += block
        self.store = json.loads(buff.decode('utf-8'))
        sock.close()



if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3:
        d = DistributedDict('127.0.0.1', 9111)
        d[sys.argv[1]] = sys.argv[2]
