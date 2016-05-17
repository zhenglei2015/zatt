import argparse
import sys
import os
import json


parser = argparse.ArgumentParser(description=('Zatt. An implementation of '
                                              'the Raft algorithm for '
                                              'distributed consensus'))
parser.add_argument('-s', '--storage', help=('Path for the persistent state'
                    ' directory. Default: zatt.persist'),
                    default='zatt.persist')
parser.add_argument('-c', '--config', dest='path_conf',
                    help='Config file path. Default: zatt.persist/zatt.conf')
parser.add_argument('--save', action='store_true', help='Save config to'
                    ' persistence directory')
parser.add_argument('-i', '--id', help='This node ID. Default: 0', default=0)
parser.add_argument('-a', '--address', help=('This node address. Default: '
                    '127.0.0.1'), default='127.0.0.1')
parser.add_argument('-p', '--port', help='This node port. Default: 5254',
                    default=5254)
parser.add_argument('--remote-id', action='append', default=[],
                    help='Remote node id')
parser.add_argument('--remote-address', action='append', default=[],
                    help='Remote node address')
parser.add_argument('--remote-port', action='append', default=[],
                    help='Remote node port')
parser.add_argument('--debug', action='store_true', help='Enable debug mode')


class Config:
    __shared_state = {}

    def __new__(cls, *p, **k):
        if '_instance' not in cls.__dict__:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self, config={}):
        self.__dict__ = config if config else self._get()
        self._persist()

    def _get_cmdline(self):
        args = parser.parse_args()
        if len(args.remote_id) != len(args.remote_port)\
           or len(args.remote_id) != len(args.remote_address):
            print('There should be the same number of:node-id, node-address,',
                  'node-port')
            sys.exit(1)
        if args.path_conf is not None and not os.path.isfile(args.path_conf):
            print('Config file not found')
            sys.exit(1)

        config = {'debug': args.debug, 'id':int(args.id),
                  'storage':args.storage, 'save': args.save,
                  'cluster':{int(args.id):[args.address, args.port]},
                  'conf_path': args.path_conf if args.path_conf else
                               os.path.join(args.storage, 'config')}

        for x in zip(args.remote_id, args.remote_address, args.remote_port):
            config['cluster'][int(x[0])] = x[1:3]

        return config

    def _get_config_file(self, path):
        if os.path.isfile(path):
            with open(path, 'r') as f:
                return json.loads(f.read())
        else:
            return {}

    def _get(self):
        cmdline = self._get_cmdline()
        config = self._get_config_file(cmdline['conf_path'])

        if 'id' in config:
            del cmdline['cluster'][cmdline['id']]
            del cmdline['id']

        if not 'cluster' in config:
           config['cluster'] = {}
        config['cluster'].update(cmdline['cluster'])
        del cmdline['cluster']
        config.update(cmdline)
        print(config)
        config['cluster'] = {int(k): (v[0], int(v[1]))
                             for (k, v) in config['cluster'].items()}

        return config

    def _persist(self):
        if not self.save:
            return
        if not os.path.isdir(self.storage):
            os.mkdir(self.storage)
        with open(os.path.join(self.storage, 'config'), 'w+') as f:
            f.write(json.dumps(self.__dict__))

config = Config()
