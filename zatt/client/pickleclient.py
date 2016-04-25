import pickle
from base64 import b64decode, b64encode
from .abstractClient import AbstractClient


class DistributedPickle(AbstractClient):
    def __init__(self, addr, port):
        super().__init__()
        self.target = (addr, port)
        self.refresh()

    def save(self):
        self.append_log(b64encode(pickle.dumps(self.data)) .decode('utf-8'))

    def refresh(self):
        s = self.get_state()
        self.data = pickle.loads(b64decode(s['data'])) if s else None
