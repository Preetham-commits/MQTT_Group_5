import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from mqtt_utils import MQTTUtils

class SubscriberGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("IoT Subscriber")
        
        # MQTT Client
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Data storage
        self.data_points = []
        self.last_packet_id = None
        self.missing_packets = 0
        self.out_of_range_count = 0
        
        self.setup_gui()
        
    def setup_gui(self):
        # Connection Frame
        connection_frame = ttk.LabelFrame(self.root, text="MQTT Connection", padding="5")
        connection_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        ttk.Label(connection_frame, text="Broker:").grid(row=0, column=0)
        self.broker_entry = ttk.Entry(connection_frame)
        self.broker_entry.insert(0, "localhost")
        self.broker_entry.grid(row=0, column=1)
        
        ttk.Label(connection_frame, text="Port:").grid(row=0, column=2)
        self.port_entry = ttk.Entry(connection_frame, width=5)
        self.port_entry.insert(0, "1883")
        self.port_entry.grid(row=0, column=3)
        
        ttk.Label(connection_frame, text="Topic:").grid(row=0, column=4)
        self.topic_entry = ttk.Entry(connection_frame)
        self.topic_entry.insert(0, "iot/data")
        self.topic_entry.grid(row=0, column=5)
        
        self.connect_button = ttk.Button(connection_frame, text="Connect", command=self.connect_mqtt)
        self.connect_button.grid(row=0, column=6)
        
        # Data Display Frame
        data_frame = ttk.LabelFrame(self.root, text="Data Display", padding="5")
        data_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        # Text display
        self.data_text = tk.Text(data_frame, height=10, width=60)
        self.data_text.grid(row=0, column=0, padx=5, pady=5)
        
        # Statistics Frame
        stats_frame = ttk.LabelFrame(self.root, text="Statistics", padding="5")
        stats_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        
        ttk.Label(stats_frame, text="Missing Packets:").grid(row=0, column=0)
        self.missing_label = ttk.Label(stats_frame, text="0")
        self.missing_label.grid(row=0, column=1)
        
        ttk.Label(stats_frame, text="Out of Range Values:").grid(row=0, column=2)
        self.oor_label = ttk.Label(stats_frame, text="0")
        self.oor_label.grid(row=0, column=3)
        
        # Plot Frame
        plot_frame = ttk.LabelFrame(self.root, text="Data Plot", padding="5")
        plot_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        
        self.figure = plt.Figure(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.ax = self.figure.add_subplot(111)
        self.line, = self.ax.plot([], [])
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Value')
        
    def connect_mqtt(self):
        try:
            broker = self.broker_entry.get()
            port = int(self.port_entry.get())
            topic = self.topic_entry.get()
            
            self.client.connect(broker, port)
            self.client.subscribe(topic)
            self.client.loop_start()
            self.log_status("Connected to MQTT broker")
            self.connect_button.config(state="disabled")
        except Exception as e:
            self.log_status(f"Connection error: {str(e)}")
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.log_status("Connected to MQTT broker")
        else:
            self.log_status(f"Connection failed with code {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            data = MQTTUtils.unpack_data(msg.payload.decode())
            if data:
                self.process_data(data)
        except Exception as e:
            self.log_status(f"Error processing message: {str(e)}")
    
    def process_data(self, data):
        # Check for missing packets
        if self.last_packet_id is not None:
            expected_id = self.last_packet_id + 1
            if data["packet_id"] > expected_id:
                self.missing_packets += data["packet_id"] - expected_id
                self.missing_label.config(text=str(self.missing_packets))
        
        self.last_packet_id = data["packet_id"]
        
        # Check for out of range values
        value = data["value"]
        if abs(value) > 1000:  # Example threshold
            self.out_of_range_count += 1
            self.oor_label.config(text=str(self.out_of_range_count))
            self.log_status(f"Out of range value detected: {value}")
        
        # Store data point
        timestamp = datetime.fromisoformat(data["timestamp"])
        self.data_points.append((timestamp, value))
        
        # Update display
        self.update_display(data)
        self.update_plot()
    
    def update_display(self, data):
        self.data_text.insert(tk.END, f"Time: {data['timestamp']}\n")
        self.data_text.insert(tk.END, f"Value: {data['value']}\n")
        self.data_text.insert(tk.END, f"Device: {data['device_id']}\n")
        self.data_text.insert(tk.END, "-" * 50 + "\n")
        self.data_text.see(tk.END)
        
        # Keep only last 100 lines
        if self.data_text.index("end-1c").split(".")[0] > "100":
            self.data_text.delete("1.0", "2.0")
    
    def update_plot(self):
        if len(self.data_points) > 0:
            timestamps, values = zip(*self.data_points)
            self.line.set_data(range(len(timestamps)), values)
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw()
    
    def log_status(self, message):
        print(f"Status: {message}")  # Can be replaced with GUI status display if needed

if __name__ == "__main__":
    root = tk.Tk()
    app = SubscriberGUI(root)
    root.mainloop() 