import argparse
import os
import json


parser = argparse.ArgumentParser(description=('Zatt. An implementation of '
                                              'the Raft algorithm for '
                                              'distributed consensus'))
parser.add_argument('-c', '--config', dest='path_conf',
                    help='Config file path. Default: zatt.persist/config')
parser.add_argument('-s', '--storage', help=('Path for the persistent state'
                    ' directory. Default: zatt.persist'))
parser.add_argument('-a', '--address', help=('This node address. Default: '
                    '127.0.0.1'))
parser.add_argument('-p', '--port', help='This node port. Default: 5254',
                    type=int)
parser.add_argument('--remote-address', action='append', default=[],
                    help='Remote node address')
parser.add_argument('--remote-port', action='append', default=[], type=int,
                    help='Remote node port')
parser.add_argument('--debug', action='store_true', help='Enable debug mode')


class Config:
    """Collect and merge CLI and file based config.
    This class is a singleton based on the Borg pattern."""
    __shared_state = {}

    def __new__(cls, *p, **k):
        if '_instance' not in cls.__dict__:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self, config={}):
        self.__dict__ = config if config else self._get()

    def _get(self):
        default = {'debug': False, 'address': ('127.0.0.1', 5254),
                   'cluster': set(), 'storage': 'zatt.persist',
                   'path_conf': 'zatt.persist/conf'}
        cmdline = parser.parse_args().__dict__

        path_conf = cmdline['path_conf'] if cmdline['path_conf']\
            else default['path_conf']

        config = default.copy()
        if os.path.isfile(path_conf):
            with open(path_conf, 'r') as f:
                config.update(json.loads(f.read()))

        config['cluster'] = {(a, int(p)) for (a, p) in config['cluster']}

        cmdline['address'] = (cmdline['address'], cmdline['port'])\
            if cmdline['address'] else None
        del cmdline['port']

        if cmdline['remote_address'] and cmdline['remote_port']:
            config['cluster'].add(*zip(cmdline['remote_address'],
                                       cmdline['remote_port']))
        del cmdline['remote_address']
        del cmdline['remote_port']
        if cmdline['address'] is not None:
            config['cluster'].remove(tuple(config['address']))

        for k, v in cmdline.items():
            if v is not None:
                config[k] = v

        config['address'] = tuple(config['address'])
        config['cluster'].add(config['address'])
        return config

config = Config()
