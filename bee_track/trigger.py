import logging
import time
import datetime
from enum import Enum
import multiprocessing

import RPi.GPIO as GPIO

from configurable import Configurable

logger = logging.getLogger(__name__)


class FlashSequence(Enum):
    """
    Flash sequence options
    """
    ALL = 0
    "Fire every flash"
    TWO_AT_A_TIME = 1
    "Fire two flashes at once"
    IN_SEQUENCE = 2
    "Flash all the flashes sequentially"
    NONE = 9
    "Disable all flashes"


class Trigger(Configurable):
    """
    A worker to handle triggering the GPIO pins, etc.

    E.g. Send a signal to the camera to take an exposure.

    Raspberry Pi GPIO module basics
    https://sourceforge.net/p/raspberry-gpio-python/wiki/BasicUsage/
    """

    def __init__(self, message_queue, cam_trigger, t=2.0):
        super().__init__(message_queue)
        print("Initialising Trigger Control")
        self.cam_trigger = cam_trigger
        self.manager = multiprocessing.Manager()
        self.flashselection: list = self.manager.list()
        self.index = multiprocessing.Value('i', 0)
        "Incrementing identifier number per trigger event"
        self.record: list = self.manager.list()
        "Camera exposure trigger event log"
        self.direction = 0
        self.flash_select_pins = [14, 15, 18, 23]  # [8,10,12,16] #Board->BCM pins
        "Custom flash selection"
        self.trigger_pin = 24  # 18 #Board->BCM pins
        # ???
        self.flashselection.append(0)
        self.flashselection.append(1)
        self.flashselection.append(2)
        self.flashselection.append(3)
        self.t = multiprocessing.Value('d', t)
        "Time interval/seconds"
        self.ds = multiprocessing.Value('d', 0)
        "Delayed start (proportion of time interval)"
        self.flashseq = multiprocessing.Value('i', FlashSequence.ALL)
        "Flash sequence"
        self.skipnoflashes = multiprocessing.Value('i', 0)
        "How many flashes to skip???"
        self.preptime = 0.02
        "Preparation time/seconds"
        self.triggertime = 0.03  # this will end up at least 200us
        "Trigger exposure time"
        self.seqn = 0
        "Flash sequence position tracker"
        self.set_up_gpio()
        self.run = multiprocessing.Event()
        "Trigger activation flag"
        self.mode = GPIO.BCM  # GPIO.BOARD, GPIO.BCM or None
        "Pin numbering mode. See: https://sourceforge.net/p/raspberry-gpio-python/wiki/BasicUsage/"

    def set_up_gpio(self):
        """
        Set up GPIO

        https://sourceforge.net/p/raspberry-gpio-python/wiki/BasicUsage/
        """

        # Set GPIO pin numbering mode
        GPIO.setmode(self.mode)

        # Set up pins as outputs (GPIO.OUT is output)
        GPIO.setup(self.trigger_pin, GPIO.OUT)
        for pin in self.flash_select_pins:
            GPIO.setup(pin, GPIO.OUT)

        time.sleep(0.5)

        # Disable those output pins
        self.deactivate_flashes()
        self.deactivate()

        print("Running")

    @property
    def flash_count(self) -> int:
        """
        The number of flashes
        """
        return len(self.flashselection)

    def activate_flashes(self):
        """
        Activate the GPIO pins to configure the flashes that should fire
        """

        # All flashes
        if self.flashseq.value == FlashSequence.ALL:
            for flash in self.flashselection:
                GPIO.output(self.flash_select_pins[flash], True)

        # Two at a time
        if self.flashseq.value == FlashSequence.TWO_AT_A_TIME:
            # Activate two flashes based on our position in the sequence
            GPIO.output(self.flash_select_pins[self.flashselection[self.seqn]], True)
            GPIO.output(self.flash_select_pins[self.flashselection[self.seqn + 1]], True)

            # Loop through the flash sequence
            self.seqn += 2
            if self.seqn >= self.flash_count:
                self.seqn = 0

        # Flash in sequence
        if self.flashseq.value == FlashSequence.IN_SEQUENCE:
            GPIO.output(self.flash_select_pins[self.flashselection[self.seqn]], True)

            # Loop through the flash sequence
            self.seqn += 1
            if self.seqn >= self.flash_count:
                self.seqn = 0

        # Custom flash selection
        if self.flashseq.value == FlashSequence.NONE:
            self.deactivate_flashes()

    def deactivate_flashes(self):
        """
        Deactivate all flash GPIO pins
        """
        for pin in self.flash_select_pins:
            GPIO.output(pin, False)

    def trigger_camera(self, fire_flash: bool, end_of_set: bool):
        """
        Send trigger to camera (and flash, optionally) to take a photograph exposure.

        @param fire_flash: Whether to activate the flashes
        @param end_of_set: whether this is the last photo of a set (tells the tracking system to look for the bee)
        """
        logger.debug("Photo:    Flash" if fire_flash else "Photo: No Flash")

        # Activate flash
        if fire_flash:
            self.activate_flashes()
        else:
            # Deactivate all flash GPIO pins
            self.deactivate_flashes()

        # Wait for preparation time
        time.sleep(self.preptime)

        # Get current timestamp
        triggertime = time.time()  # TODO Why are these two different?
        triggertime_datetime = datetime.datetime.now()  # need to convert to string later
        # triggertime = triggertime_datetime.timestamp()
        triggertimestring = triggertime_datetime.strftime("%Y%m%d_%H:%M:%S.%f")

        # Log the photo capture
        record = {
            'index': self.index.value, 'endofset': end_of_set, 'direction': self.direction, 'flash': fire_flash,
            'flashselection': list(self.flashselection), 'triggertime': triggertime,
            'triggertimestring': triggertimestring
        }
        self.record.append(record)

        # Increment exposure count
        print("Incrementing trigger index from %d" % self.index.value)
        self.index.value += 1

        # Software trigger...
        # self.cam_trigger.set()

        # Trigger via pin...
        self.activate()
        time.sleep(self.triggertime)

        # Deactivate
        self.deactivate_flashes()
        self.deactivate()

    def activate(self):
        """
        Turn on the trigger GPIO pin
        """
        GPIO.output(self.trigger_pin, True)

    def deactivate(self):
        """
        Turn off the trigger GPIO pin
        """
        GPIO.output(self.trigger_pin, False)

    def worker(self):
        """
        Tell the camera to take exposures when the trigger flag is activated.
        """

        # ???
        skipcount = 0

        # Loop until the run event is deactivated (cleared)
        while True:
            self.run.wait()

            # Delayed start
            delaystart = self.ds.value * self.t.value
            time.sleep(delaystart)

            # Increment skip counter
            skipcount += 1
            # ???
            skipnoflashphoto = skipcount <= self.skipnoflashes.value

            # Capture data
            self.trigger_camera(fire_flash=True, end_of_set=skipnoflashphoto)

            # Is something different happening when we reach the end of a set? What's a set?
            # ???
            if not skipnoflashphoto:
                self.trigger_camera(fire_flash=False, end_of_set=True)
                skipcount = 0

                # Wait for ???
                time.sleep(self.t.value - self.triggertime * 2 - self.preptime * 2 - delaystart)
            else:
                # Wait for ???
                time.sleep(self.t.value - self.triggertime - self.preptime - delaystart)
