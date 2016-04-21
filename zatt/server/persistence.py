import os
import json
import collections
import asyncio
from .logger import logger
from .config import config


class PersistentDict(collections.UserDict):
    def __init__(self, path=None, data={}):
        if os.path.isfile(path):
            with open(path, 'r') as f:
                data = json.loads(f.read())
        self.path = path
        super().__init__(data)

    def __setitem__(self, key, value):
        self.data[self.__keytransform__(key)] = value
        self.persist()

    def __delitem__(self, key):
        del self.data[self.__keytransform__(key)]
        self.persist()

    def __keytransform__(self, key):
        return key

    def persist(self):
        with open(self.path, 'w+') as f:
            f.write(json.dumps(self.data))


class Log(collections.UserList):
    def __init__(self):
        super().__init__()
        self.path = os.path.join(config['storage'], 'log')
        #  loading
        if os.path.isfile(self.path):
            with open(self.path, 'r') as f:
                self.data = list(map(json.loads, f.readlines()))

    def persist(self, start, stop):
        with open(self.path, '+a') as f:
            for entry in self[start:stop]:
                f.write(json.dumps(entry) + '\n')


class Compactor():
    def __init__(self):
        self.count = 0
        self.term = None
        self.data = {}
        self.path = os.path.join(config['storage'], 'compact')
        #  load
        if os.path.isfile(self.path):
            with open(self.path, 'r') as f:
                raw = json.loads(f.read())
                self.__dict__.update(raw)

    @property
    def index(self):
        return self.count - 1

    def persist(self):
        with open(self.path, 'w+') as f:
            f.write(json.dumps({'count': self.count,
                                'term': self.term,
                                'data': self.data}))


class LogManager:
    def __init__(self, compactor=Compactor, log=Log, machine=None):
        self.log = log()
        self.compacted = compactor()
        self.state_machine = machine(self.compacted.data)
        self.state_machine.apply(self.log)
        self.commitIndex = self.compacted.count + len(self.log) - 1
        self.lastApplied = self.commitIndex

    def __getitem__(self, index):
        if type(index) is slice:
            start = index.start - self.compacted.count if index.start else None
            stop = index.stop - self.compacted.count if index.stop else None
            return self.log[start:stop:index.step]
        elif type(index) is int:
            return self.log[index - self.compacted.count]

    @property
    def index(self):
        return self.compacted.index + len(self.log)

    def term(self, index=-1):
        if not len(self.log) or index < self.compacted.index:
            return self.compacted.index
        else:
            return self[index]['term']

    def append_entries(self, entries, prevLogIndex):
        del self.log.data[prevLogIndex - self.compacted.count + 1:]
        self.log.data += entries

    def commit(self, leaderCommit):
        if leaderCommit <= self.commitIndex:  # or leaderCommit > self.index:
            return

        self.commitIndex = min(leaderCommit, self.index + 1)  # +1 ?
        logger.debug('Advancing commit to {}'.format(self.commitIndex))
        self.log.persist(self.lastApplied - self.compacted.index,
                         self.commitIndex - self.compacted.index)
        self.state_machine.apply(self[self.lastApplied + 1:self.commitIndex + 1])
        logger.debug('State machine: {}'.format(self.state_machine.data))
        logger.debug('Log: {}'.format(self.log.data))
        self.lastApplied = self.commitIndex
        self.compaction_timer_touch()

    def compact(self):
        del self.compaction_timer
        if self.commitIndex - self.compacted.count < 3:
            return
        logger.debug('Compaction started')
        self.compacted.data = self.state_machine.data
        self.compacted.term = self.term(self.lastApplied)
        self.compacted.persist()
        self.log.data = self[self.lastApplied + 1:]
        self.log.persist(0, self.commitIndex - self.compacted.count)
        self.compacted.count = self.lastApplied + 1

        if os.path.isfile(self.log.path):
            os.remove(self.log.path)
        logger.debug('Compacted: {}'.format(self.compacted.data))
        logger.debug('Log: {}'.format(self.log.data))

    def compaction_timer_touch(self):
        if not hasattr(self, 'compaction_timer'):
            loop = asyncio.get_event_loop()
            self.compaction_timer = loop.call_later(1, self.compact)


class DictStateMachine(collections.UserDict):
    def apply(self, items):
        for item in items:
            item = item['data']
            if item['action'] == 'change':
                self.data[item['key']] = item['value']
            elif item['action'] == 'delete':
                del self.data[item['key']]


def factory_dict_manager():
    return LogManager(compactor=Compactor, log=Log, machine=DictStateMachine)
