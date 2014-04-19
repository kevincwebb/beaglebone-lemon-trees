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

import datetime
import os.path
import sys

import matplotlib
import matplotlib.dates
import matplotlib.figure
import numpy
from matplotlib.backends.backend_agg import FigureCanvasAgg

class Sample(object):
    __slots__ = ('time', 'hum', 'temp', 'lux')

    def __init__(self, time, humidity, temperature, luminosity):
        self.time = time
        self.hum = humidity
        self.temp = temperature
        self.lux = luminosity

output = sys.argv[1]
inputs = sorted(sys.argv[2:])

data = []

for i in inputs:
    f = open(i, 'r')
    year, month, day = map(int, os.path.basename(i).split('-'))
    for line in f:
        tokens = line.split()
        if len(tokens) == 4:
            hour, minute = map(int, tokens[0].split(':'))
            dt = datetime.datetime(year, month, day, hour, minute)
            h = float(tokens[1])
            t = float(tokens[2])
            l = int(tokens[3])
            if h < 100 and t < 110:
                data.append(Sample(dt, h, t, l))
    f.close()

dates = matplotlib.dates.date2num([d.time for d in data])
hum = [d.hum for d in data]
temp = [d.temp for d in data]
lux = [d.lux for d in data]

fig = matplotlib.figure.Figure()
hplot = fig.add_subplot(3,1,1)
tplot = fig.add_subplot(3,1,2)
lplot = fig.add_subplot(3,1,3)

hplot.plot_date(dates, hum)
tplot.plot_date(dates, temp)
lplot.plot_date(dates, lux)

hplot.xaxis.set_major_locator(matplotlib.dates.DayLocator())
hplot.xaxis.set_minor_locator(matplotlib.dates.HourLocator(numpy.arange(0,24,1)))
hplot.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y-%m-%d'))
tplot.xaxis.set_major_locator(matplotlib.dates.DayLocator())
tplot.xaxis.set_minor_locator(matplotlib.dates.HourLocator(numpy.arange(0,24,1)))
tplot.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y-%m-%d'))
lplot.xaxis.set_major_locator(matplotlib.dates.DayLocator())
lplot.xaxis.set_minor_locator(matplotlib.dates.HourLocator(numpy.arange(0,24,1)))
lplot.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y-%m-%d'))

canvas = FigureCanvasAgg(fig)
canvas.print_eps(output, dpi=110)

of = open('export.csv', 'w')
of.write('Humidity,Temperature,Luminosity,Date\n')
for d in data:
    of.write('%.2f,%.2f,%d,%s\n' % (d.hum, d.temp, d.lux / 20000.0, d.time.strftime('%m/%d/%Y %H:%M')))
of.close()
