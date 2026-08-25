import time
import calendar
from datetime import datetime, timezone, timedelta
import sys
import threading
import math
import struct
import os
import glob
import subprocess
from SimConnect import SimConnect, AircraftRequests
from Airport_Loader import *

class Connector(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)

		self.running = True
		self.INVALDATA = 0x7FFFFFFF
		self.LAT_LON_SCALE_FACTOR = 3600.0
		self.altitude_scaled = self.INVALDATA
		self.altitude = self.INVALDATA
		self.temperature = 5
		self.FPA = 30
		self.prev_altitude = 0.0
		self.vertical_speed = 0.0
		self.ground_speed = self.INVALDATA
		self.head_wind = self.INVALDATA
		self.remaining_time = self.INVALDATA
		self.true_airspeed = self.INVALDATA
		self.mach = self.INVALDATA
		self.total_dist_nm = self.INVALDATA
		self.dist_traveled = self.INVALDATA
		self.distance_to_destination = self.INVALDATA
		self.tailwind = self.INVALDATA
		self.time_since_departure = self.INVALDATA
		self.pitch = self.INVALDATA
		self.roll = self.INVALDATA
		self.estimated_arrival_time = self.INVALDATA
		self.time_enc = self.INVALDATA
		self.vertical_speed = self.INVALDATA
		self.date_enc = self.INVALDATA
		self.heading = self.INVALDATA
		self.current_lat = self.INVALDATA
		self.current_lon = self.INVALDATA
		self.destination_heading= self.INVALDATA
		self.flightnumber = b'NULL0'
		SIM_PROCESSES = ["FlightSimulator.exe", "FlightSimulator2024.exe"]
		islaunched=False
		self.flightnumber_len = len(self.flightnumber)
		self.year=0
		self.month=0
		self.day=0
		self.hours=0
		self.minutes=0
		self.seconds=0
		
		try:
    # Run the Windows 'tasklist' command to list running processes
			output=subprocess.check_output("tasklist", shell=True).decode('utf-8', errors='ignore')
			for process in SIM_PROCESSES:
				if process in output:
					islaunched = True
					break
		except Exception as e:
			print(f"Error checking processes: {e}")
			

		if not islaunched:
			print("MSFS process not found. Exiting.")
			sys.exit(1)
			

		# Initialize SimConnect connection
		try:
			self.sm = SimConnect()
			self.aq = AircraftRequests(self.sm, _time=0)
		except Exception as e:
			print(f"Failed to connect to SimConnect: {e}")
			sys.exit()
			self.sm = None
			self.aq = None

		# Parse ICAOs from the active MSFS .pln file
		self.dpt_ICAO_str = None
		self.dst_ICAO_str = None
		try:
			base_path = os.path.expanduser(r"~\AppData\Local\Packages\Microsoft.FlightSimulator_*\\LocalState")
			search_paths = glob.glob(base_path)
			if search_paths:
				pln_files = glob.glob(os.path.join(search_paths[0], "**", "*.pln"), recursive=True)
				flt_files = glob.glob(os.path.join(search_paths[0], "**", "*.flt"), recursive=True)
				if pln_files:
					latest_pln = max(pln_files, key=os.path.getmtime)
					
					with open(latest_pln, 'r', encoding='utf-8', errors='ignore') as f:
						for line in f:
							if "<DepartureID>" in line:
								icao_str = line.replace("<DepartureID>", "").replace("</DepartureID>", "").strip()
								if icao_str:
									self.dpt_ICAO_str = icao_str
							elif "<DestinationID>" in line:
								icao_str = line.replace("<DestinationID>", "").replace("</DestinationID>", "").strip()
								if icao_str:
									self.dst_ICAO_str = icao_str
				else:
					print("pln files not found")
				if flt_files:
					latest_flt = max(flt_files, key=os.path.getmtime)
					in_datetime_season = False
					with open(latest_flt, 'r', encoding='utf-8', errors='ignore') as f:
						for line in f:
							line_stripped = line.strip()
							
							# Global scan for FlightNumber anywhere in the file
							if line_stripped.startswith("FlightNumber="):
								fn_val = line_stripped.replace("FlightNumber=", "").strip()
								if fn_val and len(fn_val)==5:
									self.flightnumber = fn_val.encode('utf-8')
									self.flightnumber_len = len(self.flightnumber)

							if line_stripped.startswith("[DateTimeSeason]"):
								in_datetime_season = True
								continue
							elif line_stripped.startswith("["):
								in_datetime_season = False
							
							if in_datetime_season:
								if "Year=" in line_stripped:
									self.year = line_stripped.replace("Year=", "").strip()
								elif "Day=" in line_stripped:
									self.day = line_stripped.replace("Day=", "").strip()
								elif "Hours=" in line_stripped:
									self.hours = line_stripped.replace("Hours=", "").strip()
								elif "Minutes=" in line_stripped:
									self.minutes = line_stripped.replace("Minutes=", "").strip()
								elif "Seconds=" in line_stripped:
									self.seconds = line_stripped.replace("Seconds=", "").strip()
				else:
					print("flt files not found")

		except Exception:
			print("issue loading the files")
			pass

		dpt_arg = self.dpt_ICAO_str if self.dpt_ICAO_str else self.INVALDATA
		dst_arg = self.dst_ICAO_str if self.dst_ICAO_str else self.INVALDATA

		self.airports = Airport_Loader(dpt_arg, dst_arg, 'icao')

		self.dpt_ICAO =  self.airports.get_dpt_ICAO()
		
		self.dst_ICAO =  self.airports.get_dst_ICAO()

		
		# Fallback/Static airport variables from loader
		self.dpt_LAT = self.airports.get_dpt_LAT()
		self.dpt_LON = self.airports.get_dpt_LON()
		self.dpt_IATA = self.airports.get_dpt_IATA()
		self.dpt_GEOID = self.airports.get_dpt_GEOID()
		self.dst_LAT = self.airports.get_dst_LAT()
		self.dst_LON = self.airports.get_dst_LON()
		self.dst_IATA = self.airports.get_dst_IATA()
		self.dst_GEOID = self.airports.get_dst_GEOID()
		self.destination_heading= self.compute_heading(self.current_lat, self.current_lon, self.dst_LAT, self.dst_LON)



		# State variables initialized
		self.current_phase = 1
		self.acars_phase_id = 1
		self.miqat_phase = 1
		self.profile_mode = 1
		self.end_of_flight = 0
		self.elapsed = 0
		self.start_time = datetime.now(timezone.utc)
		self.time_init = time.time()
		

	def run(self):
		self.time_init = time.time()
		self.ciclo()
	
	def ciclo(self):
		while self.running:
			if not self.aq:
				time.sleep(1)
				continue



			# --- Pull Variables from SimConnect ---
			self.current_lat = self.aq.get("PLANE_LATITUDE") or 0.0
			self.current_lon = self.aq.get("PLANE_LONGITUDE") or 0.0
			self.altitude = self.aq.get("PLANE_ALTITUDE") or 0.0  # Feet
			self.altitude_scaled = int(self.altitude * 100)
			
			self.ground_speed = int(self.aq.get("GROUND_VELOCITY") or 0.0) # Knots
			self.true_airspeed = self.aq.get("AIRSPEED_TRUE") or 0.0
			self.mach = int((self.aq.get("AIRSPEED_MACH") or 0.0) * 1000)

			
			heading_val = self.aq.get("PLANE_HEADING_DEGREES_TRUE")
			if heading_val is not None:
				self.heading = int(math.degrees(heading_val))
			else:
				self.heading = 0

			self.vertical_speed = self.aq.get("VERTICAL_SPEED") or 0.0 # Ft/min
			self.vertical_speed_scaled = int(self.vertical_speed * 100)
			
			pitch_val = self.aq.get("PLANE_PITCH_DEGREES")
			self.pitch = int(math.degrees(pitch_val*-1)) if pitch_val is not None else 0.0
			
			roll_val = self.aq.get("PLANE_BANK_DEGREES")
			self.roll = int(math.degrees(roll_val*-1)) if roll_val is not None else 0.0
			
			self.temperature = self.aq.get("AMBIENT_TEMPERATURE") or 15.0 # Celsius
			self.head_wind = int(self.aq.get("AMBIENT_WIND_DIRECTION") or 0) # Simplified handling
			self.tailwind = int(self.aq.get("AMBIENT_WIND_VELOCITY") or 0)
			
			# Distances & Navigation (Check valid airport coordinates before calculation)
			if self.dpt_LAT != self.INVALDATA and self.dst_LAT != self.INVALDATA and self.dpt_LAT is not None and self.dst_LAT is not None:
				self.total_dist_nm = self.haversine_distance(self.dpt_LAT, self.dpt_LON, self.dst_LAT, self.dst_LON)
				self.dist_traveled = self.haversine_distance(self.dpt_LAT, self.dpt_LON, self.current_lat, self.current_lon)
				self.distance_to_destination = max(int(self.total_dist_nm - self.dist_traveled), 0)
			else:
				self.total_dist_nm = 0.0
				self.dist_traveled = 0.0
				self.distance_to_destination = 0

			# Flight Phase Logic (Example based on altitude/speed)
			if self.altitude < 100 and self.ground_speed < 40 and self.dist_traveled < 100:
				self.current_phase = 1  # Preflight / Taxi
			elif self.ground_speed >= 40 and self.altitude < 1000:
				self.current_phase = 2  # Takeoff
			elif self.vertical_speed > 300:
				self.current_phase = 3  # Climb
			elif abs(self.vertical_speed) <= 300 and self.altitude > 10000:
				self.current_phase = 4  # Cruise
			elif self.vertical_speed < -300 and self.altitude > 3000:
				self.current_phase = 5  # Descent
			elif self.altitude <= 3000 and self.altitude > 200:
				self.current_phase = 6  # Approach
			elif self.altitude <= 200:
				self.current_phase = 7  # Landing

			try:
				sim_year = int(self.year) if self.year else 2026
				sim_day = int(self.day) if self.day else 1
				sim_hours = int(self.hours) if self.hours else 0
				sim_minutes = int(self.minutes) if self.minutes else 0
				sim_seconds = float(self.seconds) if self.seconds else 0.0
			except (ValueError, TypeError):
				sim_year, sim_day, sim_hours, sim_minutes, sim_seconds = 2026, 1, 0, 0, 0.0

			base_date = datetime(sim_year, 1, 1, tzinfo=timezone.utc) + timedelta(days=sim_day - 1)
			start_seconds = sim_hours * 3600 + sim_minutes * 60 + int(sim_seconds)
			
			elapsed_real = time.time() - self.time_init
			total_sim_seconds = (start_seconds + int(elapsed_real)) % 86400
			
			self.time_enc = total_sim_seconds
			date_packed = struct.pack('>HBB', base_date.year, base_date.month, base_date.day)
			self.date_enc = struct.unpack('>I', date_packed)[0]
			
			self.elapsed = int(elapsed_real)

			if self.dist_traveled > 0 and self.ground_speed > 5:
				calculated_time_min = (self.dist_traveled / self.ground_speed) * 60
				self.time_since_departure = int(calculated_time_min)
			else:
				self.time_since_departure = 0

			effective_speed = self.ground_speed if self.ground_speed > 20 else 450
			self.remaining_time = int((self.distance_to_destination / effective_speed) * 60) if self.distance_to_destination > 0 else 0
			
			current_total_minutes = (self.time_enc // 60)
			self.estimated_arrival_time = (current_total_minutes + self.remaining_time) % 1440
			
			time.sleep(0.5)

	def haversine_distance(self, lat1, lon1, lat2, lon2):
		R = 6371 # Earth radius in km
		dlat = math.radians(lat2 - lat1)
		dlon = math.radians(lon2 - lon1)
		a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
		c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
		return R * c * 0.539957  # Nautical miles
	
	def compute_heading(self,lat1, lon1, lat2, lon2):
		lat1_rad = math.radians(lat1)
		lat2_rad = math.radians(lat2)
		dlon_rad = math.radians(lon2 - lon1)
		x = math.sin(dlon_rad) * math.cos(lat2_rad)
		y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
		return int((math.degrees(math.atan2(x, y)) + 360) % 360)


	# Getter methods remain unchanged to preserve compatibility with get_Packet()
	def get_LatLon(self, par):
		if par == "lat":
			return int(self.current_lat * self.LAT_LON_SCALE_FACTOR) if self.current_lat != self.INVALDATA else 0
		elif par == "lon":
			return int(self.current_lon * self.LAT_LON_SCALE_FACTOR) if self.current_lon != self.INVALDATA else 0

	def get_Altitude(self, scaled):
		if(scaled==True):
			return int(self.altitude_scaled) if self.altitude_scaled != self.INVALDATA else 0
		else:
			return int(self.altitude) if self.altitude != self.INVALDATA else 0
         
	def get_GroundSpeed(self):
		return int(self.ground_speed) if self.ground_speed != self.INVALDATA else 0
	
	def get_dptIATA(self):
		return int(self.dpt_IATA) if isinstance(self.dpt_IATA, (int, float)) and self.dpt_IATA != self.INVALDATA else 0
	def get_dstIATA(self):
		return int(self.dst_IATA) if isinstance(self.dst_IATA, (int, float)) and self.dst_IATA != self.INVALDATA else 0
		
	def get_dpt_ICAO(self):
		return self.dpt_ICAO
	def get_dst_ICAO(self):
		return self.dst_ICAO
	
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

	def get_Headwind(self):
		return int(self.head_wind) if self.head_wind != self.INVALDATA else 0

	def get_Phase(self):
		return self.current_phase
		
	def get_Elapsed(self):
		return int(self.elapsed)
		
	def get_Phase_str(self):
		if(self.current_phase==1):
			return "Preflight"
		elif(self.current_phase==2):
			return "Takeoff"
		elif(self.current_phase==3):
			return "Climb"
		elif(self.current_phase==4):
			return "Cruise"
		elif(self.current_phase==5):
			return "Descent"
		elif(self.current_phase==6):
			return "Approach"
		elif(self.current_phase==7):
			return "Landing"
		elif(self.current_phase==8):
			return "Postflight/taxi"
		else:
			return "UNDEFINED"
			

	def get_RemainingTime(self):
		return int(self.remaining_time) if self.remaining_time != self.INVALDATA else 0

	def get_EstimatedArrivalTime(self):
		return int(self.estimated_arrival_time) if self.estimated_arrival_time != self.INVALDATA else 0

	def get_VerticalSpeed(self, scaled):
		if(scaled==False):
			return int(self.vertical_speed) if self.vertical_speed != self.INVALDATA else 0
		else:
			return int(self.vertical_speed_scaled) if self.vertical_speed_scaled != self.INVALDATA else 0

	def get_Tailwind(self):
		return int(self.tailwind) if self.tailwind != self.INVALDATA else 0

	def get_TrueAirspeed(self):
		return int(self.true_airspeed) if self.true_airspeed != self.INVALDATA else 0

	def get_TotalDist(self):
		return int(self.total_dist_nm) if self.total_dist_nm != self.INVALDATA else 0

	def get_DistTraveled(self):
		return int(self.dist_traveled * 100) if self.dist_traveled != self.INVALDATA else 0

	def get_DistanceToDestination(self):
		return int(self.distance_to_destination) if self.distance_to_destination != self.INVALDATA else 0

	def get_Pitch(self):
		return int(self.pitch) if self.pitch != self.INVALDATA else 0

	def get_Roll(self):
		return int(self.roll) if self.roll != self.INVALDATA else 0

	def get_Date(self):
		return int(self.date_enc) if self.date_enc != self.INVALDATA else 0

	def get_Time(self):
		return int(self.time_enc) if self.time_enc != self.INVALDATA else 0

	def get_End_Of_Flight(self):
		return int(self.end_of_flight)

	def get_Temperature(self):
		return int(self.temperature) if self.temperature != self.INVALDATA else 0

	def get_Mach(self):
		return int(self.mach) if self.mach != self.INVALDATA else 0
		
	def get_Flightnumber(self):
		return self.flightnumber
	def get_Flightnumber_Len(self):
		return self.flightnumber_len

	def get_Heading(self):
		return int(self.heading) if self.heading != self.INVALDATA else 0

	def get_HeadingToDestination(self):
		return int(self.destination_heading) if self.heading != self.INVALDATA else 0

	def get_FPA(self):
		return int(self.FPA) if self.FPA != self.INVALDATA and self.FPA is not None else 0

	def get_MiqatPhase(self):
		return self.miqat_phase

	def get_AcarsPhase(self):
		return self.acars_phase_id

	def get_ProfileMode(self):
		return self.profile_mode
		
	def get_TimeSinceDeparture(self):
		return self.time_since_departure
		
	def get_Packet(self):
		def safe_int(val):
			try:
				i_val = int(val)
				if i_val > 2147483647 or i_val < -2147483648:
					return 0
				return i_val
			except Exception:
				return 0

		packet = [
			1,
			safe_int(self.get_LatLon("lat")),
			safe_int(self.get_LatLon("lon")),
			safe_int(self.ground_speed),
			safe_int(self.true_airspeed),
			safe_int(self.FPA),
			safe_int(self.head_wind),
			safe_int(self.distance_to_destination),
			safe_int(self.dist_traveled),
			safe_int(self.altitude),
			safe_int(self.temperature),
			safe_int(self.remaining_time),
			safe_int(self.time_since_departure),
			safe_int(self.heading),
			safe_int(self.destination_heading),
			safe_int(self.tailwind),
			safe_int(self.estimated_arrival_time),
			safe_int(self.mach),
			safe_int(self.dist_traveled * 100 if self.dist_traveled != self.INVALDATA else 0),
			safe_int(self.time_enc),
			safe_int(self.date_enc),
			safe_int(self.dpt_LAT * self.LAT_LON_SCALE_FACTOR if self.dpt_LAT != self.INVALDATA and self.dpt_LAT is not None else 0),
			safe_int(self.dpt_LON * self.LAT_LON_SCALE_FACTOR if self.dpt_LON != self.INVALDATA and self.dpt_LON is not None else 0),
			safe_int(self.dpt_IATA),
			safe_int(self.dpt_ICAO),
			safe_int(self.dpt_GEOID),
			safe_int(self.dst_LAT * self.LAT_LON_SCALE_FACTOR if self.dst_LAT != self.INVALDATA and self.dst_LAT is not None else 0),
			safe_int(self.dst_LON * self.LAT_LON_SCALE_FACTOR if self.dst_LON != self.INVALDATA and self.dst_LON is not None else 0),
			safe_int(self.dst_IATA),
			safe_int(self.dst_ICAO),
			safe_int(self.dst_GEOID),
			safe_int(self.current_phase),
			safe_int(self.acars_phase_id),
			safe_int(self.miqat_phase),
			safe_int(self.flightnumber_len),
			self.flightnumber,
			0,
			safe_int(self.end_of_flight),
			safe_int(self.profile_mode),
			safe_int(self.altitude_scaled),
			safe_int(self.vertical_speed),
			safe_int(self.pitch),
			safe_int(self.roll),
		]
		return packet
