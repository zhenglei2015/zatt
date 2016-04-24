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
        expected = {'log': {'commitIndex': -1,
                            'compacted': {'count': 0, 'data': {},
                                          'term': None,
                                          'path': 'zatt.0.persist/compact'},
                            'log': {'data': [], 'path': 'zatt.0.persist/log'},
                            'state_machine': {'data': {}, 'lastApplied': -1}},
                    'persist': {'currentTerm': 'STUB', 'votedFor': 'STUB'},
                    'status': 'Follower',
                    'volatile': {'Id': 0, 'leaderId': 'STUB'},
                    'files': 'STUB'}

        d = DistributedDict('127.0.0.1', 9110)
        diagnostics = d.diagnostic
        diagnostics['files'] = 'STUB'
        diagnostics['log']['compacted']['path'] = 'zatt.0.persist/compact'
        diagnostics['log']['log']['path'] = 'zatt.0.persist/log'
        diagnostics['persist']['votedFor'] = 'STUB'
        diagnostics['persist']['currentTerm'] = 'STUB'
        diagnostics['volatile']['leaderId'] = 'STUB'
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
