# Alveoles

A MicroPython project running on an ESP32 that drives 13 LEDs arranged in a
*hexagonal alvéoles* shape.

## How it works now

The ESP32 hosts its own control website, so no Raspberry Pi or MQTT broker is
needed anymore (the previous setup is kept in [`legacy/`](legacy/)).

At boot the device:

1. Scans for the WiFi networks listed in `KNOWN_NETWORKS`
   ([`alveoles/configuration.py`](alveoles/configuration.py)) and tries to join
   the first reachable one (station mode).
2. If none are available, it exposes its own access point (`AP_SSID` /
   `AP_PASSWORD`, default `Phasm` / `HarryThePhasm`).
3. Serves a small website on port `80` (a [Microdot](https://github.com/miguelgrinberg/microdot)
   app) to pick a LED program and tune its parameters live.

Then open the website:

- **Station mode**: from a computer on the same WiFi, go to `http://alveoles.local`
  (the `HOSTNAME` set in `configuration.py`, advertised over mDNS). If `.local`
  resolution is unavailable, use the IP printed in the serial console instead.
- **Access point mode**: join the `Phasm` network and go to `http://192.168.4.1`.

## Project layout (`alveoles/`)

- `main.py` - entry point: brings up WiFi, runs the web server and the LED
  runner concurrently with `uasyncio`.
- `wifi.py` - station-first connection with access-point fallback.
- `configuration.py` - pins, WiFi credentials, `KNOWN_NETWORKS`, the mDNS
  `HOSTNAME`, shared `STATE` and the program/parameter metadata used by the UI.
- `programs.py` - the LED animation engine (`propagate`, `walker`, `phasm`,
  `random_fill`, `flash`).
- `helpers.py` - pin helpers.
- `web_ui.py` - the single-page web interface.
- `microdot/` - vendored web framework.

## Deploy

Regarding the firmware, it should be built with `ulab` (= numpy).
Use one of the available file in `setup` (I don't remember which one is good, I think 1.28 is too new and was buggy for our ESP)

Copy the contents of `main/` to the device root (so `main.py` runs on boot),
including the `microdot` package (the package modules, e.g.
`microdot/__init__.py` and `microdot/microdot.py`, must be importable as
`import microdot`). Requires a MicroPython build with `ulab` (numpy) available.

To use an existing WiFi network, add it to `KNOWN_NETWORKS` in
`alveoles/configuration.py` as `("ssid", "password")`.
