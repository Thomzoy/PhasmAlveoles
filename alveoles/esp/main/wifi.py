import time

import network

try:
    import usocket as socket
except ImportError:
    import socket

from configuration import (
    AP_PASSWORD,
    AP_SSID,
    HOSTNAME,
    KNOWN_NETWORKS,
    STA_CONNECT_TIMEOUT,
)


def _set_hostname(sta):
    """Best-effort hostname setup so the device answers to <HOSTNAME>.local.

    APIs vary across MicroPython versions/ports, so try them in order and
    ignore the ones that are unavailable.
    """
    if not HOSTNAME:
        return
    try:
        network.hostname(HOSTNAME)
        return
    except (AttributeError, OSError, ValueError):
        pass
    try:
        sta.config(dhcp_hostname=HOSTNAME)
    except (AttributeError, OSError, ValueError):
        print("Could not set hostname; falling back to IP access")


def _scan_ssids(sta):
    try:
        return {entry[0].decode("utf-8") for entry in sta.scan()}
    except Exception as exc:  # noqa: BLE001
        print("WiFi scan failed:", exc)
        return set()


def _connect_sta(sta, ssid, password):
    print("Trying to join network:", ssid)
    sta.connect(ssid, password)

    deadline = time.time() + STA_CONNECT_TIMEOUT
    while not sta.isconnected() and time.time() < deadline:
        time.sleep(0.5)

    if sta.isconnected():
        ip = sta.ifconfig()[0]
        print("Connected to", ssid, "with IP", ip)
        return ip

    print("Could not join", ssid)
    sta.disconnect()
    return None


def _disable_sta_powersave(sta):
    """Prefer low-latency Wi-Fi mode to improve inbound reachability on APs."""
    pm_none = getattr(network.WLAN, "PM_NONE", None)
    if pm_none is None:
        return
    try:
        sta.config(pm=pm_none)
    except (AttributeError, OSError, ValueError):
        pass


def _prime_gateway_path(sta):
    """Send one UDP datagram so peers quickly learn our L2/L3 mapping."""
    try:
        ip, _mask, gateway, _dns = sta.ifconfig()
        if not gateway or gateway == "0.0.0.0" or ip == "0.0.0.0":
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(b"alive", (gateway, 9))
        finally:
            sock.close()
    except Exception as exc:  # noqa: BLE001
        print("Could not prime gateway path:", exc)


def _start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, password=AP_PASSWORD, authmode=network.AUTH_WPA_WPA2_PSK)
    while not ap.active():
        time.sleep(0.1)
    ip = ap.ifconfig()[0]
    print("Access point", AP_SSID, "started with IP", ip)
    return ip


def setup_network():
    """Join a known network if reachable, otherwise expose an access point.

    Returns a ``(mode, ip)`` tuple where ``mode`` is ``"sta"`` or ``"ap"``.
    """
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    _disable_sta_powersave(sta)
    _set_hostname(sta)

    available = _scan_ssids(sta)
    print(available)

    for ssid, password in KNOWN_NETWORKS:
        if ssid not in available:
            continue
        ip = _connect_sta(sta, ssid, password)
        if ip is not None:
            _prime_gateway_path(sta)
            if HOSTNAME:
                print("Also reachable at http://%s.local" % HOSTNAME)
            return sta, ip

    sta.active(False)
    return "ap", _start_ap()
