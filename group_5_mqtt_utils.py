import json
import time
import random
from datetime import datetime
import group_5_config as config


class MQTTUtils:
    @staticmethod
    def package_data(value, packet_id=None):
        if packet_id is None:
            packet_id = int(time.time() * 10000 + random.randint(0, 99))
        data = {
            "timestamp": datetime.now().isoformat(),
            "packet_id": packet_id,
            "value": value,
            "device_id": f"device_{random.randint(1000, 9999)}"
        }
        return json.dumps(data)

    @staticmethod
    def unpack_data(json_str):
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def should_drop_packet(drop_chance=config.DROP_PACKET_CHANCE/100):
        return random.random() < drop_chance

    @staticmethod
    def should_skip_block(skip_chance=0.001):
        return random.random() < skip_chance
