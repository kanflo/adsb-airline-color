#!/usr/bin/python
# -*- coding: utf-8 -*-
#


import imagecolor
import os
import paho.mqtt.client as mosquitto
import Queue
import time
from threading import *
import remotelogger, logging, sys
import socket
import calendar, datetime
import json
import traceback
import math
import signal
import random

gQuitting = False
gCurrentColor = ()
gMaxDistance = 10.0 # km

gMQTTBroker = "172.16.3.104"
#gMQTTBroker = "gateway.local"
gMQTTPort = "1883"

log = logging.getLogger(__name__)


def mqttOnConnect(mosq, obj, rc):
    mosq.subscribe("adsb/proximity/json", 0)
    log.debug("MQTT Connect: %s" % (str(rc)))

def mqttOnDisconnect(mosq, obj, rc):
    global gQuitting
    log.info("MQTT Disconnect: %s" % (str(rc)))
    if not gQuitting:
        while not mqttConnect():
            time.sleep(10)
            log.info("Attempting MQTT reconnect")
    log.info("MQTT connected")

def mqttOnMessage(mosq, obj, msg):
    global gMaxDistance
    global gCurrentColor
    try:
        data = json.loads(msg.payload)
    except Exception as e:
        log.error("JSON load failed for '%s' : %s" % (msg.payload, e))
        print traceback.format_exc()
        return

    if data["operator"] and data["distance"]:
        airline = data["operator"]
        distance = data["distance"]
        lost = False
        if "lost" in data:
            lost = data["lost"]

        if airline == "SAS":
            airline = "SAS Airlines"

        if lost:
            log.debug("Lost sight of aircraft")
            color = (0, 0, 0)
        else:
            try:
                color = imagecolor.getColor(airline)
            except Exception as e:
                log.error("getColor failed for '%s' : %s" % (msg.payload, e))
                print traceback.format_exc()
                return
        if distance > gMaxDistance:
          color = (0, 0, 0)
        else:
          color_0 = int(color[0] * (1 - (distance / gMaxDistance)))
          color_1 = int(color[1] * (1 - (distance / gMaxDistance)))
          color_2 = int(color[2] * (1 - (distance / gMaxDistance)))
          color = (color_0, color_1, color_2)
        if color != gCurrentColor:
            log.debug("New color is %02x%02x%02x" % (color[0], color[1], color[2]))
            cmd = "mosquitto_pub -h %s -t ghost/led -m \"#%02x%02x%02x\"" % (gMQTTBroker, color[0], color[1], color[2])
            os.system(cmd)
            gCurrentColor = color



def mqttOnPublish(mosq, obj, mid):
# log.debug("mid: "+str(mid)))
    pass


def mqttOnSubscribe(mosq, obj, mid, granted_qos):
    log.debug("Subscribed")


def mqttOnLog(mosq, obj, level, string):
    log.debug("log:"+string)


def mqttThread():
    global gQuitting
    try:
        mqttc.loop_forever()
        gQuitting = True
        log.info("MQTT thread exiting")
        gQuitting = True
    except Exception as e:
        log.error("MQTT thread got exception: %s" % (e))
        print traceback.format_exc()
#        gQuitting = True
#        log.info("MQTT disconnect")
#        mqttc.disconnect();

def mqttConnect():
    global mqttc
    try:
        # If you want to use a specific client id, use
        # mqttc = mosquitto.Mosquitto("client-id")
        # but note that the client id must be unique on the broker. Leaving the client
        # id parameter empty will generate a random id for you.
        mqttc = mosquitto.Mosquitto("airlinecolor-%d" % (random.randint(0, 65535)))
        mqttc.on_message = mqttOnMessage
        mqttc.on_connect = mqttOnConnect
        mqttc.on_disconnect = mqttOnDisconnect
        mqttc.on_publish = mqttOnPublish
        mqttc.on_subscribe = mqttOnSubscribe

        #mqttc.on_log = mqttOnLog # Uncomment to enable debug messages
        mqttc.connect(gMQTTBroker, gMQTTPort, 60)

        thread = Thread(target = mqttThread)
        thread.daemon = True
        thread.start()
        return True
    except socket.error, e:
        return False

    log.info("MQTT wierdness")


def loggingInit():
    log = logging.getLogger(__name__)

    # Initialize remote logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    remotelogger.init(logger = logger, appName = "airlinecol", subSystem = None, host = "midi.local", level = logging.DEBUG)

    if 1:
        # Log to stdout
        ch = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

def signal_handler(signal, frame):
    global gQuitting
    global mqttc
    print "ctrl-c"
    gQuitting = True
    mqttc.disconnect();
    sys.exit(0)

def main():
    global gQuitting
    global mqttc
    imagecolor.loadColorData()

    try:
        signal.signal(signal.SIGINT, signal_handler)
        loggingInit()
        log.info("Client started")
        mqttConnect()
        while not gQuitting:
            time.sleep(1)
    except Exception as e:
        log.error("Mainloop got exception: %s" % (e))
        print traceback.format_exc()
        gQuitting = True
    log.debug("MQTT disconnect")
    mqttc.disconnect();

# Ye ol main
main()
