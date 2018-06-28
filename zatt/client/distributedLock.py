import collections
from zatt.client.abstractClient import AbstractClient
from zatt.client.refresh_policies import RefreshPolicyAlways


class DistributedLock(AbstractClient):
    def __init__(self, addr, port, append_retry_attempts=3,
                 refresh_policy=RefreshPolicyAlways()):
        super().__init__()
        self.data['cluster'] = [(addr, port)]
        self.append_retry_attempts = append_retry_attempts
        self.refresh_policy = refresh_policy
        self.refresh(force=True)
        self.id = 123456


    def TryLock(self, key):
        self._append_log({'action': 'change', 'key': key, 'value': self.id})

    def OwnTheLock(self, key):
        self.refresh()
        return self.data[key] == self.id

    def _append_log(self, payload):
        for attempt in range(self.append_retry_attempts):
            response = super()._append_log(payload)
            if response['success']:
                break
        # TODO: logging
        return response

    def refresh(self, force=False):
        if force or self.refresh_policy.can_update():
            self.data = self._get_state()
