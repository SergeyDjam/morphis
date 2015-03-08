import llog

import asyncio
import logging
import os

import packet as mnetpacket
import rsakey
import mn1
from mutil import hex_dump
import chord
import peer
import enc

log = logging.getLogger(__name__)

class Peer():
    def __init__(self, engine):
        self.engine = engine

        self.dbid = None

        self.protocol_handler = None

        self.node_key = None
        self.node_id = None
        self.channel_handler = ChannelHandler(self)
        self.connection_handler = ConnectionHandler(self)

    def get_protocol_handler(self):
        return self.protocol_handler

    def set_protocol_handler(self, value):
        self.protocol_handler = value

        self.protocol_handler.set_channel_handler(self.channel_handler)
        self.protocol_handler.set_connection_handler(self.connection_handler)

    def _peer_authenticated(self, key):
        self.node_key = key
        self.node_id = enc.generate_ID(self.node_key.asbytes())

class ConnectionHandler():
    def __init__(self, peer):
        self.peer = peer

    def connection_made(self, protocol):
        self.peer.engine.connection_made(self.peer)

    def error_recieved(self, protocol, exc):
        pass

    def connection_lost(self, protocol, exc):
        self.peer.engine.connection_lost(self.peer, exc)

    def peer_authenticated(self, protocol):
        if protocol.server_mode:
            self.peer._peer_authenticated(self.peer.protocol_handler.client_key)
        else:
            self.peer._peer_authenticated(self.peer.protocol_handler.server_key)

        return self.peer.engine.peer_authenticated(self.peer)

class ChannelHandler():
    def __init__(self, peer):
        self.peer = peer

    @asyncio.coroutine
    def open_channel(self, protocol, packet):
        m = mnetpacket.SshChannelOpenMessage(packet)
        log.info("S: Received CHANNEL_OPEN: channel_type=[{}], sender_channel=[{}].".format(m.get_channel_type(), m.get_sender_channel()))

        cm = mnetpacket.SshChannelOpenConfirmationMessage()
        cm.set_recipient_channel(m.get_sender_channel())
        cm.set_sender_channel(0)
        cm.set_initial_window_size(65535)
        cm.set_maximum_packet_size(65535)

        cm.encode()

        protocol.write_packet(cm)

    @asyncio.coroutine
    def data(self, protocol, packet):
        m = mnetpacket.SshChannelDataMessage(packet)
        if log.isEnabledFor(logging.DEBUG):
            log.debug("Received data, recipient_channel=[{}], value=[\n{}].".format(m.get_recipient_channel(), hex_dump(m.get_data())))
