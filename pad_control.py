"""Remote control of the pad over the Bluetooth FTMS Fitness Machine Control Point (0x2AD9).

Standard op codes (FTMS spec 4.16): 0x00 request control, 0x02 set target speed (uint16, 0.01 km/h),
0x07 start/resume, 0x08 stop/pause (param 0x01 = stop, 0x02 = pause). The machine answers each write
with an indication [0x80, op, result] where result 0x01 = success.

Safety: speeds are clamped to the pad's own supported range AND the user's max; starting is only done
when the app asks (it shows a countdown first); stop is always allowed.
"""
import asyncio
import logging

log = logging.getLogger("urevo")

FTMS_FEATURE = "00002acc-0000-1000-8000-00805f9b34fb"
SPEED_RANGE = "00002ad4-0000-1000-8000-00805f9b34fb"
CONTROL_POINT = "00002ad9-0000-1000-8000-00805f9b34fb"
MACHINE_STATUS = "00002ada-0000-1000-8000-00805f9b34fb"
RESULTS = {1: "success", 2: "not supported", 3: "invalid parameter", 4: "operation failed", 5: "control not permitted"}
STATUS = {0x01: "reset", 0x02: "stopped or paused", 0x03: "stopped (safety key)", 0x04: "started or resumed",
          0x05: "target speed changed", 0xFF: "control lost"}

PAD = {"client": None, "control": False, "has_control": False, "paused": False, "feature": None, "speed_range": None,
       "status": None, "target_speed": None, "chars": []}
_pending = {}


def _on_indication(_, data: bytearray):
    data = bytes(data)
    if len(data) >= 3 and data[0] == 0x80:
        fut = _pending.pop(data[1], None)
        if fut and not fut.done():
            fut.set_result(data[2])


def _on_status(_, data: bytearray):
    data = bytes(data)
    if data:
        PAD["status"] = STATUS.get(data[0], f"status 0x{data[0]:02x}")
        if data[0] == 0x05 and len(data) >= 3:
            PAD["target_speed"] = int.from_bytes(data[1:3], "little") / 100
        if data[0] == 0xFF:
            PAD["has_control"] = False
        log.info("pad status: %s (%s)", PAD["status"], data.hex())


async def attach(client):
    """Called once per connection: discover what the pad supports and log it."""
    PAD.update(client=client, control=False, has_control=False, status=None, chars=[])
    for svc in client.services:
        for ch in svc.characteristics:
            PAD["chars"].append(f"{svc.uuid[4:8]}/{ch.uuid[4:8]} {','.join(ch.properties)}")
    log.info("pad characteristics: %s", " | ".join(PAD["chars"]))
    try:
        f = await client.read_gatt_char(FTMS_FEATURE)
        machine, target = int.from_bytes(f[0:4], "little"), int.from_bytes(f[4:8], "little")
        PAD["feature"] = {"machine": machine, "target": target, "speed_target_supported": bool(target & 0x01)}
        log.info("pad features: machine=0x%08x target=0x%08x", machine, target)
    except Exception as e:
        log.info("pad features unreadable: %r", e)
    try:
        r = await client.read_gatt_char(SPEED_RANGE)
        PAD["speed_range"] = {"min": int.from_bytes(r[0:2], "little") / 100, "max": int.from_bytes(r[2:4], "little") / 100,
                              "inc": int.from_bytes(r[4:6], "little") / 100}
        log.info("pad speed range: %s", PAD["speed_range"])
    except Exception as e:
        log.info("pad speed range unreadable: %r", e)
    if any(ch.uuid.lower() == CONTROL_POINT for svc in client.services for ch in svc.characteristics):
        try:
            await client.start_notify(CONTROL_POINT, _on_indication)
            PAD["control"] = True
        except Exception as e:
            log.info("control point indications failed: %r", e)
    try:
        await client.start_notify(MACHINE_STATUS, _on_status)
    except Exception:
        pass
    log.info("pad control point available: %s", PAD["control"])


def detach():
    PAD.update(client=None, control=False, has_control=False, paused=False)


def info():
    return {"control": PAD["control"], "speedRange": PAD["speed_range"] or {"min": 1.0, "max": 6.0, "inc": 0.5},
            "targetSpeed": PAD["target_speed"], "paused": PAD["paused"], "status": PAD["status"]}


async def _write(op, payload=b"", timeout=3.0):
    c = PAD["client"]
    if not c or not PAD["control"]:
        raise RuntimeError("The pad isn't connected or doesn't accept commands.")
    fut = asyncio.get_running_loop().create_future()
    _pending[op] = fut
    # this pad exposes the control point as write-without-response + indicate; the indication is the answer
    await c.write_gatt_char(CONTROL_POINT, bytes([op]) + payload, response=False)
    try:
        res = await asyncio.wait_for(fut, timeout)
    except asyncio.TimeoutError:
        _pending.pop(op, None)
        raise RuntimeError("The pad didn't answer.")
    if res != 1:
        raise RuntimeError(f"The pad said: {RESULTS.get(res, res)}.")
    return True


async def _ensure_control():
    if not PAD["has_control"]:
        await _write(0x00)
        PAD["has_control"] = True


async def command(action, speed=None, user_max=6.0):
    """action: start | pause | stop | speed. Returns the speed actually requested (for 'speed')."""
    await _ensure_control()
    if action == "control":                     # only take control (safe: the belt does not move)
        return None
    if action == "start":
        await _write(0x07); PAD["paused"] = False
    elif action == "pause":
        await _write(0x08, b"\x02"); PAD["paused"] = True
    elif action == "stop":
        await _write(0x08, b"\x01"); PAD["paused"] = False
    elif action == "speed":
        rng = PAD["speed_range"] or {"min": 1.0, "max": 6.0, "inc": 0.1}
        hi = min(rng["max"], user_max)
        v = max(rng["min"], min(hi, float(speed)))
        inc = rng["inc"] or 0.1
        v = round(round(v / inc) * inc, 2)
        await _write(0x02, int(round(v * 100)).to_bytes(2, "little"))
        PAD["target_speed"] = v
        return v
    else:
        raise ValueError("unknown action")
    log.info("pad command: %s", action)
    return None
