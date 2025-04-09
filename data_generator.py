import random
import time
from datetime import datetime

class DataGenerator:
    def __init__(self, base_value=50, variance=10, trend=0, pattern_type="normal"):
        """
        Initialize the data generator with configurable parameters
        
        Args:
            base_value (float): The base value around which data will fluctuate
            variance (float): Maximum amount of random variation
            trend (float): Long-term trend (positive or negative)
            pattern_type (str): Type of pattern ("normal", "sinusoidal", "spike")
        """
        self.base_value = base_value
        self.variance = variance
        self.trend = trend
        self.pattern_type = pattern_type
        self.time_offset = 0
        self.last_value = base_value
        
    def generate(self):
        """
        Generate a new data point based on the configured pattern
        
        Returns:
            float: Generated data value
        """
        self.time_offset += 1
        
        if self.pattern_type == "normal":
            # Normal pattern with slight random variation
            value = self.base_value + random.uniform(-self.variance, self.variance)
        elif self.pattern_type == "sinusoidal":
            # Sinusoidal pattern
            value = self.base_value + self.variance * math.sin(self.time_offset * 0.1)
        elif self.pattern_type == "spike":
            # Occasional spikes
            if random.random() < 0.05:  # 5% chance of spike
                value = self.base_value + random.uniform(self.variance * 2, self.variance * 3)
            else:
                value = self.base_value + random.uniform(-self.variance, self.variance)
        
        # Apply trend
        value += self.trend * self.time_offset
        
        # Add some randomness to make it less predictable
        value += random.uniform(-self.variance * 0.1, self.variance * 0.1)
        
        self.last_value = value
        return value
    
    def generate_wild_data(self):
        """
        Generate a completely out-of-range value (for testing error handling)
        
        Returns:
            float: Wildly out-of-range value
        """
        return self.base_value * random.uniform(10, 100)  # 10x to 100x normal range 