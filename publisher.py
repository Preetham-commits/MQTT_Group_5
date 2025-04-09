import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
import time
import threading
import random
from datetime import datetime
from data_generator import DataGenerator
from mqtt_utils import MQTTUtils

class PublisherGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("IoT Publisher")
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
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
        self.connect_button.grid(row=0, column=6, padx=5)

        # Data Generation Frame
        data_frame = ttk.LabelFrame(self.root, text="Data Generation", padding="5")
        data_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ttk.Label(data_frame, text="Base Value:").grid(row=0, column=0)
        self.base_value_entry = ttk.Entry(data_frame, width=10)
        self.base_value_entry.insert(0, "50")
        self.base_value_entry.grid(row=0, column=1, padx=2)
        ttk.Label(data_frame, text="Variance:").grid(row=0, column=2)
        self.variance_entry = ttk.Entry(data_frame, width=10)
        self.variance_entry.insert(0, "10")
        self.variance_entry.grid(row=0, column=3, padx=2)
        ttk.Label(data_frame, text="Pattern:").grid(row=0, column=4)
        self.pattern_var = tk.StringVar(value="normal")
        pattern_combo = ttk.Combobox(data_frame, textvariable=self.pattern_var,
                                     values=["normal", "sinusoidal", "spike"], width=10)
        pattern_combo.grid(row=0, column=5, padx=2)
        self.start_button = ttk.Button(data_frame, text="Start Publishing", state="disabled",
                                       command=self.start_publishing)
        self.start_button.grid(row=0, column=6, padx=5)

        # Status Frame
        status_frame = ttk.LabelFrame(self.root, text="Status", padding="5")
        status_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        self.status_text = tk.Text(status_frame, height=10, width=70)
        self.status_text.grid(row=0, column=0)
        scrollbar = ttk.Scrollbar(status_frame, command=self.status_text.yview)
        scrollbar.grid(row=0, column=1, sticky="nsew")
        self.status_text['yscrollcommand'] = scrollbar.set

    def connect_mqtt(self):
        if self.client.is_connected():
            self.log_status("Already connected.")
            return
        try:
            broker = self.broker_entry.get()
            port = int(self.port_entry.get())
            self.client.connect(broker, port, 60)
            self.client.loop_start()
        except Exception as e:
            self.log_status(f"Connection error: {e}")
            self.connect_button.config(state="normal")

    def start_publishing(self):
        if not self.client.is_connected():
            self.log_status("Not connected to MQTT broker.")
            return
        if not self.publishing:
            try:
                base_value = float(self.base_value_entry.get())
                variance = float(self.variance_entry.get())
                pattern = self.pattern_var.get()
                if variance < 0:
                    self.log_status("Variance cannot be negative.")
                    return
                self.data_generator = DataGenerator(base_value, variance, 0, pattern)
                self.publishing = True
                topic = self.topic_entry.get()
                if not topic:
                    self.log_status("MQTT Topic cannot be empty.")
                    self.publishing = False
                    return
                self.publish_thread = threading.Thread(target=self.publish_loop, args=(topic,))
                self.publish_thread.daemon = True
                self.publish_thread.start()
                self.start_button.config(text="Stop Publishing")
                self.log_status(f"Started publishing to '{topic}'")
            except Exception as e:
                self.log_status(f"Error starting publisher: {e}")
                self.publishing = False
                self.start_button.config(text="Start Publishing")
        else:
            self.publishing = False
            self.start_button.config(text="Start Publishing")
            self.log_status("Stopped publishing.")

    def publish_loop(self, topic):
        packet_id = 0
        while self.publishing:
            try:
                if MQTTUtils.should_skip_block():
                    skip_duration = random.uniform(2, 5)
                    self.log_status(f"Simulating block skip for {skip_duration:.1f}s...")
                    time.sleep(skip_duration)
                    continue
                if random.random() < 0.005:
                    value = self.data_generator.generate_wild_data() if self.data_generator else None
                    log_prefix = "[WILD DATA] "
                else:
                    value = self.data_generator.generate() if self.data_generator else None
                    log_prefix = ""
                if MQTTUtils.should_drop_packet():
                    self.log_status(f"{log_prefix}Simulating packet drop (ID: {packet_id})")
                    packet_id += 1
                    time.sleep(1)
                    continue
                payload = MQTTUtils.package_data(value, packet_id)
                if self.client.is_connected():
                    result, mid = self.client.publish(topic, payload)
                    if result == mqtt.MQTT_ERR_SUCCESS:
                        self.log_status(f"{log_prefix}Published (ID: {packet_id}): {value:.2f}")
                    else:
                        self.log_status(f"Failed to publish (ID: {packet_id}). Error code: {result}")
                        if result == mqtt.MQTT_ERR_NO_CONN:
                            self.log_status("Disconnected during publish. Stopping.")
                            self.publishing = False
                else:
                    self.log_status("Client disconnected. Stopping publish loop.")
                    self.publishing = False
                packet_id += 1
                time.sleep(1)
            except Exception as e:
                self.log_status(f"Publishing loop error: {e}")
                if not self.client.is_connected():
                    self.log_status("Client disconnected. Stopping publish loop.")
                    self.publishing = False
                time.sleep(2)
        self.log_status("Publishing loop finished.")
        self.root.after(0, lambda: self.start_button.config(text="Start Publishing"))

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.log_status(f"Connected to MQTT broker: {self.broker_entry.get()}:{self.port_entry.get()}")
            self.connect_button.config(state="disabled")
            self.start_button.config(state="normal")
        else:
            self.log_status(f"Connection failed with code {rc}")
            self.connect_button.config(state="normal")
            self.start_button.config(state="disabled")
            self.publishing = False

    def on_publish(self, client, userdata, mid):
        # Publish acknowledgment (not used for QoS 0)
        pass

    def log_status(self, message):
        now = datetime.now().strftime("%H:%M:%S")
        entry = f"[{now}] {message}\n"
        self.status_text.insert(tk.END, entry)
        self.status_text.see(tk.END)

    def on_closing(self):
        self.log_status("Shutdown requested. Disconnecting...")
        self.publishing = False
        if self.publish_thread and self.publish_thread.is_alive():
            self.publish_thread.join(timeout=1.5)
        if self.client.is_connected():
            self.client.loop_stop()
            self.client.disconnect()
            self.log_status("Disconnected from MQTT broker.")
        else:
            self.log_status("Already disconnected.")
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = PublisherGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
