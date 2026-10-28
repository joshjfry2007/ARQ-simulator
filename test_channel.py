# test_channel.py
# Verification of the IoT Wireless Channel simulator.

import random
from packet import Packet
from channel import Channel
from config import get_config


config = get_config()
random.seed(config.seed)
channel = Channel(
    packet_loss_prob=config.loss,
    ack_loss_prob=0.0,
)

total_packets = 1000
lost_packets = 0

for i in range(total_packets):
    packet = Packet(i, device_id=config.device_id, metric=config.metric)
    delivered = channel.send(packet)
    if not delivered:
        lost_packets += 1

loss_percentage = (lost_packets / total_packets) * 100

print("--- IoT Wireless Channel Loss Test ---")
print(f"Device ID              : {config.device_id}")
print(f"Monitored Metric       : {config.metric.capitalize()} ({config.unit})")
print(f"Total telemetry packets: {total_packets}")
print(f"Lost telemetry packets : {lost_packets}")
print(f"Observed channel loss  : {loss_percentage:.2f}%")
print(f"Configured loss target : {config.loss * 100:.2f}%")
