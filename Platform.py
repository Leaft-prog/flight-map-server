import socket
import struct
import time
import threading
import urllib.parse
import xml.etree.ElementTree as ET


class Platform(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.daemon=True
		self.REFRESH_RATE=1
		self.MULTICAST_IP = "239.1.40.1"
		self.PORT = 50061 
		self.HOST_IP=self.get_active_ip() 
		self.MAGIC_DATAGRAM_ID = 0xDECE  #platform datagram id
		self.PACKET_TYPE = 0x0010 #platform packet type
		self.PLATFORM_VERSION = 1  # Must be < 7
		#Airshow platform ip addresses (this will not affect the experience, change only if it is already used in your network)
		#"239.1.40.1"  port="50061" platforms="1,4,5,6" for Venue-HDAV/CES/AS 500/ICS
		#"239.1.40.1"  port="50041" platforms="3" for AS 4xxx
		#"225.224.0.3" port="5000" platforms="2" for Venue-MCD
		#Airshow before starting it will lookup in one of those ip addresses, flight data ip address and aircraft type can be overrided
		#If config version is increased airshow will redownload the config.zip, clearing airshow cache will delete the downloaded config and return config version to 0
		#Purchased flag must be true otherwise it will refuse the service string or download configs, in iOS it will reject flight data completely if an incorrect service string is served
		self.DEFAULT_SERVICE_STRING = """<root purchased="true">
					<flight_data fd_ip="224.0.0.1" fd_port="50066" trk_line_ip="192.168.1.50" trk_line_port="50062"/>
					<asxi_config>
						<symbols aircraft_type="eGeneric"/>
					</asxi_config>
					<config url="http://0.0.0.0/config" version="2.1.0"/>
					</root>"""
		self.service_filename="service.xml"
		#try opening service.xml otherwise use hardcoded default service string
		try:
			with open(self.service_filename, "r", encoding="utf-8") as service_file:
				self.SERVICE_STRING = service_file.read()
		except FileNotFoundError:
			print("ERROR loading platform config, serving default one")
			self.SERVICE_STRING = self.DEFAULT_SERVICE_STRING
		
		#Override config url to link host ip address
		self.SERVICE_STRING=self.update_config_ip(self.SERVICE_STRING, self.HOST_IP) 
		
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
	
	@staticmethod
	def get_active_ip():
		"""Finds the active local network IP address of the machine dynamically."""
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		try:
		# Connects to a non-reachable address to determine the outgoing network interface IP
			s.connect(("10.255.255.255", 1))
			ip = s.getsockname()[0]
		except Exception:
			ip = "127.0.0.1"
		finally:
			s.close()
		return ip
	
	@staticmethod
	def update_config_ip(xml_string: str, new_ip: str) -> str:
		"""Updates the IP address in the config tag's URL attribute."""
		root = ET.fromstring(xml_string)

		# Find the config element
		config_elem = root.find("config")
		if config_elem is not None and "url" in config_elem.attrib:
			# Parse current URL to isolate and replace the host IP
			parsed_url = urllib.parse.urlparse(config_elem.attrib["url"])

			# Rebuild URL with new netloc while preserving scheme and path
			new_url = urllib.parse.urlunparse(
				parsed_url._replace(netloc=new_ip)
			)
			config_elem.attrib["url"] = new_url

		# Convert XML tree back to string
		return ET.tostring(root, encoding="unicode")

	def send_discovery_broadcast(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("b", 1))

		# Optional: Bind to your local interface IP if running on a multi-homed machine (e.g., '192.168.56.1')
		# sock.bind(('0.0.0.0', 0))

		packet_data = self.create_discovery_packet(self.PLATFORM_VERSION, self.SERVICE_STRING)

		while True:
			sock.sendto(packet_data, (self.MULTICAST_IP, self.PORT))
			time.sleep(self.REFRESH_RATE)
	
	
	def get_ip(self):
		return self.MULTICAST_IP
		
	def get_port(self):
		return self.PORT
		
	def get_platform_version(self):
		return self.PLATFORM_VERSION

	def get_service_string(self):
		return self.SERVICE_STRING
