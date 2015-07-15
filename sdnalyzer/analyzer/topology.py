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
from sdnalyzer.store import NodeSample, LinkSample
from sqlalchemy import func


class SimpleTopologyCentrality(AnalysisTask):
    def __init__(self):
        super(SimpleTopologyCentrality, self).__init__()
        self.type = "TopologyCentrality"

    def _analyze(self, session):
        newest_timestamp = session.execute(func.max(NodeSample.sampled)).scalar()
        self.nodes = session.query(NodeSample).filter(NodeSample.sampled == newest_timestamp).all()
        newest_timestamp = session.execute(func.max(LinkSample.sampled)).scalar()
        self.links = session.query(LinkSample).filter(LinkSample.sampled == newest_timestamp).all()

        self.samples.add(newest_timestamp)

    def _write_report(self, report):
        content = {
            "devices": {},
            "links": {}
        }

        for node_sample in self.nodes:
            content["devices"][node_sample.node.device_id] = {
                "degree": node_sample.degree,
                "betweenness": node_sample.betweenness,
                "closeness": node_sample.closeness if node_sample.degree != 0 else 0
            }

        for link_sample in self.links:
            link_id = self.generate_link_id(link_sample.link)
            content["links"][link_id] = {"betweenness": link_sample.betweenness}

        report.content = json.dumps(content)