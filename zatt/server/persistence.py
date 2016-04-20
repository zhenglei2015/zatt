import os
import json
import asyncio
import collections
from .logger import logger
from .config import config


class PersistentDict(collections.MutableMapping):
    def __init__(self, filepath = None, model = None):
        self.store = dict()
        if os.path.isfile(filepath):
            with open(filepath, 'r') as f:
                self.store =  json.loads(f.read())
        elif type(model) == dict:
            self.store = model
        self.filepath = filepath

    def __getitem__(self, key):
        return self.store[self.__keytransform__(key)]

    def __setitem__(self, key, value):
        self.store[self.__keytransform__(key)] = value
        self.persist()

    def __delitem__(self, key):
        del self.store[self.__keytransform__(key)]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __keytransform__(self, key):
        return key

    def persist(self):
        with open(self.filepath, 'w+') as f:
            f.write(json.dumps(self.store))

    def replace(self, data):
        self.store = data
        self.persist()


class LogDictMachine:
    def __init__(self, state_machine={}):
        self.state_machine = state_machine.store.copy()

    def apply(self, items):
        for item in items:
            item = item['data']
            if item['action'] == 'change':
                self.state_machine[item['key']] = item['value']
            elif item['action'] == 'delete':
                del self.state_machine[item['key']]


class LogDict:
    def __init__(self):
        self.log = []
        self.load_log()
        self.commitIndex = -1
        self.lastApplied = -1
        self.compacted_log = PersistentDict(os.path.join(config['storage'], 'compacted'), {})
        self.compacted_count = 0  # compacted items count, or last compacted item index + 1
        self.compacted_term = None  # term of last compacted item
        self.state_machine = LogDictMachine(state_machine=self.compacted_log)

    @property
    def compacted_index(self):  # TODO: maybe remove?
        return self.compacted_count - 1

    @property
    def index(self):
        return self.compacted_count + len(self.log) - 1

    def term(self, index=-1):
        if not self.log or index < self.compacted_index:
            return self.compacted_term
        else:
            return self[index]['term']

    def __getitem__(self, index):
        #  TODO: what if index < self.compacted_index ?
        if type(index) is slice:
            start = index.start - self.compacted_count if index.start else None
            stop = index.stop - self.compacted_count if index.stop else None
            return self.log[start:stop:index.step]
        elif type(index) is int:
            return self.log[index - self.compacted_count]

    def append_entries(self, entries, prevLogIndex):
        #  TODO: what if prevLogIndex < self.commitIndex ?
        del self.log[prevLogIndex - self.compacted_count + 1:]
        self.log += entries

    def commit(self, leaderCommit):
        ## TODO: what if  leaderCommit > self.index?
        if leaderCommit > self.commitIndex:
            self.commitIndex = min(leaderCommit, self.index + 1)
            logger.debug('Advancing commit to {}'.format(self.commitIndex))
            self.state_machine.apply(self[self.lastApplied + 1:self.commitIndex + 1])
            # self.persist_log()
            print('STATE MACHINE:', self.state_machine.state_machine)
            print('LOG:', self.log)
            self.lastApplied = self.commitIndex
            self.touch_compaction_timer() # TODO: right place?

    def persist_log(self):
        for entry in self[self.lastApplied + 1:self.commitIndex + 1]:
            with open(os.path.join(config['storage'], 'log'), 'a+') as f:
                f.write(json.dumps(payload) + '\n')

    def touch_compaction_timer(self):
        if not hasattr(self, 'compaction_timer'):
            loop = asyncio.get_event_loop()
            self.compaction_timer = loop.call_later(1, self.compact)

    def compact(self):
        del self.compaction_timer
        if self.commitIndex - self.compacted_count < 3:
            return
        logger.debug('Compaction started')
        self.compacted_log.replace(self.state_machine.state_machine)
        self.compacted_term = self.term(self.lastApplied)
        self.log = self[self.lastApplied + 1:]
        self.compacted_count = self.lastApplied + 1

        if os.path.isfile(os.path.join(config['storage'], 'log')):
            os.remove(os.path.join(config['storage'], 'log'))
        print('COMPACT:', self.compacted_log.store)
        print('LOG:', self.log)

    def load_log(self):
        logfile = os.path.join(config['storage'], 'log')
        if os.path.isfile(logfile):
            with open(logfile, 'r') as f:
                entries = f.readlines()
                self.log = map(json.loads, entries)
