import argparse
import sys
import os
import json


parser = argparse.ArgumentParser(description=('Zatt. An implementation of'
                                              'the Raft algorithm for '
                                              'distributed consensus'))
parser.add_argument('-c', '--config', dest='path_conf',
                    help='Config file path. Default: zatt.conf')
parser.add_argument('-i', '--id', help='This node ID. Default: 0', default=0)
parser.add_argument('-a', '--address', help=('This node address. Default: '
                    '127.0.0.1'))
parser.add_argument('-p', '--port', help='This node port. Default: 5254')
parser.add_argument('-s', '--storage', help=('Path for the persistent state'
                    ' file. Default: zatt.persist'), dest='path_storage')
parser.add_argument('--node-id', action='append', default=[],
                    help='Remote node id')
parser.add_argument('--node-address', action='append', default=[],
                    help='Remote node address')
parser.add_argument('--node-port', action='append', default=[],
                    help='Remote node port')
parser.add_argument('--debug', action='store_true', help='Enable debug mode')


class Config:
    __shared_state = {}

    def __new__(cls, *p, **k):
        if '_instance' not in cls.__dict__:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self, config={}):
        self.__dict__ = config if config else self.get_from_cmdline_and_file()

    def get_from_cmdline_and_file(self):
        args = parser.parse_args()
        if len(args.node_id) != len(args.node_port)\
           or len(args.node_id) != len(args.node_address):
            print('There should be the same number of:node-id, node-address,',
                  'node-port')
            sys.exit(1)
        if args.path_conf is not None and not os.path.isfile(args.path_conf):
            print('Config file not found')
            sys.exit(1)

        config = {'id': int(args.id), 'cluster': {}, 'debug': args.debug}

        path = args.path_conf if args.path_conf else 'zatt.conf'
        if os.path.isfile(path):
            with open(path, 'r') as f:
                config.update(json.loads(f.read()))

        if 'storage' not in config:
            config['storage'] = 'zatt.persist'

        if args.path_storage:
            config['storage'] = args.path_storage

        for x in zip(args.node_id, args.node_address, args.node_port):
            config['cluster'][x[0]] = x[1:3]

        if args.address:
            config['cluster'][config['id']][0] = args.address

        if args.port:
            config['cluster'][config['id']][1] = args.port

        cluster = config['cluster']
        config['cluster'] = {int(k): (v[0], int(v[1]))
                             for (k, v) in cluster.items()}

        if config['id'] not in config['cluster']:
            config['cluster'][config['id']] = ['127.0.0.1', '5254']

        return config

config = Config()
