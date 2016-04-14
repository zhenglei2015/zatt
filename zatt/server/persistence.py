import os
import json
import asyncio
from .logger import logger
from .config import config

class PersistentDict(dict):
    def __init__(self, filepath = None, model = None):
        dict.__init__(self)
        if os.path.isfile(filepath):
            with open(filepath, 'r') as f:
                for k,v in json.loads(f.read()).items():
                    dict.__setitem__(self, k,v)
        elif model:
            for k,v in model.items():
                dict.__setitem__(self, k,v)
        self.filepath = filepath

    def persist(self):
        with open(self.filepath, 'w+') as f:
            f.write(json.dumps(self))

    def __setitem__(self, key, val):
        dict.__setitem__(self, key, val)
        self.persist()


class LogDictMachine:
    def __init__(self, state_machine={}):
        self.state_machine = state_machine
    # def __init__(self):
    #     self.state_machine = PersistentDict(os.path.join(config['storage'], 'log'), {})

    def apply(self, items):
        for item in items:
            item = item['data']
            if item['action'] == 'change':
                self.state_machine[item['key']] = item['value']
            elif item['action'] == 'delete':
                del self.state_machine[item['key']]
        print(self.state_machine)


class LogDict:
    def __init__(self):
        self.compacted_log = {}
        self.compacted_count = 0 # compacted items count, or c_index + 1!
        self.compacted_term = None  # term of last compacted item
        self.log = []
        self.commitIndex = -1
        self.lastApplied = 0
        self.state_machine = LogDictMachine()
        # self.state_machine = LogDictMachine(state_machine=self.compacted_log)

    @property
    def compacted_index(self):
        return self.compacted_count - 1

    @property
    def index(self):
        return self.compacted_count + len(self.log) - 1

    def term(self, index=-1):
        if not self.log or index < self.compacted_index:  # TODO: review
            return self.compacted_term
        else:
            return self[index]['term']

    def __getitem__(self, index):
        #  TODO: what if index < self.compacted_index ?
        if type(index) is slice:
            return self.log[index]  # TODO: review
        elif type(index) is int:
            return self.log[index - self.compacted_count]

    def append_entries(self, entries, prevLogIndex):
        #  TODO: what if prevLogIndex < self.commitIndex ?
        del self.log[prevLogIndex - self.compacted_count + 1:]
        self.log += entries

    def commit(self, leaderCommit):
        ## TODO: what if  leaderCommit > self.compacted_index?
        if leaderCommit > self.commitIndex:
            self.commitIndex = min(leaderCommit, self.index)
            logger.debug('Advancing commit to {}'.format(self.commitIndex))
            self.state_machine.apply(self.log[self.lastApplied:self.commitIndex + 1])
            self.lastApplied = self.commitIndex
            self.touch_compaction_timer() # TODO: right place?

    def touch_compaction_timer(self):
        if not hasattr(self, 'compaction_timer'):
            loop = asyncio.get_event_loop()
            self.compaction_timer = loop.call_later(1, self.compact)

    def compact(self):
        del self.compaction_timer
        if self.commitIndex - self.compacted_count < 1:
            return
        logger.debug('Compaction started')
        self.compacted_log = self.state_machine.state_machine
        self.compacted_term = self.term(self.lastApplied)
        # del self[:self.lastApplied - self.compacted_index]
        self.log = self[self.lastApplied - self.compacted_index:]
        self.compacted_count = self.lastApplied + 1
