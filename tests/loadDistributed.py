import argparse
import time
import shutil
import asyncio
import datetime
import dateutil.parser
from multiprocessing import Process, Pool
from utils import get_random_string
from zatt.server.main import setup as serverSetup
from zatt.client.distributedDict import DistributedDict


class Server:
    def __init__(self, args):
        self.address = (args.address, args.port)
        self.config = {'address': self.address, 'debug': False,
                       'cluster': {self.address},
                       'storage': 'zatt.{}.persist'.format(args.port)}
        self.leader_address = (args.leader_address, args.leader_port)
        self.create_server()

        while True:
            time.sleep(2)
            self.repeat()

    def repeat(self):
        self.leader.refresh()
        if 'restart' not in self.leader:
            return
        time.sleep(2)  # for other nodes to acknowledge restart
        print('Stopping server')
        self.server.terminate()
        time.sleep(2)
        print('Removing files')
        shutil.rmtree('zatt.{}.persist'.format(self.address[1]))
        print('Starting')
        self.create_server()

    def create_server(self, is_leader=True):
        def server_factory(config):
            serverSetup(config)
            loop = asyncio.get_event_loop()
            loop.run_forever()

        self.server = Process(target=server_factory, args=(self.config,))
        self.server.start()

        if is_leader and self.address == self.leader_address:
            time.sleep(1)
            print('Restarting Leader to increment term')
            self.server.terminate()
            self.create_server(is_leader=False)  # prevents recurtion
            time.sleep(1)
        else:
            time.sleep(3)
        self.leader = DistributedDict(*self.leader_address)
        self.leader.config_cluster('add', *self.address)


class Client:
    def __init__(self, args):
        self.prefix = get_random_string(lenght=6)
        self.last_job = None
        self.leader_address = (args.leader_address, args.leader_port)
        self.leader = DistributedDict(*self.leader_address)

        while True:
            try:
                self.repeat()
            except ConnectionRefusedError:
                print('Connection refused')
            except KeyError:
                print('Server Initialization')
            time.sleep(15 if self.last_job else 1)

    def broadcast(self, term, read=False):
        handle = '{}_{}'.format(term, self.prefix)
        self.leader = DistributedDict(*self.leader_address)
        if read:
            return handle in self.leader
        else:
            self.leader[handle] = True

    def repeat(self):
        self.leader.refresh()
        if not self.broadcast('checkin', read=True):
            self.broadcast('checkin')
            self.last_job = None
            print('Restarted')
        if 'job' not in self.leader:
            return
        job = self.leader['job']
        start_time = dateutil.parser.parse(job['start_time'])
        if start_time == self.last_job:
            return
        if start_time > datetime.datetime.now():
            return
        self.last_job = start_time
        self.run_pool(
            self.worker_writer, job['workers'],
            [job['entries'] // job['machines'], job['dimention'],
             self.leader_address[0], self.leader_address[1]])

    def run_pool(self, func, workers, arguments=[]):
            print('Running', workers)
            pool = Pool(workers)
            arguments[0] = arguments[0] // workers
            pool.starmap(func, [arguments] * workers)
            pool.terminate()
            print('Terminated')

    def worker_writer(self, entries, dimention, address, port):
        client = DistributedDict(address, port)
        worker_prefix = get_random_string(lenght=6)
        stub_value = 'a' * dimention
        for key in range(entries):
            client[worker_prefix + str(key)] = stub_value
        self.leader['done_write_{}'.format(worker_prefix)] = True


class Head:
    def __init__(self, args):
        self.leader_address = (args.leader_address, args.leader_port)
        self.leader = DistributedDict(*self.leader_address)

        for test_case in test_cases:
            self.send_test(test_case)

    def count_comm(self, term):
        self.leader.refresh()
        return len(list(filter(lambda x: x.startswith(term), self.leader)))

    def send_test(self, case):
        print('Initiating test case', case)
        print('Restarting...')
        self.leader['restart'] = True
        ready = False
        while not ready:
            try:
                self.leader.refresh()
            except ConnectionRefusedError:
                continue
            print('Server count', len(self.leader['cluster']))
            client_count = self.count_comm('checkin')
            print('Client count', client_count)

            ready = input('Everybody online? ') in ['y', 'Y', 'yes']

        start_time = datetime.datetime.now() + datetime.timedelta(seconds=10)
        case.update({'machines': client_count,
                     'start_time': start_time.isoformat()})
        self.leader['job'] = case
        print('Executing', case)
        while self.count_comm('done_write') < case['workers']:
            time.sleep(1)
        finish_time = datetime.datetime.now()
        print('Done writing', finish_time - start_time)

        self.collect_stats()

    def collect_stats(self):
        pass


test_cases = [{'entries': 300, 'workers': 20, 'dimention': 100}]

types = {'server': Server, 'client': Client, 'head': Head}

parser = argparse.ArgumentParser(description='Load test client')
parser.add_argument('--type', choices=types.keys(), help='Type of instance')
parser.add_argument('--address', help='Server IP')
parser.add_argument('--port', type=int, help='Server Port')
parser.add_argument('--leader-address', help='leader Server IP')
parser.add_argument('--leader-port', type=int, help='leader Server Port')

if __name__ == '__main__':
    args = parser.parse_args()
    types[args.type](args)
