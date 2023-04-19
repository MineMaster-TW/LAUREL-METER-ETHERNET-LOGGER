#  LAUREL-METER-ETHERNET-LOGGER
Data logging code for laurel meters over ethernet.

## Background
Laurel provides configuration software for ethernet but not data acquisition over ethernet for older equipment. This code scans for laurel nodes and acquires data from the panel meters.

Tested on models (with ethernet option):
- "Laureate™ Digital Panel Meter for Process and Ratiometric Signals"
- "Laureate™ Digital Panel Meterfor Load Cell & Microvolt Input"

## How to use:
	- Run python code laurel_logger_gui.py
	- Code runs a GUI 
	- Searching for nodes
		○ Button "scan nodes" searches for laurel nodes on all LAN networks
		○ The search is based on broadcast messages from nodes every 15 seconds or so, searching takes 20 seconds.
	- Start logging logs data to a csv file "readout_data.csv" and will add an incrementing number for each log file
		○ Log files one header row
		○ Log files have n+1 columns, where n is the number of nodes detected
		○ Time is in seconds since epoch (Linux time)
	- Stopping logging usually causes logger GUI to stop responding. This is a known bug. Force quit application if this occurs.

## Data Sample Rate
This code pulls data as fast as possible and uses n threads to request data from all nodes simultaneously. The unreliable nature of the UDP protocol means that sometimes the sample frequency is inconsistent. A default UDP timeout of 500ms is set to prevent missed packets from stopping logging for too long.