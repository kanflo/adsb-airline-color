# Visualising Airline Colors

This script extracts an airline's color from the ADSB MQTT feed from `adsb-client.py`.

The script listens to the MQTT topic `adsb/proximity/json` and extracts the name of the airline. It then does a Google image search for "<airline name> logo" and downloads the first image found. The image is analyzed and the dominant color is found (the one occuring in the most pixels, white and black excluded). This color is sent to the MQTT topic `ghost/led` making my Wifi Ghost light in the color of the nearest airliner. Colors are cached in `imagecolors.json`.
