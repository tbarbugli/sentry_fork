from datetime import timedelta, datetime

class Switch(object):
    """
    resends emails if WAKEUP_PERIOD is passed since last time an email was sent
    or since last email was sent AMOUNT_TRIGGER of messages are received for the
    same group.
    Does not send email for loggers in SKIP_LOGGERS
    """
    AMOUNT_TRIGGER = 100
    WAKEUP_PERIOD = 24 * 3600
    SKIP_LOGGERS = ('http404',)

    def __init__(self, group, logger_name= None):
        self.last_seen = group.last_seen
        self.last_email_sent = group.last_email_sent
        self.group = group
        self.logger_name = logger_name

    def send_email(self):
        if self.logger_name in self.SKIP_LOGGERS:
            return False
        now = datetime.now()
        if not self.last_email_sent:
            return True
        if self.last_email_sent + timedelta(seconds= self.WAKEUP_PERIOD) < now:
            return True
        if self.group.message_set.filter(datetime__gte= self.last_email_sent,
            datetime__lte= now).count() > self.AMOUNT_TRIGGER:
            return True
        return False