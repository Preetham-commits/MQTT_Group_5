# IoT MQTT Publisher-Subscriber System

This project implements an end-to-end IoT solution using MQTT protocol for data transmission between publishers and subscribers.

## Prerequisites

1. Python 3.6.5 or later
2. Eclipse Mosquitto MQTT broker
3. Required Python packages (install using `pip install -r requirements.txt`)

## Installation

1. Install Eclipse Mosquitto:
   - Windows: Download and install from https://mosquitto.org/download/
   - Linux: `sudo apt-get install mosquitto`
   - Mac: `brew install mosquitto`

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Project Structure

- `data_generator.py`: Generates random data with configurable patterns
- `mqtt_utils.py`: Utility functions for MQTT operations and data packaging
- `publisher.py`: Publisher GUI and MQTT client
- `subscriber.py`: Subscriber GUI and MQTT client
- `requirements.txt`: Python dependencies

## Usage

1. Start the Mosquitto broker:
   ```bash
   mosquitto
   ```

2. Run the publisher:
   ```bash
   python publisher.py
   ```

3. Run the subscriber:
   ```bash
   python subscriber.py
   ```

4. Configure the publisher:
   - Set broker address (default: localhost)
   - Set port (default: 1883)
   - Set topic (default: iot/data)
   - Configure data generation parameters
   - Click "Start Publishing"

5. Configure the subscriber:
   - Set broker address (default: localhost)
   - Set port (default: 1883)
   - Set topic (default: iot/data)
   - Click "Connect"

## Features

### Publisher
- Configurable data generation patterns
- Random data with controlled variance
- Simulated packet loss (1%)
- Optional block transmission skips
- Wild data generation capability

### Subscriber
- Real-time data display
- Data visualization using matplotlib
- Missing packet detection
- Out-of-range value detection
- Statistics tracking

## Notes
- The system simulates real-world conditions with:
  - 1% random packet loss
  - Occasional block transmission skips
  - Configurable data patterns
  - Error handling and recovery 