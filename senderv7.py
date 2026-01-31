import socket
import struct
import time
import calendar
from datetime import datetime, timezone, timedelta
import sys
import math
import csv

# --- CONFIGURATION ---
MULTICAST_GROUP ='224.0.0.1'
MULTICAST_PORT = 50066
REFRESH_RATE = 0.1
INVALDATA = 0x7FFFFFFF
MAGIC_ID = 0xFDFD
DATA_PACKET_TYPE = 0x10
LAT_LON_SCALE_FACTOR = 3600.0
TOTAL_FLIGHT_SECONDS = 600
AIRPORT_DATA_FILE = "tbairportinfo.csv"

start_time=datetime.now(timezone.utc)

oldheading=0
# --- FLIGHT PHASES and HELPERS ---
FLIGHT_PHASES = {
    1: "Preflight", 2: "Takeoff", 3: "Climb", 4: "Cruise", 5: "Descent", 6: "Approach", 7: "Landing", 8: "Postflight/Taxi"
}
PHASE_TIMINGS = {30: 2, 60: 3, 180: 4, 480: 5, 540: 6, 600: 7}

def load_airports(filename=AIRPORT_DATA_FILE):
    airports = {}
    try:
        with open(filename, newline='') as f:
            reader = csv.DictReader(f)
            required_fields = ['FourLetId', 'ThreeLetId', 'Lat', 'Lon', 'PointGeoRefId']
            if not all(field in reader.fieldnames for field in required_fields):
                 print(f"FATAL ERROR: CSV file '{filename}' is missing required headers: {required_fields}")
                 sys.exit(1)
                 
            for row in reader:
                iata_code = row['ThreeLetId'].upper()
                icao_code = row['FourLetId'].upper()
                
                # --- City Code (PointGeoRefId) Parsing (FIXED for ValueError) ---
                geoID_str = row['PointGeoRefId'].strip()
                geoID_val = INVALDATA 
                
                if geoID_str and geoID_str.upper() not in ('NULL', 'N/A', 'NONE'):
                    try:
                        geoID_val = int(geoID_str)
                    except ValueError:
                         # Use INVALDATA if it fails conversion
                         geoID_val = INVALDATA 
                
                # --- Lat/Lon Parsing ---
                try:
                    latitude = float(row['Lat'])
                    longitude = float(row['Lon'])
                except ValueError:
                    continue

                airports[iata_code] = {
                    "icao": icao_code, 
                    "lat": latitude, 
                    "lon": longitude, 
                    "geoID": geoID_val
                }
                
    except FileNotFoundError:
        print(f"Error: {filename} not found. Cannot load airport data.")
        sys.exit(1)
    return airports

def pick_route(AIRPORTS): 
    if len(sys.argv) == 3:
        dep = sys.argv[1].upper()
        dst = sys.argv[2].upper()
        if dep not in AIRPORTS or dst not in AIRPORTS:
            print("Unknown airport code(s) provided.")
            sys.exit(1)
        if dep == dst:
            print("Departure and destination cannot be the same.")
            sys.exit(1)
        return dep, dst
    return 'JFK', 'ORD'

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "0.0.0.0"

def encode_airport(code):
    s = code.strip().upper().ljust(4, ' ')[:4]
    return struct.unpack('<I', s.encode('ascii'))[0]

def compute_heading(lat1, lon1, lat2, lon2):
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon_rad = math.radians(lon2 - lon1)
    x = math.sin(dlon_rad) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
    return int((math.degrees(math.atan2(x, y)) + 360) % 360)

def interpolate_great_circle(lat1, lon1, lat2, lon2, fraction):
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

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    # Return distance in nautical miles (1 km ≈ 0.539957 nm)
    return R * c * 0.539957
    
    
def encode_flight_name(name):
    # Ensure exactly 8 characters
    padded = name.ljust(8, ' ')
    # Split into two 4-byte chunks
    part1 = padded[0:4].encode('ascii')
    part2 = padded[4:8].encode('ascii')
    
    # Use the <I logic that worked for IST/CCS
    val1 = struct.unpack('<I', part1)[0]
    val2 = struct.unpack('<I', part2)[0]
    return val1, val2


# --- PACKET FORMAT (SIMPLIFIED TO MATCH 177 BYTES) ---
# Total 45 arguments: 2 (HH) + 42 (i) + 1 (5s)
#DATA_FULL_FORMAT = '>HH' + ('i' * 20) + 'I' + ('i' * 2) + ('I'*3) + ('i' * 2) + ('I'*3) + ('i' * 11) + '8s'
DATA_FULL_FORMAT = '>HH' + ('i' * 20)+ 'I'+ ('i'*21)
EXPECTED_PACKET_SIZE = struct.calcsize(DATA_FULL_FORMAT) # 177 bytes

# --- PACKET SENDER ---
def send_data_packet(sock, lat, lon, heading, phase, elapsed, DEP, DST, DEP_APT, DST_APT):
    global start_time
    fraction = min(elapsed / TOTAL_FLIGHT_SECONDS, 1.0)
    remaining_time = max(TOTAL_FLIGHT_SECONDS - elapsed, 0)/60
    # --- Dynamic Simulated Flight Data ---
    altitude = 35000 * math.sin(math.pi * fraction) if fraction < 1.0 else 0
    altitude_scaled = int(altitude * 100)
    
    # Calculate Vertical Speed (fpm) based on altitude change rate
    vertical_speed_rate = 3000 * math.cos(math.pi * fraction) if fraction < 1.0 else 0
    vertical_speed = int(vertical_speed_rate) # Vertical Speed in feet/min
    vertical_speed_scaled = int(vertical_speed * 100)
    
    # Calculate True Airspeed (TAS) and Mach (M)
    true_airspeed = 450 * (1 - abs(math.cos(math.pi * fraction)) * 0.2) # TAS varies slightly
    temperature = 5
    speed_of_sound = 20.05 * math.sqrt(temperature) * 1.944 # approx ft/s to knots
    mach = int((true_airspeed / speed_of_sound) * 1000)
    # Calculate Distance to Destination
    total_dist_nm = haversine_distance(DEP_APT["lat"], DEP_APT["lon"], DST_APT["lat"], DST_APT["lon"])
    dist_traveled = total_dist_nm * fraction
    distance_to_destination = int(total_dist_nm - dist_traveled) # Remaining distance in NM

    # --- Other Data ---
    ground_speed = int(true_airspeed * 0.95)
    head_wind = 39 
    wind_direction = heading + 10
    wind_angle_diff = heading - wind_direction
    tailwind = int(head_wind * math.cos(math.radians(wind_angle_diff)))
    time_since_departure= int((elapsed)/60)
    FPA=14
    
    acars_phase_id=1
    miqat_phase=1
    profile_mode=1
    
    # --- PITCH and ROLL DEPENDENT ON FLIGHT PHASE (DYNAMIC) ---
    pitch = 0
    roll = 0
    
    if phase == 2: # Takeoff
        pitch = int(5 + 5 * min(elapsed, 30) / 30) # Up to 10 degrees pitch up
    elif phase == 3: # Climb
        pitch = 5
    elif phase == 4: # Cruise
        pitch = 0
    elif phase == 5: # Descent
        pitch = -2
    elif phase == 6: # Approach
        pitch = 2
    elif phase == 7: # Landing
        pitch = 5 # Flare
        roll = 0
    # For phase 1 (Preflight) and 8 (Postflight/Taxi), pitch and roll remain 0.
	
    # --- Encoding ---
# --- The Hard-Limit Protected Fix ---
    now = datetime.now(timezone.utc)
    
    # Year remains 1970 for 2026
    year_to_send = now.year
    
    # Month remains 1-indexed (1=Jan)
    month_to_send = now.month
    
    # Day Logic:
    # We want (Real Day + 10). 
    # But the C++ code you found WILL crash the iPad if we send > 31.
    day_to_send = now.day
    

    date_packed = struct.pack('>HBB', year_to_send, month_to_send, day_to_send)
    date_enc = struct.unpack('>I', date_packed)[0]
    #time_enc = int(time.time())
    
    seconds_today = (now.hour * 3600) + (now.minute * 60) + now.second

	# Use this for time_enc instead of time.time()
    time_enc = (seconds_today) % 86400
    
    current_minutes_today = (start_time.hour * 60) + (start_time.minute*1.2)
    
    # 2. Convert your remaining flight seconds into minutes
    remaining_minutes = int(remaining_time / 60)
    # 3. Calculate ETA in Minutes
    # We use 1440 because there are 1440 minutes in a day (24 * 60)
    estimated_arrival_time = (current_minutes_today+(TOTAL_FLIGHT_SECONDS/60))%1440
   
    
    flight_str = "TK  1920" # You can now use more than 4 chars
    # 1. Convert string to bytes and ensure it is null-terminated
    # We need to pack these into the 4-byte integer slots
    #flight_bytes = flight_str.encode('ascii').ljust(8, b'\x00')
    
    flight_num_str = "TK  1920".encode('ascii')
   
    
    # The 42 integers (Combining all parts into one single 42-item list)
    all_42_integers = [
        # 0-31 (32 integers)
        1,                                                                          # 0. Valid Flag
        int(lat*LAT_LON_SCALE_FACTOR),                                              # 1. Current Lat
        int(lon*LAT_LON_SCALE_FACTOR),                                              # 2. Current Lon
        int(ground_speed), 															# 3. ground speed,
        int(true_airspeed),	 														# 4. true airspeed (formerly Mach field)
        int(FPA),																	# 5. FPA
        int(head_wind), 															# 6. headwind
        distance_to_destination,                                                    # 7. Distance to destination
        int(dist_traveled),                                      					# 8. Distance from departure
        int(altitude),                                                            # 9. Altitude (Scaled)
        int(temperature),                                                    		# 10. temperature
        int(remaining_time),                                                        # 11. Remaining time
        time_since_departure,                         								# 12 Time since departure
        heading,                                                      				# 13. heading
        heading,                                                 					# 14. heading to destination
        tailwind,                                                                   # 15. Tail/Headwind Component
        int(estimated_arrival_time),                                                # 16. estimated arrival time
        mach,                                                                       # 17. MACH (scaled * 10000)
        int(dist_traveled * 100),                                                   # 18. Distance Traveled (Scaled)
        int(time_enc),                                                    		    # 19. Local time
        int(date_enc),                                                              # 20. Date Enc
        int(DEP_APT["lat"]*LAT_LON_SCALE_FACTOR),                                   # 21. DEP Lat
        int(DEP_APT["lon"]*LAT_LON_SCALE_FACTOR),                                   # 22. DEP Lon
        encode_airport(DEP),                                                        # 23. DEP IATA
        encode_airport(DEP_APT["icao"]),                                            # 24. DEP ICAO
        DEP_APT["geoID"],                                      				        # 25. DEP NAME/CITY ID
        int(DST_APT["lat"]*LAT_LON_SCALE_FACTOR),                                   # 26. DST Lat
        int(DST_APT["lon"]*LAT_LON_SCALE_FACTOR),                                   # 27. DST Lon
        encode_airport(DST),                                                        # 28. DST IATA
        encode_airport(DST_APT["icao"]),                                            # 29. DST ICAO
        DST_APT["geoID"],						                                    # 30. DST NAME/CITY ID
        phase,                                                                      # 31. Phase
        acars_phase_id,                                                             # 32. Acars Phase ID
        miqat_phase,                                                                # 33. Miqat phase (1:Disabled 2:Working 3:Countdown 4:Welcome)
        0,                                                                          # 34. weird pitch and roll values combined (not using, using 40/41 instead)
        0,                                                              			# 35. end of flight flag (DONT TOUCH it breaks the program when greater than 0 and causes crash)
        1,                                                                          # 36. ? (MUST BE GREATER THAN 0 OTHERWISE CRASH)
        profile_mode,                                                               # 37. Profile mode
        altitude_scaled,                                                            # 38. unscaled altitude
        vertical_speed,                                                             # 39. vertical speed (unscaled)
        pitch,                                                                   	# 40. pitch (dynamic)
        roll,																		# 41. roll (dynamic)																																			                                                                
    ]
    
    # --- Final Assembly and Packing ---
    # Construct the argument list: 2 Headers + 42 Integers + 1 String (Total 45 arguments)
    pack_args = [MAGIC_ID, DATA_PACKET_TYPE] 
    pack_args.extend(all_42_integers)
    

    # Pass the unpacked argument list to struct.pack
    packet = struct.pack(DATA_FULL_FORMAT, *pack_args)
	
    if len(packet) != EXPECTED_PACKET_SIZE:
        raise RuntimeError(f"Packet size mismatch! Expected {EXPECTED_PACKET_SIZE} bytes, got {len(packet)} bytes.")

    sock.sendto(packet, (MULTICAST_GROUP, MULTICAST_PORT))


def main():
    # 1. Load Data and Select Route
    global AIRPORTS, DEP, DST, DEP_APT, DST_APT 

    try:
        AIRPORTS = load_airports(AIRPORT_DATA_FILE) 
    except NameError:
        AIRPORTS = load_airports()

    DEP, DST = pick_route(AIRPORTS)
    DEP_APT = AIRPORTS[DEP]
    DST_APT = AIRPORTS[DST]

    # 2. Setup Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    # Binding to a specific IP (if available) can help with multicast on some systems
    sock.bind((get_local_ip(), 0)) 

    # 3. Start Simulation
    start_time = time.time()
    current_phase = 1

    print(f"--- Flight Simulator Started ---")
    print(f"Route: {DEP}  -> {DST}")
    print(f"Multicast: {MULTICAST_GROUP}:{MULTICAST_PORT}")
    print(f"Packet Format: {DATA_FULL_FORMAT} ({EXPECTED_PACKET_SIZE} bytes)")
    print(f"Total Flight Time: {TOTAL_FLIGHT_SECONDS}s")
    print("-" * 50)

    while True:
        global oldheading
        elapsed = time.time() - start_time

        # Update flight phase
        # Note: This checks for the highest phase achieved (last item in sorted list)
        for t, phase in sorted(PHASE_TIMINGS.items()):
            if elapsed >= t:
                current_phase = phase

        fraction = min(elapsed / TOTAL_FLIGHT_SECONDS, 1.0)
        current_lat, current_lon = interpolate_great_circle(
            DEP_APT["lat"], DEP_APT["lon"],
            DST_APT["lat"], DST_APT["lon"],
            fraction
        )
		
        if phase!=8:
            heading = compute_heading(current_lat, current_lon, DST_APT["lat"], DST_APT["lon"])
            oldheading=heading
        else:
            heading=oldheading

        if fraction >= 1.0:
            current_phase = 8
            current_lat, current_lon = DST_APT["lat"], DST_APT["lon"]

        try:
            send_data_packet(sock, current_lat, current_lon, heading, current_phase, elapsed, DEP, DST, DEP_APT, DST_APT)
        except (struct.error, RuntimeError, ValueError) as e:
            print(f"\nFATAL PACKING/SIZE ERROR: {e}")
            sys.exit(1)
        
        # Calculate for display purposes
        altitude = 35000 * math.sin(math.pi * fraction) if fraction < 1.0 else 0
        
        sys.stdout.write(
            f"Phase {current_phase} ({FLIGHT_PHASES[current_phase]}) | "
            f"Time: {int(elapsed):>3}s / {TOTAL_FLIGHT_SECONDS}s | "
            f"Alt: {int(altitude):>5}ft | "
            f"Lat: {current_lat:.4f} Lon: {current_lon:.4f} Heading: {heading}    \r"
            
        )
        sys.stdout.flush()
        time.sleep(REFRESH_RATE)

    print(f"\n--- Simulation finished at {int(elapsed)} seconds. ---")


if __name__ == "__main__":
    main()
