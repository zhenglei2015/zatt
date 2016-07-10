import argparse
import shutil
import time
import asyncio
from multiprocessing import Process
from zatt.server.main import setup as serverSetup
from zatt.client.distributedDict import DistributedDict


parser = argparse.ArgumentParser(description='Load test server')
parser.add_argument('--address', help='Server IP')
parser.add_argument('--port', type=int, help='Server Port')


class Server:
    def __init__(self):
        args = parser.parse_args()
        self.address = (args.address, args.port)
        self.config = {'address': self.address, 'debug': False,
                       'cluster': {self.address},
                       'storage': 'zatt.{}.persist'.format(args.port)}
        self.start()
        self.monitor()

    def run_server(self):
        serverSetup(self.config)
        loop = asyncio.get_event_loop()
        loop.run_forever()

    def start(self):
        self.server = Process(target=self.run_server)
        self.server.start()

    def monitor(self):
        time.sleep(1)
        while True:
            client = DistributedDict(*self.address)
            is_leader = client.diagnostic['status'] == 'Leader'
            if 'restart' in client and client['restart']:
                time.sleep(1)  # for other nodes to acknowledge restart
                print('Stopping server')
                self.server.terminate()
                time.sleep(2)
                print('Removing files')
                shutil.rmtree('zatt.{}.persist'.format(self.address[1]))
                print('Starting')
                self.start()
                print('Stopping server')
                if is_leader:
                    time.sleep(1)
                    print('Restarting ex Leader')
                    self.server.terminate()
                    self.start()
            time.sleep(2)

Server()
