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
from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey, Float, Numeric, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, relationship

connection_string = ""
Base = declarative_base()


class SampleTimestamp(Base):
    __tablename__ = "sample_timestamp"
    id = Column(Integer, primary_key=True)  # auto increment identifier
    timestamp = Column(DateTime(timezone=False))
    interval = Column(Numeric)


internet_address_association = Table("internet_address_association", Base.metadata,
                                   Column("node_id", Integer, ForeignKey("node.id")),
                                   Column("address_id", Integer, ForeignKey("internet_address.id")))


class Node(Base):
    __tablename__ = "node"
    id = Column(Integer, primary_key=True)  # auto increment identifier
    device_id = Column(String(23), nullable=False, unique=True)  # Data path: 00:00:00:00:00:00:00:00

    # datetime information
    created = Column(DateTime(timezone=False))
    last_seen = Column(DateTime(timezone=False))
    type = Column(String(50))

    connected_since = Column(DateTime(timezone=False))

    ports = relationship("Port")
    addresses = relationship("InternetAddress", secondary=internet_address_association, backref="nodes")

    samples = relationship("NodeSample", backref="node")

    # Compare logic http://regebro.wordpress.com/2010/12/13/python-implementing-rich-comparison-the-correct-way/
    def _compare(self, other, method):
        return method(self.device_id, other.device_id)

    def __lt__(self, other):
        return self._compare(other, lambda s, o: s < o)

    def __le__(self, other):
        return self._compare(other, lambda s, o: s <= o)

    def __eq__(self, other):
        return self._compare(other, lambda s, o: s == o)

    def __ge__(self, other):
        return self._compare(other, lambda s, o: s >= o)

    def __gt__(self, other):
        return self._compare(other, lambda s, o: s > o)

    def __ne__(self, other):
        return self._compare(other, lambda s, o: s != o)


class NodeSample(Base):
    __tablename__ = "node_sample"
    id = Column(Integer, primary_key=True)  # auto increment identifier

    sampled = Column(DateTime(timezone=False))

    closeness = Column(Float)
    betweenness = Column(Float)
    degree = Column(Integer)

    node_id = Column(Integer, ForeignKey("node.id"))


class InternetAddress(Base):
    __tablename__ = "internet_address"
    id = Column(Integer, primary_key=True)  # auto increment identifier

    created = Column(DateTime(timezone=False))
    address = Column(String(50))


class Flow(Base):
    __tablename__ = "flow"
    id = Column(Integer, primary_key=True)  # auto increment identifier

    created = Column(DateTime(timezone=False))

    cookie = Column(Numeric)

    data_layer_destination = Column(String(17))
    data_layer_source = Column(String(17))
    data_layer_type = Column(Integer)
    data_layer_virtual_lan = Column(Numeric)
    data_layer_virtual_lan_priority_code_point = Column(Numeric)
    input_port = Column(Numeric)
    network_destination = Column(String(15))
    network_destination_mask_len = Column(Integer)
    network_protocol = Column(Integer)
    network_source = Column(String(15))
    network_source_mask_len = Column(Integer)
    network_type_of_service = Column(Integer)
    transport_destination = Column(Numeric)
    transport_source = Column(Numeric)
    wildcards = Column(Numeric)

    node_id = Column(Integer, ForeignKey("node.id"))
    node = relationship(Node)

    samples = relationship("FlowSample", backref="flow")


class FlowSample(Base):
    __tablename__ = "flow_sample"
    id = Column(Integer, primary_key=True)  # auto increment identifier

    sampled = Column(DateTime(timezone=False))

    packet_count = Column(Integer)
    byte_count = Column(Integer)
    duration_seconds = Column(Integer)
    priority = Column(Numeric)
    idle_timeout_sec = Column(Numeric)
    hard_timeout_sec = Column(Numeric)

    flow_id = Column(Integer, ForeignKey("flow.id"))


class Link(Base):
    __tablename__ = "link"
    id = Column(Integer, primary_key=True)  # auto increment identifier

    # datetime information
    created = Column(DateTime(timezone=False))
    last_seen = Column(DateTime(timezone=False))

    direction = Column(String(50))
    type = Column(String(50))

    # source
    src_id = Column(Integer, ForeignKey("node.id"), nullable=False)
    src_port = Column(Integer)
    src = relationship("Node", foreign_keys=[src_id])

    # destination
    dst_id = Column(Integer, ForeignKey("node.id"), nullable=False)
    dst_port = Column(Integer)
    dst = relationship("Node", foreign_keys=[dst_id])

    samples = relationship("LinkSample")


class LinkSample(Base):
    __tablename__ = "link_sample"
    id = Column(Integer, primary_key=True)  # auto increment identifier

    sampled = Column(DateTime(timezone=False))

    betweenness = Column(Float)

    src_packet_loss = Column(Float)
    dst_packet_loss = Column(Float)

    src_transmit_data_rate = Column(Integer)
    src_receive_data_rate = Column(Integer)
    dst_transmit_data_rate = Column(Integer)
    dst_receive_data_rate = Column(Integer)

    src_delay = Column(Float)
    dst_delay = Column(Float)

    link_id = Column(Integer, ForeignKey("link.id"))
    link = relationship(Link)


class Port(Base):
    __tablename__ = "port"
    id = Column(Integer, primary_key=True)  # auto increment identifier
    hardware_address = Column(String(17), nullable=False)  # MAC: 00:00:00:00:00:00
    port_number = Column(Integer)
    name = Column(String(50))

    # datetime information
    created = Column(DateTime(timezone=False))
    last_seen = Column(DateTime(timezone=False))

    samples = relationship("PortSample")

    node_id = Column(Integer, ForeignKey("node.id"))
    node = relationship(Node)


class PortSample(Base):
    __tablename__ = "port_sample"
    id = Column(Integer, primary_key=True)  # auto increment identifier

    sampled = Column(DateTime(timezone=False))

    receive_packets = Column(Numeric)
    transmit_packets = Column(Numeric)
    receive_bytes = Column(Numeric)
    transmit_bytes = Column(Numeric)
    receive_dropped = Column(Numeric)
    transmit_dropped = Column(Numeric)
    receive_errors = Column(Numeric)
    transmit_errors = Column(Numeric)
    receive_frame_errors = Column(Numeric)
    receive_overrun_errors = Column(Numeric)
    receive_crc_errors = Column(Numeric)
    collisions = Column(Numeric)

    port_id = Column(Integer, ForeignKey("port.id"))
    port = relationship(Port)


class Report(Base):
    __tablename__ = "report"
    id = Column(Integer, primary_key=True)  # auto increment identifier

    created = Column(DateTime(timezone=False))
    type = Column(String(100))

    sample_interval = Column(Numeric)
    sample_start = Column(DateTime(timezone=False))
    sample_stop = Column(DateTime(timezone=False))
    sample_count = Column(Numeric)

    execution_duration = Column(Numeric)

    content = Column(Text)


def get_session():
    engine = create_engine(connection_string)
    Base.metadata.bind = engine
    session = sessionmaker(bind=engine)()
    return session


def start(conn_string):
    global connection_string
    connection_string = conn_string


def init():
    logging.debug("Create store database via ORM.")
    engine = create_engine(connection_string)
    Base.metadata.create_all(engine)


def drop():
    logging.debug("Drop store database via ORM.")
    engine = create_engine(connection_string)
    Base.metadata.drop_all(engine)