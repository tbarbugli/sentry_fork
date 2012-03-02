from datetime import timedelta, datetime

_switches = {}

class RegisteringMetaClass(type):
    '''
    Registers switches classes
    '''
    def __new__(cls, classname, bases, classDict):
        class_definition = type.__new__(cls, classname, bases, classDict)
        if not classDict.get("__metaclass__"):
            _switches[classname] = class_definition
        return class_definition

    @classmethod
    def should_send(cls, *args, **kwargs):
        raise NotImplementedError

class Switch():
    __metaclass__ = RegisteringMetaClass

class SwitchManager():

    @classmethod
    def send_email(cls, *args, **kws):
        return all([s.should_send(*args, **kws) for s in _switches.values()])

class IgnoreLoggerSwitch(Switch):
    """
    Does not send email for loggers in SKIP_LOGGERS
    """
    SKIP_LOGGERS = ('http404',)

    @classmethod
    def should_send(cls, *args, **kwargs):
        logger_name = kwargs['logger_name']
        return not logger_name in cls.SKIP_LOGGERS

class WakeUpSwitch(Switch):
    """
    resends emails if WAKEUP_PERIOD is passed since last time an email was sent
    or since last email was sent AMOUNT_TRIGGER of messages are received for the
    same group.
    """
    AMOUNT_TRIGGER = 100
    WAKEUP_PERIOD = 30 * 24 * 3600

    @classmethod
    def should_send(cls, *args, **kwargs):
        group = kwargs['group']
        last_email_sent = group.last_email_sent
        now = datetime.now()
        if not last_email_sent:
            return True
        if last_email_sent + timedelta(seconds= cls.WAKEUP_PERIOD) < now:
            return True
        if group.message_set.filter(datetime__gte= last_email_sent,
            datetime__lte= now).count() > cls.AMOUNT_TRIGGER:
            return True
        return False

from django.core.cache import cache

class ThrottleSwitch(Switch):
    """
    it keeps track of amount of messages received in the last 
    SAMPLE * RESOLUTION seconds counts are stored in cache 
    (1 cache key every RESOLUTION seconds)
    sends emails only when the messages/s are less than the THROTTLE_RATE
    Once it goes in throttle mode it will take at least COOL_DOWN_PERIOD seconds
    before any email will be sent again
    """

    RESOLUTION = 10
    SAMPLES = 15
    THROTTLE_RATE = '5/s'
    COOL_DOWN_PERIOD = 600

    @classmethod
    def format_cache_key(cls, dt):
        return dt.strftime("%Y-%m-%d-%H:%M:%S")

    @classmethod
    def get_cache_keys(cls, start_dt):
        keys = []
        for i in range(cls.SAMPLES):
            dt = start_dt - timedelta(seconds=cls.RESOLUTION * (i+1))
            keys.append(cls.format_cache_key(dt))
        return keys

    @classmethod
    def normalize_dt(cls, dt):
        seconds = (dt.second/cls.RESOLUTION) * cls.RESOLUTION
        normalized_now = datetime(year=dt.year, month=dt.month, day=dt.day, minute=dt.minute, second=seconds)
        return normalized_now

    @classmethod
    def get_throughput_per_second(cls, dt=None):
        now = dt or datetime.now()
        keys = cls.get_cache_keys(cls.normalize_dt(now))
        return sum(cache.get_many(keys).values()) / float(cls.SAMPLES * cls.RESOLUTION)

    @classmethod
    def update_throughput_per_second(cls):
        now = datetime.now()
        normalized_now = cls.normalize_dt(now)
        cls.incr(normalized_now)

    @classmethod
    def incr(cls, dt):
        k = cls.format_cache_key(dt)
        try:
            cache.incr(k)
        except ValueError:
            cache.set(k, 1, (cls.RESOLUTION + 1))

    @classmethod
    def is_throttled(cls, exceeded_limit=False):
        throttling = cache.get('SENTRY_THROTTLED_AT')
        if exceeded_limit:
            cache.set('SENTRY_THROTTLED_AT', throttling or datetime.now(),
                      cls.COOL_DOWN_PERIOD)
        return exceeded_limit or bool(cache.get('SENTRY_THROTTLED_AT'))

    @classmethod
    def should_send(cls, *args, **kwargs):
        group = kwargs['group']
        limit, period = cls.THROTTLE_RATE.split('/')
        limit = float(limit)
        if group.times_seen == 1:
            cls.update_throughput_per_second()
        num = cls.get_throughput_per_second()
        threshold = num / {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[period[0]]
        return not cls.is_throttled(limit < threshold)

