# MIT License
#
# Copyright (c) 2023 Tom Kalmijn
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
import os
import signal
import time
from typing import List

import daemon
from daemon import pidfile
from dotenv import load_dotenv

from AdjSaberSpotRGBW import AdjSaberSpotRGBW
from AdjSaberSpotWW import AdjSaberSpotWW
from DmxFixture import DmxFixture
from DmxSender import DmxSender
from HueBridge import HueBridge

# initialize variables from config file (.env)
load_dotenv()

PID_FILE = os.getenv('PID')
WORK_DIR = os.getenv('WORK_DIR')
LOG_FILE = os.getenv('LOG_FILE')
DAEMONIZE = os.getenv('DAEMONIZE', '').lower() == 'true'
HUE_API_KEY = os.getenv('HUE_API_KEY')
HUE_BRIDGE_IP = os.getenv('HUE_BRIDGE_IP')
STUB_DMX = os.getenv('STUB_DMX')
HUE_TIMEOUT_SEC = int(os.environ.get('HUE_TIMEOUT_SEC', 240))

logger = logging.getLogger()
file_logger = logging.FileHandler(LOG_FILE)
hue_connection_lost = False

dmx_sender: DmxSender
hue_bridge: HueBridge

pin_spot_buddha = AdjSaberSpotWW(name="Buddha", hue_device_id="74b88e35-f81e-4f5a-b7af-3730ae5de366", dmx_address=1)
pin_spot_bureau = AdjSaberSpotRGBW(name="Bureau", hue_device_id="e0a5dd4a-67d3-4f40-ab6d-67c8ebbd463d", dmx_address=2)
dmx_fixtures: List[DmxFixture] = [pin_spot_buddha, pin_spot_bureau]  # add more fixtures here

def init_logger():
    global logger, file_logger
    logger.setLevel(logging.INFO)
    console_logger = logging.StreamHandler()
    console_logger.setLevel(logging.INFO)
    file_logger.setLevel(logging.INFO)
    file_logger.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_logger)
    logger.addHandler(console_logger)

def track_hue_lamp_and_update_dmx():
    while True:
        for sse_event in hue_bridge.hue_bridge_event_stream():
            event = hue_bridge.parse_sse_event(sse_event)
            if event and event["type"] == "update":
                for fixture in dmx_fixtures:
                    info = hue_bridge.get_hue_light_info(fixture.hue_device_id)
                    logger.debug(f"Update {fixture.name}")
                    if STUB_DMX:
                        fixture.get_dmx_message(info)
                    else:
                        dmx_sender.send_message(fixture.dmx_address, fixture.get_dmx_message(info))
        time.sleep(5)

def start():
    init_logger()
    logger.info("Starting up")
    global hue_bridge
    hue_bridge = HueBridge(bridge_ip=HUE_BRIDGE_IP, api_key=HUE_API_KEY, timeout_sec=HUE_TIMEOUT_SEC, logger=logger)

    logger.info("Discovering Hue bulbs")
    for key, value in hue_bridge.get_hue_lights().items():
         logger.info(f"{key}: {value}")

    logger.info("Initializing DMX sender")
    global dmx_sender
    dmx_sender = DmxSender(logger=logger)

    track_hue_lamp_and_update_dmx()

def shutdown(signum, frame):
    logger.info('Shutting down')
    exit(0)

def start_daemon():
    with daemon.DaemonContext(
            umask=0o002,
            working_directory=WORK_DIR,
            files_preserve=[file_logger.stream],
            pidfile=pidfile.PIDLockFile(PID_FILE)):
        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)
        start()

if __name__ == "__main__":
    if DAEMONIZE:
        start_daemon()
    else:
        start()
