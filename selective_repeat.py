# selective_repeat.py
# Selective Repeat ARQ simulation for IoT Sensor Telemetry.
#
# IoT Device: IoT-TempNode-01
# Monitored Metric: Temperature (°C)
#
# IoT Performance Characteristics:
#   - Pipelined transmissions (Window N).
#   - Individual timers per telemetry packet.
#   - Gateway buffers out-of-order telemetry readings.
#   - IoT Device retransmits ONLY unacknowledged packets.
#   - Achieves lowest radio transmission energy overhead per telemetry reading.

import random

from packet import Packet, DEFAULT_DEVICE_ID, DEFAULT_METRIC
from channel import Channel
from metrics import Metrics
from config import get_config


class Sender:
    def __init__(self, total_packets, window_size, timeout, device_id=DEFAULT_DEVICE_ID, metric=DEFAULT_METRIC):
        self.total_packets = total_packets
        self.window_size = window_size
        self.timeout = timeout
        self.device_id = device_id
        self.metric = metric

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
            print(f"IoT-NODE [{self.device_id}]: ACK received for telemetry packet {seq}")
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
    def __init__(self, total_packets, window_size, metric=DEFAULT_METRIC):
        self.total_packets = total_packets
        self.window_size = window_size
        self.metric = metric
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
            print(f"GATEWAY: Telemetry packet {seq} received ({data})")

        delivered = []

        while self.expected_seq in self.buffer:
            data_to_deliver = self.buffer.pop(self.expected_seq)

            delivered.append(
                (self.expected_seq, data_to_deliver)
            )
            self.delivered_packets.append(
                (self.expected_seq, data_to_deliver)
            )
            print(f"GATEWAY: Telemetry packet {self.expected_seq} delivered to cloud buffer")
            self.expected_seq += 1

        return delivered, True


def run_simulation(
    total_packets,
    window_size,
    timeout,
    channel,
    metrics,
    device_id=DEFAULT_DEVICE_ID,
    metric=DEFAULT_METRIC,
):
    sender = Sender(total_packets, window_size, timeout, device_id=device_id, metric=metric)
    receiver = Receiver(total_packets, window_size, metric=metric)

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
                    print(f"GATEWAY: Sending ACK for telemetry packet {seq}")

                    if channel.send(ack):
                        events.append(
                            (current_time + 1, "ack", seq, None)
                        )
                    else:
                        metrics.record_ack_lost()

            elif event_type == "ack":
                sender.receive_ack(seq)
                metrics.record_ack_received()

        # Retransmit only packets whose individual timers expired.
        for seq in sender.get_timed_out_packets(current_time):
            print(f"IoT-NODE [{device_id}]: Retransmitting telemetry packet {seq}")
            sender.retransmitted.append(seq)

            metrics.record_retransmit()
            metrics.record_sent()

            packet = Packet(seq, device_id=device_id, metric=metric)
            sender.send_times[seq] = current_time

            if channel.send(packet):
                events.append(
                    (current_time + 1, "data", seq, packet.data)
                )

        # Send new packets while the window has available space.
        for seq in sender.get_packets_to_send():
            packet = Packet(seq, device_id=device_id, metric=metric)

            print(f"IoT-NODE [{device_id}]: Sending telemetry packet {seq} ({metric}={packet.value}{packet.unit})")
            metrics.record_sent()

            sender.send_times[seq] = current_time

            if channel.send(packet):
                events.append(
                    (current_time + 1, "data", seq, packet.data)
                )

        # Advance the simulated clock.
        current_time += 1

    # Count delivered packets from the receiver's delivery list.
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

    metrics = Metrics(
        tx_energy_mj=config.tx_energy,
        rx_energy_mj=config.rx_energy,
        idle_power_mj=config.idle_power,
    )

    sender, receiver = run_simulation(
        total_packets=15,
        window_size=4,
        timeout=config.timeout,
        channel=channel,
        metrics=metrics,
        device_id=config.device_id,
        metric=config.metric,
    )

    energy = metrics.compute_energy(12)
    print("\n--- SUMMARY: Selective Repeat ARQ (IoT Sensor Telemetry) ---")
    print(f"IoT Device ID          : {config.device_id}")
    print(f"Monitored Metric       : {config.metric.capitalize()} ({config.unit})")
    print("Telemetry delivered    :", len(receiver.delivered_packets))
    print("Retransmitted packets  :", sender.retransmitted)
    print("IoT Device Total Energy:", energy["energy_total_mj"], "mJ")
    print("Energy / Telemetry Pkt :", energy["energy_per_sample_mj"], "mJ/sample")
    print("Base Metrics           :", metrics.summary())
