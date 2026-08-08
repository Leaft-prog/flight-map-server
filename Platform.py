import socket
import struct
import time
import threading


class Platform(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.MULTICAST_IP = "239.1.40.1"
		self.PORT = 50061 
		self.MAGIC_DATAGRAM_ID = 0xDECE  # 0xdece
		self.PACKET_TYPE = 0x0010  # 0x10
		self.PLATFORM_VERSION = 1  # Must be < 7
		self.SERVICE_STRING = """<root purchased="true">
					<flight_data fd_ip="224.0.0.1" fd_port="50066" trk_line_ip="192.168.1.50" trk_line_port="50062" aircraft="Boeing 777"/>
					<asxi_config>
						<symbols aircraft_type="Boeing 777"/>
					</asxi_config>
					</root>"""

	def create_discovery_packet(self, platform_version: int, service_name: str) -> bytes:
			"""Constructs the packet using network byte order (Big-Endian)

				with a length-prefixed string matching BinaryReader::ReadString expectations.
			"""
			# 1. Header: Magic ID (2 bytes), Packet Type (2 bytes), Version (2 bytes)
			header = struct.pack(
			">HHH", self.MAGIC_DATAGRAM_ID, self.PACKET_TYPE, self.PLATFORM_VERSION
			)

			# 2. String Payload: Length-prefixed (32-bit big-endian integer length + string bytes)
			name_bytes = self.SERVICE_STRING.encode("utf-8")
			# Note: The serialize code showed length calculation + 1 or similar,
			# but standard BinaryReader string format uses a 4-byte big-endian length prefix.
			string_length = len(name_bytes)
			string_block = struct.pack(">I", string_length) + name_bytes

			return header + string_block

	def run(self):
		self.send_discovery_broadcast()

	def send_discovery_broadcast(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("b", 1))

		# Optional: Bind to your local interface IP if running on a multi-homed machine (e.g., '192.168.56.1')
		# sock.bind(('0.0.0.0', 0))

		packet_data = self.create_discovery_packet(self.PLATFORM_VERSION, self.SERVICE_STRING)

		while True:
			sock.sendto(packet_data, (self.MULTICAST_IP, self.PORT))
			time.sleep(2)

	def get_ip(self):
		return self.MULTICAST_IP
		
	def get_port(self):
		return self.PORT
