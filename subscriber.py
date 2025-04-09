import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates  # Import DateFormatter and locator helpers
import numpy as np
from collections import deque  # Use deque for efficient fixed-size storage
from mqtt_utils import MQTTUtils

class SubscriberGUI:
    # Define a reasonable threshold for 'out of range'
    OUT_OF_RANGE_THRESHOLD_FACTOR = 5  # e.g., 5 times the typical expected range might be suspect
    MAX_DATA_POINTS = 500  # Max points to store and plot
    EXPECTED_BASE = 50  # Approximate expected baseline for OOR check (could be dynamic)
    EXPECTED_VARIANCE = 20  # Approximate expected variance for OOR check

    def __init__(self, root):
        self.root = root
        self.root.title("IoT Subscriber")

        # MQTT Client
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Data storage using deque for efficiency
        self.data_points = deque(maxlen=self.MAX_DATA_POINTS)
        self.last_packet_id = None
        self.last_packet_timestamp = None  # Added to track the timestamp of the last processed packet
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
        self.broker_entry.insert(0, "localhost")
        self.broker_entry.grid(row=0, column=1, padx=2, pady=2)

        ttk.Label(connection_frame, text="Port:").grid(row=0, column=2, padx=2, pady=2, sticky="w")
        self.port_entry = ttk.Entry(connection_frame, width=6)
        self.port_entry.insert(0, "1883")
        self.port_entry.grid(row=0, column=3, padx=2, pady=2)

        ttk.Label(connection_frame, text="Topic:").grid(row=0, column=4, padx=2, pady=2, sticky="w")
        self.topic_entry = ttk.Entry(connection_frame, width=20)
        self.topic_entry.insert(0, "iot/data")
        self.topic_entry.grid(row=0, column=5, padx=2, pady=2)

        self.connect_button = ttk.Button(connection_frame, text="Connect", command=self.connect_mqtt)
        self.connect_button.grid(row=0, column=6, padx=5, pady=2)
        self.disconnect_button = ttk.Button(connection_frame, text="Disconnect", command=self.disconnect_mqtt, state="disabled")
        self.disconnect_button.grid(row=0, column=7, padx=5, pady=2)

        # Data Display Frame (Raw Text)
        data_frame = ttk.LabelFrame(self.root, text="Raw Data Log", padding="5")
        data_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.data_text = tk.Text(data_frame, height=10, width=50, state="disabled")  # Start disabled
        self.data_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        data_scrollbar = ttk.Scrollbar(data_frame, command=self.data_text.yview)
        data_scrollbar.grid(row=0, column=1, sticky='nsew')
        self.data_text['yscrollcommand'] = data_scrollbar.set
        data_frame.grid_rowconfigure(0, weight=1)
        data_frame.grid_columnconfigure(0, weight=1)

        # Statistics Frame
        stats_frame = ttk.LabelFrame(self.root, text="Statistics", padding="5")
        stats_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        ttk.Label(stats_frame, text="Missing Packets:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.missing_label = ttk.Label(stats_frame, text="0", width=10, anchor="w")
        self.missing_label.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(stats_frame, text="Out of Range Values:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.oor_label = ttk.Label(stats_frame, text="0", width=10, anchor="w")
        self.oor_label.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(stats_frame, text="Total Received:").grid(row=0, column=4, padx=5, pady=2, sticky="w")
        self.received_label = ttk.Label(stats_frame, text="0", width=10, anchor="w")
        self.received_label.grid(row=0, column=5, padx=5, pady=2)

        # Status Frame (for connection/error messages)
        status_frame = ttk.LabelFrame(self.root, text="System Status", padding="5")
        status_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")  # Place next to Raw Data

        self.status_text = tk.Text(status_frame, height=10, width=40, state="disabled")  # Start disabled
        self.status_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        status_scrollbar = ttk.Scrollbar(status_frame, command=self.status_text.yview)
        status_scrollbar.grid(row=0, column=1, sticky='nsew')
        self.status_text['yscrollcommand'] = status_scrollbar.set
        status_frame.grid_rowconfigure(0, weight=1)
        status_frame.grid_columnconfigure(0, weight=1)

        # Plot Frame
        plot_frame = ttk.LabelFrame(self.root, text="Data Plot", padding="5")
        plot_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

        self.figure = plt.Figure(figsize=(7, 3.5), dpi=100)  # Slightly taller figure?
        self.ax = self.figure.add_subplot(111)
        self.line, = self.ax.plot([], [], 'b.-')  # Blue line with dots
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Value')
        self.ax.grid(True)  # Add grid
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))  # Format x-axis

        # NO initial tight_layout or subplots_adjust here

        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        # Configure grid weights for resizing
        self.root.grid_rowconfigure(3, weight=1)  # Let the plot expand vertically
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

    def connect_mqtt(self):
        if self.is_connected:
            self.log_status("Already connected.")
            return
        try:
            broker = self.broker_entry.get()
            port = int(self.port_entry.get())
            self.topic = self.topic_entry.get()  # Store topic for use in on_connect

            if not self.topic:
                self.log_status("Error: MQTT Topic cannot be empty.")
                return

            # Reset UI state before attempting connection
            self.connect_button.config(state="disabled")
            self.disconnect_button.config(state="disabled")
            self.log_status(f"Connecting to {broker}:{port}...")

            self.client.connect(broker, port, 60)
            self.client.loop_start()  # Start network loop in background thread
            # Status update and button changes happen in on_connect
        except ValueError:
            self.log_status("Invalid Port number.")
            self.connect_button.config(state="normal")  # Re-enable connect button on error
        except ConnectionRefusedError:
            self.log_status("Connection refused. Is the broker running?")
            self.connect_button.config(state="normal")  # Re-enable connect button on error
        except OSError as e:  # Catch other network errors like host not found
            self.log_status(f"Network error: {e}")
            self.connect_button.config(state="normal")  # Re-enable connect button on error
        except Exception as e:
            self.log_status(f"Connection error: {str(e)}")
            self.connect_button.config(state="normal")  # Re-enable connect button on error
            # Ensure loop is stopped if connection failed mid-way
            if self.client.is_connected():
                self.client.loop_stop()

    def disconnect_mqtt(self):
        if not self.is_connected:
            self.log_status("Not currently connected.")
            return
        try:
            self.log_status("Disconnecting from MQTT broker...")
            self.client.loop_stop()  # Stop network loop first
            # Check if subscribed before unsubscribing
            if hasattr(self, 'topic') and self.topic:
                try:
                    self.client.unsubscribe(self.topic)
                except Exception as unsub_e:
                    # Log unsubscribe error but continue disconnect
                    self.log_status(f"Error unsubscribing: {unsub_e}")

            self.client.disconnect()
            self.log_status("Disconnected.")
            self.is_connected = False
            self.connect_button.config(state="normal")
            self.disconnect_button.config(state="disabled")
            self.broker_entry.config(state="normal")
            self.port_entry.config(state="normal")
            self.topic_entry.config(state="normal")
            # Optionally clear plot/data on disconnect?
            # self.reset_data()
        except Exception as e:
            self.log_status(f"Error during disconnect: {str(e)}")
            # Attempt to restore reasonable UI state even on error
            self.is_connected = False  # Assume disconnect happened or is unusable
            self.connect_button.config(state="normal")
            self.disconnect_button.config(state="disabled")
            self.broker_entry.config(state="normal")
            self.port_entry.config(state="normal")
            self.topic_entry.config(state="normal")

    def on_connect(self, client, userdata, flags, rc):
        # Run GUI updates in main thread
        def _update_on_connect():
            if rc == 0:
                self.log_status(f"Connected to MQTT broker at {self.broker_entry.get()}:{self.port_entry.get()}")
                self.log_status(f"Subscribing to topic: {self.topic}")
                try:
                    client.subscribe(self.topic)
                    self.is_connected = True
                    self.connect_button.config(state="disabled")
                    self.disconnect_button.config(state="normal")
                    # Disable connection fields while connected
                    self.broker_entry.config(state="disabled")
                    self.port_entry.config(state="disabled")
                    self.topic_entry.config(state="disabled")
                    # Reset stats on new connection
                    self.reset_data()
                except Exception as sub_e:
                    self.log_status(f"Error subscribing to topic '{self.topic}': {sub_e}")
                    # Attempt to disconnect cleanly if subscribe fails
                    self.disconnect_mqtt()

            else:
                error_map = {
                    1: "Connection refused - incorrect protocol version",
                    2: "Connection refused - invalid client identifier",
                    3: "Connection refused - server unavailable",
                    4: "Connection refused - bad username or password",
                    5: "Connection refused - not authorised"
                }
                self.log_status(f"Connection failed: {error_map.get(rc, f'Unknown error code {rc}')}")
                self.is_connected = False
                self.connect_button.config(state="normal")  # Allow retry
                self.disconnect_button.config(state="disabled")
                # Ensure connection fields are enabled if connect failed
                self.broker_entry.config(state="normal")
                self.port_entry.config(state="normal")
                self.topic_entry.config(state="normal")

        if self.root:
            self.root.after(0, _update_on_connect)

    def on_message(self, client, userdata, msg):
        # Process message in main thread for GUI safety
        # Check if root window exists before scheduling
        if self.root:
            self.root.after(0, self.process_message, msg.payload)

    def process_message(self, payload):
        """Processes a received MQTT message payload."""
        try:
            json_str = payload.decode('utf-8')
            data = MQTTUtils.unpack_data(json_str)

            if data and isinstance(data, dict) and all(k in data for k in ["timestamp", "packet_id", "value", "device_id"]):
                self.process_data(data)
            elif data:
                self.log_status(f"Received malformed data: {data}")
            else:
                self.log_status(f"Failed to decode JSON: {json_str}")

        except UnicodeDecodeError:
            self.log_status("Received message with invalid encoding.")
        except Exception as e:
            # Catch other potential errors during processing
            self.log_status(f"Error processing message: {str(e)}")

    def process_data(self, data):
        """Handles validated data dictionary."""
        current_packet_id = data["packet_id"]
        value = data["value"]
        timestamp_str = data["timestamp"]

        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            self.log_status(f"Received invalid timestamp format: {timestamp_str}")
            timestamp = datetime.now()  # Use current time as fallback

        # --- Packet Sequence Handling ---
        if self.last_packet_timestamp is None:
            # First packet initialization
            self.last_packet_id = current_packet_id
            self.last_packet_timestamp = timestamp
        else:
            if timestamp > self.last_packet_timestamp:
                # Newer packet received in time order
                if current_packet_id < self.last_packet_id:
                    # Likely a publisher restart; reset sequence without flagging an error
                    self.log_status(f"New publishing session detected. Resetting packet ID from {self.last_packet_id} to {current_packet_id}.", level="info")
                elif current_packet_id > self.last_packet_id:
                    expected_id = self.last_packet_id + 1
                    if current_packet_id > expected_id:
                        missing_count = current_packet_id - expected_id
                        self.missing_packets += missing_count
                        self.log_status(f"Detected {missing_count} missing packet(s) between ID {self.last_packet_id} and {current_packet_id}")
                # Update sequence tracking
                self.last_packet_id = current_packet_id
                self.last_packet_timestamp = timestamp
            else:
                # Received a packet with an older timestamp; flag as out-of-order.
                self.log_status(f"Received out-of-order packet: ID {current_packet_id} after {self.last_packet_id}", level="warning")

        # --- Out of Range Value Detection (More Robust) ---
        expected_min = self.EXPECTED_BASE - self.EXPECTED_VARIANCE * self.OUT_OF_RANGE_THRESHOLD_FACTOR
        expected_max = self.EXPECTED_BASE + self.EXPECTED_VARIANCE * self.OUT_OF_RANGE_THRESHOLD_FACTOR

        is_out_of_range = False
        if isinstance(value, (int, float)):
            if not (expected_min <= value <= expected_max):
                is_out_of_range = True
        else:
            self.log_status(f"Received non-numeric value: {value}", level="warning")

        if is_out_of_range:
            self.out_of_range_count += 1
            self.log_status(f"Out of range value detected: {value:.2f} (Expected ~{expected_min:.1f}-{expected_max:.1f})", level="warning")

        # --- Store Data Point ---
        self.data_points.append((timestamp, value))  # deque handles maxlen automatically

        # --- Update Displays ---
        self.update_raw_data_display(data)
        self.update_stats_display()
        self.update_plot()  # Schedule plot update

    def update_raw_data_display(self, data):
        """Updates the raw data text log."""
        if not hasattr(self, 'data_text') or not self.data_text:
            return
        try:
            self.data_text.config(state="normal")  # Enable writing
            value_str = f"{data['value']:.4f}" if isinstance(data['value'], (int, float)) else str(data['value'])
            log_entry = (
                f"Time: {data['timestamp']}\n"
                f" PktID: {data['packet_id']}\n"
                f" Value: {value_str}\n"
                f" Device: {data['device_id']}\n"
                f"{'-'*30}\n"
            )
            self.data_text.insert(tk.END, log_entry)
            self.data_text.see(tk.END)  # Auto-scroll
            self.data_text.config(state="disabled")  # Disable editing
        except tk.TclError:
            self.log_status("Error updating raw data display (widget destroyed?)", level="error")

    def update_stats_display(self):
        """Updates the statistics labels."""
        if not all(hasattr(self, w) and getattr(self, w) for w in ['missing_label', 'oor_label', 'received_label']):
            return
        try:
            self.missing_label.config(text=str(self.missing_packets))
            self.oor_label.config(text=str(self.out_of_range_count))
            self.received_label.config(text=str(len(self.data_points)))
        except tk.TclError:
            self.log_status("Error updating stats display (widget destroyed?)", level="error")

    def update_plot(self):
        """Updates the matplotlib plot."""
        if not all(hasattr(self, w) and getattr(self, w) for w in ['figure', 'canvas', 'ax', 'line', 'data_points']):
            return

        if len(self.data_points) > 0:
            plot_data = [(ts, v) for ts, v in self.data_points if isinstance(v, (int, float))]
            if not plot_data:
                self.line.set_data([], [])
                self.canvas.draw_idle()
                return

            timestamps, values = zip(*plot_data)
            min_val = min(values)
            max_val = max(values)
            min_time = min(timestamps)
            max_time = max(timestamps)

            y_range = max_val - min_val
            y_padding = 1.0 if y_range == 0 else y_range * 0.10

            time_range_seconds = (max_time - min_time).total_seconds()
            time_buffer = timedelta(seconds=1) if time_range_seconds == 0 else timedelta(seconds=max(time_range_seconds * 0.01, 1))

            self.line.set_data(timestamps, values)
            self.ax.set_ylim(min_val - y_padding, max_val + y_padding)
            self.ax.set_xlim(min_time - time_buffer, max_time + time_buffer)

            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            self.ax.xaxis.set_major_locator(plt.MaxNLocator(integer=False, prune='both', nbins=6))
            plt.setp(self.ax.get_xticklabels(), rotation=15, ha="right")

            try:
                self.figure.subplots_adjust(bottom=0.25, left=0.15, right=0.95, top=0.95)
            except Exception as e:
                self.log_status(f"Plot layout adjustment failed: {e}", level="warning")

            self.canvas.draw_idle()
        else:
            self.line.set_data([], [])
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw_idle()

    def log_status(self, message, level="info"):
        """Logs messages to the status text area."""
        def _log():
            if hasattr(self, 'status_text') and self.status_text:
                try:
                    if self.status_text.winfo_exists():
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
                    else:
                        print(f"Status (widget destroyed): {message}")
                except tk.TclError:
                    print(f"Status (TCL error on widget): {message}")
            else:
                print(f"Status ({level}): {message}")

        if self.root:
            try:
                if self.root.winfo_exists():
                    self.root.after(0, _log)
                else:
                    print(f"Status (root gone): {message}")
            except tk.TclError:
                print(f"Status (root gone during after): {message}")

    def reset_data(self):
        """Resets data storage and statistics."""
        self.data_points.clear()
        self.last_packet_id = None
        self.last_packet_timestamp = None
        self.missing_packets = 0
        self.out_of_range_count = 0

        if hasattr(self, 'missing_label') and self.missing_label:
            try: self.missing_label.config(text="0")
            except tk.TclError: pass
        if hasattr(self, 'oor_label') and self.oor_label:
            try: self.oor_label.config(text="0")
            except tk.TclError: pass
        if hasattr(self, 'received_label') and self.received_label:
            try: self.received_label.config(text="0")
            except tk.TclError: pass

        if hasattr(self, 'line') and self.line:
            self.line.set_data([], [])
        if hasattr(self, 'ax') and self.ax:
            self.ax.relim()
            self.ax.autoscale_view()
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.draw_idle()

        if hasattr(self, 'data_text') and self.data_text:
            try:
                self.data_text.config(state="normal")
                self.data_text.delete("1.0", tk.END)
                self.data_text.config(state="disabled")
            except tk.TclError:
                self.log_status("Error clearing data text (widget destroyed?)", level="warning")

        self.log_status("Data and statistics reset.")

    def on_closing(self):
        """Handles window close event."""
        self.log_status("Shutdown requested.")
        self.disconnect_mqtt()
        if self.root:
            self.root.destroy()
            self.root = None

if __name__ == "__main__":
    root = tk.Tk()
    app = SubscriberGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
