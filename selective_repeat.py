
import random

from packet import Packet
from channel import Channel
from metrics import Metrics
from config import get_config


class Sender:
    def __init__(self, total_packets, window_size, timeout):
        self.total_packets = total_packets
        self.window_size = window_size
        self.timeout = timeout

        self.base = 0
        self.next_seq = 0
        self.acked = {}
        self.send_times = {}
        self.retransmitted = []

    def get_packets_to_send(self):
        packets = []

        while (
            self.next_seq < self.total_packets
            and self.next_seq < self.base + self.window_size
        ):
            seq = self.next_seq
            packets.append(seq)
            self.acked[seq] = False
            self.next_seq += 1

        return packets

    def receive_ack(self, seq):
        if seq not in self.acked:
            return

        if not self.acked[seq]:
            print(f"Sender: ACK received for packet {seq}")
            self.acked[seq] = True
            self.send_times.pop(seq, None)

        while (
            self.base < self.total_packets
            and self.acked.get(self.base, False)
        ):
            self.base += 1

    def get_timed_out_packets(self, current_time):
        timed_out = []

        for seq, sent_time in list(self.send_times.items()):
            if (
                not self.acked[seq]
                and current_time - sent_time >= self.timeout
            ):
                timed_out.append(seq)

        return timed_out


class Receiver:
    def __init__(self, total_packets, window_size):
        self.total_packets = total_packets
        self.window_size = window_size
        self.expected_seq = 0
        self.buffer = {}
        self.delivered_packets = []

    def receive_packet(self, seq, data):
        # Ignore packets outside the receiver's valid window.
        if (
            seq < self.expected_seq
            or seq >= self.expected_seq + self.window_size
            or seq >= self.total_packets
        ):
            if seq < self.expected_seq:
                print(f"Receiver: Duplicate packet {seq}")
                return [], True

            return [], False

        if seq not in self.buffer:
            self.buffer[seq] = data
            print(f"Receiver: Packet {seq} received")

        delivered = []

        while self.expected_seq in self.buffer:
            data_to_deliver = self.buffer.pop(self.expected_seq)

            delivered.append(
                (self.expected_seq, data_to_deliver)
            )
            self.delivered_packets.append(
                (self.expected_seq, data_to_deliver)
            )

            print(f"Receiver: Packet {self.expected_seq} delivered")
            self.expected_seq += 1

        return delivered, True


def run_simulation(
    total_packets,
    window_size,
    timeout,
    channel,
    metrics
):
    sender = Sender(total_packets, window_size, timeout)
    receiver = Receiver(total_packets, window_size)

    # Events: (delivery_time, event_type, sequence_number, data)
    events = []
    current_time = 0

    while sender.base < total_packets:
        # Process packets and ACKs that have arrived.
        due_events = [
            event for event in events
            if event[0] <= current_time
        ]
        events = [
            event for event in events
            if event[0] > current_time
        ]

        for _, event_type, seq, data in due_events:
            if event_type == "data":
                _, should_ack = receiver.receive_packet(seq, data)

                if should_ack:
                    ack = Packet(seq, None, is_ack=True)
                    print(f"Receiver: Sending ACK for packet {seq}")

                    if channel.send(ack):
                        events.append(
                            (current_time + 1, "ack", seq, None)
                        )
                    else:
                        metrics.record_ack_lost()

            elif event_type == "ack":
                sender.receive_ack(seq)

        # Retransmit only packets whose individual timers expired.
        for seq in sender.get_timed_out_packets(current_time):
            print(f"Sender: Retransmitting packet {seq}")
            sender.retransmitted.append(seq)

            metrics.record_retransmit()
            metrics.record_sent()

            packet = Packet(seq, f"data-{seq}")
            sender.send_times[seq] = current_time

            if channel.send(packet):
                events.append(
                    (current_time + 1, "data", seq, packet.data)
                )

        # Send new packets while the window has available space.
        for seq in sender.get_packets_to_send():
            packet = Packet(seq, f"data-{seq}")

            print(f"Sender: Sending packet {seq}")
            metrics.record_sent()

            sender.send_times[seq] = current_time

            if channel.send(packet):
                events.append(
                    (current_time + 1, "data", seq, packet.data)
                )

        # Advance the simulated clock.
        current_time += 1

    # Count delivered packets from the receiver's delivery list.
    # These are application deliveries, not transmission attempts.
    metrics.packets_delivered = len(receiver.delivered_packets)

    print(f"\nSimulation time steps: {current_time}")

    return sender, receiver


if __name__ == "__main__":
    config = get_config()
    random.seed(config.seed)

    channel = Channel(
        packet_loss_prob=0.0,
        ack_loss_prob=0.0,
        forced_drop_seq=2
    )

    metrics = Metrics()

    sender, receiver = run_simulation(
        total_packets=15,
        window_size=4,
        timeout=config.timeout,
        channel=channel,
        metrics=metrics
    )

    print("\n--- Selective Repeat Summary ---")
    print("Packets delivered:", len(receiver.delivered_packets))
    print("Retransmitted packets:", sender.retransmitted)
    print("Metrics:", metrics.summary())
