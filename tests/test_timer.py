import caduc.timer
import signal
import threading
import time
import unittest

from . import mock
from caduc.image import ClientSemaphore

class TestTimer(unittest.TestCase):

    def test_timer_is_well_created_and_delayed(self):
        sem = threading.Semaphore(1)
        def delayed():
            sem.release()
        lock_time = time.time()
        sem.acquire()
        caduc.timer.Timer(1, delayed).start()

        sem.acquire()
        release_time = time.time()
        (release_time-lock_time).should.be.eql(1., epsilon=0.1)

    def test_unstarted_timer_is_not_executed(self):
        executed_timers = []
        def delayed(timer_id):
            executed_timers.append(timer_id)
        caduc.timer.Timer(1, delayed, (1, ))
        time.sleep(2)
        executed_timers.should.be.empty

    def test_timer_cancellation(self):
        executed_timers = []
        def delayed(timer_id):
            executed_timers.append(timer_id)
        timer = caduc.timer.Timer(1, delayed, (1, ))
        timer.start()
        caduc.timer.Timer(1, delayed, (2, )).start()
        time.sleep(0.5)
        timer.cancel()
        time.sleep(2)
        executed_timers.should_not.contain(1)
        executed_timers.should.contain(2)

    def test_unstarted_timer_cancellation_should_success(self):
        executed_timers = []
        def delayed(timer_id):
            executed_timers.append(timer_id)
        timer = caduc.timer.Timer(1, delayed)
        timer.cancel()
        timer.cancel()

    def test_all_timer_cancellation(self):
        executed_timers = []
        def delayed(timer_id):
            executed_timers.append(timer_id)
        caduc.timer.Timer(1, delayed, (1, )).start()
        caduc.timer.Timer(1, delayed, (2, )).start()
        time.sleep(0.5)
        caduc.timer.Timer.CancelAll()
        time.sleep(2)
        executed_timers.should_not.contain(1)
        executed_timers.should_not.contain(2)
   
    def test_accessing_undefined_attribute_should_raise_error(self):
        def delayed():
            pass
        timer = caduc.timer.Timer(1, delayed)
        getattr.when.called_with(timer, 'aNonExistingAttribute').should.throw(AttributeError)
        timer.cancel()
        getattr.when.called_with(timer, 'aNonExistingAttribute').should.throw(AttributeError)

    def test_abort(self):
        cancel = caduc.timer.Timer.CancelAll
        orig = caduc.timer.orig
        cancel_mock = mock.Mock()
        orig_mock = mock.Mock()
        try:
            caduc.timer.Timer.CancelAll = cancel_mock
            caduc.timer.orig = orig_mock
            caduc.timer.abort(signal.SIGINT, 'backtrace')
            cancel_mock.assert_called_once_with()
            orig_mock.assert_called_once_with(signal.SIGINT, 'backtrace')
        finally:
            caduc.timer.Timer.CancelAll = cancel
            caduc.timer.orig = orig
    def test_abort_is_registered_as_sigint_handler(self):
        orig = signal.signal(signal.SIGINT, mock.Mock())
        try:
            orig.should.be(caduc.timer.abort)
        finally:
            signal.signal(signal.SIGINT, orig)
