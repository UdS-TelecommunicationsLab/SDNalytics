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

from datetime import datetime as dt
import sdnalyzer.store as store


class AnalysisTask(object):
    def __init__(self):
        self.type = None
        self.samples = set()

    def _create_report(self, session):
        sorted_unique_samples = sorted(self.samples)
        intervals = map(lambda x: x[0], session.query(store.SampleTimestamp.interval).filter(
            store.SampleTimestamp.timestamp.in_(self.samples)).group_by(store.SampleTimestamp.interval).all())

        samples_present = len(sorted_unique_samples) > 0
        return store.Report(created=dt.now(),
                            type=self.type,
                            sample_count=len(self.samples),
                            sample_start=sorted_unique_samples[0] if samples_present else None,
                            sample_stop=sorted_unique_samples[-1] if samples_present else None,
                            sample_interval=str(intervals[0]) if len(intervals) == 1 else "nan")

    def run(self):
        start = dt.now()
        print "Started with {} at {:%H:%M:%S}.".format(self.type, start)
        session = store.get_session()
        self._analyze(session)
        session.rollback()

        if self.type is None:
            raise NotImplementedError("The concrete AnalysisTask implementation needs a type information.")

        report = self._create_report(session)

        self._write_report(report)
        stop = dt.now()
        seconds = (stop - start).total_seconds()

        report.execution_duration = seconds
        session = store.get_session()
        session.add(report)
        session.commit()

        print "Completed {} at {:%H:%M:%S}. Took {} seconds.".format(self.type, stop, seconds)

    def _analyze(self, session):
        raise NotImplementedError('The concrete AnalysisTask implementation needs a _analyze method.')

    def _write_report(self, report):
        raise NotImplementedError('The concrete AnalysisTask implementation needs a _write_report method.')

    @staticmethod
    def generate_link_id(link):
        return "{}-{}.{}-{}".format(link.src.device_id, link.src_port, link.dst.device_id, link.dst_port)