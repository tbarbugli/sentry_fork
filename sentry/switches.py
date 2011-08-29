from datetime import timedelta, datetime

class Switch(object):
    amount_trigger = 10
    wakeup_period = 10 * 3600 #1 day

    def __init__(self, group):
        self.last_seen = group.last_seen
        self.last_email_sent = group.last_email_sent
        self.group = group

    def send_email(self):
        now = datetime.now()
        if not self.last_email_sent:
            return True
        if self.last_email_sent + timedelta(seconds= self.wakeup_period) < now:
            return True
        if self.group.message_set.filter(datetime__gte= self.last_email_sent, datetime__lte= now).count() > self.amount_trigger:
            return True
        return False