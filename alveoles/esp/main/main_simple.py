import wifi

mode, ip = wifi.setup_network()
print("Network ready (%s) -> http://%s" % (mode, ip))

import uasyncio as asyncio

from microdot import Microdot, Response

import helpers as h
import programs as p
from configuration import PROGRAM_NAMES, PROGRAMS
from web_ui import INDEX_HTML, GRID_HTML

# Shared, mutable state read by the LED runner and written by the web app.
STATE = {
    "program": "alveoles_propagate",
    "kwargs": {},
}

h.reset_pins()
app = Microdot()

Response.default_content_type = "text/html"

# Signals the LED runner that STATE changed and the program must restart.
restart_event = asyncio.Event()


@app.route("/")
async def index(request):
    return INDEX_HTML


@app.route("/grid")
async def grid(request):
    return GRID_HTML


@app.route("/api/programs")
async def api_programs(request):
    return PROGRAMS


@app.route("/api/state")
async def api_state(request):
    return STATE


@app.route("/api/grid")
async def api_grid(request):
    return {
        "coords": p.COORDS,
        "edges": p.EDGES,
    }


@app.route("/health")
async def health(request):
    return {"ok": True, "program": STATE.get("program")}


@app.route("/api/program", methods=["POST"])
async def api_set_program(request):
    payload = request.json
    if not payload:
        return {"error": "invalid payload"}, 400

    program = payload.get("program")
    if program not in PROGRAM_NAMES:
        return {"error": "unknown program"}, 400

    if STATE["program"] != program:
        STATE["program"] = program
        restart_event.set()

    # Backward-compatible: if kwargs are provided, merge them.
    kwargs = payload.get("kwargs")
    if isinstance(kwargs, dict):
        STATE["kwargs"].update(kwargs)

    return STATE


@app.route("/api/params", methods=["POST", "PATCH"])
async def api_set_params(request):
    payload = request.json
    if not isinstance(payload, dict):
        return {"error": "invalid payload"}, 400

    STATE["kwargs"].update(payload)
    return STATE


print("Running 80")
print(mode.ifconfig())
print(p.COORDS, p.EDGES)
app.run(port=80, debug=True)

# C8:C9:A3:CC:06:14
