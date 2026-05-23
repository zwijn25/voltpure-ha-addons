"""
VoltPure Edge — HA-addon variant
================================
Doel: data uit HA → license-gated MQTT-publish naar VoltPure cloud.

Verschil met Pi5-balena vp-edge:
- Geen directe Modbus/DSMR/Sessy-reads — alles via HA-Supervisor REST API
- License-check verplicht bij startup + elke 24u (anders geen MQTT-creds)
- Geïsoleerd in HA-Supervisor container (geen toegang tot HA-supervisor proces)
"""
import os
import sys
import json
import time
import asyncio
import logging
import ssl
from typing import Optional

import httpx
import paho.mqtt.client as mqtt
from aiohttp import web


LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
LOG = logging.getLogger("vp-edge")

KLANT_ID = os.environ["KLANT_ID"]
LICENSE_TOKEN = os.environ["LICENSE_TOKEN"]
LICENSE_URL = os.environ.get("LICENSE_URL", "https://app.voltpure.be/api/license/check")
MQTT_HOST = os.environ.get("MQTT_HOST", "mqtt.voltpure.be")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "443"))
MQTT_USE_WS = os.environ.get("MQTT_USE_WS", "true").lower() == "true"
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HASSIO_TOKEN")

VERSION = "1.0.0"
PUBLISH_INTERVAL = 30  # sec
LICENSE_RECHECK_INTERVAL = 24 * 3600  # 24u

state = {
    "status": "starting",
    "license_ok": False,
    "license_checked_at": 0,
    "last_publish_at": 0,
    "publish_count": 0,
    "errors": [],
    "klant_id": KLANT_ID,
    "version": VERSION,
}


# ── HA Supervisor REST helpers ───────────────────────────────────────────────


async def ha_states(client: httpx.AsyncClient) -> dict:
    """Lees alle entity-states van HA via Supervisor proxy."""
    url = "http://supervisor/core/api/states"
    headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}
    r = await client.get(url, headers=headers, timeout=10.0)
    r.raise_for_status()
    return {row["entity_id"]: row for row in r.json()}


def pick_state(states: dict, entity_id: str) -> Optional[float]:
    s = states.get(entity_id)
    if not s:
        return None
    try:
        return float(s["state"])
    except (ValueError, TypeError):
        return None


def derive_metrics(states: dict) -> dict:
    """Map HA-entities → VoltPure cloud-schema (net/pv/batt/load)."""

    grid = (
        pick_state(states, "sensor.p1_actief_vermogen")
        or pick_state(states, "sensor.huidig_net_vermogen")
        or pick_state(states, "sensor.power_consumed")
        or pick_state(states, "sensor.total_power")
    )

    pv = (
        pick_state(states, "sensor.solar_panels_total_power")
        or pick_state(states, "sensor.pv_total_power")
        or pick_state(states, "sensor.solax_pv_power")
        or pick_state(states, "sensor.solar_power")
    )

    batt = (
        pick_state(states, "sensor.battery_charge_discharge_power")
        or pick_state(states, "sensor.byd_seal_power")
        or pick_state(states, "sensor.battery_power")
    )

    soc = (
        pick_state(states, "sensor.battery_soc")
        or pick_state(states, "sensor.solax_battery_capacity")
        or pick_state(states, "sensor.byd_battery_soc")
    )

    ev = (
        pick_state(states, "sensor.easee_power")
        or pick_state(states, "sensor.peblar_power")
        or pick_state(states, "sensor.ev_power")
    )

    result = {
        "klant_id": KLANT_ID,
        "ts": int(time.time()),
        "version": VERSION,
        "source": "ha-addon",
    }
    if grid is not None:
        result["net_w"] = grid
    if pv is not None:
        result["pv_w"] = pv
    if batt is not None:
        result["batt_w"] = batt
    if soc is not None:
        result["batt_soc"] = soc
    if ev is not None:
        result["ev_w"] = ev

    if grid is not None or pv is not None or batt is not None:
        load = (grid or 0) + (pv or 0) - (batt or 0) - (ev or 0)
        result["load_w"] = round(load, 1)

    return result


# ── License-gate ─────────────────────────────────────────────────────────────


async def check_license(client: httpx.AsyncClient) -> Optional[dict]:
    """Check licentie → krijg MQTT-credentials terug."""
    try:
        r = await client.post(
            LICENSE_URL,
            json={
                "klant_id": KLANT_ID,
                "license_token": LICENSE_TOKEN,
                "edge_version": VERSION,
                "edge_type": "ha-addon",
            },
            timeout=15.0,
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("active"):
                state["license_ok"] = True
                state["license_checked_at"] = time.time()
                LOG.info(
                    "License OK · verloopt op %s · plan=%s",
                    data.get("expires", "?"),
                    data.get("plan", "?"),
                )
                return data
        elif r.status_code == 403:
            err = r.json().get("error", "license_invalid")
            LOG.error("License geweigerd: %s", err)
            state["license_ok"] = False
            state["errors"].append(f"license-403: {err}")
            return None
        else:
            LOG.warning("License-check ongeldig statuscode %s", r.status_code)
            return None
    except Exception as e:
        LOG.error("License-check fout: %s", e)
        state["errors"].append(f"license-exc: {e}")
        return None


# ── MQTT publish ─────────────────────────────────────────────────────────────


class MQTTPublisher:
    def __init__(self, host: str, port: int, use_ws: bool):
        self.host = host
        self.port = port
        self.use_ws = use_ws
        self.client: Optional[mqtt.Client] = None
        self.connected = False

    def connect(self, username: str, password: str):
        transport = "websockets" if self.use_ws else "tcp"
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"vp-edge-{KLANT_ID}-addon",
            transport=transport,
        )
        self.client.username_pw_set(username, password)
        if self.use_ws:
            self.client.ws_set_options(path="/mqtt")
            ctx = ssl.create_default_context()
            self.client.tls_set_context(ctx)
        else:
            self.client.tls_set()

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

        LOG.info("MQTT connecting → %s:%s (ws=%s)", self.host, self.port, self.use_ws)
        self.client.connect(self.host, self.port, keepalive=60)
        self.client.loop_start()

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.connected = True
            LOG.info("MQTT connected")
        else:
            LOG.error("MQTT connect failed rc=%s", rc)

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        self.connected = False
        LOG.warning("MQTT disconnected rc=%s", rc)

    def publish_metrics(self, metrics: dict):
        if not (self.client and self.connected):
            return False
        topic = f"vp/{KLANT_ID}/metrics"
        payload = json.dumps(metrics)
        result = self.client.publish(topic, payload, qos=0, retain=False)
        return result.rc == mqtt.MQTT_ERR_SUCCESS


# ── Health-endpoint ──────────────────────────────────────────────────────────


async def health(request):
    s = "ok" if state["license_ok"] and state["publish_count"] > 0 else (
        "degraded" if state["license_ok"] else "starting"
    )
    state["status"] = s
    return web.json_response({**state, "errors": state["errors"][-5:]})


# ── Main loop ────────────────────────────────────────────────────────────────


async def main():
    if not SUPERVISOR_TOKEN:
        LOG.fatal("Geen SUPERVISOR_TOKEN — addon draait niet binnen HA?")
        sys.exit(1)

    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    LOG.info("Health-endpoint op :8080/health")

    async with httpx.AsyncClient() as client:
        # 1. License-gate bij startup
        creds = await check_license(client)
        if not creds:
            LOG.fatal("Geen geldige license — addon stopt. Check klant_id+license_token.")
            await asyncio.sleep(60)
            sys.exit(2)

        publisher = MQTTPublisher(MQTT_HOST, MQTT_PORT, MQTT_USE_WS)
        publisher.connect(creds["mqtt_username"], creds["mqtt_password"])

        # 2. Wacht op MQTT-connect (max 10s)
        for _ in range(20):
            if publisher.connected:
                break
            await asyncio.sleep(0.5)

        last_license_check = time.time()

        # 3. Publish-loop
        while True:
            try:
                states = await ha_states(client)
                metrics = derive_metrics(states)

                if publisher.publish_metrics(metrics):
                    state["publish_count"] += 1
                    state["last_publish_at"] = time.time()
                    if state["publish_count"] % 10 == 0:
                        LOG.info("Published #%d · %s", state["publish_count"], metrics)

                # License-recheck elke 24u
                if time.time() - last_license_check > LICENSE_RECHECK_INTERVAL:
                    LOG.info("License-recheck (24u)…")
                    new_creds = await check_license(client)
                    if not new_creds:
                        LOG.fatal("License-recheck faalde — addon stopt voor handhaving.")
                        sys.exit(3)
                    if new_creds.get("mqtt_password") != creds.get("mqtt_password"):
                        LOG.info("MQTT-creds rotation — reconnect.")
                        publisher.client.disconnect()
                        publisher.connect(new_creds["mqtt_username"], new_creds["mqtt_password"])
                    creds = new_creds
                    last_license_check = time.time()

            except Exception as e:
                LOG.error("Loop-iter fout: %s", e)
                state["errors"].append(f"loop: {e}")

            await asyncio.sleep(PUBLISH_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOG.info("Stop op signaal")
        sys.exit(0)
