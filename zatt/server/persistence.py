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

# class LogEntry:
#     def __init__(self, term, index, data):
#         self.term = term
#         self.index = index
#         self.data = data
#
# class Log:
#     def __init__(self, ):
#         self.log = []
#
#     @property
#     def term(self):
#         if self.log:
#             return self.log[-1].term
#         else:
#             return 0
#
#     @property
#     def index(self):
#         return len(self.log)
#
#     def __getitem__(self, item):
#         return self.log[item]
#
#     def append_entries(self, entries):
#         for entry in entries:
#             index = entry['index']
#             del entry['index']
#             if index < self.index:
#                 self.log[index] = entry
#             elif entry['index'] == self.index:
#                 self.log.append(entry)
#             else:
#                 print('else') # TODO
