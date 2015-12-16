#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import sys
import time
from subprocess import check_call, check_output

# Numerical GPIO values.
SOLENOID_A = '44' # P8_12
SOLENOID_B = '26' # P8_14

SOIL_A = '47' # P8_15
SOIL_B = '46' # P8_16

AIN_A = '/sys/bus/iio/devices/iio:device1/in_voltage0_raw' # P9_
AIN_B = '/sys/bus/iio/devices/iio:device1/in_voltage1_raw' # P9_

class Logfile(object):
    def __init__(self, directory):
        self.directory = directory
        self.logfile = None
        self.last_rotated = None

    def check_rotate(self, n):
        if self.directory == None:
            return

        if self.last_rotated is None or self.last_rotated.tm_mday != n.tm_mday:
            try:
                if self.logfile is not None:
                    self.logfile.close()

                self.logfile = open('%s/%d-%02d-%02d' % (self.directory, n.tm_year,
                                                 n.tm_mon, n.tm_mday), 'a', 1)

                self.last_rotated = n
                self.write(n, 'Opened log file: %s\n' % self.logfile.name)
            except Exception as e:
                print 'Failed to rotate log file: %s' % str(e)

    def write(self, now, text):
        formatted = '%d:%02d %s' % (now.tm_hour, now.tm_min, text)
        print formatted

        try:
            if self.logfile is not None:
                self.logfile.write(formatted)
        except Exception as e:
            print 'Failed to write to log file: %s' % str(e)

def invalid_hum_temp(hum, temp):
    if hum <= 0 or hum > 100:
        return True

    # In Celcius
    if temp <= 0 or temp > 50:
        return True

    return False


def read_hum_temp():
    attempts = 0
    hum, temp = check_output('DHT22/read_dht').split()
    while (invalid_hum_temp(float(hum), float(temp)) and attempts < 10):
        hum, temp = check_output('DHT22/read_dht').split()
        attempts += 1

    # Explicitly report 0's if the sensor isn't working.
    if attempts > 9 or (int(float(hum)) == 0 and int(float(temp)) == 0):
        print 'Check DHT!'
        return (0.0, 0.0)

    return (float(hum), (float(temp) * (9.0 / 5.0)) + 32)

def read_sys(filename, as_type=int):
    attempts = 0
    while attempts < 10:
        try:
            f = open(filename, 'r')
            value = f.readline()
            f.close()
            return as_type(value)
        except IOError as e:
            print 'Trying %s again (%s)' % (filename, str(e))

    raise Exception('Can\'t read from %s?' % filename)

def write_sys(value, filename):
    f = open(filename, 'w')
    f.write(value)
    f.close()

def set_gpio(pin, attribute, value):
    write_sys(value, '/sys/class/gpio/gpio%s/%s' % (pin, attribute))

def export_gpio(pin, direction, value):
    write_sys(pin, '/sys/class/gpio/export')
    write_sys(direction, '/sys/class/gpio/gpio%s/direction' % pin)
    write_sys(value, '/sys/class/gpio/gpio%s/value' % pin)

def init():
    # Register the temperature/humidity sensor's pin for GPIO.
    check_call(['DHT22/read_dht', '-i'])

    # Luminosity sensor uses driver 'tsl2563'.
    try:
        check_call(['modprobe', 'tsl2563'])
        write_sys('tsl2561 0x39', '/sys/bus/i2c/devices/i2c-1/new_device')
    except:
        print 'Failed to init luminosity!'

    # Analog input pinmux.
    write_sys('BB-ADC', '/sys/devices/bone_capemgr.9/slots')

    # Configure P8_12 (GPIO 44) for output to control one of the solenoids.
    export_gpio(SOLENOID_A, 'out', '0')

    # Configure P8_14 (GPIO 26) for output to control the other solenoid.
    export_gpio(SOLENOID_B, 'out', '0')

    # Configure P8_15 (GPIO 47) for output to apply voltage to soil sensor.
    export_gpio(SOIL_A, 'out', '0')

    # Configure P8_16 (GPIO 46) for output to apply voltage to soil sensor.
    export_gpio(SOIL_B, 'out', '0')

def test(arg):
    print 'Testing temperature/humidity sensor...'
    print '%s %% relative humidity, %s F' % read_hum_temp()

    print '\nTesting luminosity sensor...'
    lux = read_sys('/sys/bus/iio/devices/iio:device0/in_intensity_both_raw')
    print '%d raw lux intensity' % lux

    print '\nTesting soil moisture sensors...'

    if ':' in arg:
        seca, secb = map(int, arg.split(':'))
        print '\nTesting solenoids...'
        print '--Solenoid A, solo. (%d seconds)' % seca
        set_gpio(SOLENOID_A, 'value', '1')
        time.sleep(seca)
        set_gpio(SOLENOID_A, 'value', '0')
        time.sleep(2)
        print '--Solenoid B, solo. (%d seconds)' % secb
        set_gpio(SOLENOID_B, 'value', '1')
        time.sleep(secb)
        set_gpio(SOLENOID_B, 'value', '0')
        time.sleep(2)
        print '--Both solenoids together.'
        set_gpio(SOLENOID_A, 'value', '1')
        set_gpio(SOLENOID_B, 'value', '1')
        time.sleep(2)
        set_gpio(SOLENOID_A, 'value', '0')
        set_gpio(SOLENOID_B, 'value', '0')
    else:
        sec = int(arg)
        print '--Both solenoids together.'
        set_gpio(SOLENOID_A, 'value', '1')
        set_gpio(SOLENOID_B, 'value', '1')
        time.sleep(sec)
        set_gpio(SOLENOID_A, 'value', '0')
        set_gpio(SOLENOID_B, 'value', '0')

    print '\nTest complete!'
    sys.exit(0)

if __name__ == '__main__':
    print 'Called util.py standalone, running test()!'
    while True:
        choice = raw_input('Run init first? [n]')
        if choice.lower() in ('y', 'yes'):
            init()
            break
        elif choice.lower() in ('n', 'no', ''):
            break
    test()
