from time import perf_counter
import logging

logger = logging.getLogger(__name__)

# Import latency monitor if available
try:
    from latency_monitor import monitor
    LATENCY_MONITORING = True
except ImportError:
    LATENCY_MONITORING = False
    monitor = None


class BaseHandler:
    """
    Base class for pipeline parts. Each part of the pipeline has an input and an output queue.
    The `setup` method along with `setup_args` and `setup_kwargs` can be used to address the specific requirements of the implemented pipeline part.
    To stop a handler properly, set the stop_event and, to avoid queue deadlocks, place b"END" in the input queue.
    Objects placed in the input queue will be processed by the `process` method, and the yielded results will be placed in the output queue.
    The cleanup method handles stopping the handler, and b"END" is placed in the output queue.
    """

    def __init__(self, stop_event, queue_in, queue_out, setup_args=(), setup_kwargs={}):
        self.stop_event = stop_event
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.setup(*setup_args, **setup_kwargs)
        self._times = []

    def setup(self):
        pass

    def process(self):
        raise NotImplementedError

    def run(self):
        while not self.stop_event.is_set():
            input = self.queue_in.get()
            if isinstance(input, bytes) and input == b"END":
                # sentinelle signal to avoid queue deadlock
                logger.debug("Stopping thread")
                break
            start_time = perf_counter()
            for output in self.process(input):
                duration_s = perf_counter() - start_time
                self._times.append(duration_s)

                # Log to latency monitor if available
                if LATENCY_MONITORING and monitor:
                    component_name = self.__class__.__name__.replace('Handler', '').upper()
                    monitor.log_component_time(component_name, duration_s * 1000)

                if self.last_time > self.min_time_to_debug:
                    logger.debug(f"{self.__class__.__name__}: {self.last_time: .3f} s")
                self.queue_out.put(output)
                start_time = perf_counter()

        self.cleanup()
        self.queue_out.put(b"END")

    @property
    def last_time(self):
        return self._times[-1]
    
    @property
    def min_time_to_debug(self):
        return 0.001

    def cleanup(self):
        pass
