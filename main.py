#!/usr/bin/env python

# Copyright (c) 2014, Kevin Webb
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import collections
import time
import sys

import fusiontables
import util

from oauth2client import tools

class Plant(object):
    def __init__(self, solenoid, soil, ain, history_size):
        self.solenoid = solenoid
        self.soil = soil
        self.ain = ain
        self.history = collections.deque([], history_size)
        self.last_watering = time.time()

    def sample(self):
        util.set_gpio(self.soil, 'value', '1')
        readings = []
        for i in xrange(10):
            time.sleep(0.05)
            value = util.read_sys(self.ain)
            if value:
                readings.append(value)
        util.set_gpio(self.soil, 'value', '0')
        if len(readings) > 0:
            reading = max(readings)
            self.history.append(reading)
            return reading, max(self.history)
        else:
            return None, max(self.history)

    def water(self, duration, log):
        # TODO: Spawn thread that sets pin high, sleeps duration, sets pin low?
        return

def main_loop(args):
    log = util.Logfile(args.output)
    gft = fusiontables.GoogleAPI(args)

    plant_a = Plant(util.SOLENOID_A, util.SOIL_A, util.AIN_A, args.hsize)
    plant_b = Plant(util.SOLENOID_B, util.SOIL_B, util.AIN_B, args.hsize)

    while True:
        # Read humidity, temperature, and luminosity.
        hum, temp = util.read_hum_temp()
        lux = util.read_sys('/sys/bus/iio/devices/iio:device0/in_intensity_both_raw')

        # Read soil moisture.
        a_raw, a_max = plant_a.sample()
        b_raw, b_max = plant_b.sample()

        now = time.localtime()

        log.check_rotate(now)
        log.write(now, '%.2f %.2f %d' % (hum, temp, lux))
        log.write(now, 'A: %d (max %d), B: %d (max %d)\n' % (a_raw, a_max,
                                                             b_raw, b_max))

        gft.push_update(now, hum, temp, lux)

        if a_max < args.water_threshold:
            plant_a.water(args.duration, log)
        if b_max < args.water_threshold:
            plant_b.water(args.duration, log)

        # Open solenoid(s), if necessary.  Add hysteresis? Check moisture again?
        time.sleep(args.interval)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    parser.add_argument('-c', '--config_ft', default='client_data.json',
        dest='config_ft', help='JSON file containing FT client info.')
    parser.add_argument('-d', '--duration', default=20, dest='duration',
        type=int, help='Duration to keep solenoids open (in seconds) [20].')
    parser.add_argument('--history', default=15, dest='hsize', type=int,
        help='Number of entries to keep in the soil probe history. [15]')
    parser.add_argument('-i', '--interval', default=300, dest='interval',
        type=int, help='Time between sensor readings (in seconds). [300]')
    parser.add_argument('-n', '--noinit', default=True, dest='init',
        action='store_false', help='Don\'t initialize devices at startup.')
    parser.add_argument('-o', '--output', dest='output',
        help='Directory to use for logging output.  [stdout only.]')
    parser.add_argument('-t', '--test', default=False, dest='test',
        action='store_true', help='Run a test of the sensors and solenoids.')
    # TODO: Calibrate sensors and set this to a reasonable default.
    parser.add_argument('-w', '--water-threshold', default=0,
        dest='water_threshold', type=int,
        help='AIN value below which we open the solenoid to water.')
    args = parser.parse_args()

    if args.init:
        print 'Initializing...'
        util.init()

    if args.test:
        util.test()

    main_loop(args)
