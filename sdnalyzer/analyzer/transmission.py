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

from datetime import datetime as dt, timedelta
import json
import numpy as np
import scipy.spatial.distance as sp
from task import AnalysisTask
from sdnalyzer.store import Node, Link, LinkSample, Port, PortSample
from sqlalchemy import or_


class PathSplitRecommendations(AnalysisTask):
    def __init__(self):
        super(PathSplitRecommendations, self).__init__()
        self.max_distance = 0.0
        self.type = "PathSplitRecommendations"
        self.splits = []
        self.nodes = {}
        self.timedelta = timedelta(days=1)

        self._minimal_delay = 1
        self._minimal_loss = 10 ** -3

    def _convert_parameter(self, parameter, link):
        return {
            "link_id": self.generate_link_id(link),
            "loss": max(self._minimal_loss, parameter[0]),
            "delay": max(self._minimal_delay, parameter[1]),
        }

    def _convert_src(self, x):
        return [max(self._minimal_loss, x.src_packet_loss) if x.src_packet_loss is not None else self._minimal_loss,
                max(self._minimal_delay, x.src_delay) if x.src_delay is not None else self._minimal_delay]

    def _convert_dst(self, x):
        return [max(self._minimal_loss, x.dst_packet_loss) if x.dst_packet_loss is not None else self._minimal_loss,
                max(self._minimal_delay, x.dst_delay) if x.dst_delay is not None else self._minimal_delay]

    def _analyze(self, session):
        for node in session.query(Node).filter(Node.type == "switch").all():
            links = session.query(Link) \
                .filter(or_(Link.src_id == node.id, Link.dst_id == node.id)) \
                .order_by(Link.id).all()

            links = filter(lambda x: x.src.type != "host" and x.dst.type != "host", links)
            link_count = len(links)

            feature_count = 2  # loss, delay

            link_parameters = np.ndarray((link_count, feature_count), dtype=np.float64)
            variances = np.ndarray((0, feature_count), dtype=np.float64)
            count = 0
            for i in range(link_count):
                link = links[i]


                most_recent_samples = list(session.query(LinkSample) \
                                           .filter(LinkSample.link_id == link.id,
                                                   LinkSample.sampled > dt.now() - self.timedelta) \
                                           .order_by(LinkSample.sampled.desc()).all())

                self.samples.update((x.sampled for x in most_recent_samples))

                samples = map(self._convert_src if link.src_id == node.id else self._convert_dst, most_recent_samples)

                avg_array = np.ndarray((0, feature_count), dtype=np.float64)
                c = len(most_recent_samples)
                avg_array = np.append(avg_array, samples).reshape((c, feature_count))
                link_parameters[i:] = np.mean(avg_array, axis=0)
                variances = np.append(variances, avg_array)
                count += c

            link_parameters = np.nan_to_num(link_parameters)
            variances = variances.reshape(count, feature_count)

            np_sum = np.var(variances, axis=0)
            np_sum[0] = max(np_sum[0], self._minimal_loss ** 2)
            np_sum[1] = max(np_sum[1], self._minimal_delay ** 2)

            distances = sp.pdist(link_parameters, "seuclidean", V=np_sum)
            distances = sp.squareform(distances)
            np.set_printoptions(precision=5, suppress=True)

            splits = []

            node_max_distance = 0.0

            for i in range(distances.shape[0]):
                for j in range(i + 1, distances.shape[1]):
                    port1 = links[i].src_port if links[i].src_id == node.id else links[i].dst_port
                    port2 = links[j].src_port if links[j].src_id == node.id else links[j].dst_port
                    dist = distances[i, j] if not np.isnan(distances[i, j]) else 0
                    self.max_distance = max(self.max_distance, dist)
                    node_max_distance = max(node_max_distance, dist)
                    splits.append({
                        "left": port1,
                        "right": port2,
                        "distance": dist
                    })

            if link_count > 1:
                self.nodes[node.device_id] = {
                    "max_distance": node_max_distance,
                    "ports": {
                        links[i].src_port if links[i].src_id == node.id else links[i].dst_port: self._convert_parameter(
                            link_parameters[i], links[i]) for i in range(link_count)},
                    "splits": sorted(splits, key=lambda x: x["distance"], reverse=True)
                }

    def _write_report(self, report):
        result = {
            "max_distance": self.max_distance,
            "nodes": self.nodes
        }
        report.content = json.dumps(result, sort_keys=True)