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
from sqlalchemy import func
from task import AnalysisTask
import pandas as pd
from sdnalyzer.store import Node, FlowSample, Flow, Link, SampleTimestamp
from sqlalchemy import or_
import itertools


class NoDataException(Exception):
    pass


class ServiceStatistics(AnalysisTask):
    def __init__(self):
        super(ServiceStatistics, self).__init__()
        self.type = "ServiceStatistics"
        self.content = []
        self.bits_per_byte = 8
        self.observation_window = timedelta(hours=1)

    def _calculate_statistics(self, flow_entries, ap):
        local_flow_entries = filter(lambda x: x.node_id == ap.id, flow_entries)
        statistics_samples = []
        for flow in local_flow_entries:
            statistics_samples.extend(
                map(lambda x: (x.sampled, x.byte_count, x.duration_seconds),
                    sorted(flow.samples, key=lambda x: x.sampled)))

        # TODO: use pandas for the complete calculation (grouping and accumulation)
        stamp_groups = itertools.groupby(statistics_samples, key=lambda x: x[0])

        maximum_valid_stamps = float(len(self.samples))
        non_valid_stamps = set(self.samples)

        statistics = []
        for stamp, grouper in stamp_groups:
            non_valid_stamps.discard(stamp)
            samples = list(grouper)
            stats = reduce(lambda acc, x: (acc[0], acc[1] + x[1], acc[2] + x[2]), samples, (samples[0][0], 0.0, 0.0))
            statistics.append(stats + (len(samples),))

        if len(statistics) > 0:
            df = pd.DataFrame(statistics, columns=["Time", "Bytes", "Duration", "FlowCounts"])
            df["PrevBytes"] = df["Bytes"].shift(1)
            df["PrevTime"] = df["Time"].shift(1)
            df["DeltaBytes"] = df["Bytes"] - df["PrevBytes"] / ((df["Time"] - df["PrevTime"]).astype('timedelta64[s]'))
            df["DataRate"] = df["DeltaBytes"] * self.bits_per_byte

            means = df.mean()
            deviations = df.std()

            valid_bytes_samples = df[df["DeltaBytes"] > 0]

            res = {
                "rate_avg": str(valid_bytes_samples.mean()["DataRate"]),
                "rate_std": str(valid_bytes_samples.std()["DataRate"]),
                "count_avg": str(means["FlowCounts"]),
                "count_std": str(deviations["FlowCounts"]),
                "duration_avg": str(means["Duration"]),
                "duration_std": str(deviations["Duration"]),
                "activity_actual": maximum_valid_stamps - len(non_valid_stamps),
                "activity_max": maximum_valid_stamps
            }
            return res
        else:
            raise NoDataException()


    @staticmethod
    def _get_provider(flow):
        is_consume = flow.transport_destination < flow.transport_source
        provider_mac = flow.data_layer_destination if is_consume else flow.data_layer_source
        provider_ip = flow.network_destination if is_consume else flow.network_source
        provider_port = flow.transport_destination if is_consume else flow.transport_source
        return is_consume, (provider_mac, provider_ip, flow.network_protocol, provider_port), provider_port

    def _prepare_output(self, providers, session):
        for provider_ident, d in providers.iteritems():
            mac = '00:00:' + provider_ident[0]
            node = session.query(Node).filter(Node.device_id == mac).first()
            if node:
                link = session.query(Link).filter(or_(Link.src_id == node.id, Link.dst_id == node.id)).first()
                if link is not None:
                    ap = link.src if link.src.type != "host" else link.dst

                    try:
                        d["consume"] = self._calculate_statistics(d["consume_flows"], ap)
                        d["provide"] = self._calculate_statistics(d["provide_flows"], ap)
                    except NoDataException:
                        print ap.id, " has no flow entries."
                        continue

                d["device_id"] = "00:00:" + provider_ident[0]
                d["mac"] = provider_ident[0]
                d["ip"] = provider_ident[1]
                d["protocol"] = int(provider_ident[2])
                d["port"] = int(provider_ident[3])
                del d["consume_flows"]
                del d["provide_flows"]

                if "consume" in d or "provide" in d:
                    self.content.append(d)

    def _analyze(self, session):
        interval_start = dt.now() - self.observation_window
        self.samples = set(map(lambda x: x[0], session.query(SampleTimestamp.timestamp).filter(
            SampleTimestamp.timestamp > interval_start).all()))
        recent_entry_query = session.query(FlowSample).filter(FlowSample.sampled > interval_start)
        flows = list(session.query(Flow).filter(recent_entry_query.exists().where(FlowSample.flow_id == Flow.id)).all())

        # Find where providers (host := (mac, ip), service := port) are located
        known_ports = [21, 22, 23, 25, 53, 80, 110, 143, 161, 443, 554]
        providers = {}
        for flow in flows:
            is_consume, provider_ident, provider_port = self._get_provider(flow)

            if provider_port in known_ports:
                if provider_ident not in providers:
                    providers[provider_ident] = {
                        "consume_flows": [],
                        "provide_flows": []
                    }

                if is_consume:
                    providers[provider_ident]["consume_flows"].append(flow)
                else:
                    providers[provider_ident]["provide_flows"].append(flow)

        self._prepare_output(providers, session)

    def _write_report(self, report):
        self.content = sorted(self.content, key=lambda x: x["device_id"] + str(x["protocol"]))
        report.content = json.dumps(self.content, sort_keys=True)


class SimpleServiceUsage(AnalysisTask):
    def __init__(self):
        super(SimpleServiceUsage, self).__init__()
        self.type = "ServiceUsage"
        self.tcp_ports = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3",
                          143: "IMAP", 161: "SNMP", 443: "HTTPS", 554: "RTSP"}
        self.udp_ports = {554: "RTSP"}
        self.devices = {}
        self.observation_window = timedelta(hours=1)

    def _add_count(self, count, device_id, port, protocol_key, consume_or_provide):
        if consume_or_provide not in self.devices[device_id]:
            self.devices[device_id][consume_or_provide] = {}
        if protocol_key not in self.devices[device_id][consume_or_provide]:
            self.devices[device_id][consume_or_provide][protocol_key] = {}
        if port not in self.devices[device_id][consume_or_provide][protocol_key]:
            self.devices[device_id][consume_or_provide][protocol_key][port] = 0

        self.devices[device_id][consume_or_provide][protocol_key][port] += count

    def _accumulate_for_protocol(self, count, flow, ports, protocol_key, protocol_number):
        if flow.network_protocol == protocol_number:
            data_layer_source = "00:00:" + flow.data_layer_source
            data_layer_destination = "00:00:" + flow.data_layer_destination

            if flow.transport_source in ports:
                port = int(flow.transport_source)
                if data_layer_source in self.devices:
                    self._add_count(count, data_layer_source, port, protocol_key, "provides")

                if data_layer_destination in self.devices:
                    self._add_count(count, data_layer_destination, port, protocol_key, "consumes")

            if flow.transport_destination in ports:
                port = int(flow.transport_destination)
                if data_layer_source in self.devices:
                    self._add_count(count, data_layer_source, port, protocol_key, "consumes")

                if data_layer_destination in self.devices:
                    self._add_count(count, data_layer_destination, port, protocol_key, "provides")

    def _analyze(self, session):
        for device in session.query(Node).all():
            self.devices[device.device_id] = {}

        tcp_keys = self.tcp_ports.keys()
        udp_keys = self.udp_ports.keys()

        self.samples = map(lambda x: x[0], session.query(SampleTimestamp.timestamp).filter(
            SampleTimestamp.timestamp > dt.now() - self.observation_window).all())

        for fs in session.query(FlowSample.flow_id, func.count(FlowSample.flow_id)).filter(
                        FlowSample.sampled > dt.now() - self.observation_window).group_by(FlowSample.flow_id).all():
            flow = session.query(Flow).filter(Flow.id == fs[0]).first()

            count = int(fs[1] // 2)

            self._accumulate_for_protocol(count, flow, tcp_keys, "tcp", 6)
            self._accumulate_for_protocol(count, flow, udp_keys, "udp", 17)

        devices = {}

        for key in self.devices:
            value = self.devices[key]
            if "consumes" in value or "provides" in value:
                devices[key] = value

        self.devices = devices

    def _write_report(self, report):
        content = {
            "udp": self.udp_ports,
            "tcp": self.tcp_ports,
            "devices": self.devices
        }
        report.content = json.dumps(content, sort_keys=True)