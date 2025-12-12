import socket
import struct
import time
import sys
import threading

# --- CONFIGURATION (FINAL STABLE VERSION) ---
MULTICAST_GROUP = '224.0.0.1'
MULTICAST_PORT = 50066
REFRESH_RATE = 0.1         # Send packet every 100ms
INVALDATA = 0x7FFFFFFF     # Standard placeholder for invalid data
MAGIC_ID = 0xFDFD          # Confirmed magic ID
DATA_PACKET_TYPE = 0x10    # Confirmed data packet type
LAT_LON_SCALE_FACTOR = 3600.0 # Confirmed scale factor

# --- FLIGHT DEFINITION (ORD to JFK) ---
FLIGHT_PHASES = {
    1: "Preflight",
    2: "Takeoff",
    3: "Climb",
    4: "Cruise",
    5: "Descent",
    6: "Approach",
    7: "Landing",
    8: "Postflight/Taxi"
}

# Coordinates for the journey
ORD_LAT = 41.9742
ORD_LON = -87.9073
JFK_LAT = 40.6413
JFK_LON = -73.7781

# Initial State
current_lat = ORD_LAT
current_lon = ORD_LON
current_phase = 1

TOTAL_FLIGHT_SECONDS = 600
TOTAL_PACKETS = TOTAL_FLIGHT_SECONDS / REFRESH_RATE
LAT_DELTA = (JFK_LAT - ORD_LAT) / TOTAL_PACKETS
LON_DELTA = (JFK_LON - ORD_LON) / TOTAL_PACKETS
packet_counter = 0

# Phase Timing
PHASE_TIMINGS = {
    30: 2,
    60: 3,
    180: 4,
    480: 5,
    540: 6,
    600: 7
}

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "0.0.0.0"

LOCAL_IP = get_local_ip()

def create_mcast_socket():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        s.bind((LOCAL_IP, 0))
        return s
    except Exception as e:
        print(f"Socket Error: {e}")
        sys.exit(1)

sock_main = create_mcast_socket()

def to_int(val): return int(val)
def enc_code(code):
    if not code: return INVALDATA
    s = code.ljust(4, ' ')
    if sys.version_info[0] > 2: s = s.encode('ascii')
    return struct.unpack('>i', s)[0]

# --- PACKET FORMAT (only corrected heading values) ---
DATA_FULL_FORMAT = '>HH' + ('i'*32) + 'iii' + '5s' + ('i'*7)
VALID_FLAG = to_int(1)
trail_post_zeros = [0, INVALDATA, INVALDATA, 35000, 0, 0, 0]

def send_data_packet(current_lat, current_lon, current_phase):
    tm = time.gmtime()
    time_sec = to_int(tm.tm_hour * 3600 + tm.tm_min * 60 + tm.tm_sec)
    date_enc = to_int((tm.tm_year << 16) | (tm.tm_mon << 8) | tm.tm_mday)

    # ---------------------------------------
    # FIX APPLIED HERE: heading changed 270 → 90
    # ---------------------------------------
    core_data = [
        VALID_FLAG,
        to_int(current_lat * LAT_LON_SCALE_FACTOR),
        to_int(current_lon * LAT_LON_SCALE_FACTOR),
        450, 450, 50, 50, 2000, 250, 35000, -50,
        7200, 3600,
        90,   # Heading 1 corrected
        90,   # Heading 2 corrected
        90,   # Heading 3 already correct
        0, 850, 1000,
        time_sec, date_enc,
        to_int(ORD_LAT * LAT_LON_SCALE_FACTOR),
        to_int(ORD_LON * LAT_LON_SCALE_FACTOR),
        enc_code('ORD'), enc_code('KORD'), INVALDATA,
        to_int(JFK_LAT * LAT_LON_SCALE_FACTOR),
        to_int(JFK_LON * LAT_LON_SCALE_FACTOR),
        enc_code('JFK'), enc_code('KJFK'), INVALDATA,
        current_phase
    ]

    flight_str = b'RC901'
    flight_len = len(flight_str)
    trail_pre = [INVALDATA, INVALDATA, flight_len]

    full_data = [MAGIC_ID, DATA_PACKET_TYPE] + core_data + trail_pre + [flight_str] + trail_post_zeros
    packet = struct.pack(DATA_FULL_FORMAT, *full_data)
    sock_main.sendto(packet, (MULTICAST_GROUP, MULTICAST_PORT))

print("--- ASXi Flight Simulator (ORD to JFK) ---")
print("Goal: Simulate a full flight with correct heading.")
print("------------------------------------------")

start_time = time.time()

try:
    while True:
        elapsed_time = time.time() - start_time

        new_phase = current_phase
        for t, phase_code in PHASE_TIMINGS.items():
            if elapsed_time >= t:
                new_phase = phase_code

        if new_phase != current_phase:
            current_phase = new_phase
            print(f"\n--- Phase Change: {current_phase} - {FLIGHT_PHASES.get(current_phase)} ---")

        if 2 <= current_phase <= 7:
            current_lat += LAT_DELTA
            current_lon += LON_DELTA

        send_data_packet(current_lat, current_lon, current_phase)

        sys.stdout.write(
            f"Phase: {current_phase} ({FLIGHT_PHASES.get(current_phase):<10}) | "
            f"Time: {int(elapsed_time):<3}s | "
            f"Lat/Lon: {current_lat:.4f} / {current_lon:.4f} \r"
        )
        sys.stdout.flush()

        if elapsed_time > TOTAL_FLIGHT_SECONDS + 10:
            current_phase = 8
            print(f"\nSimulation complete. Final Phase: {FLIGHT_PHASES.get(current_phase)}")
            break

        time.sleep(REFRESH_RATE)

except KeyboardInterrupt:
    print("\nStopped by user.")
finally:
    sock_main.close()
