
import random

class Channel:
    def __init__(
        self,
        packet_loss_prob=0.0,
        ack_loss_prob=0.0,
        forced_drop_seq=None
    ):
        self.packet_loss_prob = packet_loss_prob
        self.ack_loss_prob = ack_loss_prob
        self.forced_drop_seq = forced_drop_seq
        self.forced_drop_done = False

    def send(self, packet):
        if packet.is_ack:
            loss_probability = self.ack_loss_prob
        else:
            # Deliberately lose this sequence number once
            if (
                packet.seq == self.forced_drop_seq
                and not self.forced_drop_done
            ):
                self.forced_drop_done = True
                print(f"Channel: Packet {packet.seq} deliberately lost")
                return False

            loss_probability = self.packet_loss_prob

        if random.random() < loss_probability:
            return False

        return True
    