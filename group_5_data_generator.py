import random
import math
import group_5_config as config


class DataGenerator:
    def __init__(self, base_value=50, variance=10, trend=0, pattern_type="normal"):
        self.base_value = base_value
        self.variance = variance
        self.trend = trend
        self.pattern_type = pattern_type
        self.time_offset = 0
        self.last_value = base_value

    def generate(self):
        self.time_offset += 1
        if self.pattern_type == "normal":
            value = self.base_value + random.uniform(-self.variance, self.variance)
        elif self.pattern_type == "sinusoidal":
            value = self.base_value + self.variance * math.sin(self.time_offset * 0.1)
        elif self.pattern_type == "spike":
            value = (self.base_value + random.uniform(self.variance * 2, self.variance * 3)
                     if random.random() < 0.05 else self.base_value + random.uniform(-self.variance, self.variance))
        value += self.trend * self.time_offset
        value += random.uniform(-self.variance * 0.1, self.variance * 0.1)
        self.last_value = value
        return value

    def generate_wild_data(self):
        wild_multiplier = random.uniform(5, 15)
        return (self.base_value + self.base_value * wild_multiplier
                if random.random() < 0.5 else self.base_value - self.base_value * wild_multiplier)
