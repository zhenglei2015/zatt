import asyncio
import random
import logging
from .persistence import PersistentDict

class State:
    def __init__(self, old_state=None, orchestrator=None, config=None):
        logging.info('State:' + self.__class__.__name__)
        if isinstance(old_state, State):
            self.orchestrator = old_state.orchestrator
            self.persist = old_state.persist
            self.volatile = old_state.volatile
        elif orchestrator and config:
            self.orchestrator = orchestrator
            orchestrator.cluster = config['cluster']
            self.persist = PersistentDict(config['storage'],
                                          {'log': [],
                                           'votedFor': None,
                                           'currentTerm': 0})
            self.volatile = {'commitIndex': 0,
                             'lastApplied': 0,
                             'leaderId': None,
                             'Id': config['id']}

    def data_received_peer(self, peer_id, message):
        if message['term'] > self.persist['currentTerm']\
           and not isinstance(self, Follower):
            self.orchestrator.change_state(Follower)
            self.orchestrator.state.data_received_peer(peer_id, message)
            return

        method = getattr(self, 'handle_' + message['type'], None)
        if method:
            method(peer_id, message)
            logging.info('Received message from peer type: ' + message['type'])
        else:
            logging.info('Received unrecognized message from peer')

    def data_received_client(self, transport, message):
        methods = {'Append': self.handle_client_append,
                   'Get': self.handle_client_get}

        if message['type'] in methods:
            methods[message['type']](transport, message)
            logging.info('Received message of type: ' + message['type'])
        else:
            logging.info('Received unrecognized message from client')

    def handle_request_vote(self, peer_id, message):
        wrong_current_term = message['term'] < self.persist['currentTerm']
        voted_for = self.persist['votedFor'] in [None, message['candidateId']]
        log_index_updated = message['lastLogIndex'] >= len(self.persist['log'])
        vote = not wrong_current_term and voted_for and log_index_updated

        if vote:
            self.persist['votedFor'] = message['candidateId']

        logging.info('Vote for {}: {}'.format(message['candidateId'], vote))
        response = {'type': 'response_vote', 'voteGranted': vote,
                   'term': self.persist['currentTerm']}
        self.orchestrator.send_peer(peer_id, response)

    def handle_client_append(self, transport, message):
        response = {'type': 'redirect', 'leaderId': self.volatile['leaderId']}
        self.orchestrator.send(transport, response)
        logging.info('Redirect client {}:{} to leader: '.format(
                     *transport.get_extra_info('peername')))

    def handle_client_get(self, transport, message):
        pass  # TODO every server should be able to respond


class Follower(State):
    def __init__(self, old_state=None, orchestrator=None, config=None):
        super().__init__(old_state, orchestrator, config)
        self.restart_election_timer()

    def teardown(self):
        self.election_timer.cancel()

    def restart_election_timer(self):
        if hasattr(self, 'election_timer'):
            self.election_timer.cancel()

        timeout = random.randrange(100,300) * 10 ** -3

        loop = asyncio.get_event_loop()
        self.election_timer = loop.call_later(timeout,
            self.orchestrator.change_state, Candidate)

    def data_received_peer(self, peer_id, message):
        self.restart_election_timer()
        super().data_received_peer(peer_id, message)

    def handle_append_entries(self, peer_id, message):
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
    def __init__(self, old_state=None):
        super().__init__(old_state)
        self.persist['currentTerm'] += 1
        self.persist['votedFor'] = self.volatile['Id']
        self.restart_election_timer()
        self.votes_counter = 0
        self.send_vote_requests()

    def send_vote_requests(self):
        message = {'type': 'request_vote', 'term': self.persist['currentTerm'],
                   'candidateId': self.volatile['Id'],
                   'lastLogIndex': len(self.persist['log']),
                   'lastLogTerm': self.persist['log'][-1]['term'] if self.persist['log'] else 0}
        self.orchestrator.broadcast_peers(message)

    def handle_append_entries(self, peer_id, message):
        self.orchestrator.change_state(Follower)
        self.orchestrator.state.handle_append_entries(peer_id, message)

    def handle_response_vote(self, peer_id, message):
        if message['voteGranted']:
            self.votes_counter += 1
        if self.votes_counter > len(self.orchestrator.cluster) / 2:
            self.orchestrator.change_state(Leader)


class Leader(State):
    def __init__(self, old_state=None):
        super().__init__(old_state)
        self.send_append_entries([])
        self.restart_empty_append_timer()

    def teardown(self):
        self.empty_append_timer.cancel()

    def restart_empty_append_timer(self):
        if hasattr(self, 'empty_append_timer'):
            self.empty_append_timer.cancel()

        timeout = random.randrange(100,300) * 10 ** -4  # TODO check range

        loop = asyncio.get_event_loop()
        self.empty_append_timer = loop.call_later(timeout,
            self.send_append_entries, [])

    def send_append_entries(self, entries):
        self.restart_empty_append_timer()

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
