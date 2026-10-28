# channel.py
# Models an unreliable wireless channel between an IoT Sensor Node and an IoT Gateway.
# Subject to RF path loss, fading, interference, and collisions.

import random


class Channel:
    def __init__(
        self,
        packet_loss_prob=0.0,
        ack_loss_prob=0.0,
        forced_drop_seq=None,
        **kwargs,
    ):
        # Support alias pack_loss_prob for backwards compatibility
        if "pack_loss_prob" in kwargs:
            packet_loss_prob = kwargs["pack_loss_prob"]

        self.packet_loss_prob = packet_loss_prob
        self.ack_loss_prob = ack_loss_prob
        self.forced_drop_seq = forced_drop_seq
        self.forced_drop_done = False

    def send(self, packet):
        if packet.is_ack:
            loss_probability = self.ack_loss_prob
        else:
            # Deliberately lose this sequence number once for controlled demos
            if (
                packet.seq == self.forced_drop_seq
                and not self.forced_drop_done
            ):
                self.forced_drop_done = True
                print(f"IoT-Channel: Telemetry packet {packet.seq} deliberately dropped (RF interference)")
                return False

            loss_probability = self.packet_loss_prob

        if random.random() < loss_probability:
            return False

        return True
