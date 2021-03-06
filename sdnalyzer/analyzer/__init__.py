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

from metrics import SimpleLinkStatistics
from reliability import LinkReliabilityStatistics, LinkImprovementAnalysis
from services import SimpleServiceUsage, ServiceStatistics
from topology import SimpleTopologyCentrality
from transmission import PathSplitRecommendations
import time


class Analyzer(object):
    def __init__(self):
        self.program_state = None
        self.tasks = {
            "ServiceStatistics": ServiceStatistics,
            "LinkImprovementAnalysis": LinkImprovementAnalysis,
            "PathSplitRecommendations": PathSplitRecommendations,
            "LinkReliabilityStatistics": LinkReliabilityStatistics,
            "ServiceUsage": SimpleServiceUsage,
            "LinkStatistics": SimpleLinkStatistics,
            "TopologyCentrality": SimpleTopologyCentrality
        }

    def analyze(self, single, program_state):
        self.program_state = program_state
        if single:
            self.run()
        else:
            while True:
                time.sleep(1000)

    def run(self, task="all"):
        tasks = {}
        if task == "all":
            tasks = self.tasks
        else:
            tasks[task] = self.tasks[task]

        for (key, task) in tasks.iteritems():
            task().run()