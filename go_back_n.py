# go_back_n.py
# Go-Back-N ARQ simulation using the shared Channel and Metrics modules.
#
# Sender  : keeps `base` (oldest unACKed packet) and `next_seq` (next new packet).
#           May send while next_seq < base + window_size.
#           One timer, for the oldest unACKed packet (base).
#           On timeout -> resend EVERYTHING from base to next_seq - 1.
# Receiver: keeps `expected_seq`.
#           seq == expected  -> deliver, expected += 1, send cumulative ACK.
#           seq  > expected  -> out of order: DISCARD, re-send ACK of last in-order packet.
#           seq  < expected  -> duplicate: discard, re-send ACK of last in-order packet.
# ACK n is cumulative: "everything up to and including packet n has arrived in order".

import heapq
import random

from packet import make_data_packet, make_ack_packet
from channel import Channel
from metrics import Metrics


def run_go_back_n(num_packets=15, window_size=4, loss_prob=0.2, ack_loss_prob=0.2,
                  timeout=8, delay=2, seed=42, verbose=True, forced_drop_seq=None):
    random.seed(seed)

    ch = Channel(packet_loss_prob=loss_prob, ack_loss_prob=ack_loss_prob,
                 forced_drop_seq=forced_drop_seq)
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
        """Sender transmits packet `seq` (first time or retransmission)."""
        nonlocal order
        m.record_sent()
        if seq in sent_before:
            m.record_retransmit()
            log(f"SENDER   RETRANSMIT packet {seq}")
        else:
            sent_before.add(seq)
            log(f"SENDER   sent packet {seq} (window base={base}, next={next_seq})")
        pkt = make_data_packet(seq, f"data-{seq}")
        if ch.send(pkt):
            order += 1
            heapq.heappush(events, (t + delay, order, "DATA", seq))
        else:
            log(f"CHANNEL  data packet {seq} LOST")

    def receiver_gets(seq):
        """Receiver handles an arriving data packet."""
        nonlocal expected_seq, out_of_order, order
        if seq == expected_seq:
            expected_seq += 1
            m.record_delivered()
            log(f"RECEIVER got packet {seq} in order -> delivered")
        elif seq > expected_seq:
            out_of_order += 1
            log(f"RECEIVER got packet {seq} OUT OF ORDER (expected {expected_seq}) -> discarded")
        else:
            m.record_duplicate()
            log(f"RECEIVER got DUPLICATE packet {seq} (expected {expected_seq}) -> discarded")

        if expected_seq == 0:
            log("RECEIVER nothing in order yet, no ACK sent")
            return
        ack_no = expected_seq - 1            # cumulative ACK
        ack = make_ack_packet(ack_no)
        log(f"RECEIVER sent cumulative ACK {ack_no}")
        if ch.send(ack):
            order += 1
            heapq.heappush(events, (t + delay, order, "ACK", ack_no))
        else:
            m.record_ack_lost()
            log(f"CHANNEL  ACK {ack_no} LOST")

    max_time = 200000
    while base < num_packets and t < max_time:
        # 1. Deliver everything that has arrived by now (data to receiver, ACKs to sender)
        while events and events[0][0] <= t:
            _, _, kind, number = heapq.heappop(events)
            if kind == "DATA":
                receiver_gets(number)
            else:  # ACK arrives at sender
                if number >= base:
                    log(f"SENDER   received cumulative ACK {number} -> window slides, base {base} -> {number + 1}")
                    base = number + 1
                    timer_start = t if base < next_seq else None   # restart or stop timer
                else:
                    log(f"SENDER   received old ACK {number} (base={base}) -> ignored")
        if base >= num_packets:
            break

        # 2. Timeout on the oldest unacknowledged packet -> go back N
        if timer_start is not None and t >= timer_start + timeout:
            log(f"SENDER   TIMEOUT for packet {base} -> GO BACK: resend packets {base} to {next_seq - 1}")
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
    result["completion_time"] = t
    result["delivery_rate"] = 100.0 * result["packets_delivered"] / num_packets
    result["out_of_order_discarded"] = out_of_order
    return result


def print_summary(res):
    print("\n--- SUMMARY (Go-Back-N) ---")
    print(f"Packets delivered      : {res['packets_delivered']} ({res['delivery_rate']:.1f}%)")
    print(f"Total transmissions    : {res['packets_sent']}")
    print(f"Retransmissions        : {res['retransmissions']}")
    print(f"ACKs lost              : {res['ack_lost']}")
    print(f"Duplicates discarded   : {res['duplicates']}")
    print(f"Out-of-order discarded : {res['out_of_order_discarded']}")
    print(f"Completion time        : {res['completion_time']} time units")


if __name__ == "__main__":
    # Demo 1: packet 2 deliberately lost once (window 4, no other loss) - shows Go-Back-N clearly
    print("=== DEMO 1: packet 2 lost, window = 4 ===")
    res = run_go_back_n(num_packets=15, window_size=4, loss_prob=0.0,
                        ack_loss_prob=0.0, forced_drop_seq=2)
    print_summary(res)

    # Demo 2: random loss
    print("\n=== DEMO 2: random loss (20% data, 20% ACK), seed 42 ===")
    res = run_go_back_n(num_packets=15, window_size=4, loss_prob=0.2,
                        ack_loss_prob=0.2, seed=42, verbose=False)
    print_summary(res)