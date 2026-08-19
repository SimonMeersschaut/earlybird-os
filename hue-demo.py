from phue import Bridge, Group

BRIDGE_IP = '10.2.1.210'
b = Bridge(BRIDGE_IP)

# Optional: Auto-connect using cached credentials
b.connect()

group: Group = b.get_group(b.get_group_id_by_name("Kamer Simon"))
group_light_ids = [int(light_id) for light_id in group['lights']]

# Simulate a Gradual Sunrise (20-second fade-in)
# transitiontime is in deciseconds (10 deciseconds = 1 second)
sunrise_command = {
    'on': True,
    'bri': 254,
    'hue': 5000,         # Warm red/orange tone
    'sat': 200,
    'transitiontime': 200 # 20 seconds transition
}

for light_id in group_light_ids:
    b.set_light(light_id, sunrise_command)