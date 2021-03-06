##################################################################
# COMP3331/9331 Computer Networks and Applications 
# Assignment 2 | Term 2, 2021
# By Sean Go (z5310199)
#
# >>> Python Verion Used: 3.8.5
##################################################################

##################################################################
# Imports
##################################################################

import sys
import socket
import select
from helper import *

##################################################################
# Constants
##################################################################

SENDER_ERROR = \
    'USAGE: python sender.py receiver_host_ip receiver_port ' \
    + 'FileToSend.txt MWS MSS timeout pdrop seed'
PDROP_ERROR = 'Pdrop parameter must be between 0 and 1'
MSS_ERROR = 'Maximum Segment Size must be greater than 0'

##################################################################
# PTP
##################################################################

# Parse commandline arguments
if (len(sys.argv) != 9): exit(SENDER_ERROR)
try:
    ip, port, filename, MWS, MSS, timeout, pdrop, seed = (
        sys.argv[1], int(sys.argv[2]), 
        sys.argv[3], int(sys.argv[4]), 
        int(sys.argv[5]), float(sys.argv[6]), 
        float(sys.argv[7]), sys.argv[8], 
    )
except: exit(SENDER_ERROR)

# Basic error handling
if not 0 < pdrop < 1: exit(PDROP_ERROR)
if MSS <= 0: exit(MSS_ERROR)

# Set initial sequence and acknowledgement number
seq, ack = 121, 0

# Calculate window size
window_length = int(MWS/MSS)

# Create UDP socket client
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Instantiate sender class
sender = Sender(client, seq, ack, window_length, (ip, port))
sender.set_PL_module(seed, pdrop)

# Opening handshake
sender.send(Data.NONE, Packet.SYN, handshake=True)
sender.receive(handshake=True)
sender.send(Data.NONE, Packet.ACK, handshake=True)

# Polled send and receive functions
def poll_send():
    global packet
    _, w, _ = select.select([], [client], [], timeout/1000)
    while w and not sender.is_full() and packet:
        if sender.PL_module(): sender.send(packet, Packet.DATA)
        else: sender.drop(packet, Packet.DATA)
        packet = file.read(MSS)

def poll_receive():
    r, w, e = select.select([client], [], [], timeout/1000)
    if r: sender.receive()
    if not (r or w or e): 
        for i in sender.window.data_to_resend(): sender.resend(*i, Packet.DATA)

# Open file for reading. If the file does not exist, throw error
with open(filename, "r") as file:
    packet = file.read(MSS)
    while packet:
        poll_send()
        poll_receive()
    while not sender.is_empty(): poll_receive()
    # Initiate teardown -> no connection or teardown packets will be dropped
    sender.send(Data.NONE, Packet.FIN, handshake=True)
    sender.receive(handshake=True)
    sender.send(Data.NONE, Packet.ACK, handshake=True)
    
# Create log file
with open("Sender_log.txt", "w") as logfile:
    for a, b, c, d, e, f in sender.get_log():
        logfile.write(f"{a:<5} {b:<12} {c:<4} {d:<8} {f:<6} {e:<6}\n")
    tot_data, num_seg, drp_pkt, re_seg, dup_ack = sender.get_stats()
    logfile.write("\n--------- Log File Statistics ---------\n\n")
    logfile.write(f"Total Data Transferred (bytes):  {tot_data}\n")
    logfile.write(f"No. Data Segments Sent:          {num_seg}\n")
    logfile.write(f"No. Packets Dropped:             {drp_pkt}\n")
    logfile.write(f"No. Retransmitted Segments:      {re_seg}\n")
    logfile.write(f"No. Duplicate Acknowledgements:  {dup_ack}\n\n")
