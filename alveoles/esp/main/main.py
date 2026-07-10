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
    edges = []
    for i in range(p.N):
        for j in range(i + 1, p.N):
            if i != j and int(p.ADJ_MAT[i][j]) == 1:
                edges.append([i, j])

    return {
        "coords": p.COORDS,
        "edges": edges,
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


async def led_runner():
    """Run the selected program, restarting it whenever STATE changes."""
    while True:
        restart_event.clear()
        task = asyncio.create_task(p.program(STATE["program"], state=STATE))
        print("Running program:", STATE["program"], STATE["kwargs"])

        await restart_event.wait()

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        h.reset_pins()


async def run_app():
    print("Starting HTTP server on 0.0.0.0:80")
    await asyncio.gather(
        app.start_server(host="0.0.0.0", port=80, debug=True),
        led_runner(),
    )


print(mode.isconnected())
print(mode.ifconfig())

try:
    asyncio.run(run_app())
finally:
    asyncio.new_event_loop()
