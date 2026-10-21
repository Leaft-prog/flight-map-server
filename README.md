This program simulates flight data compatible with ASXi mobile. Now it also supports MSFS telemetry. It simulates a flight with the desired destinations.


ADMIN permissions are necessary to open port 80 for local file server (required for pushing config.zip and ticker ads, the program works anyway without admin permissions
but config server will not work).

how to use:

[Linux & MacOS] run_simulator.sh [departure iata code] [destination iata code] [simulation seconds]

[WINDOWS] Simulator: run_simulator.bat [departure iata code] [destination iata code] [simulation seconds] MSFS: run_msfs.bat

For MSFS SimConnect module is required

NOTE: Now simulated flight calculates the full time at the destination if flight seconds arent specified instead of simulating a short 10 minutes flight

ASXI clients:
Airshow Mobile 2 (recomended version, removed from playstore and appstore)
https://apkpure.net/airshow-mobile-2/com.rockwellcollins.airshowgen2
Falcon Map (if you have iOS or want to download from playstore)
https://play.google.com/store/apps/details?id=com.dassault.falconmap
https://apps.apple.com/in/app/falconmap-by-collins/id1473265374
Airshow Mobile 3
https://play.google.com/store/apps/details?id=com.rockwellcollins.airshow3&hl=en-US
https://apps.apple.com/us/app/airshow-mobile-3/id1525957526
Airshow Mobile HD (not recomended)
https://play.google.com/store/apps/details?id=com.rockwellcollins.unifiedentertainment&hl=en-US
https://apps.apple.com/au/app/airshow-hd/id6451424595
Airshow Mobile (legacy) (not compatible with modern android, unstable)
https://apkpure.net/airshow-mobile/com.rockwellcollins.tustin.airshow

NOTE for IOS: ticker ads and logo arent supported on falconmap,
only on airshow mobile 3 and higher support logo on iOS 

NOTE for FalconMap: Notifications about cabin wifi or cabin system not being connected are often shown repeatedly
, these can be ignored as those are Dassault Falcon CMS related stuff, if you find these annoying consider using airshow mobile 2 or 3

Note for Falcon Map and Airshow Mobile 3 and HD: A warning about map terrain data not being found is shown upon opening

Note for Airshow Mobile Legacy: This version is really unstable and isnt compatible on modern android versions causing crash upon opening,
also downloaded config doesnt work for some configurations and screen elements arent shown correctly especially on 1920x1080 resolution


Some code was made by ai (most of these parts are just formulas and calculations as I don't have any knowledge in aviation lmao and some weird logic).

Legal Notice

This project is for educational and research purposes only made only for interoperability.

Disclaimer

This software is provided AS-IS without warranty. Users are responsible for compliance with all applicable laws and terms of service.
Images:

<img width="970" height="502" alt="image" src="https://github.com/user-attachments/assets/86111b9e-3485-463f-b3fb-cbf17049b298" />

<img width="1000" height="746" alt="Screenshot 2026-10-18 121911" src="https://github.com/user-attachments/assets/d4d974c3-4aa6-4425-845f-54210a33dd45" />
<img width="998" height="747" alt="Screenshot 2026-10-18 121850" src="https://github.com/user-attachments/assets/2f057210-2451-48f9-8749-1f2db88e632b" />
<img width="1002" height="743" alt="Screenshot 2026-10-18 121833" src="https://github.com/user-attachments/assets/4e2a2441-3ade-46c3-a7c8-a87afaff51da" />
<img width="1000" height="747" alt="Screenshot 2026-10-18 121819" src="https://github.com/user-attachments/assets/2ee36eff-6168-4150-988e-9acd08190baf" />
<img width="1006" height="747" alt="Screenshot 2026-10-18 121807" src="https://github.com/user-attachments/assets/247e8b5b-a298-403f-aa5b-d8b8902d327a" />
<img width="1001" height="748" alt="Screenshot 2026-10-18 121743" src="https://github.com/user-attachments/assets/b5c4112b-e77e-48da-9c0c-93dc02a8c2b2" />
<img width="1004" height="748" alt="Screenshot 2026-10-18 121715" src="https://github.com/user-attachments/assets/172b471e-91c8-496c-be6c-fa1e898c4db7" />

