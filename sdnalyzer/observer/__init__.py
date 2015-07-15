# The MIT License (MIT)
# 
# Copyright (c) 2015 Saarland University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# Contributor(s): Andreas Schmidt (Saarland University)
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# 
# This license applies to all parts of SDNalytics that are not externally
# maintained libraries.

import time
import math
from datetime import datetime as dt, timedelta
from threading import *

from augmentation import CentralityAugmentation
from sdnalyzer.common import RequestException
from sdnalyzer.observer.sensors.floodlightControllerSensor import DevicesQuery, SwitchListQuery, LinksQuery, SwitchStatFlowQuery, \
    SwitchStatPortQuery, SwitchStatFeaturesQuery, DelayQuery
import sdnalyzer.store as store


class Observer(object):
    def __init__(self, controller_url, api_port):
        self._poll_interval = None
        self._started = dt.now()
        self._completed = None
        self._queries = [SwitchListQuery(self._poll_interval, controller_url=controller_url, api_port=api_port),
                         DevicesQuery(self._poll_interval, controller_url=controller_url, api_port=api_port),
                         SwitchStatFeaturesQuery(self._poll_interval, controller_url=controller_url, api_port=api_port),
                         SwitchStatPortQuery(self._poll_interval, controller_url=controller_url, api_port=api_port),
                         LinksQuery(self._poll_interval, controller_url=controller_url, api_port=api_port),
                         SwitchStatFlowQuery(self._poll_interval, controller_url=controller_url, api_port=api_port),
                         DelayQuery(self._poll_interval, controller_url=controller_url, api_port=api_port)]

        self._post_processes = [CentralityAugmentation()]

    def _save_timestamp(self):
        session = store.get_session()
        session.add(store.SampleTimestamp(timestamp=self._started, interval=self._poll_interval))
        session.commit()

    def _prepare_queries(self):
        print "Start preparing at {:%H:%M:%S}.".format(self._started)

        threads = []
        for query in self._queries:
            thread = Thread(target=query.prepare)
            thread.daemon = True
            threads.append((thread, query))
            thread.start()

        for (thread, query) in threads:
            thread.join(10)
            if thread.is_alive() or not query.success:
                raise RequestException(query)

        print "Completed preparing."

    def _execute_queries(self):
        print "Start executing at {:%H:%M:%S}.".format(dt.now())
        for query in self._queries:
            query.execute(self._started)
        print "Completed executing at {:%H:%M:%S}.".format(dt.now())

    def _post_processing(self):
        print "Start postprocessing at {:%H:%M:%S}.".format(dt.now())
        for p in self._post_processes:
            p.execute(self._started)
        self._completed = dt.now()
        print "Completed postprocessing at {:%H:%M:%S}.".format(self._completed)

    def wait_for_next_run(self):
        next_iteration = (self._started + timedelta(seconds=self._poll_interval))
        delta = int(max(0, math.floor((next_iteration - self._completed).total_seconds())))
        print "Waiting {} seconds till next run.".format(delta)
        time.sleep(delta)

    def _execute_run(self, program_state):
        self._started = dt.now()
        successful_preparation_phase = True
        try:
            self._prepare_queries()
        except RequestException as e:
            print "Some requests failed. In particular: ", e.query.url
            successful_preparation_phase = False
            self._completed = dt.now()
        program_state.healthy = successful_preparation_phase
        if successful_preparation_phase:
            self._execute_queries()
            self._post_processing()
            self._save_timestamp()

    def observe(self, single, poll_interval, program_state):
        if single:
            self._execute_run(program_state)
        else:
            self._poll_interval = poll_interval
            while True:
                self._execute_run(program_state)
                self.wait_for_next_run()