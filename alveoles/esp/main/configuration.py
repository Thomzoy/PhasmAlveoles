from machine import PWM, Pin

# --- LED hardware --------------------------------------------------------

PINS = [0, 4, 5, 13, 16, 17, 18, 19, 21, 22, 23, 25, 26]

PWMS = [PWM(Pin(i)) for i in PINS]

# --- WiFi ----------------------------------------------------------------

# Access point exposed when no known network is reachable at boot.
AP_SSID = "Phasm"
AP_PASSWORD = "HarryThePhasm"

# Networks to try (in order) as a station at boot. Add your home network
# here as ("ssid", "password") to have the device join it automatically.
KNOWN_NETWORKS = [
    ("Phasm", "HarryThePhasm"),
    ("LALABbox-BCA85F14-Secondaire", "7Xp5dLZZnwUSc7cVqc"),
]

# Seconds to wait for a station connection before giving up on a network.
STA_CONNECT_TIMEOUT = 10

# mDNS hostname. When connected to a known network, the website is reachable
# at http://<HOSTNAME>.local (e.g. http://alveoles.local) without needing to
# know the DHCP-assigned IP. Requires firmware with mDNS support.
HOSTNAME = "alveoles"

# --- Runtime state -------------------------------------------------------

# --- UI metadata ---------------------------------------------------------

# Describes the selectable programs and their tunable parameters so the web
# UI can render the right inputs. `default` values mirror programs.py.
MAX_INTENSITY = {
    "name": "max_intensity",
    "label": "Max intensity",
    "default": 1023,
    "min": 0,
    "max": 1023,
    "step": 1,
}

PROGRAMS = [
    {
        "name": "alveoles_propagate",
        "label": "Propagate",
        "params": [
            {
                "name": "duration_step",
                "label": "Step duration (s)",
                "default": 0.01,
                "min": 0.001,
                "max": 10,
                "step": 0.001,
                "scale": "log",
            },
            MAX_INTENSITY,
        ],
    },
    {
        "name": "alveoles_phasm",
        "label": "Phasm",
        "params": [
            {
                "name": "duration_step",
                "label": "Step duration (s)",
                "default": 0.01,
                "min": 0.001,
                "max": 10,
                "step": 0.001,
                "scale": "log",
            },
            MAX_INTENSITY,
        ],
    },
    {
        "name": "alveoles_walker",
        "label": "Walker",
        "params": [
            {
                "name": "duration_step",
                "label": "Step duration (s)",
                "default": 0.1,
                "min": 0.001,
                "max": 10,
                "step": 0.001,
                "scale": "log",
            },
            {
                "name": "numbers",
                "label": "Number of walkers",
                "default": 1,
                "min": 1,
                "max": 13,
                "step": 1,
            },
            MAX_INTENSITY,
        ],
    },
    {
        "name": "alveoles_random_fill",
        "label": "Random fill",
        "params": [
            {
                "name": "duration_step",
                "label": "Step duration (s)",
                "default": 0.01,
                "min": 0.001,
                "max": 10,
                "step": 0.001,
                "scale": "log",
            },
            MAX_INTENSITY,
        ],
    },
    {
        "name": "alveoles_flash",
        "label": "Flash",
        "params": [
            {
                "name": "duration",
                "label": "Flash duration (s)",
                "default": 1,
                "min": 0.001,
                "max": 10,
                "step": 0.1,
                "scale": "log",
            },
            {
                "name": "pause_between",
                "label": "Pause between (s)",
                "default": 0.001,
                "min": 0.001,
                "max": 10,
                "step": 0.1,
                "scale": "log",
            },
            MAX_INTENSITY,
        ],
    },
]

PROGRAM_NAMES = [program["name"] for program in PROGRAMS]
