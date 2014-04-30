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
import httplib2
import json
import sys

from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run_flow

class GoogleAPI(object):
    def __init__(self, args):
        f = open(args.config_ft, 'r')
        js = json.load(f)
        f.close()

        self.client_id = js['client_id']
        self.client_secret = js['client_secret']
        self.table_id = js['table_id']
        self.args = args
        self.scope = 'https://www.googleapis.com/auth/fusiontables'

    def push_update(self, when, hum, temp, lux):
        flow = OAuth2WebServerFlow(self.client_id, self.client_secret,
                                   self.scope)

        storage = Storage('credentials.dat')
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            credentials = run_flow(flow, storage, self.args)

        http = httplib2.Http()
        http = credentials.authorize(http)

        service = build('fusiontables', 'v1', http=http)

        datestring = '%02d-%02d-%d %d:%02d' % (when.tm_mon, when.tm_mday,
                                               when.tm_year, when.tm_hour,
                                               when.tm_min)

        query = "INSERT INTO %s (Date, Humidity, Temperature, Luminosity) VALUES ('%s', %.2f, %.2f, %d)" % (self.table_id, datestring, hum, temp, lux / 20000.0)

        request = service.query().sql(sql=query)
        request.execute()
