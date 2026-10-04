from packet import Packet
from channel import Channel
from config import get_config
import random


config = get_config()
random.seed(config.seed)
channel = Channel(
    pack_loss_prob=config.loss,
    ack_loss_prob=0.0
)

total_packets = 1000
lost_packets = 0


for i in range(total_packets):
    packet = Packet(i, f"data-{i}")

    delivered = channel.send(packet)

    if not delivered:
        lost_packets += 1


loss_percentage = (lost_packets / total_packets) * 100

print("Total packets:", total_packets)
print("Lost packets:", lost_packets)
print("Observed loss:", loss_percentage, "%")