import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from collections import deque
from group_5_mqtt_utils import MQTTUtils
from matplotlib.ticker import MaxNLocator
import group_5_config as config


class SubscriberGUI:
    MAX_DATA_POINTS = config.MAX_DATA_POINTS
    EXPECTED_BASE = config.EXPECTED_BASE
    EXPECTED_VARIANCE = config.EXPECTED_VARIANCE
    OUT_OF_RANGE_THRESHOLD_FACTOR = config.OUT_OF_RANGE_THRESHOLD_FACTOR

    def __init__(self, root):
        self.root = root
        self.root.title("IoT Subscriber")
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.data_points = deque(maxlen=self.MAX_DATA_POINTS)
        self.last_packet_id = None
        self.last_packet_timestamp = None
        self.missing_packets = 0
        self.out_of_range_count = 0
        self.is_connected = False

        self.setup_gui()

    def setup_gui(self):
        # Connection Frame
        connection_frame = ttk.LabelFrame(self.root, text="MQTT Connection", padding="5")
        connection_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        ttk.Label(connection_frame, text="Broker:").grid(row=0, column=0, padx=2, pady=2, sticky="w")
        self.broker_entry = ttk.Entry(connection_frame, width=20)
        self.broker_entry.insert(0, config.MQTT_BROKER_URL)
        self.broker_entry.grid(row=0, column=1, padx=2, pady=2)
        ttk.Label(connection_frame, text="Port:").grid(row=0, column=2, padx=2, pady=2, sticky="w")
        self.port_entry = ttk.Entry(connection_frame, width=6)
        self.port_entry.insert(0, config.MQTT_BROKER_PORT)
        self.port_entry.grid(row=0, column=3, padx=2, pady=2)
        ttk.Label(connection_frame, text="Topic:").grid(row=0, column=4, padx=2, pady=2, sticky="w")
        self.topic_entry = ttk.Entry(connection_frame, width=20)
        self.topic_entry.insert(0, config.MQTT_TOPIC)
        self.topic_entry.grid(row=0, column=5, padx=2, pady=2)
        self.connect_button = ttk.Button(connection_frame, text="Connect", command=self.connect_mqtt)
        self.connect_button.grid(row=0, column=6, padx=5, pady=2)
        self.disconnect_button = ttk.Button(connection_frame, text="Disconnect", command=self.disconnect_mqtt, state="disabled")
        self.disconnect_button.grid(row=0, column=7, padx=5, pady=2)

        # Data Log Frame
        data_frame = ttk.LabelFrame(self.root, text="Raw Data Log", padding="5")
        data_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.data_text = tk.Text(data_frame, height=10, width=50, state="disabled")
        self.data_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        scrollbar = ttk.Scrollbar(data_frame, command=self.data_text.yview)
        scrollbar.grid(row=0, column=1, sticky="nsew")
        self.data_text['yscrollcommand'] = scrollbar.set

        # Statistics Frame
        stats_frame = ttk.LabelFrame(self.root, text="Statistics", padding="5")
        stats_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        ttk.Label(stats_frame, text="Missing Packets:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.missing_label = ttk.Label(stats_frame, text="0", width=10)
        self.missing_label.grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(stats_frame, text="Out of Range Values:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.oor_label = ttk.Label(stats_frame, text="0", width=10)
        self.oor_label.grid(row=0, column=3, padx=5, pady=2)
        ttk.Label(stats_frame, text="Total Received:").grid(row=0, column=4, padx=5, pady=2, sticky="w")
        self.received_label = ttk.Label(stats_frame, text="0", width=10)
        self.received_label.grid(row=0, column=5, padx=5, pady=2)

        # Status Frame
        status_frame = ttk.LabelFrame(self.root, text="System Status", padding="5")
        status_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        self.status_text = tk.Text(status_frame, height=10, width=40, state="disabled")
        self.status_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        status_scrollbar = ttk.Scrollbar(status_frame, command=self.status_text.yview)
        status_scrollbar.grid(row=0, column=1, sticky="nsew")
        self.status_text['yscrollcommand'] = status_scrollbar.set

        # Plot Frame
        plot_frame = ttk.LabelFrame(self.root, text="Data Plot", padding="5")
        plot_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        self.figure = plt.Figure(figsize=(7, 3.5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.line, = self.ax.plot([], [], 'b.-')
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Value')
        self.ax.grid(True)
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.root.grid_rowconfigure(3, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

    def connect_mqtt(self):
        if self.is_connected:
            self.log_status("Already connected.")
            return
        try:
            broker = self.broker_entry.get()
            port = int(self.port_entry.get())
            self.topic = self.topic_entry.get()
            if not self.topic:
                self.log_status("MQTT Topic cannot be empty.")
                return
            self.connect_button.config(state="disabled")
            self.disconnect_button.config(state="disabled")
            self.log_status(f"Connecting to {broker}:{port}...")
            self.client.connect(broker, port, 60)
            self.client.loop_start()
        except Exception as e:
            self.log_status(f"Connection error: {e}")
            self.connect_button.config(state="normal")

    def disconnect_mqtt(self):
        if not self.is_connected:
            self.log_status("Not currently connected.")
            return
        try:
            self.log_status("Disconnecting from MQTT broker...")
            self.client.loop_stop()
            if self.topic:
                self.client.unsubscribe(self.topic)
            self.client.disconnect()
            self.log_status("Disconnected.")
            self.is_connected = False
            self.connect_button.config(state="normal")
            self.disconnect_button.config(state="disabled")
            self.broker_entry.config(state="normal")
            self.port_entry.config(state="normal")
            self.topic_entry.config(state="normal")
        except Exception as e:
            self.log_status(f"Disconnect error: {e}")
            self.is_connected = False
            self.connect_button.config(state="normal")
            self.disconnect_button.config(state="disabled")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.log_status(f"Connected to MQTT broker at {self.broker_entry.get()}:{self.port_entry.get()}")
            self.log_status(f"Subscribing to topic: {self.topic}")
            try:
                client.subscribe(self.topic)
                self.is_connected = True
                self.connect_button.config(state="disabled")
                self.disconnect_button.config(state="normal")
                self.broker_entry.config(state="disabled")
                self.port_entry.config(state="disabled")
                self.topic_entry.config(state="disabled")
                self.reset_data()
            except Exception as e:
                self.log_status(f"Subscribe error: {e}")
                self.disconnect_mqtt()
        else:
            self.log_status(f"Connection failed with code {rc}")
            self.is_connected = False
            self.connect_button.config(state="normal")
            self.disconnect_button.config(state="disabled")
            self.broker_entry.config(state="normal")
            self.port_entry.config(state="normal")
            self.topic_entry.config(state="normal")

    def on_message(self, client, userdata, msg):
        self.process_message(msg.payload)

    def process_message(self, payload):
        try:
            json_str = payload.decode('utf-8')
            data = MQTTUtils.unpack_data(json_str)
            if data and all(k in data for k in ["timestamp", "packet_id", "value", "device_id"]):
                self.process_data(data)
            elif data:
                self.log_status(f"Received malformed data: {data}")
            else:
                self.log_status(f"Failed to decode JSON: {json_str}")
        except Exception as e:
            self.log_status(f"Processing error: {e}")

    def process_data(self, data):
        current_packet_id = data["packet_id"]
        value = data["value"]
        timestamp_str = data["timestamp"]
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except Exception:
            self.log_status(f"Invalid timestamp: {timestamp_str}")
            timestamp = datetime.now()

        if self.last_packet_timestamp is None or timestamp > self.last_packet_timestamp:
            if self.last_packet_timestamp is not None and current_packet_id < self.last_packet_id:
                self.log_status(f"New session detected. Resetting packet ID from {self.last_packet_id} to {current_packet_id}.", level="info")
            elif self.last_packet_timestamp is not None and current_packet_id > self.last_packet_id:
                if current_packet_id > self.last_packet_id + 1:
                    missing = current_packet_id - self.last_packet_id - 1
                    self.missing_packets += missing
                    self.log_status(f"Detected {missing} missing packet(s) from {self.last_packet_id} to {current_packet_id}.")
            self.last_packet_id = current_packet_id
            self.last_packet_timestamp = timestamp
        else:
            self.log_status(f"Received out-of-order packet: ID {current_packet_id} after {self.last_packet_id}", level="warning")

        expected_min = self.EXPECTED_BASE - self.EXPECTED_VARIANCE * self.OUT_OF_RANGE_THRESHOLD_FACTOR
        expected_max = self.EXPECTED_BASE + self.EXPECTED_VARIANCE * self.OUT_OF_RANGE_THRESHOLD_FACTOR
        if isinstance(value, (int, float)):
            if not (expected_min <= value <= expected_max):
                self.out_of_range_count += 1
                self.log_status(f"Out of range value: {value:.2f} (Expected {expected_min:.1f}-{expected_max:.1f})", level="warning")
        else:
            self.log_status(f"Non-numeric value: {value}", level="warning")
        self.data_points.append((timestamp, value))
        self.update_raw_data_display(data)
        self.update_stats_display()
        self.update_plot()

    def update_raw_data_display(self, data):
        self.data_text.config(state="normal")
        value_str = f"{data['value']:.4f}" if isinstance(data['value'], (int, float)) else str(data['value'])
        entry = f"Time: {data['timestamp']}\n PktID: {data['packet_id']}\n Value: {value_str}\n Device: {data['device_id']}\n{'-'*30}\n"
        self.data_text.insert(tk.END, entry)
        self.data_text.see(tk.END)
        self.data_text.config(state="disabled")

    def update_stats_display(self):
        self.missing_label.config(text=str(self.missing_packets))
        self.oor_label.config(text=str(self.out_of_range_count))
        self.received_label.config(text=str(len(self.data_points)))

    def update_plot(self):
        if self.data_points:
            plot_data = [(t, v) for t, v in self.data_points if isinstance(v, (int, float))]
            if not plot_data:
                self.line.set_data([], [])
                self.canvas.draw_idle()
                return
            timestamps, values = zip(*plot_data)
            min_val, max_val = min(values), max(values)
            min_time, max_time = min(timestamps), max(timestamps)
            y_pad = (max_val - min_val) * 0.1 if max_val != min_val else 1.0
            total_seconds = (max_time - min_time).total_seconds()
            time_buffer = timedelta(seconds=1) if total_seconds == 0 else timedelta(seconds=max(total_seconds * 0.01, 1))
            self.line.set_data(timestamps, values)
            self.ax.set_ylim(min_val - y_pad, max_val + y_pad)
            self.ax.set_xlim(min_time - time_buffer, max_time + time_buffer)
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            self.ax.xaxis.set_major_locator(MaxNLocator(nbins=6, prune='both'))
            for label in self.ax.get_xticklabels():
                label.set_rotation(15)
            self.figure.subplots_adjust(bottom=0.25, left=0.15, right=0.95, top=0.95)
            self.canvas.draw_idle()
        else:
            self.line.set_data([], [])
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw_idle()

    def log_status(self, message, level="info"):
        now = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{now}] "
        if level == "warning":
            prefix += "[WARN] "
        elif level == "error":
            prefix += "[ERROR] "
        self.status_text.config(state="normal")
        self.status_text.insert(tk.END, f"{prefix}{message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state="disabled")

    def reset_data(self):
        self.data_points.clear()
        self.last_packet_id = None
        self.last_packet_timestamp = None
        self.missing_packets = 0
        self.out_of_range_count = 0
        self.missing_label.config(text="0")
        self.oor_label.config(text="0")
        self.received_label.config(text="0")
        self.line.set_data([], [])
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()
        self.data_text.config(state="normal")
        self.data_text.delete("1.0", tk.END)
        self.data_text.config(state="disabled")
        self.log_status("Data and statistics reset.")

    def on_closing(self):
        self.log_status("Shutdown requested.")
        self.disconnect_mqtt()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SubscriberGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
