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
            packet_id = int(time.time() * 1000)  # Use timestamp as packet ID
            
        data = {
            "timestamp": datetime.now().isoformat(),
            "packet_id": packet_id,
            "value": value,
            "device_id": f"device_{random.randint(1000, 9999)}"
        }
        
        return json.dumps(data)
    
    @staticmethod
    def unpack_data(json_str):
        """
        Unpack JSON data into a Python dictionary
        
        Args:
            json_str (str): JSON string to unpack
            
        Returns:
            dict: Unpacked data
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    
    @staticmethod
    def should_drop_packet():
        """
        Simulate packet loss (1% chance)
        
        Returns:
            bool: True if packet should be dropped
        """
        return random.random() < 0.01
    
    @staticmethod
    def should_skip_block():
        """
        Simulate block transmission skip (0.1% chance)
        
        Returns:
            bool: True if block should be skipped
        """
        return random.random() < 0.001 