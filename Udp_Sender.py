import socket
import threading
import struct
import math
import time
import sys

class Udp_Sender(threading.Thread):

    def __init__(self, fd):
        threading.Thread.__init__(self)
        self.daemon=True
        self.MULTICAST_GROUP = '224.0.0.1' #flight data ip address
        self.MULTICAST_PORT = 50066 #flight data port
        self.REFRESH_RATE = 1
        self.INVALDATA = 0x7FFFFFFF #placeholder value if data is missing (airshow will omit the data safely without crashing)
        
        self.MAGIC_ID = 0xFDFD #flight data datagram id
        self.DATA_PACKET_TYPE = 0x10 #flight data packet type
        
        self.fd = fd
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock_lock = threading.Lock()  # Prevents thread collision on socket write
        
        self.DATA_FULL_FORMAT = '>HH' + ('i'*35) + '5s' + ('i'*7) #Big endian packet
        self.EXPECTED_PACKET_SIZE = struct.calcsize(self.DATA_FULL_FORMAT)

    def run(self): 
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        self.sock.bind((self.get_local_ip(), 0))
        self.cycle()

    def cycle(self):

        while True:
            self.send_data_packet()

          

            time.sleep(self.REFRESH_RATE)

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "0.0.0.0"

    def _send_bytes(self, packet_bytes: bytes):
        """Thread-safe socket transmission method."""
        with self._sock_lock:
            self.sock.sendto(packet_bytes, (self.MULTICAST_GROUP, self.MULTICAST_PORT))

    def send_data_packet(self):
        """Builds and transmits 0x10 Flight Data Packet."""
        flight_data = self.fd.get_Packet()
    
        pack_args = [self.MAGIC_ID, self.DATA_PACKET_TYPE] 
        pack_args.extend(flight_data)

        packet = struct.pack(self.DATA_FULL_FORMAT, *pack_args)
    
        if len(packet) != self.EXPECTED_PACKET_SIZE:
            raise RuntimeError(f"Packet size mismatch! Expected {self.EXPECTED_PACKET_SIZE} bytes, got {len(packet)} bytes.")

        self._send_bytes(packet)


    def get_ip(self):
        return self.MULTICAST_GROUP
        
    def get_port(self):
        return self.MULTICAST_PORT
