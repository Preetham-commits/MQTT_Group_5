import json
import time
import random
from datetime import datetime

class MQTTUtils:
    @staticmethod
    def package_data(value, packet_id=None):
        """
        Package data into a JSON object with timestamp and packet ID

        Args:
            value (float): The data value to package
            packet_id (int, optional): Packet identifier. If None, will be generated

        Returns:
            str: JSON string containing the packaged data
        """
        if packet_id is None:
            # Use a more robust way to get unique IDs if multiple publishers start simultaneously
            # For this example, sequential ID managed by publisher is better.
            # Fallback if publisher doesn't provide one:
            packet_id = int(time.time() * 10000 + random.randint(0,99))


        data = {
            "timestamp": datetime.now().isoformat(), # Use ISO format for standard compatibility
            "packet_id": packet_id,
            "value": value,
            "device_id": f"device_{random.randint(1000, 9999)}" # Simple random device ID per packet
        }

        return json.dumps(data)

    @staticmethod
    def unpack_data(json_str):
        """
        Unpack JSON data into a Python dictionary

        Args:
            json_str (str): JSON string to unpack

        Returns:
            dict: Unpacked data, or None if decoding fails
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None # Return None on error

    @staticmethod
    def should_drop_packet(drop_chance=0.01): # Default to 1%
        """
        Simulate packet loss based on a given probability.

        Args:
            drop_chance (float): Probability (0.0 to 1.0) of dropping the packet.

        Returns:
            bool: True if packet should be dropped
        """
        return random.random() < drop_chance

    @staticmethod
    def should_skip_block(skip_chance=0.001): # Default to 0.1%
        """
        Simulate block transmission skip based on a given probability.

        Args:
            skip_chance (float): Probability (0.0 to 1.0) of skipping the block.

        Returns:
            bool: True if block should be skipped
        """
        return random.random() < skip_chance