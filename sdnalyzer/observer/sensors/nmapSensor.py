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

import logging
from libnmap.process import NmapProcess
from libnmap.parser import NmapParser, NmapParserException

import sdnalyzer.store as store

class NmapQuery(object):
    def __init__(self):
        pass

    def execute(self):
        session = store.get_session()
        self._process(session)
        session.commit()

    def _process(self, session):
        nmproc = NmapProcess("10.0.0.1", "-sT")
        parsed = None
        rc = nmproc.run()
        if rc != 0:
            logging.critical("NMAP Scan failed: {0}".format(nmproc.stderr))

        try:
            parsed = NmapParser.parse(nmproc.stdout)
        except NmapParserException as e:
            logging.critical("NMAP Parse failed: {0}".format(e.msg))

        if parsed is not None:
            for host in parsed.hosts:
                if len(host.hostnames):
                    tmp_host = host.hostnames.pop()
                else:
                    tmp_host = host.address

                print("Nmap scan report for {0} ({1})".format(
                    tmp_host,
                    host.address))
                print("Host is {0}.".format(host.status))
                print("  PORT     STATE         SERVICE")

                for serv in host.services:
                    pserv = "{0:>5s}/{1:3s}  {2:12s}  {3}".format(
                            str(serv.port),
                            serv.protocol,
                            serv.state,
                            serv.service)
                    if len(serv.banner):
                        pserv += " ({0})".format(serv.banner)
                    print(pserv)