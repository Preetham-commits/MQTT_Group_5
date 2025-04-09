import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
import json
import time
import threading
import random
from datetime import datetime # <-- ADDED THIS IMPORT
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

        self.start_button = ttk.Button(data_frame, text="Start Publishing", state="disabled", # Start disabled
                                     command=self.start_publishing)
        self.start_button.grid(row=0, column=6, padx=5)

        # Status Frame
        status_frame = ttk.LabelFrame(self.root, text="Status", padding="5")
        status_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

        self.status_text = tk.Text(status_frame, height=10, width=70) # Increased width slightly
        self.status_text.grid(row=0, column=0)
        # Add scrollbar to status text
        scrollbar = ttk.Scrollbar(status_frame, command=self.status_text.yview)
        scrollbar.grid(row=0, column=1, sticky='nsew')
        self.status_text['yscrollcommand'] = scrollbar.set

    def connect_mqtt(self):
        if self.client.is_connected():
            self.log_status("Already connected.")
            return
        try:
            broker = self.broker_entry.get()
            port = int(self.port_entry.get())
            self.client.connect(broker, port, 60) # Added keepalive
            self.client.loop_start()
            # Status logged via on_connect callback
            # Button states handled in on_connect
        except ValueError:
             self.log_status("Invalid Port number.")
        except ConnectionRefusedError:
             self.log_status("Connection refused. Is the broker running?")
        except OSError as e: # Catch other network errors like host not found
            self.log_status(f"Network error: {e}")
        except Exception as e:
            self.log_status(f"Connection error: {str(e)}")
            # Explicitly ensure button state is correct on failure before on_connect might fire
            self.connect_button.config(state="normal")
            self.start_button.config(state="disabled")

    def start_publishing(self):
        if not self.client.is_connected():
             self.log_status("Cannot publish: Not connected to MQTT broker.")
             return

        if not self.publishing:
            try:
                base_value = float(self.base_value_entry.get())
                variance = float(self.variance_entry.get())
                pattern = self.pattern_var.get()

                # Validate inputs
                if variance < 0:
                    self.log_status("Variance cannot be negative.")
                    return

                self.data_generator = DataGenerator(base_value, variance, 0, pattern) # Trend is fixed at 0 for now
                self.publishing = True
                # Pass the current topic to the thread
                topic = self.topic_entry.get()
                if not topic:
                    self.log_status("Error: MQTT Topic cannot be empty.")
                    self.publishing = False
                    return

                self.publish_thread = threading.Thread(target=self.publish_loop, args=(topic,))
                self.publish_thread.daemon = True # Ensure thread exits when main program exits
                self.publish_thread.start()
                self.start_button.config(text="Stop Publishing")
                self.log_status(f"Started publishing data to topic '{topic}'")
            except ValueError:
                self.log_status("Invalid input for Base Value or Variance (must be numbers).")
            except Exception as e:
                 self.log_status(f"Error starting publisher: {str(e)}")
                 self.publishing = False # Ensure state is correct
                 self.start_button.config(text="Start Publishing") # Reset button state
        else:
            self.publishing = False
            # Wait briefly for the thread to notice the flag (optional but good practice)
            # if self.publish_thread and self.publish_thread.is_alive():
            #     self.publish_thread.join(timeout=1.5)
            self.start_button.config(text="Start Publishing")
            self.log_status("Stopped publishing data.")

    def publish_loop(self, topic):
        packet_id = 0
        wild_data_chance = 0.005 # 0.5% chance to send wild data
        skip_block_chance = 0.001 # Reusing skip_block logic chance

        while self.publishing:
            try:
                # Simulate occasional block skip before generating any data
                if MQTTUtils.should_skip_block(skip_block_chance): # Pass chance for clarity
                    skip_duration = random.uniform(2, 5) # Skip for 2-5 seconds
                    self.log_status(f"Simulating block skip for {skip_duration:.1f}s...")
                    time.sleep(skip_duration)
                    continue # Skip the rest of this loop iteration

                # Decide whether to generate normal or wild data
                if random.random() < wild_data_chance:
                    # Ensure data_generator exists before calling methods on it
                    if self.data_generator:
                        value = self.data_generator.generate_wild_data()
                        log_prefix = "[WILD DATA] "
                    else:
                        # Should not happen if start logic is correct, but safeguard
                        self.log_status("Error: Data generator missing in loop.")
                        time.sleep(1)
                        continue
                else:
                    if self.data_generator:
                        value = self.data_generator.generate()
                        log_prefix = ""
                    else:
                         self.log_status("Error: Data generator missing in loop.")
                         time.sleep(1)
                         continue

                # Simulate packet drop *before* packaging and sending
                if MQTTUtils.should_drop_packet():
                    self.log_status(f"{log_prefix}Simulating packet drop (ID: {packet_id})")
                    # Still increment packet_id even if dropped, as the ID was 'generated'
                    packet_id += 1
                    time.sleep(1) # Maintain publishing interval even on drop
                    continue # Skip publishing this value

                # If not dropped, package and publish
                payload = MQTTUtils.package_data(value, packet_id)
                # Ensure client is still connected before publishing
                if self.client.is_connected():
                    result, mid = self.client.publish(topic, payload)
                    if result == mqtt.MQTT_ERR_SUCCESS:
                        self.log_status(f"{log_prefix}Published (ID: {packet_id}): {value:.2f}")
                    else:
                         self.log_status(f"Failed to publish (ID: {packet_id}). Error code: {result}")
                         # If publish fails (e.g., disconnected), might need to stop
                         if result == mqtt.MQTT_ERR_NO_CONN:
                             self.log_status("Disconnected during publish. Stopping.")
                             self.publishing = False # Signal stop
                             # No break here, let the loop condition handle exit

                else:
                     self.log_status("Client disconnected. Stopping publish loop.")
                     self.publishing = False # Signal stop

                packet_id += 1
                time.sleep(1)  # Adjust frequency as needed

            except AttributeError as e:
                 # This can happen if start is clicked before connect/data_generator is None
                 # Or if self.data_generator becomes None unexpectedly
                 self.log_status(f"Error: Missing attribute, likely data generator issue ({e}). Stopping.")
                 self.publishing = False # Stop the loop
                 break # Exit loop
            except Exception as e:
                self.log_status(f"Publishing loop error: {str(e)}")
                # Decide if the error is critical and requires stopping
                if not self.client.is_connected():
                     self.log_status("Client disconnected, stopping loop.")
                     self.publishing = False # Stop loop if disconnected
                time.sleep(2) # Wait a bit longer after an error

        self.log_status("Publishing loop finished.")
        # Ensure button text is reset when loop finishes naturally or by error
        # Use root.after to schedule this GUI update from the thread
        def _reset_button():
             if self.start_button:
                 self.start_button.config(text="Start Publishing")
        if self.root:
            self.root.after(0, _reset_button)


    def on_connect(self, client, userdata, flags, rc):
        # Use connect callback to log connection status and manage button states
        # Run GUI updates in main thread
        def _update_on_connect():
            if rc == 0:
                self.log_status(f"Connected to MQTT broker: {self.broker_entry.get()}:{self.port_entry.get()}")
                self.connect_button.config(state="disabled")
                self.start_button.config(state="normal") # Enable start only on successful connect
            else:
                error_map = {
                    1: "Connection refused - incorrect protocol version",
                    2: "Connection refused - invalid client identifier",
                    3: "Connection refused - server unavailable",
                    4: "Connection refused - bad username or password",
                    5: "Connection refused - not authorised"
                }
                self.log_status(f"Connection failed: {error_map.get(rc, f'Unknown error code {rc}')}")
                self.connect_button.config(state="normal") # Allow retry
                self.start_button.config(state="disabled") # Disable start if not connected
                # Consider stopping the loop if it was started somehow before connection failed
                self.publishing = False
                # No need to set button text here, loop exit handles it

        if self.root:
            self.root.after(0, _update_on_connect)

    def on_publish(self, client, userdata, mid):
        # This confirms the message reached the broker, useful for QoS 1 or 2
        # self.log_status(f"Publish acknowledged by broker (MID: {mid})")
        pass # Keep it simple for QoS 0

    def log_status(self, message):
        # Ensure updates happen in the main thread for Tkinter safety
        def _log():
            # Check if the root window and text widget still exist
            if self.root and hasattr(self, 'status_text') and self.status_text:
                try:
                    now = datetime.now().strftime("%H:%M:%S") # datetime is now imported
                    self.status_text.insert(tk.END, f"[{now}] {message}\n")
                    self.status_text.see(tk.END) # Auto-scroll
                except tk.TclError:
                    # Handle case where the widget might be destroyed during shutdown
                    print(f"Status (widget gone): {message}")
            else:
                 print(f"Status (no GUI): {message}") # Fallback if GUI is gone

        # Schedule the GUI update in the main thread
        if self.root:
            try:
                self.root.after(0, _log)
            except tk.TclError:
                 # Handle case where root window is destroyed during shutdown
                 print(f"Status (root gone): {message}")

    def on_closing(self):
        # Gracefully disconnect MQTT client and stop thread
        self.log_status("Shutdown requested. Disconnecting...")
        self.publishing = False # Signal thread to stop
        if self.publish_thread and self.publish_thread.is_alive():
             self.log_status("Waiting for publish thread to finish...")
             # Wait a short time for the thread to exit cleanly
             self.publish_thread.join(timeout=1.5)
             if self.publish_thread.is_alive():
                 self.log_status("Publish thread did not stop gracefully.")

        if self.client.is_connected():
            self.client.loop_stop() # Stop network loop
            self.client.disconnect()
            self.log_status("Disconnected from MQTT broker.")
        else:
            self.log_status("Already disconnected or never connected.")

        self.root.destroy() # Close the window


if __name__ == "__main__":
    root = tk.Tk()
    app = PublisherGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing) # Handle window close gracefully
    root.mainloop()