import time
import calendar
from datetime import datetime, timezone, timedelta
import sys
import threading
import math
import struct
from Airport_Loader import *

class Simulator(threading.Thread):
	def __init__(self, airports, TOTAL_FLIGHT_SECONDS):
		threading.Thread.__init__(self)

		self.running=True
		self.INVALDATA= 0x7FFFFFFF
		self.TOTAL_FLIGHT_SECONDS=TOTAL_FLIGHT_SECONDS
		self.LAT_LON_SCALE_FACTOR=3600.0
		self.temperature=5
		self.airports=airports
		self.FPA=self.INVALDATA
		self.prev_altitude = 0.0
		self.vertical_speed = 0.0
		self.last_update_time = time.time()
		self.PHASE_FRACTIONS = {
			0.0: 1,   # pre flight
			0.05: 2,   # takeoff
			0.15: 3,   # climb
			0.45: 4,   # cruise starts BEFORE peak
			0.55: 4,   # cruise plateau
			0.75: 5,   # descent
			0.90: 6,   # approach
			1.00: 7,	#landing
			1.05: 8    # post flight / taxi
			}
		self.phase_times = {
			int(f * self.TOTAL_FLIGHT_SECONDS): phase
			for f, phase in self.PHASE_FRACTIONS.items()
		}
		self.acars_phase_id=1
		self.miqat_phase=1
		self.profile_mode=1
		self.current_phase = 1
		self.end_of_flight=0
		self.elapsed = 0
		self.flightnumber=b'PTA00' 
		self.flightnumber_len = len(self.flightnumber)
		self.altitude_scaled=self.INVALDATA
		self.altitude=self.INVALDATA
		self.ground_speed=self.INVALDATA
		self.head_wind=self.INVALDATA
		self.remaining_time=self.INVALDATA
		self.true_airspeed = self.INVALDATA
		self.mach = self.INVALDATA
		self.total_dist_nm = self.INVALDATA
		self.dist_traveled = self.INVALDATA
		self.distance_to_destination=self.INVALDATA
		self.tailwind = self.INVALDATA
		self.time_since_departure= self.INVALDATA
		self.pitch=self.INVALDATA
		self.roll=self.INVALDATA
		self.estimated_arrival_time=self.INVALDATA
		self.time_enc=self.INVALDATA
		self.vertical_speed=self.INVALDATA
		self.date_enc=self.INVALDATA
		self.heading=self.INVALDATA
		self.current_lat=self.INVALDATA
		self.current_lon=self.INVALDATA

		self.dpt_LAT=self.airports.get_dpt_LAT()                                   # 21. DEP Lat
		self.dpt_LON=self.airports.get_dpt_LON()                                  # 22. DEP Lon
		self.dpt_IATA=self.airports.get_dpt_IATA()                                                        # 23. DEP IATA
		self.dpt_ICAO=self.airports.get_dpt_ICAO()                                           # 24. DEP ICAO
		self.dpt_GEOID=self.airports.get_dpt_GEOID()                                      				        # 25. DEP NAME/CITY ID
		self.dst_LAT=self.airports.get_dst_LAT()                             # 26. DST Lat
		self.dst_LON=self.airports.get_dst_LON()                                   # 27. DST Lon
		self.dst_IATA=self.airports.get_dst_IATA()                                                        # 28. DST IATA
		self.dst_ICAO=self.airports.get_dst_ICAO()                                            # 29. DST ICAO
		self.dst_GEOID=self.airports.get_dst_GEOID()

	def run(self):
		self.start_time=datetime.now(timezone.utc)
		self.time_init=time.time()
		self.ciclo()
	
	
	def ciclo(self):
		while self.running:
			self.elapsed = time.time() - self.time_init
			fraction = min(self.elapsed / self.TOTAL_FLIGHT_SECONDS, 1.0)
			
			self.current_phase = 8 if self.elapsed > self.TOTAL_FLIGHT_SECONDS else 7
			
			for f, phase in sorted(self.PHASE_FRACTIONS.items()):
				if fraction <= f:
					self.current_phase = phase
					break
         
			self.remaining_time = max(self.TOTAL_FLIGHT_SECONDS - self.elapsed, 0)/60
		
			self.current_lat, self.current_lon = self.interpolate_great_circle(
				self.dpt_LAT, self.dpt_LON, self.dst_LAT, self.dst_LON, fraction
			)
			
			self.heading = self.compute_heading(self.current_lat, self.current_lon, self.dst_LAT, self.dst_LON)
			
			# --- Dynamic Simulated Flight Data ---
			self.altitude = 35000 * math.sin(math.pi * fraction) if fraction < 1.0 else 0
			self.altitude_scaled = int(self.altitude * 100)

			phase_vs_targets = {
				1: 0,       # Preflight
				2: 2500,    # Takeoff
				3: 3000,    # Climb
				4: 0,       # Cruise
				5: -2500,   # Descent
				6: -1000,   # Approach
				7: -300,    # Landing (Flare)
				8: 0        # Postflight
			}

			target_vs = phase_vs_targets.get(self.current_phase, 0)

			# --- 2. Calculate Delta Time Safely ---
			current_time = time.time()
			delta_time = current_time - self.last_update_time
			self.last_update_time = current_time

			# Ensure we don't divide by zero or process a massive leap on the first frame
			if delta_time > 0 and delta_time < 1.0:
    
			# --- 3. Smooth Vertical Speed Transition ---
			# This prevents the needle from snapping instantly to the new target
				smoothing_factor = 0.05 
				self.vertical_speed += (target_vs - self.vertical_speed) * smoothing_factor
    
				# --- 4. Update Altitude based on VS ---
				# Formula: VS (ft/min) / 60 = ft/sec. Multiply by delta_time (sec)
				altitude_change = (self.vertical_speed / 60.0) * delta_time
				self.altitude += altitude_change
    
				# Safety: Don't go below ground level
				if self.altitude < 0:
					self.altitude = 0
					self.vertical_speed = 0

				# Safety: Cap at Service Ceiling
				if self.altitude > 41000:
					self.altitude = 41000

			self.altitude_scaled = int(self.altitude * 100)
			self.vertical_speed_scaled = int(self.vertical_speed * 100)

			self.vertical_speed_scaled = int(self.vertical_speed * 100)
			self.prev_altitude = self.altitude
			
			if self.altitude < 36089:
				self.temperature = 15.0 - (0.00198 * float(self.altitude))
			else:
				self.temperature = -56.5 # Tropopause temperature is constant
				
    
			# Calculate True Airspeed (TAS) and Mach (M)
			self.true_airspeed = 450 * (1 - abs(math.cos(math.pi * fraction)) * 0.2) # TAS varies slightly
			speed_of_sound = 20.05 * math.sqrt(self.temperature+273.15) * 1.944 # approx ft/s to knots
			self.mach = int((self.true_airspeed / speed_of_sound) * 1000)
			# Calculate Distance to Destination
			self.total_dist_nm = self.haversine_distance(self.dpt_LAT, self.dpt_LON, self.dst_LAT, self.dst_LON)
			self.dist_traveled = self.total_dist_nm * fraction
			self.distance_to_destination = int(self.total_dist_nm - self.dist_traveled) # Remaining distance in NM

		# --- Other Data ---
			self.ground_speed = int(self.true_airspeed * 0.95)
			self.head_wind = 39
			wind_direction = self.heading + 10
			wind_angle_diff = self.heading - wind_direction
			self.tailwind = int(self.head_wind * math.cos(math.radians(wind_angle_diff)))
			self.time_since_departure= int((self.elapsed)/60)
			self.FPA = math.degrees(math.atan(self.vertical_speed / (self.ground_speed * 101.27)))
			
    
		# --- PITCH and ROLL DEPENDENT ON FLIGHT PHASE (DYNAMIC) ---
			self.pitch = 0
			self.roll = 0
    
			if self.current_phase == 2: # Takeoff
				self.pitch = int(5 + 5 * min(self.elapsed, 30) / 30) # Up to 10 degrees pitch up
			elif self.current_phase == 3: # Climb
				self.pitch = 5
			elif self.current_phase == 4: # Cruise
				self.pitch = 0
			elif self.current_phase == 5: # Descent
				self.pitch = -2
			elif self.current_phase == 6: # Approach
				self.pitch = 2
			elif self.current_phase == 7: # Landing
				self.pitch = 5 # Flare
				self.roll = 0
			
				
			now = datetime.now(timezone.utc)
    
			year_to_send = now.year
    
			month_to_send = now.month
    
			day_to_send = now.day
		

			date_packed = struct.pack('>HBB', year_to_send, month_to_send, day_to_send)
			self.date_enc = struct.unpack('>I', date_packed)[0]
    
			seconds_today = (now.hour * 3600) + (now.minute * 60) + now.second

			self.time_enc = (seconds_today) % 86400
    
			current_minutes_today = (self.start_time.hour * 60) + (self.start_time.minute*1.2)
    
			self.remaining_minutes = int(self.remaining_time / 60)

			self.estimated_arrival_time = (current_minutes_today+(self.TOTAL_FLIGHT_SECONDS/60))%1440

			time.sleep(0.5)
   
    

    
	def compute_heading(self,lat1, lon1, lat2, lon2):
		lat1_rad = math.radians(lat1)
		lat2_rad = math.radians(lat2)
		dlon_rad = math.radians(lon2 - lon1)
		x = math.sin(dlon_rad) * math.cos(lat2_rad)
		y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
		return int((math.degrees(math.atan2(x, y)) + 360) % 360)

	def interpolate_great_circle(self,lat1, lon1, lat2, lon2, fraction):
		lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
		lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
		x1, y1, z1 = math.cos(lat1_rad)*math.cos(lon1_rad), math.cos(lat1_rad)*math.sin(lon1_rad), math.sin(lat1_rad)
		x2, y2, z2 = math.cos(lat2_rad)*math.cos(lon2_rad), math.cos(lat2_rad)*math.sin(lon2_rad), math.sin(lat2_rad)
		dot = max(min(x1*x2 + y1*y2 + z1*z2, 1.0), -1.0)
		omega = math.acos(dot)
		if omega == 0:
			return lat1, lon1
		t1, t2 = math.sin((1-fraction)*omega)/math.sin(omega), math.sin(fraction*omega)/math.sin(omega)
		x, y, z = t1*x1 + t2*x2, t1*y1 + t2*y2, t1*z1 + t2*z2
		return math.degrees(math.atan2(z, math.sqrt(x*x + y*y))), math.degrees(math.atan2(y, x))

	def haversine_distance(self, lat1, lon1, lat2, lon2):
		R = 6371 # Earth radius in km
		dlat = math.radians(lat2 - lat1)
		dlon = math.radians(lon2 - lon1)
		a = math.sin(dlat/2) * math.sin(dlat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon/2) * math.sin(dlon/2)
		c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
		# Return distance in nautical miles (1 km ≈ 0.539957 nm)
		return R * c * 0.539957
		
	def get_Altitude(self, scaled):
		if(scaled==True):
			return int(self.altitude_scaled)
		else:
			return int(self.altitude)
						
	def get_LatLon(self, par):
		if(par=="lat"):
			return int(self.current_lat*self.LAT_LON_SCALE_FACTOR)
		elif(par=="lon"):
			return int(self.current_lon*self.LAT_LON_SCALE_FACTOR)
         
	def get_GroundSpeed(self):
		return self.ground_speed

	def get_Headwind(self):
		return int(self.head_wind)

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
		return int(self.remaining_time)

	def get_EstimatedArrivalTime(self):
		return self.estimated_arrival_time

	def get_VerticalSpeed(self, scaled):
		if(scaled==False):
			return self.vertical_speed
		else:
			return self.vertical_speed_scaled

	def get_Tailwind(self):
		return self.tailwind

	def get_TrueAirspeed(self):
		return self.true_airspeed

	def get_TotalDist(self):
		return self.total_dist_nm

	def get_DistTraveled(self):
		return self.dist_traveled*100

	def get_DistanceToDestination(self):
		return self.distance_to_destination


	def get_Pitch(self):
		return self.pitch

	def get_Roll(self):
		return self.roll

	def get_Date(self):
		return int(self.date_enc)

	def get_Time(self):
		return int(self.time_enc)

	def get_End_Of_Flight(self):
		return self.end_of_flight

	def get_Temperature(self):
		return self.temperature

	def get_Mach(self):
		return self.mach
		
	def get_flightnumber(self):
		return self.flightnumber
	def get_flightnumber_len(self):
		return self.flightnumber_len

	def get_Heading(self):
		return self.heading

	def get_HeadingToDestination(self):
		return self.heading

	def get_FPA(self):
		return self.FPA

	def get_MiqatPhase(self):
		return self.miqat_phase

	def get_AcarsPhase(self):
		return self.acars_phase_id

	def get_ProfileMode(self):
		return self.profile_mode


	def get_Packet(self):
			packet = [
			# 0-31 (32 integers)
			1,                                                                          # 0. Valid Flag
			int(self.get_LatLon("lat")),                                              # 1. Current Lat
			int(self.get_LatLon("lon")),                                              # 2. Current Lon
			int(self.ground_speed), 															# 3. ground speed,
			int(self.true_airspeed),	 														# 4. true airspeed (formerly Mach field)
			int(self.FPA),																	# 5. FPA
			int(self.head_wind), 															# 6. headwind
			int(self.distance_to_destination),                                                    # 7. Distance to destination
			int(self.dist_traveled),                                      					# 8. Distance from departure
			int(self.altitude),                                                            # 9. Altitude (Scaled)
			int(self.temperature),                                                    		# 10. temperature
			int(self.remaining_time),                                                        # 11. Remaining time
			int(self.time_since_departure),                         								# 12 Time since departure
			int(self.heading),                                                      				# 13. heading
			int(self.heading),                                                 					# 14. heading to destination
			int(self.tailwind),                                                                   # 15. Tail/Headwind Component
			int(self.estimated_arrival_time),                                                # 16. estimated arrival time
			int(self.mach),                                                                       # 17. MACH (scaled * 10000)
			int(self.dist_traveled * 100),                                                   # 18. Distance Traveled (Scaled)
			int(self.time_enc),                                                    		    # 19. Local time
			int(self.date_enc),                                                              # 20. Date Enc
			int(self.dpt_LAT*self.LAT_LON_SCALE_FACTOR),                                   # 21. DEP Lat
			int(self.dpt_LON*self.LAT_LON_SCALE_FACTOR),                                   # 22. DEP Lon
			int(self.dpt_IATA),                                                        # 23. DEP IATA
			int(self.dpt_ICAO),                                            # 24. DEP ICAO
			int(self.dpt_GEOID),                                      				        # 25. DEP NAME/CITY ID
			int(self.dst_LAT*self.LAT_LON_SCALE_FACTOR),                                # 26. DST Lat
			int(self.dst_LON*self.LAT_LON_SCALE_FACTOR),                                   # 27. DST Lon
			int(self.dst_IATA),                                                        # 28. DST IATA
			int(self.dst_ICAO),                                            # 29. DST ICAO
			int(self.dst_GEOID),						                                    # 30. DST NAME/CITY ID
			self.current_phase,                                                                      # 31. Phase
			self.acars_phase_id,                                                             # 32. Acars Phase ID
			self.miqat_phase, 																# 33. Miqat phase (1:Disabled 2:Working 3:Countdown 4:Welcome)
			self.flightnumber_len,																#34. flight number length
			self.flightnumber,  															#35 flight number
			0,                                                             					  # 36. weird pitch and roll values combined (not using, using 40/41 instead)                                                                 
			self.end_of_flight,                                                              	# 37. end of flight flag (DONT TOUCH it breaks the program when greater than 0 and causes crash)                                                            
			self.profile_mode,                                                               # 38. Profile mode
			int(self.altitude_scaled),                                                            # 39. unscaled altitude
			int(self.vertical_speed),                                                             # 40. vertical speed (unscaled)
			int(self.pitch),                                                                   	# 41. pitch (dynamic)
			int(self.roll),																		# 42. roll (dynamic)													
			]

			return packet


        
