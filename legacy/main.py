import time
from mqtt_as import MQTTClient, config
import uasyncio as asyncio

from configuration import PWMS, PROGRAM, DEVICE, CURRENT_TASK

import helpers as h
import programs as p

import json
import sys


def reload(mod):
    mod_name = mod.__name__
    del sys.modules[mod_name]
    return __import__(mod_name)


def callback(topic, msg, retained):

    print((topic, msg, retained))

    if topic.endswith("overwrite"):
        global p

        payload = json.loads(msg.decode("utf-8"))
        new_code = payload["program_kwargs"]["program_code"]
        mode = payload.get("mode", "overwrite")  # overwrite / append

        with open("programs.py", "w") as f:
            f.write(new_code)

        p = reload(p)

        return

    global PROGRAM, CURRENT_TASK

    payload = json.loads(msg.decode("utf-8"))
    print("Payload: ", payload)

    if payload["program"].startswith("alveole"):
        # In case of "color_flash", etc ...
        PROGRAM["current_program"] = payload["program"]
        PROGRAM["program_kwargs"] = payload["program_kwargs"]
        print("Updated program: ", PROGRAM)

        CURRENT_TASK.cancel()


async def conn_han(client):
    await client.subscribe(f"esps/{DEVICE}", 1)
    await client.subscribe(f"esps/{DEVICE}/overwrite", 1)


async def main(client):

    h.reset_pins()
    global PROGRAM, CURRENT_TASK

    await client.connect()

    while True:
        CURRENT_TASK = asyncio.create_task(
            p.program(PROGRAM["current_program"], **PROGRAM["program_kwargs"])
        )
        print(PROGRAM)
        try:
            await CURRENT_TASK
        except asyncio.CancelledError:
            pass


config["subs_cb"] = callback
config["connect_coro"] = conn_han

MQTTClient.DEBUG = True  # Optional: print diagnostic messages
client = MQTTClient(config)
try:
    asyncio.run(main(client))
finally:
    client.close()  # Prevent LmacRxBlk:1 errors
    pass
