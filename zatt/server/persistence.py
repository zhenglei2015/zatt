import os
import json

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
            if item['action'] == 'change':
                self.state_machine[item['key']] = item['value']
            elif item['action'] == 'delete':
                del self.state_machine[item['key']]


class LogDict:
    def __init__(self, storage_path):
        self.compacted_log = {}
        self.compacted_index = 0
        self.compacted_term = 0
        self.log = []
        self.commitIndex = 0
        self.lastApplied = 0
        self.state_machine = LogDictMachine(state_machine=self.compacted_log)

    @property
    def index(self):
        return self.compacted_index + len(self.log)

    @property
    def term(self):
        if self.log:
            return self.log[-1]['term']
        else:
            return self.compacted_term


    def append_entries(self, entries, prevLogIndex):
        #  TODO: check that prevLogIndex > self.compacted_index
        del self.log[prevLogIndex - self.compacted_index:]
        self.log += entries

    def __getitem__(self, index):
        #  TODO: check that prevLogIndex > self.compacted_index
        if index > self.compacted_index:
            return self.log[item - self.compacted_index]
        else:
            return {'term': self.compacted_index}  # TODO: incomplete

    def commit(self, newCommitIndex):
        ## TODO: chec that index > self.compacted_index
        self.commitIndex = min(newCommitIndex, self.index)
        self.state_machine.apply(self.log[self.lastApplied:self.commitIndex])
        self.lastApplied = self.commitIndex

    def compact(self, n):
        pass
