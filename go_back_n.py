# go_back_n.py
# Go-Back-N ARQ simulation for IoT Sensor Telemetry.
#
# IoT Device: IoT-TempNode-01
# Monitored Metric: Temperature (°C)
#
# IoT Performance Characteristics:
#   - Pipelined transmissions (Window N).
#   - One timer for the oldest unACKed telemetry packet.
#   - On packet loss: receiver discards subsequent out-of-order packets.
#   - IoT Device must retransmit the ENTIRE window, consuming massive RF TX energy.

import heapq
import random

from packet import make_data_packet, make_ack_packet, DEFAULT_DEVICE_ID, DEFAULT_METRIC
from channel import Channel
from metrics import Metrics


def run_go_back_n(
    num_packets=15,
    window_size=4,
    loss_prob=0.2,
    ack_loss_prob=0.2,
    timeout=8,
    delay=2,
    seed=42,
    verbose=True,
    forced_drop_seq=None,
    device_id=DEFAULT_DEVICE_ID,
    metric=DEFAULT_METRIC,
):
    random.seed(seed)

    ch = Channel(
        packet_loss_prob=loss_prob,
        ack_loss_prob=ack_loss_prob,
        forced_drop_seq=forced_drop_seq,
    )
    m = Metrics()

    t = 0                      # simulated time
    base = 0                   # oldest unacknowledged packet
    next_seq = 0               # next new packet to send
    timer_start = None         # time the timer for `base` started (None = not running)
    expected_seq = 0           # receiver: next in-order packet it wants
    out_of_order = 0           # receiver: out-of-order packets discarded
    sent_before = set()        # sequence numbers that have been transmitted at least once

    events = []                # (arrival_time, order, kind, number)
    order = 0

    def log(msg):
        if verbose:
            print(f"[t={t:>4}] {msg}")

    def transmit(seq):
        """IoT Sensor Node transmits telemetry packet `seq`."""
        nonlocal order
        m.record_sent()
        pkt = make_data_packet(seq, device_id=device_id, metric=metric)
        if seq in sent_before:
            m.record_retransmit()
            log(
                f"IoT-NODE [{device_id}] RETRANSMIT telemetry pkt {seq} ({metric}={pkt.value}{pkt.unit})"
            )
        else:
            sent_before.add(seq)
            log(
                f"IoT-NODE [{device_id}] sent telemetry pkt {seq} ({metric}={pkt.value}{pkt.unit}) (window base={base}, next={next_seq})"
            )
        if ch.send(pkt):
            order += 1
            heapq.heappush(events, (t + delay, order, "DATA", seq))
        else:
            log(f"CHANNEL  telemetry pkt {seq} LOST (RF fading/interference)")

    def receiver_gets(seq):
        """IoT Edge Gateway handles an arriving data packet."""
        nonlocal expected_seq, out_of_order, order
        if seq == expected_seq:
            expected_seq += 1
            m.record_delivered()
            log(f"GATEWAY  got telemetry pkt {seq} in order -> delivered and logged")
        elif seq > expected_seq:
            out_of_order += 1
            log(
                f"GATEWAY  got telemetry pkt {seq} OUT OF ORDER (expected {expected_seq}) -> discarded"
            )
        else:
            m.record_duplicate()
            log(
                f"GATEWAY  got DUPLICATE telemetry pkt {seq} (expected {expected_seq}) -> discarded"
            )

        if expected_seq == 0:
            log("GATEWAY  nothing in order yet, no ACK sent")
            return
        ack_no = expected_seq - 1            # cumulative ACK
        ack = make_ack_packet(ack_no)
        log(f"GATEWAY  sent cumulative ACK {ack_no}")
        if ch.send(ack):
            order += 1
            heapq.heappush(events, (t + delay, order, "ACK", ack_no))
        else:
            m.record_ack_lost()
            log(f"CHANNEL  cumulative ACK {ack_no} LOST")

    max_time = 200000
    while base < num_packets and t < max_time:
        # 1. Deliver everything that has arrived by now (data to gateway, ACKs to sensor)
        while events and events[0][0] <= t:
            _, _, kind, number = heapq.heappop(events)
            if kind == "DATA":
                receiver_gets(number)
            else:  # ACK arrives at sensor node
                if number >= base:
                    m.record_ack_received()
                    log(
                        f"IoT-NODE [{device_id}] received cumulative ACK {number} -> window slides, base {base} -> {number + 1}"
                    )
                    base = number + 1
                    timer_start = (
                        t if base < next_seq else None
                    )   # restart or stop timer
                else:
                    log(
                        f"IoT-NODE [{device_id}] received old ACK {number} (base={base}) -> ignored"
                    )
        if base >= num_packets:
            break

        # 2. Timeout on the oldest unacknowledged packet -> go back N
        if timer_start is not None and t >= timer_start + timeout:
            log(
                f"IoT-NODE [{device_id}] TIMEOUT for packet {base} -> GO BACK: resend telemetry pkts {base} to {next_seq - 1}"
            )
            for seq in range(base, next_seq):
                transmit(seq)
            timer_start = t

        # 3. Send new packets while the window allows (all in the same time step)
        while next_seq < base + window_size and next_seq < num_packets:
            seq = next_seq
            next_seq += 1
            transmit(seq)
            if timer_start is None:
                timer_start = t

        t += 1

    result = m.summary()
    energy_data = m.compute_energy(t)
    result.update(energy_data)
    result["completion_time"] = t
    result["delivery_rate"] = 100.0 * result["packets_delivered"] / num_packets
    result["out_of_order_discarded"] = out_of_order
    result["device_id"] = device_id
    result["metric"] = metric
    return result


def print_summary(res):
    print("\n--- SUMMARY: Go-Back-N ARQ (IoT Sensor Telemetry) ---")
    print(f"IoT Device ID          : {res.get('device_id', DEFAULT_DEVICE_ID)}")
    print(f"Monitored Metric       : {res.get('metric', DEFAULT_METRIC).capitalize()} (°C)")
    print(
        f"Packets delivered      : {res['packets_delivered']} ({res['delivery_rate']:.1f}%)"
    )
    print(f"Total transmissions    : {res['packets_sent']}")
    print(f"Retransmissions        : {res['retransmissions']}")
    print(f"ACKs lost              : {res['ack_lost']}")
    print(f"Duplicates discarded   : {res['duplicates']}")
    print(f"Out-of-order discarded : {res['out_of_order_discarded']}")
    print(f"Completion time        : {res['completion_time']} time units")
    if "energy_total_mj" in res:
        print(f"IoT Device Total Energy: {res['energy_total_mj']} mJ")
        print(f"Energy / Telemetry Pkt : {res['energy_per_sample_mj']} mJ/sample")


if __name__ == "__main__":
    # Demo 1: packet 2 deliberately lost once (window 4, no other loss) - shows Go-Back-N retransmission waste
    print("=== DEMO 1: packet 2 lost, window = 4 ===")
    res = run_go_back_n(
        num_packets=15,
        window_size=4,
        loss_prob=0.0,
        ack_loss_prob=0.0,
        forced_drop_seq=2,
    )
    print_summary(res)

    # Demo 2: random loss
    print("\n=== DEMO 2: random loss (20% data, 20% ACK), seed 42 ===")
    res = run_go_back_n(
        num_packets=15,
        window_size=4,
        loss_prob=0.2,
        ack_loss_prob=0.2,
        seed=42,
        verbose=False,
    )
    print_summary(res)
