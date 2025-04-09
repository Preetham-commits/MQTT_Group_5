import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
import json
import time
import threading
from data_generator import DataGenerator
from mqtt_utils import MQTTUtils

class PublisherGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("IoT Publisher")
        
        # MQTT Client
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        
        # Data Generator
        self.data_generator = None
        self.publishing = False
        self.publish_thread = None
        
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
        
        # Data Generation Frame
        data_frame = ttk.LabelFrame(self.root, text="Data Generation", padding="5")
        data_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        ttk.Label(data_frame, text="Base Value:").grid(row=0, column=0)
        self.base_value_entry = ttk.Entry(data_frame, width=10)
        self.base_value_entry.insert(0, "50")
        self.base_value_entry.grid(row=0, column=1)
        
        ttk.Label(data_frame, text="Variance:").grid(row=0, column=2)
        self.variance_entry = ttk.Entry(data_frame, width=10)
        self.variance_entry.insert(0, "10")
        self.variance_entry.grid(row=0, column=3)
        
        ttk.Label(data_frame, text="Pattern:").grid(row=0, column=4)
        self.pattern_var = tk.StringVar(value="normal")
        pattern_combo = ttk.Combobox(data_frame, textvariable=self.pattern_var, 
                                   values=["normal", "sinusoidal", "spike"])
        pattern_combo.grid(row=0, column=5)
        
        self.start_button = ttk.Button(data_frame, text="Start Publishing", 
                                     command=self.start_publishing)
        self.start_button.grid(row=0, column=6)
        
        # Status Frame
        status_frame = ttk.LabelFrame(self.root, text="Status", padding="5")
        status_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        
        self.status_text = tk.Text(status_frame, height=10, width=60)
        self.status_text.grid(row=0, column=0)
        
    def connect_mqtt(self):
        try:
            broker = self.broker_entry.get()
            port = int(self.port_entry.get())
            self.client.connect(broker, port)
            self.client.loop_start()
            self.log_status("Connected to MQTT broker")
            self.connect_button.config(state="disabled")
        except Exception as e:
            self.log_status(f"Connection error: {str(e)}")
    
    def start_publishing(self):
        if not self.publishing:
            try:
                base_value = float(self.base_value_entry.get())
                variance = float(self.variance_entry.get())
                pattern = self.pattern_var.get()
                
                self.data_generator = DataGenerator(base_value, variance, 0, pattern)
                self.publishing = True
                self.publish_thread = threading.Thread(target=self.publish_loop)
                self.publish_thread.daemon = True
                self.publish_thread.start()
                self.start_button.config(text="Stop Publishing")
                self.log_status("Started publishing data")
            except ValueError:
                self.log_status("Invalid input values")
        else:
            self.publishing = False
            self.start_button.config(text="Start Publishing")
            self.log_status("Stopped publishing data")
    
    def publish_loop(self):
        packet_id = 0
        while self.publishing:
            try:
                if not MQTTUtils.should_skip_block():
                    value = self.data_generator.generate()
                    if not MQTTUtils.should_drop_packet():
                        topic = self.topic_entry.get()
                        payload = MQTTUtils.package_data(value, packet_id)
                        self.client.publish(topic, payload)
                        self.log_status(f"Published: {payload}")
                    packet_id += 1
                time.sleep(1)  # Adjust frequency as needed
            except Exception as e:
                self.log_status(f"Publishing error: {str(e)}")
                time.sleep(1)
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.log_status("Connected to MQTT broker")
        else:
            self.log_status(f"Connection failed with code {rc}")
    
    def on_publish(self, client, userdata, mid):
        pass  # Can be used for confirmation if needed
    
    def log_status(self, message):
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = PublisherGUI(root)
    root.mainloop() 