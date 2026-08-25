import sys
import math
import csv
import time
import calendar
import threading
from datetime import datetime, timezone, timedelta
from Udp_Sender import *
from Simulator import *
from Airport_Loader import *
from Platform import *
from File_Server import *


os.system("")
print("Simulator -> ASXI")
if len(sys.argv) >= 3:
        dep = sys.argv[1].upper()
        dst = sys.argv[2].upper()
else:
		print("airports code not provided, using default route")
		dep='JFK'
		dst='ORD'
		
if len(sys.argv)==4:
	TOTAL_FLIGHT_SECONDS=int(sys.argv[3])
else:
	print("total flight seconds not provided, using default timing")
	TOTAL_FLIGHT_SECONDS=600
	


airports=Airport_Loader(dep, dst, 'iata')

if airports.validity()==False:
	print("INVALID codes aborting!")
	sys.exit(1)

print("-"*30)
print("Departure: "+dep)
print("Destination: "+dst)
print("Total flight time: "+str(TOTAL_FLIGHT_SECONDS))
print("-"*30)

sim=Simulator(airports, TOTAL_FLIGHT_SECONDS)

sender=Udp_Sender(sim)
plat=Platform()
server=File_Server()

print("Sending data to : multicast ip: " +str(sender.get_ip()) +" , port: "+ str(sender.get_port()))
print("Platform ip:"+ str(plat.get_ip())+", port: "+str(plat.get_port()))
	
		


sim.start()
sender.start()
plat.start()
server.start()

time.sleep(1)

NUM_LINES = 19
first_run = True

print("-"*30)

try:
	while True:
		if not first_run:
        # Move cursor UP by NUM_LINES to return to the top of the telemetry block
			sys.stdout.write(f"\033[{NUM_LINES}F")
		first_run = False

        # Clear each line to the end as we write to prevent ghost characters
		lines = [
            f"\033[KDeparture: IATA {sim.get_dptIATA()}, ICAO {sim.get_dpt_ICAO()}, geoID {sim.get_dpt_GEOID()}, LAT {sim.get_dpt_LAT()}, LON {sim.get_dpt_LON()}",
            f"\033[KDestination: IATA {sim.get_dstIATA()}, ICAO {sim.get_dst_ICAO()}, geoID {sim.get_dst_GEOID()}, LAT {sim.get_dst_LAT()}, LON {sim.get_dst_LON()}",
            f"\033[KCurrent Latitude: {sim.get_LatLon('lat')}, Current Longitude {sim.get_LatLon('lon')}",
            f"\033[KAltitude: {sim.get_Altitude(False)} ft",
            f"\033[KTrue airspeed: {sim.get_TrueAirspeed()}",
            f"\033[KHeadwind: {sim.get_Headwind()}",
            f"\033[KGround Speed: {sim.get_GroundSpeed()} kt",
            f"\033[KVertical Speed: {sim.get_VerticalSpeed(False)} fpm",
            f"\033[KFPA: {sim.get_FPA():.2f} deg",
            f"\033[KPITCH: {sim.get_Pitch()} ROLL:{sim.get_Roll()}",
            f"\033[KHeading: {sim.get_Heading()} deg",
            f"\033[KDistance: {sim.get_DistanceToDestination()} NM",
            f"\033[KPhase: {sim.get_Phase_str()}",
            f"\033[KFlight name: {sim.get_Flightnumber()}",
            f"\033[KEstimated arrival time: {sim.get_EstimatedArrivalTime()}",
            f"\033[KRemaining time: {sim.get_RemainingTime()}",
            f"\033[KTime (encoded): {sim.get_Time()}",
            f"\033[KTime since departure: {sim.get_TimeSinceDeparture()}",
            "\033[K" + "-" * 30
       		 ]

		print("\n".join(lines))
		sys.stdout.flush()  # Ensures smooth update without repeating
		time.sleep(0.5)

except KeyboardInterrupt:
	pass
sim.join()
plat.join()
server.join()
sender.join()

