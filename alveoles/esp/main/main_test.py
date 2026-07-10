# net_diag.py
import time
import network

try:
    import usocket as socket
except ImportError:
    import socket

SSID = "Phasm"
PASSWORD = "HarryThePhasm"
HOST = "0.0.0.0"
PORT = 80


def disable_powersave(sta):
    pm_none = getattr(network.WLAN, "PM_NONE", None)
    if pm_none is None:
        print("PM_NONE not available on this firmware")
        return
    try:
        sta.config(pm=pm_none)
        print("Power save disabled")
    except Exception as exc:
        print("Could not disable power save:", exc)


def connect():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    disable_powersave(sta)

    print("Connecting to", SSID)
    sta.connect(SSID, PASSWORD)

    deadline = time.time() + 20
    while not sta.isconnected() and time.time() < deadline:
        time.sleep(0.5)

    if not sta.isconnected():
        print("FAILED to connect")
        return None

    ip, mask, gw, dns = sta.ifconfig()
    print("Connected")
    print("ifconfig:", sta.ifconfig())
    print("mac:", ":".join("{:02X}".format(b) for b in sta.config("mac")))
    try:
        print("bssid:", sta.config("bssid"))
    except Exception:
        pass
    return sta


def run_http_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(2)
    s.settimeout(1)
    print("HTTP listening on {}:{}".format(HOST, PORT))

    last_beat = time.time()

    while True:
        # periodic heartbeat
        now = time.time()
        if now - last_beat >= 5:
            print("alive", now)
            last_beat = now

        try:
            cl, addr = s.accept()
        except OSError:
            continue

        try:
            req = cl.recv(256)
            print("HTTP from", addr, "len", len(req))
            cl.send(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/plain\r\n"
                b"Connection: close\r\n"
                b"\r\n"
                b"ESP OK\n"
            )
        except Exception as exc:
            print("client error:", exc)
        finally:
            try:
                cl.close()
            except Exception:
                pass


sta = connect()
if sta:
    run_http_server()
