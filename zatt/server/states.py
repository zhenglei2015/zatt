import asyncio
import random
from .persistence import PersistentDict
from .logger import logger

class State:
    def __init__(self, old_state=None, orchestrator=None, config=None):
        logger.info('State change:' + self.__class__.__name__)
        if old_state:
            self.orchestrator = old_state.orchestrator
            self.persist = old_state.persist
            self.volatile = old_state.volatile
        elif orchestrator and config:
            self.orchestrator = orchestrator
            self.persist = PersistentDict(config['storage'],
                                          {'log': [], 'votedFor': None,
                                           'currentTerm': 0})
            self.volatile = {'commitIndex': 0, 'lastApplied': 0,
                             'leaderId': None, 'Id': config['id'],
                             'debug':config['debug']}

    def data_received_peer(self, peer_id, message):
        logger.debug('Received {} from {}'.format(message['type'], peer_id))

        if message['term'] > self.persist['currentTerm']:
            self.persist['currentTerm'] = message['term']
            if not type(self) is Follower:
                logger.info('Remote term is higher, converting to Follower')
                self.orchestrator.change_state(Follower)
                self.orchestrator.state.data_received_peer(peer_id, message)
                return
        else:
            method = getattr(self, 'handle_' + message['type'], None)
            if method:
                method(peer_id, message)
            else:
                logger.info('Unrecognized message from {}: {}'.format(peer_id,
                                                                      message))

    def data_received_client(self, transport, message):
        methods = {'Append': self.handle_client_append,
                   'Get': self.handle_client_get}

        if message['type'] in methods:
            methods[message['type']](transport, message)
            logger.info('Received message: ' + message['type'])
        else:
            logger.info('Received unrecognized message from client')

    def handle_request_vote(self, peer_id, message):
        term_is_current =  message['term'] >= self.persist['currentTerm']
        can_vote = self.persist['votedFor'] in [None, message['candidateId']]
        index_is_current = message['lastLogIndex'] >= len(self.persist['log'])
        vote = term_is_current and can_vote and index_is_current

        if vote:
            self.persist['votedFor'] = message['candidateId']

        logger.debug('Voting for {}. Term:{} Vote:{} Index:{}'.format(peer_id,\
            term_is_current, can_vote, index_is_current))

        response = {'type': 'response_vote', 'voteGranted': vote,
                   'term': self.persist['currentTerm']}
        self.orchestrator.send_peer(peer_id, response)

    def handle_client_append(self, transport, message):
        response = {'type': 'redirect', 'leaderId': self.volatile['leaderId']}
        self.orchestrator.send(transport, response)
        logger.info('Redirect client {}:{} to leader: '.format(
                     *transport.get_extra_info('peername')))

    def handle_client_get(self, transport, message):
        pass  # TODO every server should be able to respond


class Follower(State):
    def __init__(self, old_state=None, orchestrator=None, config=None):
        super().__init__(old_state, orchestrator, config)
        self.persist['votedFor'] = None
        self.restart_election_timer()

    def teardown(self):
        self.election_timer.cancel()

    def restart_election_timer(self):
        if hasattr(self, 'election_timer'):
            self.election_timer.cancel()

        timeout = random.randrange(1,4)
        timeout = timeout * 10 ** (0 if self.volatile['debug'] else -1)

        loop = asyncio.get_event_loop()
        self.election_timer = loop.call_later(timeout,
            self.orchestrator.change_state, Candidate)
        logger.debug('Election timer restarted: {}s'.format(timeout))

    def handle_append_entries(self, peer_id, message):
        self.restart_election_timer()
        logger.debug('Appending {} entries'.format(len(message['entries'])))
        response = {'success': True, 'term': self.persist['currentTerm'],
                   'type': 'response_append'}
        self.orchestrator.send_peer(peer_id, response)
        return # TODO: FIX function
        wrong_current_term = message['term'] < self.persist['currentTerm']
        wrong_prev_log_term = self.persist['log'][message['prevLogIndex']]\
            ['term'] != message['prevLogTerm']
        success = not (wrong_current_term or wrong_prev_log_term)

        if success:
            self.persist['log'] = self.persist['log'][:message['prevLogIndex'] + 1]
            self.persist['log'] += message['entries']
            self.volatile['leaderId'] = message['leaderId']

            if message['leaderCommit'] > self.volatile['commitIndex']:
                self.volatile['commitIndex'] =  min(message['leaderCommit'],
                                                 len(self.persist['log']))

        response = {'success': success, 'term': self.persist['currentTerm'],
                   'type': 'response_append'}
        self.orchestrator.send_peer(peer_id, response)


class Candidate(Follower):
    def __init__(self, old_state=None, orchestrator=None, config=None):
        super().__init__(old_state, orchestrator, config)
        self.persist['currentTerm'] += 1
        self.persist['votedFor'] = self.volatile['Id']
        self.votes_count = 1
        logger.info('Starting election for term: {}'.\
            format(self.persist['currentTerm']))
        self.send_vote_requests()

    def send_vote_requests(self):
        logger.info('Sending vote requests')
        message = {'type': 'request_vote', 'term': self.persist['currentTerm'],
                   'candidateId': self.volatile['Id'],
                   'lastLogIndex': len(self.persist['log']),
                   'lastLogTerm': self.persist['log'][-1]['term'] if self.persist['log'] else 0}  # TODO: fix with new Log
        self.orchestrator.broadcast_peers(message)

    def handle_append_entries(self, peer_id, message):
        logger.debug('Converting to Follower')
        self.orchestrator.change_state(Follower)
        self.orchestrator.state.handle_append_entries(peer_id, message)

    def handle_response_vote(self, peer_id, message):
        self.votes_count += message['voteGranted']
        logger.info('Vote count: {}'.format(self.votes_count))
        if self.votes_count > len(self.orchestrator.cluster) / 2:
            self.orchestrator.change_state(Leader)

class Leader(State):
    def __init__(self, old_state=None, orchestrator=None, config=None):
        super().__init__(old_state, orchestrator, config)
        logger.info('Leader of term: {}'.format(self.persist['currentTerm']))
        self.send_append_entries([])
        self.restart_empty_append_timer()

    def teardown(self):
        self.empty_append_timer.cancel()

    def restart_empty_append_timer(self):
        logger.debug('Empty AppendEntries timer restarted')
        if hasattr(self, 'empty_append_timer'):
            self.empty_append_timer.cancel()

        timeout = random.randrange(1,4)
        timeout = timeout * 10 ** (-1 if self.volatile['debug'] else -2)

        loop = asyncio.get_event_loop()
        self.empty_append_timer = loop.call_later(timeout,
                                                  self.send_append_entries)

    def send_append_entries(self, entries=[]):
        self.restart_empty_append_timer()
        logger.debug('Sending AppenEntries: {} entries'.format(len(entries)))

        loop = asyncio.get_event_loop()
        message = {'type': 'append_entries', 'entries':entries,
                   'term': self.persist['currentTerm'],
                   'leaderCommit': self.volatile['commitIndex'],
                   'leaderId': self.volatile['Id'],
                   'prevLogIndex': None,  # TODO log
                   'prevLogTerm': None}  # TODO log
        self.orchestrator.broadcast_peers(message)

    def handle_response_append(self, peer_id, message):
        pass  # TODO log

    def handle_client_append(self, transport, message):
        pass  # TODO
