"""
A simple task scheduling system to run periodic tasks
"""

from datetime import datetime, timedelta
from typing import Generator, Optional, Sequence, Callable, Any, Mapping
from threading import Event, Thread

ScheduleGenerator = Generator[datetime, None, None]


class Schedule(Thread):
    """
    This represents a reoccuring task, exceuting ``target``
    every time the schedule is due.
    The target is run in an extra thread by default.
    If you stop the schedule while the target function is running,
    the thread is canceled after finishing its current run.

    :param target: The target function to execute each time
        the schedule is due
    :param interval: A generator yielding datetime objects
        that determine when the schedule is due.
        When this generator is exhausted, the schedule stops.
        Datetime objects in the past are simply ignored and the
        next value from the generator is used to schedule the job.
    """

    def __init__(
        self, target: Callable[..., Any], interval: ScheduleGenerator,
    ):
        super().__init__()
        self._target = target
        self._interval = interval
        self._stop_event = Event()
        self.is_running = Event()

    def start_schedule(self, *args: Sequence[Any], **kwargs: Mapping[str, Any]) -> None:
        """
        Start the scheduler and pass all supplied arguments to
        the target function each time the schedule is due
        """
        self._args = args
        self._kwargs = kwargs
        super().start()

    def run(self) -> None:
        """
        Start the schedule execution in an extra thread.
        The target function is called, passing all arguments
        supplied to this call.
        """
        while not self._stop_event.is_set():
            try:
                next_schedule = self.next_schedule()
            except StopIteration:
                self._stop_event.set()
                continue

            wait_time = (next_schedule - datetime.now()).total_seconds()
            self._stop_event.wait(wait_time)
            if not self._stop_event.is_set():
                self.is_running.set()
                self._target(*self._args, **self._kwargs)
                self.is_running.clear()

        self.stop()

    def next_schedule(self) -> datetime:
        """
        Return the datetime object this schedule is due
        """
        return next(self._interval)

    def stop(self) -> None:
        """
        Stop the async execution of the schedule, cacnel all future tasks
        """
        # set the stop event, then cancel the timer
        self._stop_event.set()

        # wait for the runthread to finish
        try:
            self.join()
        except RuntimeError:
            pass

    def __call__(self, *args: Sequence[Any], **kwargs: Mapping[str, Any]) -> Any:
        """
        Make calling the function possible from the decorated object
        """
        return self._target(*args, **kwargs)


def parse_cron_spec(spec: str, max_value: int, min_value: int = 0) -> Sequence[int]:
    """
    Parse a string of in a cron-like expression format to a sequence accepted numbers.
    The expression needs to have one of the following forms:

    - ``i`` sequence contains only the element i
    - ``*`` indicates that all values possible for this part are included
    - ``i,j,k`` specifies a list of possible values
    - ``i-j`` specifies a range of values *including* ``j``
    - ``i-j/s`` additionally specifies the step-size

    :param spec: The cron-like expression to parse
    :param max_value: The maximum value allowed for this range.
        This is needed to specify the range using the '*' wildcard
    :param min_value: The minimum allowed value
    :raises ValueError: if the spec tries to exceed the limits

    Example:

    .. testsetup:: *

        from pytb.schedule import parse_cron_spec

    .. doctest::

        >>> list(parse_cron_spec('5', max_value=7,))
        [5]

        >>> list(parse_cron_spec('*', max_value=7,))
        [0, 1, 2, 3, 4, 5, 6, 7]

        >>> list(parse_cron_spec('1-4', max_value=7,))
        [1, 2, 3, 4]

        >>> list(parse_cron_spec('1-4/2', max_value=7,))
        [1, 3]

    """
    parsed_values: Sequence[int] = []

    if spec.isdigit():
        parsed_values = [int(spec)]

    if spec == "*":
        parsed_values = range(min_value, max_value + 1)

    if "," in spec:
        parsed_values = tuple(int(val) for val in spec.split(","))

    if spec.count("-") == 1:
        step = 1

        if "/" in spec:
            spec, step_spec = spec.split("/")
            step = int(step_spec)

        start, end = spec.split("-")
        parsed_values = range(int(start), int(end) + 1, int(step))

    out_of_bounds = [min_value > val > max_value for val in parsed_values]

    if any(out_of_bounds):
        raise ValueError(f"found out-of-bounds value for expression {spec}")

    if len(parsed_values) == 0:
        raise ValueError(f"Cannot parse cron-like expression {spec}")

    return parsed_values


def at(  # pylint: disable=invalid-name
    minute: str = "*",
    hour: str = "*",
    day: str = "*",
    month: str = "*",
    weekday: str = "*",
) -> Callable[..., Schedule]:
    """
    run the task every time the current system-time matches
    the cron-like expression. Check the documentation for
    :func:`parse_cron_spec` for the supported syntax.
    """
    selected_minutes = parse_cron_spec(minute, max_value=59)
    selected_hours = parse_cron_spec(hour, max_value=23)
    selected_days = parse_cron_spec(day, min_value=1, max_value=31)
    selected_months = parse_cron_spec(month, min_value=1, max_value=12)
    selected_weekdays = [x % 7 for x in parse_cron_spec(weekday, max_value=7)]

    def get_next_due_date() -> ScheduleGenerator:
        """
        Get the datetime where this schedule should be run next
        """
        next_schedule = datetime.min
        while True:
            if next_schedule < datetime.now():
                now = datetime.now().replace(second=0, microsecond=0)
                # iterate over all possible dates in the next year to find the suitable next date
                # this sounds horrible at first but isn't bad at all. This check is only run when
                # the previous date expired, meaning for often-running tasks, the loop will break
                # pretty soon and for tasks scheduled long into the future, the worst case is to
                # iterate over ~0.5M possible candidates once a year.
                for offset in range(1, 60 * 24 * 366):
                    possible_date = now + timedelta(minutes=offset)
                    if (
                        possible_date.minute in selected_minutes
                        and possible_date.hour in selected_hours
                        and possible_date.day in selected_days
                        and possible_date.month in selected_months
                        and possible_date.weekday() in selected_weekdays
                    ):
                        next_schedule = possible_date
                        break
                else:
                    raise AssertionError(
                        "Could not find a suitable date matching the condition in the next year."
                    )

            yield next_schedule

    def schedule_decorator(fun: Callable[..., Any]) -> Schedule:
        return Schedule(fun, get_next_due_date())

    return schedule_decorator


def every(
    interval: timedelta, start_at: Optional[datetime] = None
) -> Callable[..., Schedule]:
    """
    Run a task repeadetly at the given interval

    :param interval: run the command this often the most
    :param start_at: run the command for the first time
        only after this date has passed. If not specified,
        run the command immediatley
    """
    start = datetime.now()
    if start_at is not None:
        start = start_at

    def get_next_due_date() -> ScheduleGenerator:
        """
        Get the datetime where this schedule should be run next
        """
        while True:
            time_since_last_schedule = (datetime.now() - start) % interval
            yield datetime.now() + (interval - time_since_last_schedule)

    def schedule_decorator(fun: Callable[..., Any]) -> Schedule:
        return Schedule(fun, get_next_due_date())

    return schedule_decorator
