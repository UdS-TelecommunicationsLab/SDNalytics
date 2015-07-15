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
import json
import logging
import requests
import sdnalyzer.store as store
from sqlalchemy import desc
from sdnalyzer.store import Node, NodeSample, InternetAddress, Port, Link, LinkSample, PortSample, Flow, FlowSample


def _print_json(obj):
    print(json.dumps(obj, sort_keys=True, indent=4))


def _output_json(obj):
    with open("out.txt", "w+") as f:
        f.write(json.dumps(obj, sort_keys=True, indent=4))


class JsonQuery(object):
    def __init__(self, poll_interval, controller_url, api_port):
        self.base_url = controller_url
        self.base_port = api_port
        self.url = ""
        self.poll_interval = poll_interval
        self._poll_result = {}
        self.success = False

    def _get_url(self):
        return "http://" + self.base_url + ":" + str(self.base_port) + "/wm/" + self.url

    def prepare(self):
        self.success = False
        url = self._get_url()
        try:
            req = requests.get(url)
            self._poll_result = req.json()
        except requests.ConnectionError as e:
            logging.warning("Requesting failed.")
            logging.warning(e)
            return

        self.success = True

    def execute(self, now):
        session = store.get_session()
        self._process(session, now, self._poll_result)
        session.commit()

    def _process(self, session, now, data):
        raise NotImplementedError("Cannot call this on abstract super class.")

    @staticmethod
    def _parse_time(unix_timestamp):
        unix_timestamp = str(unix_timestamp)
        if len(unix_timestamp) == 13:
            unix_timestamp = str(unix_timestamp)[0:-3]

        return dt.fromtimestamp(int(unix_timestamp))

    @staticmethod
    def _create_update_port(session, now, node, number, ip, name):
        port = session.query(Port).filter(Port.port_number == number, Port.node_id == node.id).first()
        if port is None:
            port = Port(node_id=node.id, port_number=number, created=now)
            session.add(port)
        port.last_seen = now
        port.hardware_address = ip
        port.name = name

    @staticmethod
    def _calculate_packet_loss_rate(before_dst, before_src, now_dst, now_src):
        delta_transmit = now_src.transmit_packets - before_src.transmit_packets
        delta_receive = now_dst.receive_packets - before_dst.receive_packets
        packet_loss_rate = 1 - (min(1, max(0, delta_receive / delta_transmit))) if (delta_transmit != 0) else 0
        return '%.5f' % round(packet_loss_rate, 5)

    @staticmethod
    def _calculate_data_rate(before, now, direction):
        # TODO: find out reason for drop in byte counts from high values to low values; currently solved by setting rates to 0
        if direction == "tx":
            delta_bytes = max(0, float((now.transmit_bytes - before.transmit_bytes))) * 8  # *8 for byte to bit
        elif direction == "rx":
            delta_bytes = max(0, float((now.receive_bytes - before.receive_bytes))) * 8  # *8 for byte to bit
        else:
            raise Exception("Specify either tx or rx.")

        delta_time = now.sampled - before.sampled
        data_rate = delta_bytes / delta_time.total_seconds()
        return int(data_rate)

    @staticmethod
    def _calculate_link_metrics(link, link_sample, session):
        src_port = filter(lambda p: p.port_number == link.src_port, link.src.ports)
        dst_port = filter(lambda p: p.port_number == link.dst_port, link.dst.ports)

        now_src = None
        now_dst = None
        before_src = None
        before_dst = None

        if len(src_port) > 0:
            src_samples = session.query(PortSample).filter(
                PortSample.port_id == src_port[0].id).order_by(
                desc(PortSample.sampled)).limit(2).all()

            if len(src_samples) == 2:
                now_src = src_samples[0]
                before_src = src_samples[1]

                link_sample.src_transmit_data_rate = JsonQuery._calculate_data_rate(before_src, now_src, "tx")
                link_sample.src_receive_data_rate = JsonQuery._calculate_data_rate(before_src, now_src, "rx")

        if len(dst_port) > 0:
            dst_samples = session.query(PortSample).filter(
                PortSample.port_id == dst_port[0].id).order_by(
                desc(PortSample.sampled)).limit(2).all()

            if len(dst_samples) == 2:
                now_dst = dst_samples[0]
                before_dst = dst_samples[1]
                link_sample.dst_transmit_data_rate = JsonQuery._calculate_data_rate(before_dst, now_dst, "tx")
                link_sample.dst_receive_data_rate = JsonQuery._calculate_data_rate(before_dst, now_dst, "rx")

        if before_dst is not None and before_src is not None and now_src is not None and now_dst is not None:
            link_sample.src_packet_loss = JsonQuery._calculate_packet_loss_rate(before_dst, before_src, now_dst,
                                                                                now_src)
            link_sample.dst_packet_loss = JsonQuery._calculate_packet_loss_rate(before_src, before_dst, now_src,
                                                                                now_dst)

    @staticmethod
    def _create_update_link(session, now, src, src_port_number, dst, dst_port_number, link_type, direction, last_seen):
        if src > dst:
            src, dst = dst, src
            src_port_number, dst_port_number = dst_port_number, src_port_number

        link = session.query(Link).filter(Link.src_id == src.id, Link.src_port == src_port_number,
                                          Link.dst_id == dst.id, Link.dst_port == dst_port_number).first()
        if link is None:
            link = Link(src=src, dst=dst, created=now)
            session.add(link)
        link.src_port = src_port_number
        link.dst_port = dst_port_number
        link.type = link_type
        link.direction = direction
        link.last_seen = last_seen

        link_sample = LinkSample(link=link, sampled=now)
        JsonQuery._calculate_link_metrics(link, link_sample, session)

        session.add(link_sample)
        return link


class SwitchListQuery(JsonQuery):
    def __init__(self, poll_interval, **kwargs):
        JsonQuery.__init__(self, poll_interval, **kwargs)
        self.url = "core/controller/switches/json"

    def _process(self, session, now, data):
        for sw in data:
            switch = session.query(Node).filter(Node.device_id == sw["switchDPID"]).first()
            if switch is None:
                switch = Node(device_id=sw["switchDPID"], created=now, type="switch")
                session.add(switch)
                session.commit()

            switch.last_seen = now
            switch.connected_since = self._parse_time(sw["connectedSince"])

            switch_sample = NodeSample(node_id=switch.id, sampled=now)
            session.add(switch_sample)


class SwitchStatQuery(JsonQuery):
    def __init__(self, poll_interval, subtype, **kwargs):
        JsonQuery.__init__(self, poll_interval, **kwargs)
        self.url = "/core/switch/all/" + subtype + "/json"

    def _process(self, session, now, data):
        raise NotImplementedError("Cannot call this on abstract super class.")


class SwitchStatFeaturesQuery(SwitchStatQuery):
    def __init__(self, poll_interval, **kwargs):
        SwitchStatQuery.__init__(self, poll_interval, "features", **kwargs)

    def _process(self, session, now, data):
        for device_id in data:
            if "portDesc" in data[device_id]:
                ports = data[device_id]["portDesc"]
                switch = session.query(Node).filter(Node.device_id == device_id).first()
                if switch is None:
                    logging.warning("Could not find Switch [%s]. This should only happen occasionally." % device_id)
                    continue

                if ports is not None:
                    for p in ports:
                        if p["portNumber"] == "local":
                            continue

                        JsonQuery._create_update_port(session, now, switch, p["portNumber"], p["hardwareAddress"],
                                                      p["name"])


class SwitchStatPortQuery(SwitchStatQuery):
    def __init__(self, poll_interval, **kwargs):
        SwitchStatQuery.__init__(self, poll_interval, "port", **kwargs)

    def _process(self, session, now, data):
        for device_id in data:
            if "port" in data[device_id]:
                ports = data[device_id]["port"]
                switch = session.query(Node).filter(Node.device_id == device_id).first()
                if switch is None:
                    logging.warning("Could not find Switch [%s]. This should only happen occasionally." % device_id)
                    continue

                if ports is not None:
                    for p in ports:
                        if p["portNumber"] == "local":
                            continue

                        port = session.query(Port).filter(Port.node_id == switch.id,
                                                          Port.port_number == p["portNumber"]).first()
                        if port is None:
                            msg = "Could not find Switch [%s]'s Port [%s]. This should only happen occasionally."
                            logging.warning(msg % (device_id, p["portNumber"]))
                            continue

                        sample = PortSample(port_id=port.id,
                                            sampled=now,
                                            receive_packets=p["receivePackets"],
                                            transmit_packets=p["transmitPackets"],
                                            receive_bytes=p["receiveBytes"],
                                            transmit_bytes=p["transmitBytes"],
                                            receive_dropped=p["receiveDropped"],
                                            transmit_dropped=p["transmitDropped"],
                                            receive_errors=p["receiveErrors"],
                                            transmit_errors=p["transmitErrors"],
                                            receive_frame_errors=p["receiveFrameErrors"],
                                            receive_overrun_errors=p["receiveOverrunErrors"],
                                            receive_crc_errors=p["receiveCRCErrors"],
                                            collisions=p["collisions"])

                        session.add(sample)


class SwitchStatFlowQuery(SwitchStatQuery):
    def __init__(self, poll_interval, **kwargs):
        SwitchStatQuery.__init__(self, poll_interval, "flow", **kwargs)

    @staticmethod
    def _parse_match(match):
        tp_src = "0"
        tp_dst = "0"
        if match["eth_type"] == "2054":
            nw_dest = match["arp_tpa"] if "arp_tpa" in match else ""
            nw_src = match["arp_spa"] if "arp_spa" in match else ""
        else:
            try:
                nw_dest = match["ipv4_dst"]
                nw_src = match["ipv4_src"]

                if "tcp_src" in match and "tcp_dst" in match:
                    tp_dst = match["tcp_dst"]
                    tp_src = match["tcp_src"]

                if "udp_src" in match and "udp_dst" in match:
                    tp_dst = match["udp_dst"]
                    tp_src = match["udp_src"]
            except KeyError as e:
                print match
                raise e

        return {
            "dataLayerDestination": match["eth_dst"] if ("eth_dst" in match) else "",
            "dataLayerSource": match["eth_src"] if ("eth_src" in match) else "",
            "dataLayerType": int(match["eth_type"]) if ("eth_type" in match) else "",
            "dataLayerVirtualLan": match["eth_vlan_vid"] if ("eth_vlan_vid" in match) else -1,
            "inputPort": match["in_port"] if ("in_port" in match and match["in_port"] != "any") else 0,
            # TODO: handle any case properly
            "networkDestination": nw_dest,
            "networkSource": nw_src,
            "networkProtocol": match["ip_proto"] if ("ip_proto" in match) else "0",
            "networkTypeOfService": match["ip_dscp"] if ("ip_dscp" in match) else "0",
            "transportDestination": tp_dst,
            "transportSource": tp_src,
            "dataLayerVirtualLanPriorityCodePoint": "0",  # TODO: insert proper value
            "networkDestinationMaskLen": "0",  # TODO: insert proper value
            "networkSourceMaskLen": "24",  # TODO: insert proper value
            "wildcards": "0"  # TODO: insert proper value
        }

    def _process(self, session, now, data):
        for dpid in data:
            switch = session.query(Node).filter(Node.device_id == dpid).first()

            if switch is not None:
                if "flows" in data[dpid]:
                    for flow in data[dpid]["flows"]:
                        match = self._parse_match(flow["match"])

                        fl = session.query(Flow).filter(Flow.cookie == flow["cookie"],
                                                        Flow.data_layer_destination == match["dataLayerDestination"],
                                                        Flow.data_layer_source == match["dataLayerSource"],
                                                        Flow.data_layer_type == match["dataLayerType"],
                                                        Flow.data_layer_virtual_lan == match["dataLayerVirtualLan"],
                                                        Flow.data_layer_virtual_lan_priority_code_point == match[
                                                            "dataLayerVirtualLanPriorityCodePoint"],
                                                        Flow.input_port == match["inputPort"],
                                                        Flow.network_destination == match["networkDestination"],
                                                        Flow.network_destination_mask_len == match[
                                                            "networkDestinationMaskLen"],
                                                        Flow.network_protocol == match["networkProtocol"],
                                                        Flow.network_source == match["networkSource"],
                                                        Flow.network_source_mask_len == match["networkSourceMaskLen"],
                                                        Flow.network_type_of_service == match["networkTypeOfService"],
                                                        Flow.transport_destination == match["transportDestination"],
                                                        Flow.transport_source == match["transportSource"],
                                                        Flow.wildcards == match["wildcards"],
                                                        Flow.node_id == switch.id).first()
                        if fl is None:
                            fl = Flow(created=now,
                                      cookie=flow["cookie"],
                                      data_layer_destination=match["dataLayerDestination"],
                                      data_layer_source=match["dataLayerSource"],
                                      data_layer_type=match["dataLayerType"],
                                      data_layer_virtual_lan=match["dataLayerVirtualLan"],
                                      data_layer_virtual_lan_priority_code_point=match[
                                          "dataLayerVirtualLanPriorityCodePoint"],
                                      input_port=match["inputPort"],
                                      network_destination=match["networkDestination"],
                                      network_destination_mask_len=match["networkDestinationMaskLen"],
                                      network_protocol=match["networkProtocol"],
                                      network_source=match["networkSource"],
                                      network_source_mask_len=match["networkSourceMaskLen"],
                                      network_type_of_service=match["networkTypeOfService"],
                                      transport_destination=match["transportDestination"],
                                      transport_source=match["transportSource"],
                                      wildcards=match["wildcards"],
                                      node=switch)
                            session.add(fl)

                        fs = FlowSample(sampled=now, flow=fl)
                        fs.packet_count = flow["packetCount"]
                        fs.byte_count = flow["byteCount"]
                        fs.duration_seconds = flow["durationSeconds"]
                        fs.priority = flow["priority"]
                        fs.idle_timeout_sec = flow["idleTimeoutSec"]
                        fs.hard_timeout_sec = flow["hardTimeoutSec"]
                        session.add(fs)


class DevicesQuery(JsonQuery):
    def __init__(self, poll_interval, **kwargs):
        JsonQuery.__init__(self, poll_interval, **kwargs)
        self.url = "device/"

    @staticmethod
    def _create_update_address(ip, now, session):
        address = session.query(InternetAddress).filter(InternetAddress.address == ip).first()
        if address is None:
            address = InternetAddress(created=now, address=ip)
            session.add(address)
            session.commit()
        return address

    @staticmethod
    def _create_update_node(ip_addresses, mac, now, session):
        cl = session.query(Node).filter(Node.device_id == "00:00:" + mac).first()
        if cl is None:
            cl = Node(created=now, device_id="00:00:" + mac, type="host")
            session.add(cl)
            session.commit()

        for ip in ip_addresses:
            address = DevicesQuery._create_update_address(ip, now, session)
            if address is not None and address not in cl.addresses:
                cl.addresses.append(address)

        return cl

    def _process(self, session, now, data):
        for client in data:
            if len(client["mac"]) > 0:
                mac = client["mac"][0]

                cl = DevicesQuery._create_update_node(client["ipv4"], mac, now, session)
                cl.last_seen = JsonQuery._parse_time(client["lastSeen"])
                client_sample = session.query(NodeSample).filter(NodeSample.node_id == cl.id,
                                                                 NodeSample.sampled == cl.last_seen).first()
                if client_sample is None and len(client["attachmentPoint"]) > 0:
                    client_sample = NodeSample(node_id=cl.id, sampled=now)
                    session.add(client_sample)
                    session.commit()

                for ap in client["attachmentPoint"]:
                    switch = session.query(Node).filter(Node.device_id == ap["switchDPID"]).first()
                    if switch is not None:
                        local_port = 1
                        JsonQuery._create_update_port(session, now, cl, local_port, mac, "UNK")
                        JsonQuery._create_update_link(session, now, cl, local_port, switch, ap["port"],
                                                      "ethernet", "bidirectional", now)


class LinksQuery(JsonQuery):
    def __init__(self, poll_interval, **kwargs):
        JsonQuery.__init__(self, poll_interval, **kwargs)
        self.url = "topology/links/json"

    def _process(self, session, now, data):
        for ln in data:
            src = session.query(Node).filter(Node.device_id == ln["src-switch"]).first()
            dst = session.query(Node).filter(Node.device_id == ln["dst-switch"]).first()

            if src is None or dst is None:
                logging.warning("Could not find Switch [%s] or Switch [%s]. This should only happen occasionally." % (
                    ln["src-switch"], ln["dst-switch"]))
                continue

            JsonQuery._create_update_link(session, now, src, ln["src-port"], dst, ln["dst-port"], ln["type"],
                                          ln["direction"], now)


class DelayQuery(JsonQuery):
    def __init__(self, poll_interval, **kwargs):
        JsonQuery.__init__(self, poll_interval, **kwargs)
        self.url = "uds/delay/json"

    def _process(self, session, now, data):
        links = session.query(LinkSample).filter(LinkSample.sampled == now).all()

        if "code" in data and data["code"] == 404:
            return

        for delaySample in data:
            if not delaySample["inconsistency"] and delaySample["srcCtrlDelay"] is not None and delaySample["dstCtrlDelay"] is not None:
                delay = delaySample["fullDelay"] - 0.5 * (delaySample["srcCtrlDelay"] + delaySample["dstCtrlDelay"])

                src_port = int(delaySample["srcPort"])
                src_links = filter(lambda x: x.link.src.device_id == delaySample["srcDpid"] and x.link.src_port == src_port, links)
                for l in src_links:
                    l.src_delay = delay

                dst_port = int(delaySample["dstPort"])
                dst_links = filter(lambda x: x.link.dst.device_id == delaySample["dstDpid"] and x.link.dst_port == dst_port, links)
                for l in dst_links:
                    l.dst_delay = delay

