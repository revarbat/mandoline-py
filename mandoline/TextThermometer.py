from __future__ import print_function

import sys
import time

class TextThermometer(object):
    def __init__(self, target=100, value=0, update_period=0.5):
        self.value = value
        self.target = target
        self.last_time = time.time()
        self.update_period = update_period
        self.spincnt = 0
        self.spinchars = r'/-\|'

    def set_target(self, target):
        self.target = target
        self.last_time = time.time()
        self.spincnt = 0

    def update(self, value):
        self.value = value
        now = time.time()
        if now - self.last_time >= self.update_period:
            self.last_time = now
            pct = 100.0 * self.value / self.target
            self.spincnt = (self.spincnt + 1) % len(self.spinchars)
            spinchar = "" if pct >= 100.0 else self.spinchars[self.spincnt]
            print("\r  [{:50s}] {:.1f}%".format("="*int(pct/2) + spinchar, pct), end="")
            sys.stdout.flush()

    def clear(self):
        print("\r{:78s}".format(""), end="\r")


