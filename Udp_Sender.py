import socket
import threading
import struct
import math
import time
import sys

class Udp_Sender(threading.Thread):

	def __init__(self, fd):
		threading.Thread.__init__(self)
		self.MULTICAST_GROUP ='224.0.0.1'
		self.MULTICAST_PORT = 50066
		self.REFRESH_RATE = 1
		self.INVALDATA = 0x7FFFFFFF
		self.MAGIC_ID = 0xFDFD
		self.DATA_PACKET_TYPE = 0x10
		self.fd=fd
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		# Udp_Sender
		self.DATA_FULL_FORMAT ='>HH' + ('i'*32) + 'iii' + '5s' + ('i'*7)
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
		except:
			return "0.0.0.0"
	
	def send_data_packet(self):

		flight_data=self.fd.get_Packet()
    
		pack_args = [self.MAGIC_ID, self.DATA_PACKET_TYPE] 
		pack_args.extend(flight_data)
	

		packet = struct.pack(self.DATA_FULL_FORMAT, *pack_args)
	
		if len(packet) != self.EXPECTED_PACKET_SIZE:
			raise RuntimeError(f"Packet size mismatch! Expected {self.EXPECTED_PACKET_SIZE} bytes, got {len(packet)} bytes.")

		self.sock.sendto(packet, (self.MULTICAST_GROUP, self.MULTICAST_PORT))

	def get_ip(self):
		return self.MULTICAST_GROUP
		
	def get_port(self):
		return self.MULTICAST_PORT
