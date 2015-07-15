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
import numpy as np
from datetime import datetime as dt, timedelta
from task import AnalysisTask
from sdnalyzer.store import Node, NodeSample, Link, LinkSample, SampleTimestamp
import itertools


# noinspection PyAbstractClass
class ReliabilityTask(AnalysisTask):
    @staticmethod
    def _convert_reliability(available_stamps):
        return lambda time: available_stamps[time] if (
            time in available_stamps and available_stamps[time] is not None) else 0.0

    @staticmethod
    def _get_reliability(x):
        if x.src_packet_loss is not None and x.dst_packet_loss is not None:
            loss = max(x.src_packet_loss, x.dst_packet_loss)
        elif x.src_packet_loss is not None:
            loss = x.src_packet_loss
        elif x.dst_packet_loss is not None:
            loss = x.dst_packet_loss
        else:
            loss = 0.0

        return 1. - loss


class LinkImprovementAnalysis(ReliabilityTask):
    def __init__(self):
        super(LinkImprovementAnalysis, self).__init__()
        self.type = "LinkImprovementAnalysis"
        self.result = {}

    @staticmethod
    def _convert_centrality(centrality_samples):
        return lambda x: centrality_samples[x] if x in centrality_samples else 0.0

    def _analyze(self, session):
        links = {d.id: d for d in session.query(Link).all()}
        max_centrality = 0

        self.samples = map(lambda x: x[0], session.query(SampleTimestamp.timestamp).filter(SampleTimestamp.timestamp > dt.now() - timedelta(days=1)).order_by(SampleTimestamp.timestamp).all())
        timestamps = [a.isoformat() for a in self.samples]

        link_samples = session.query(LinkSample) \
            .filter(LinkSample.sampled > dt.now() - timedelta(days=1), LinkSample.link_id is not None) \
            .order_by(LinkSample.link_id).all()

        link_series = []
        for link_id, value in itertools.groupby(link_samples, key=lambda d: d.link_id):
            v = list(value)
            reliability_samples = {x.sampled.isoformat(): self._get_reliability(x) for x in v}
            centrality_samples = {x.sampled.isoformat(): x.betweenness if x.betweenness is not None else 0.0 for x in v}
            reliability = map(self._convert_reliability(reliability_samples), timestamps)
            centrality = map(self._convert_centrality(centrality_samples), timestamps)

            max_centrality = max(max_centrality, np.max(centrality))

            link_series.append({
                "id": link_id,
                "link_id": self.generate_link_id(links[link_id]),
                "reliability": reliability,
                "centrality": centrality
            })

        self.result = {
            "series": link_series,
            "centrality_max": max_centrality,
            "timestamps": timestamps
        }

    def _write_report(self, report):
        report.content = json.dumps(self.result)


class LinkReliabilityStatistics(ReliabilityTask):
    def __init__(self):
        super(LinkReliabilityStatistics, self).__init__()
        self.type = "LinkReliabilityStatistics"
        self.result = {}

    def _analyze(self, session):
        links = {d.id: d for d in session.query(Link).all()}

        self.samples = map(lambda x: x[0], session.query(LinkSample.sampled).filter(
            LinkSample.sampled > dt.now() - timedelta(days=1)).distinct(LinkSample.sampled).order_by(
            LinkSample.sampled).all())
        timestamps = [a.isoformat() for a in self.samples]

        link_samples = session.query(LinkSample) \
            .filter(LinkSample.sampled > dt.now() - timedelta(days=1), LinkSample.link_id is not None) \
            .order_by(LinkSample.link_id).all()

        link_series = []
        for link_id, value in itertools.groupby(link_samples, key=lambda d: d.link_id):
            reliability_samples = {x.sampled.isoformat(): self._get_reliability(x) for x in value}

            samples = map(self._convert_reliability(reliability_samples), timestamps)
            link_series.append({
                "id": link_id,
                "link_id": self.generate_link_id(links[link_id]),
                "data": samples,
                "ratio": np.average(samples),
                "last_mile": links[link_id].src.type == "host" or links[link_id].dst.type == "host"
            })
        link_series.sort(key=lambda d: d["ratio"])

        self.result = {
            "linkSeries": link_series,
            "timestamps": timestamps
        }

    def _write_report(self, report):
        report.content = json.dumps(self.result)