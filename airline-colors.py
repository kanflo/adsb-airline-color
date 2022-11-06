#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Johan Kanflo (github.com/kanflo)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#
# Subscribes to the topic 'adsb/proximity/json' and publishes a color to the
# topic 'ghost/led' according to operator/distance of an aircraft.
#

from typing import *
import sys
import json
import argparse
import logging
try:
    import mqttwrapper
except ImportError:
    print("sudo -H python -m pip install git+https://github.com/kanflo/mqttwrapper")
    sys.exit(1)
import imagecolor


current_color = ()


def mqtt_callback(topic: str, payload: str) -> Optional[list[tuple]]:
    logging.debug("Got %s : %s" % (topic, payload))
    global current_color
    try:
        payload = payload.decode("utf-8")
        payload = payload.replace("\r", "")
        payload = payload.replace("\n", "")
        data = json.loads(payload)
    except Exception as e:
        logging.error("JSON load failed for '%s'" % (payload), exc_info=True)
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
            logging.debug("Lost sight of aircraft")
            color = (0, 0, 0)
        else:
            try:
                color = imagecolor.get_color(airline)
                logging.debug("#%02x%02x%02x : %s" % (color[0], color[1], color[2], airline))
            except Exception as e:
                logging.error("get_color failed", exc_info = True)
                return
        if not color or distance > args.max_distance:
            color = (0, 0, 0)
        else:
            color_0 = int(color[0] * (1 - (distance / args.max_distance)))
            color_1 = int(color[1] * (1 - (distance / args.max_distance)))
            color_2 = int(color[2] * (1 - (distance / args.max_distance)))
            color = (color_0, color_1, color_2)
        if color != current_color:
            logging.info("New color is %02x%02x%02x for %s" % (color[0], color[1], color[2], airline))
            current_color = color
            resp = (args.color_topic, "#%02x%02x%02x" % (color[0], color[1], color[2]))
            return [resp]


def main():
    global gQuitting
    global mqttc
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--mqtt-host', dest='mqtt_host', help="MQTT broker hostname", default='127.0.0.1')
    parser.add_argument('-p', '--prox-topic', dest='prox_topic', help="ADSB MQTT proximity topic", default="/adsb/proximity/json")
    parser.add_argument('-t', '--color-topic', dest='color_topic', help="MQTT color topic", default="ghost/color")
    parser.add_argument('-d', '--max-distance', dest='max_distance', type=float, help="Max distance to light the LED (km)", default=10.0)
    parser.add_argument('-v', '--verbose', dest='verbose', action="store_true", help="Verbose output")
    parser.add_argument('-l', '--logger', dest='log_host', help="Remote log host")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, stream=sys.stdout,
                        format='%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s',
                        datefmt='%Y%m%d %H:%M:%S')
    logging.info("---[ Starting %s ]---------------------------------------------" % sys.argv[0])
    imagecolor.load_color_data()

    try:
        mqttwrapper.run_script(mqtt_callback, broker="mqtt://nano.local", topics=[args.prox_topic])
    except Exception as e:
        logging.error("Caught exception", exc_info = True)


# Ye ol main
if __name__ == "__main__":
    main()
