import asyncio
import random
from .persistence import PersistentDict, LogDict
from .logger import logger
from .config import fetch_config

class State:
    def __init__(self, old_state=None, orchestrator=None, config=None):
        logger.info('State change:' + self.__class__.__name__)
        if old_state:
            self.orchestrator = old_state.orchestrator
            self.persist = old_state.persist
            self.volatile = old_state.volatile
            self.log = old_state.log
        elif orchestrator and config:
            self.orchestrator = orchestrator
            self.persist = PersistentDict(config['storage'],
                                          {'votedFor': None,
                                           'currentTerm': 0})
            self.volatile = {'leaderId': None, 'Id': config['id'],
                             'debug':config['debug']}
            self.log = LogDict(config['storage'])

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

    def handle_request_vote(self, peer_id, message):
        self.restart_election_timer()
        term_is_current =  message['term'] >= self.persist['currentTerm']
        can_vote = self.persist['votedFor'] in [None, message['candidateId']]
        index_is_current = message['lastLogIndex'] >= self.log.index
        vote = term_is_current and can_vote and index_is_current

        if vote:
            self.persist['votedFor'] = message['candidateId']

        logger.debug('Voting for {}. Term:{} Vote:{} Index:{}'.format(peer_id,\
            term_is_current, can_vote, index_is_current))

        response = {'type': 'response_vote', 'voteGranted': vote,
                   'term': self.persist['currentTerm']}
        self.orchestrator.send_peer(peer_id, response)

    def handle_append_entries(self, peer_id, message):
        self.restart_election_timer()

        term_is_current = message['term'] >= self.persist['currentTerm']
        prev_log_term_match = self.log.index >= message['prevLogIndex'] and\
            (message['prevLogIndex'] == 0 or\
            self.log[message['prevLogIndex']]['term'] == message['prevLogTerm'])
        success = term_is_current and prev_log_term_match

        if success:
            self.log.append_entries(message['entries'], message['prevLogIndex'])
            self.volatile['leaderId'] = message['leaderId']
            self.log.commit(message['leaderCommit'])
            logger.debug('Log length is now {}'.format((len(self.log.log))))
        else:
            logger.warning('Couldnt append entries. cause: {}'.format('term\
                mismatch' if not term_is_current else 'prev log term mismatch'))

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
        logger.info('Broadcasting request_vote')
        message = {'type': 'request_vote', 'term': self.persist['currentTerm'],
                   'candidateId': self.volatile['Id'],
                   'lastLogIndex': self.log.index,
                   'lastLogTerm': self.log.term}
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

import random  # TODO: debug
class Leader(State):
    def __init__(self, old_state=None, orchestrator=None, config=None):
        super().__init__(old_state, orchestrator, config)
        self.cluster = fetch_config()['cluster']
        self.leader_status = {x:{'nextIndex':self.log.commitIndex + 1,  # TODO: review: could it be self.log.index ?
                                   'matchIndex': 0} for x in self.cluster}
        self.counter = {self.log.commitIndex: len(self.cluster)}
        logger.info('Leader of term: {}'.format(self.persist['currentTerm']))
        self.send_append_entries()

    def teardown(self):
        self.append_timer.cancel()

    def send_append_entries(self):
        self.restart_append_timer()
        # entries = [{'key': random.randint(1,10), 'value': random.randint(20,30),
        #             'action': 'change'}] # TODO: debug
        # entries = list(map(lambda x:{'term': self.persist['currentTerm'],
        #                              'data': x}, entries)) # TODO: debug
        # logger.debug('Broadcasting append_entries: {} entries'.format(len(entries)))

        message = {'type': 'append_entries', 'entries':entries,
                   'term': self.persist['currentTerm'],
                   'leaderCommit': self.log.commitIndex,
                   'leaderId': self.volatile['Id'],
                   'prevLogIndex': self.log.index,
                   'prevLogTerm': self.log.term}
        self.orchestrator.broadcast_peers(message)
        # self.log.commitIndex = self.log.index #  TODO: just for debug, RMOVE!

        # self.log.append_entries(entries, self.log.index)
        # logger.debug('Log length is now {}'.format((len(self.log.log))))


        for peer in self.leader_status:
            message = {'type': 'append_entries', 'entries':entries,
                       'term': self.persist['currentTerm'],
                       'leaderCommit': self.log.commitIndex,
                       'leaderId': self.volatile['Id'],
                       'prevLogIndex': self.log.index,
                       'prevLogTerm': self.log.term}








        timeout = random.randrange(1,4)
        timeout = timeout * 10 ** (-1 if self.volatile['debug'] else -2)
        loop = asyncio.get_event_loop()
        self.append_timer = loop.call_later(timeout, self.send_append_entries)

    def handle_response_append(self, peer_id, message):
        if message['success']:
            self.leader_status[peer_id]['matchIndex'] =\
                self.leader_status[peer_id]['nextIndex']

            self.counter[self.leader_status[peer_id]['nextIndex']] -=1
            self.leader_status[peer_id]['nextIndex'] += 1
            self.counter[self.leader_status[peer_id]['nextIndex']] +=1

            count = 0
            for category in reversed(sorted(self.counter)):
                count += self.counter[category]
                if count / len(self.cluster) > 0.5:
                    self.log.commit(category)
                    break
        else:
            logger.warning('Peer {} refused entry with index {}'.format(\
                peer_id, self.leader_status[peer_id]['nextIndex']))
            self.leader_status[peer_id]['nextIndex'] -= 1


    def handle_client_append(self, transport, message):
        pass  # TODO
