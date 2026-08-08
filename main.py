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

print("WELCOME to flight simulator!")
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
	



airports=Airport_Loader(dep, dst)

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

print("Sending data to : multicast ip: " +str(sender.get_ip()) +" , port: "+ str(sender.get_port()))
print("Platform ip:"+ str(plat.get_ip())+", port: "+str(plat.get_port()))
print("-"*30)
	
		


sim.start()
sender.start()
plat.start()
while True:
	print(f"\033[{11};0H", end="")
	print("\033[J", end="")
	
	print(f"Elapsed time: {sim.get_Elapsed()}") 
	print(f"Current Latitude: {sim.get_LatLon("lat")}, Current Longitude {sim.get_LatLon("lon")} ")
	print(f"Altitude: {sim.get_Altitude(False)} ft")
	print(f"Ground Speed: {sim.get_GroundSpeed()} kt")
	print(f"Vertical Speed: {sim.get_VerticalSpeed(False)} fpm")
	print(f"FPA: {sim.get_FPA():.2f} deg")
	print(f"Heading: {sim.get_Heading()} deg")
	print(f"Distance: {sim.get_DistanceToDestination()} NM")
	print(f"Phase: {sim.get_Phase_str()}")
	print("-"*30)

	time.sleep(0.5)
sim.join()
plat.join()
sender.join()

