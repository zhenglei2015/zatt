import unittest
from time import sleep
from utils import Pool
from zatt.client import DistributedDict


class BasicTest(unittest.TestCase):
    def setUp(self):
        print('BasicTest setup')
        self.pool = Pool(3)
        self.pool.start(self.pool.ids)
        sleep(2)

    def tearDown(self):
        self.pool.stop(self.pool.ids)
        self.pool.rm(self.pool.ids)

    def test_0_diagnostics(self):
        print('Diagnostics test')
        print('Restarting server 0 to force Follower state')
        self.pool.stop(0)
        # sleep(2)
        self.pool.start(0)
        sleep(2)
        expected =\
            {'files': 'STUB', 'status': 'Follower',
             'persist': {'votedFor': 'STUB', 'currentTerm': 'STUB'},
             'volatile': {'leaderId': 'STUB', 'address': ['127.0.0.1', 9110],
                          'cluster': set((('127.0.0.1', 9112),
                                          ('127.0.0.1', 9110),
                                          ('127.0.0.1', 9111)))},
             'log': {'commitIndex': -1, 'log': {'data': [], 'path': 'STUB'},
                     'state_machine': {'lastApplied': -1, 'data': {}},
                     'compacted': {'count': 0, 'term': None, 'path': 'STUB',
                                   'data': {}}}}

        d = DistributedDict('127.0.0.1', 9110)
        diagnostics = d.diagnostic
        diagnostics['files'] = 'STUB'
        diagnostics['log']['compacted']['path'] = 'STUB'
        diagnostics['log']['log']['path'] = 'STUB'
        diagnostics['persist']['votedFor'] = 'STUB'
        diagnostics['persist']['currentTerm'] = 'STUB'
        diagnostics['volatile']['leaderId'] = 'STUB'
        diagnostics['volatile']['cluster'] =\
            set(map(tuple, diagnostics['volatile']['cluster']))
        self.assertEqual(expected, diagnostics)

    def test_1_append(self):
        print('Append test')
        d = DistributedDict('127.0.0.1', 9110)
        d['adams'] = 'the hitchhiker guide'
        del d
        sleep(1)
        d = DistributedDict('127.0.0.1', 9110)
        self.assertEqual(d['adams'], 'the hitchhiker guide')

    def test_2_delete(self):
        print('Delete test')
        d = DistributedDict('127.0.0.1', 9110)
        d['adams'] = 'the hitchhiker guide'
        del d['adams']
        sleep(1)
        d = DistributedDict('127.0.0.1', 9110)
        self.assertEqual(d, {})

    def test_3_read_from_different_client(self):
        print('Read from different client')
        d = DistributedDict('127.0.0.1', 9110)
        d['adams'] = 'the hitchhiker guide'
        del d
        sleep(1)
        d = DistributedDict('127.0.0.1', 9111)
        self.assertEqual(d['adams'], 'the hitchhiker guide')


if __name__ == '__main__':
    unittest.TestLoader.sortTestMethodsUsing = lambda _, x, y: (y < x)-(y > x)
    unittest.main()
