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

import json
from task import AnalysisTask
from datetime import datetime as dt, timedelta
from sdnalyzer.store import Link, LinkSample, Port, PortSample, SampleTimestamp
from sqlalchemy import desc


class SimpleLinkStatistics(AnalysisTask):
    def __init__(self):
        super(SimpleLinkStatistics, self).__init__()
        self.type = "LinkStatistics"
        self.links = {}

    @staticmethod
    def parse(sample):
        return {
            "t": sample.sampled.isoformat(),
            "srcPlr": sample.src_packet_loss,
            "dstPlr": sample.dst_packet_loss,
            "srcTxDr": sample.src_transmit_data_rate,
            "srcRxDr": sample.src_receive_data_rate,
            "dstTxDr": sample.dst_transmit_data_rate,
            "dstRxDr": sample.dst_receive_data_rate
        }

    def _analyze(self, session):
        links = session.query(Link).all()

        for link in links:
            link_statistic = dict()

            samples = session.query(LinkSample).filter(LinkSample.link_id == link.id,
                                                       LinkSample.sampled > dt.now() - timedelta(days=1)).order_by(
                desc(LinkSample.sampled)).all()

            if len(samples) > 0:
                link_statistic["srcPlr"] = samples[0].src_packet_loss
                link_statistic["dstPlr"] = samples[0].dst_packet_loss

                link_statistic["srcTxDr"] = samples[0].src_transmit_data_rate
                link_statistic["srcRxDr"] = samples[0].src_receive_data_rate
                link_statistic["dstTxDr"] = samples[0].dst_transmit_data_rate
                link_statistic["dstRxDr"] = samples[0].dst_receive_data_rate

                link_statistic["samples"] = map(self.parse, samples)

                link_id = self.generate_link_id(link)
                self.links[link_id] = link_statistic

                self.samples.add(samples[0].sampled)

    def _write_report(self, report):
        report.content = json.dumps(self.links)