import collections
from zatt.client.abstractClient import AbstractClient
from zatt.client.refresh_policies import RefreshPolicyAlways


class DistributedLock(AbstractClient):
    def __init__(self, addr, port, append_retry_attempts=3,
                 refresh_policy=RefreshPolicyAlways()):
        super().__init__()
        self.data = {}
        self.data['cluster'] = [(addr, port)]
        self.append_retry_attempts = append_retry_attempts
        self.refresh_policy = refresh_policy
        self.refresh(force=True)
        self.id = 123456


    def TryLock(self, key):
        self.refresh(force=True)
        if self.data.hasKey(key):
            print("Lock Failed!Already have the key")
            return False
        else:
            self._append_log({'action': 'change', 'key': key, 'value': self.id})

    def ReleaseLock(self, key):
        self.refresh(force=True)
        if self.data.hasKey(key) and self.data[key] == self.id:
            del self.data[key]
            self._append_log({'action': 'delete', 'key': key})
            return True
        else:
            return False

    def OwnTheLock(self, key):
        self.refresh(force=True)
        if self.data.hasKey(self.id) and self.data[key] == self.id:
            return True
        else:
            return False

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
