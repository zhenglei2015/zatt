import argparse
import datetime
import time
import json
import dateutil.parser
from multiprocessing import Pool
from utils import get_random_string
from zatt.client.distributedDict import DistributedDict


parser = argparse.ArgumentParser(description='Load test client')
parser.add_argument('--stats', action='store_true', help='Collect stats')
parser.add_argument('--head', action='store_true', help='Head client')
parser.add_argument('--reads', type=int, help='Total read operations')
parser.add_argument('--servers', nargs='*', help='Servers ip:port')
parser.add_argument('--machines', type=int, help='job machines number')
parser.add_argument('--instances', type=int, help='Total instances number')
parser.add_argument('--entries', type=int, help='Log entries count')
parser.add_argument('--dimention', type=int, help='Log entry size in bytes')


def writer(entries_count, size=100, address='127.0.0.1', port=9110):
    d = DistributedDict(address, port)
    prefix = get_random_string(lenght=6)
    stub_value = 'a' * size
    for key in range(entries_count):
        d[prefix + str(key)] = stub_value
    d['done_' + prefix] = True


def reader(entries_count=100, address='127.0.0.1', port=9110):
    d = DistributedDict(address, port)
    for _ in range(entries_count):
        d.refresh()


def client_pool(func, entries_count, workers, additional_args=[]):
    print('entries/worker ', entries_count // workers, 'workers', workers)
    pool = Pool(workers)
    worker_args = [[entries_count // workers] + additional_args]
    pool.starmap(func, worker_args * workers)
    pool.terminate()
    print('done!')


class Client:
    def __init__(self):
        args = parser.parse_args()
        self.servers = [(server[0], int(server[1])) for server in
                        [server_str.split(':') for server_str in args.servers]]
        if args.head:
            self.head(args)
        elif args.stats:
            self.stats_keeper()
        else:
            self.client()

    def head(self, args):
        client = DistributedDict(*self.servers[0])
        client['restart'] = True
        time.sleep(10)

        for server in self.servers:
            client.config_cluster('add', *server)
        start_time = datetime.datetime.now() + datetime.timedelta(seconds=10)
        client['job'] = {'machines': args.machines, 'reads': args.reads,
                         'entries': args.entries, 'dimention': args.dimention,
                         'instances': args.instances,
                         'start_time': start_time.isoformat()}
        self.stats = {}
        while True:
            client.refresh(force=True)
            done = list(filter(lambda x: x.startswith('done_'), client))
            if len(done) >= len(client['cluster']):
                print('Done')
                input('Collect? At least 3 sec')
                self.collect_stats()
                with open('{}.json'.format(datetime.datetime.now()), 'w+') as f:
                    normalized = {k[0] + ':' + str(k[1]): v
                                  for (k, v) in self.stats.items()}
                    normalized['client'] = client['job']
                    f.write(json.dumps(normalized, indent=4, sort_keys=True))
                break

            time.sleep(3)

    def client(self):
        last_job = datetime.datetime.now()
        while True:
            time.sleep(1)
            try:
                client = DistributedDict(*self.servers[0])
                if 'job' not in client:
                    continue
                start_time = dateutil.parser.parse(client['job']['start_time'])
                if start_time == last_job:
                    continue
                if start_time > datetime.datetime.now():
                    continue
                last_job = start_time
                print('Start writing')
                client_pool(
                    writer,
                    client['job']['entries'] // client['job']['machines'],
                    client['job']['instances'],
                    [client['job']['dimention']] + list(self.servers[0]))
                print('Start reading')
                client_pool(
                    reader,
                    client['job']['reads'] // client['job']['machines'],
                    client['job']['instances'], list(self.servers[0]))
            except ConnectionRefusedError:
                print('Connection refused')

    def collect_stats(self):
        if not hasattr(self, 'stats'):
            self.stats = {}
        for server in self.servers:
            client = DistributedDict(*server)
            if server not in self.stats:
                self.stats[server] = {'read': {}, 'write': {},
                                      'append': {}}
            for category in self.stats[server]:
                for stat in client.diagnostic['stats'][category]['past']:
                    self.stats[server][category].update(stat)
        self.servers = tuple(map(tuple, client['cluster']))


client = Client()
