import time

class Timer:
    def __init__(self):
        self.float_duration = None
        self.start_time = None
        self.stop_time = None
        self.running = False
        self.round_times = []
        pass

    def start(self):
        self.start_time = time.monotonic()
        self.running = True
        self.stop_time = None
        self.round_times = []

    def round(self):
        if not self.running:
            raise RuntimeError("Timer has not been started")

        self.round_times.append(time.monotonic())

    def get_round_durations(self):
        if self.running:
            raise RuntimeError("Timer is running")

        durations = []
        for i in range(len(self.round_times)):
            reference = self.round_times[i - 1] if i - 1 >= 0 else self.start_time
            durations.append(self.round_times[i] - reference)
        return durations

    def stop(self, last_round=True):
        self.stop_time = time.monotonic()
        self.running = False
        if last_round:
            self.round_times.append(self.stop_time)

        self.float_duration = self.stop_time - self.start_time
        return self.float_duration

    def get_duration_tuple(self):
        # (min, sec, ms)
        if self.float_duration is None:
            raise RuntimeError("Run timer first")
        return Timer.time_to_tuple(self.float_duration)

    @staticmethod
    def time_to_tuple(time_float):
        return int(time_float) // 60, int(time_float) % 60, int(time_float * 1000) % 1000
