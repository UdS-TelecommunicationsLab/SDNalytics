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

import graph_tool.centrality as gt
import sdnalyzer.store as store
from sdnalyzer.topology import NetworkTopology


class CentralityAugmentation(object):
    @staticmethod
    def execute(now):
        session = store.get_session()

        topology = NetworkTopology(session, now)
        (node_betweenness, link_betweenness) = gt.betweenness(topology.topology)
        closeness = gt.closeness(topology.topology)

        for v in topology.nodes:
            topology.node_information[v].degree = topology.nodes[v].out_degree()
            topology.node_information[v].closeness = closeness[topology.nodes[v]]
            topology.node_information[v].betweenness = node_betweenness[topology.nodes[v]]

        for l in topology.links:
            topology.link_information[l].betweenness = link_betweenness[topology.links[l]]

        session.commit()

