import sys
import math
import csv
import struct

class Airport_Loader:
	def __init__(self, dpt_code, dst_code, switch):
		self.AIRPORT_DATA_FILE = "tbairportinfo.csv"
		self.INVALDATA = 0x7FFFFFFF
		self.scale = 3600.0
		self.switch=switch
		if(self.switch=='iata'):
			self.dpt_IATA=dpt_code
			self.dst_IATA=dst_code
		else:
			self.dpt_IATA=self.INVALDATA
			self.dst_IATA=self.INVALDATA
            
		if(self.switch=='icao'):
			self.dpt_ICAO=dpt_code
			self.dst_ICAO=dst_code
		else:
			self.dpt_ICAO=self.INVALDATA
			self.dst_ICAO=self.INVALDATA
		self.dpt_LAT=self.INVALDATA
		self.dpt_LON=self.INVALDATA
		self.dst_LAT=self.INVALDATA
		self.dst_LON=self.INVALDATA
		self.dpt_GEOID=self.INVALDATA
		self.dst_GEOID=self.INVALDATA

		try:
			with open(self.AIRPORT_DATA_FILE, newline='') as f:
				reader = csv.DictReader(f)
				required_fields = ['FourLetId', 'ThreeLetId', 'Lat', 'Lon', 'PointGeoRefId']
                
				if not all(field in reader.fieldnames for field in required_fields):
					print(f"FATAL ERROR: CSV file '{self.AIRPORT_DATA_FILE}' is missing required headers: {required_fields}")
                 
				for row in reader:
					if switch=='iata' and row['ThreeLetId'].upper() == self.dpt_IATA:
						self.dpt_ICAO = row['FourLetId'].upper()
						geoID_str = row['PointGeoRefId'].strip()
                        
						if geoID_str and geoID_str.upper() not in ('NULL', 'N/A', 'NONE'):
							try:
								self.dpt_GEOID = int(geoID_str)
							except ValueError:
								print("ERROR loading airport values")
                        
						try:
							self.dpt_LAT = float(row['Lat'])
							self.dpt_LON = float(row['Lon'])
						except ValueError:
							print("ERROR loading airport values")

					if switch=='iata' and row['ThreeLetId'].upper() == self.dst_IATA:
						self.dst_ICAO = row['FourLetId'].upper()
						geoID_str = row['PointGeoRefId'].strip()
                        
						if geoID_str and geoID_str.upper() not in ('NULL', 'N/A', 'NONE'):
							try:
								self.dst_GEOID = int(geoID_str)
							except ValueError:
								print("ERROR loading airport values")
                        
						try:
							self.dst_LAT = float(row['Lat'])
							self.dst_LON = float(row['Lon'])
						except ValueError:
							print("ERROR loading airport values")
                            
                            
                            
					if switch=='icao' and row['FourLetId'].upper() == self.dpt_ICAO:
						self.dpt_IATA = row['ThreeLetId'].upper()
						geoID_str = row['PointGeoRefId'].strip()
                        
						if geoID_str and geoID_str.upper() not in ('NULL', 'N/A', 'NONE'):
							try:
								self.dpt_GEOID = int(geoID_str)
							except ValueError:
								print("ERROR loading airport values")
                        
						try:
							self.dpt_LAT = float(row['Lat'])
							self.dpt_LON = float(row['Lon'])
						except ValueError:
							print("ERROR loading airport values")

					if switch=='icao' and row['FourLetId'].upper() == self.dst_ICAO:
						self.dst_IATA = row['ThreeLetId'].upper()
						geoID_str = row['PointGeoRefId'].strip()
                        
						if geoID_str and geoID_str.upper() not in ('NULL', 'N/A', 'NONE'):
							try:
								self.dst_GEOID = int(geoID_str)
							except ValueError:
								print("ERROR loading airport values")
                        
						try:
							self.dst_LAT = float(row['Lat'])
							self.dst_LON = float(row['Lon'])
						except ValueError:
							print("ERROR loading airport values")

		except FileNotFoundError:
			print(f"Error: {self.AIRPORT_DATA_FILE} not found. Cannot load airport data.")
		


	def encode_airport(self,code):
		if isinstance(code, int):
			return code
		s = code.strip().upper().ljust(4, ' ')[:4]
		return struct.unpack('<I', s.encode('ascii'))[0]
		
	def get_dpt_IATA(self):
		if(self.dpt_IATA is not self.INVALDATA):
			return self.encode_airport(self.dpt_IATA)
		else:
			return self.INVALDATA
		
	def get_dst_IATA(self):
		if(self.dpt_IATA is not self.INVALDATA):
			return self.encode_airport(self.dst_IATA)
		else:
			return self.INVALDATA
		
	def get_dpt_ICAO(self):
		if(self.dpt_IATA is not self.INVALDATA):
			return self.encode_airport(self.dpt_ICAO)
		else:
			return self.INVALDATA
		
	def get_dst_ICAO(self):
		if(self.dpt_IATA is not self.INVALDATA):
			return self.encode_airport(self.dst_ICAO)
		else:
			return self.INVALDATA
	
	def get_dpt_LAT(self):
		return self.dpt_LAT
	
	def get_dpt_LON(self):
		return self.dpt_LON
	
	def get_dst_LAT(self):
		return self.dst_LAT
	
	def get_dst_LON(self):
		return self.dst_LON
		
	def get_dpt_GEOID(self):
		return int(self.dpt_GEOID)
	
	def get_dst_GEOID(self):
		return int(self.dst_GEOID)

	def validity(self):
		return all([

				self.dpt_ICAO!=self.INVALDATA,
				self.dst_ICAO!=self.INVALDATA,
				self.dpt_LAT!=self.INVALDATA,
				self.dpt_LON!=self.INVALDATA,
				self.dst_LAT!=self.INVALDATA,
				self.dst_LON!=self.INVALDATA,
				self.dpt_GEOID!=self.INVALDATA,
				self.dst_GEOID!=self.INVALDATA
		])
