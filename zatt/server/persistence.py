import os
import json
import asyncio
from .logger import logger

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

    def apply(self, items):
        for item in items:
            item = item['data']
            if item['action'] == 'change':
                self.state_machine[item['key']] = item['value']
            elif item['action'] == 'delete':
                del self.state_machine[item['key']]
        print(self.state_machine)


class LogDict:
    def __init__(self, storage_path):
        self.compacted_log = {}
        self.compacted_index = 0
        self.compacted_term = 0
        self.log = []
        self.commitIndex = -1
        self.lastApplied = 0
        self.state_machine = LogDictMachine(state_machine=self.compacted_log)

    @property
    def index(self):
        return self.compacted_index + len(self.log) - 1

    @property
    def term(self):
        if self.log:
            return self.log[-1]['term']
        else:
            return self.compacted_term

    def __getitem__(self, index):
        #  TODO: what if index < self.compacted_index ?
        if type(index) is slice:
            return self.log[index]
        elif type(index) is int:
            return self.log[index - self.compacted_index]

    def append_entries(self, entries, prevLogIndex):
        #  TODO: what if prevLogIndex < self.commitIndex ?
        del self.log[prevLogIndex - self.compacted_index + 1:]
        self.log += entries

    def commit(self, leaderCommit):
        ## TODO: what if  leaderCommit > self.compacted_index?
        if leaderCommit > self.commitIndex:
            logger.debug('Advancing commit to {}'.format(leaderCommit))
            self.commitIndex = min(leaderCommit, self.index)
            self.state_machine.apply(self.log[self.lastApplied:self.commitIndex + 1])
            self.lastApplied = self.commitIndex
            # self.touch_compaction_timer() # TODO: right place?

    def touch_compaction_timer(self):
        if not hasattr(self, 'compaction_timer'):
            loop = asyncio.get_event_loop()
            self.compaction_timer = loop.call_later(5, compact, self)

    def compact(self):
        del self.compaction_timer
        self.compacted_log = self.state_machine.state_machine
        del self.log[:self.lastApplied - self.compacted_index]
        self.compacted_index = self.lastApplied
        self.compacted_term = self.log[self.lastApplied]['commit']
