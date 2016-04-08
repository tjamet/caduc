import logging
import signal
import threading

class Timer(object):
    Timers = []

    def __init__(self, *args, **kwds):
        self.logger = logging.getLogger(str(self.__class__.__name__))
        self.__class__.Timers.append(self)
        self.timer = threading.Timer(*args, **kwds)

    def __getattr__(self, name):
        try:
            return super(Timer, self).__getattr(name)
        except AttributeError as e:
            if self.timer:
                return getattr(self.timer, name)
            else:
                raise

    def cancel(self):
        if self.timer:
            self.timer.cancel()
        self.timer = None

    @classmethod
    def CancelAll(cls):
        for timer in cls.Timers:
            timer.cancel()

def abort(sig, bt):
    Timer.CancelAll()
    orig(sig, bt)
orig = signal.signal(signal.SIGINT, abort)

