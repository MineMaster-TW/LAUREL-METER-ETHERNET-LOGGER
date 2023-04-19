import socket

from enum import Enum
import tkinter as tk
import threading
import time
import csv
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

class MeasurementType(Enum):
    CURRENT = "CURRENT"
    PEAK = "PEAK"
    VALLEY = "VALLEY"

def send_laurel_command(server_address, server_port, device_address:int, command_function, sub_command, response_length=1024, timeout=0.5):
    message = f"*{device_address}{command_function}{sub_command}\r\n"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((server_address, server_port))
        s.sendall(message.encode())
        return s.recv(response_length)


def get_laurel_value(server, device_address=1, measurement_to_get=MeasurementType.CURRENT, port=502) -> float:
    if measurement_to_get == MeasurementType.CURRENT:
        response_bytes = send_laurel_command(server, port, device_address, "B", 1)
    elif measurement_to_get == MeasurementType.PEAK:
        response_bytes = send_laurel_command(server, port, device_address, "B", 2)
    elif measurement_to_get == MeasurementType.VALLEY:
        response_bytes = send_laurel_command(server, port, device_address, "B", 3)

    return float(response_bytes.decode().strip())


def scan_udp_broadcasts(port=63179, duration=20):
    start_time = time.time()
    print(f"Scanning for nodes")

    # Create a UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        # Set the socket options to allow receiving broadcasts
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Bind the socket to the wildcard address and port
        s.bind(('0.0.0.0', port))

        # Set a timeout for the socket to prevent blocking indefinitely
        s.settimeout(1)

        # Collect unique IP and MAC addresses
        devices = defaultdict(set)
        while time.time() - start_time < duration:
            try:
                data, addr = s.recvfrom(1024)
                ip_address = addr[0]
                mac_address = data[-17:]
                devices[ip_address].add(mac_address)

            except socket.timeout:
                pass

    return [(ip, mac) for ip, mac_set in devices.items() for mac in mac_set]

def get_next_log_filename(base_name):
    index = 0
    while True:
        log_filename = f"{base_name}_{index}.csv"
        if not os.path.exists(log_filename):
            return log_filename
        index += 1

event = threading.Event()
# Function to collect data from nodes
def collect_data(node_dict, seconds_between_samples=0.1):
    print(f"logging on nodes {node_dict}")
    file_name = get_next_log_filename("readout_data")
    nodes = []
    last_time = time.time()
    for ip,mac in node_dict:
        nodes.append(ip)
    with open(file_name, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["Time"] + nodes)
    
    def get_values(ip):
        value = get_laurel_value(ip)
        return (ip, value)

    with ThreadPoolExecutor() as executor:
        while collect_data_flag:
            if event.is_set():
                executor.shutdown()
                print("event set, exiting")
                time.sleep(1)
                break
            while time.time() - last_time < seconds_between_samples:
                time.sleep(0.0001)
            
            node_values = []
            last_time = time.time()
            futures = [executor.submit(get_values, ip) for ip in nodes]
            results = [future.result() for future in futures]

            with open(file_name, "a", newline="") as csvfile:
                csvwriter = csv.writer(csvfile)
                for ip, value in results:
                    node_values.append(value)
                    readouts[ip].set(f"{ip}: {value}")
                csvwriter.writerow([time.time()] + node_values)
    print("loop ended!")

# Button callbacks
def scan_nodes():
    global status_label
    global root
    status_label.configure(text="Status: Scanning for Nodes (Takes 20s)")
    root.update()
    global node_dict
    global node_labels
    global readouts
    # reset node dict and destroy existing labels
    node_dict = {} # delete and clear node dict
    for ip in node_labels: # delete and clear labels
        node_labels[ip].destroy()
    node_labels = {}
    readouts = {} # delete and clear readouts

    node_dict = scan_udp_broadcasts()
    print(f"Found nodes: {node_dict}")
    status_label.configure(text="Status: Done Scanning")

    for ip, mac in node_dict:
        readouts[ip] = tk.StringVar(value=f"{ip}: N/A")
        node_labels[ip] = tk.Label(main_frame, textvariable=readouts[ip])
        node_labels[ip].pack()

def start_stop_logging():
    global status_label
    global collect_data_flag
    global data_collection_thread
    global event
    if not collect_data_flag:
        event.clear()
        print("Staring Log")
        status_label.configure(text="Status: Logging To File")
        collect_data_flag = True
        data_collection_thread = threading.Thread(target=collect_data, args=(node_dict,))
        data_collection_thread.start()
        print(data_collection_thread.is_alive())
        print(data_collection_thread)
    else:
        print("Stopping Log")
        status_label.configure(text="Status: Stopped Scanning")
        root.update()
        print("setting event")
        # event.set()
        print(f"thread is alive: {data_collection_thread.is_alive()}")
        collect_data_flag = False
        print("joining thread")
        data_collection_thread.join()
        print("join complete")

# GUI setup
root = tk.Tk()
root.geometry("300x200")
root.title("Node Logger")

main_frame = tk.Frame(root)
main_frame.pack()

status_label = tk.Label(main_frame, text="Status: Idle")
status_label.pack()

scan_button = tk.Button(main_frame, text="Scan Nodes", command=scan_nodes)
scan_button.pack()

start_button = tk.Button(main_frame, text="Start/Stop Logging", command=start_stop_logging)
start_button.pack()


node_label = tk.Label(main_frame, text="Known nodes and Current Values")
node_label.pack()
readouts = {}
node_dict = {"10.11.1.13": "N/A", "10.11.1.105": "N/A"}
node_labels = {}

for ip in node_dict:
    if ip not in readouts:
        readouts[ip] = tk.StringVar(value=f"{ip}: {node_dict[ip]}")
        node_labels[ip] = tk.Label(main_frame, textvariable=readouts[ip])
        node_labels[ip].pack()

collect_data_flag = False

root.mainloop()