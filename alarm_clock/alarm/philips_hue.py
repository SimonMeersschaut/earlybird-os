"""Philips Hue wakeup implementation."""

BRIDGE_IP = "10.2.1.210"

from phue import Bridge

class PhilipsHueSunrise:
    """Trigger a gradual sunrise on the configured Philips Hue group."""

    def __init__(self, group_name: str, bridge_ip: str = BRIDGE_IP) -> None:
        self.group_name = group_name
        self.bridge_ip = bridge_ip
        self._bridge = None
        # self._get_bridge()

    def _get_bridge(self):
        if self._bridge is None:
            self._bridge = Bridge(self.bridge_ip)
            self._bridge.connect()
        return self._bridge

    def wake(self) -> None:
        try:
            bridge = self._get_bridge()
        except:
            print("Could not connect to the bridge.")
            return
        group = bridge.get_group(bridge.get_group_id_by_name(self.group_name))
        command = {
            "on": True,
            "bri": 254,
            "hue": 5000,
            "sat": 200,
            "transitiontime": 200,
        }
        for light_id in group["lights"]:
            bridge.set_light(int(light_id), command)
