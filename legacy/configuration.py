# config.py Local configuration for mqtt_as demo programs.
from mqtt_as import config

from machine import Pin, PWM, unique_id

import ubinascii

config["server"] = "10.3.141.1"
config["port"] = 1883

config["ssid"] = "Phasm"
config["wifi_pw"] = "HarryThePhasm"

PINS = [0, 4, 5, 13, 16, 17, 18, 19, 21, 22, 23, 25, 26]

PWMS = [PWM(Pin(i)) for i in PINS]

PROGRAM = dict(
    current_program="alveoles_propagate",
    program_kwargs={},
)

DEVICES = {
    "78e36d1a7864": 1,
    "78e36d1a7ed8": 2,
    "78e36d1a7e38": 3,
    "78e36d1a85c8": 4,
    "78e36d1a6ab0": 5,
    "c8c9a3cc0614": 6,
}

DEVICE = DEVICES[ubinascii.hexlify(unique_id()).decode("utf-8")]

CURRENT_TASK = None
