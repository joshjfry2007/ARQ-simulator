import random
from packet import make_data_packet, make_ack_packet
from channel import Channel
from metrics import Metrics


def run_go_back_n(num_packets=15, window_size=4, loss_prob=0.2, ack_loss_prob=0.2,
                  timeout=8, delay=2, seed=42, verbose=True):
    random.seed(seed)
    clock = 0
    base = 0
    next_seq_num = 0
    delivered_count = 0

    # Initialize shared Channel and Metrics instances
    ch = Channel(packet_loss_prob=loss_prob, ack_loss_prob=ack_loss_prob)
    m = Metrics()

    def log(msg):
        if verbose:
            print(f"[t={clock:>4}] {msg}")

    # Track packet states in flight
    in_flight = {}

    while delivered_count < num_packets:
        # Sender: send new packets while within the window limit
        while next_seq_num < base + window_size and next_seq_num < num_packets:
            pkt = make_data_packet(next_seq_num, f"data-{next_seq_num}")
            m.record_sent()
            log(f"SENDER   sent packet {next_seq_num} (window base={base})")

            # Send data packet through shared Channel
            if not ch.send(pkt):
                m.record_retransmit()  # Tracking loss impact
                log(f"CHANNEL  data packet {next_seq_num} LOST")
                in_flight[next_seq_num] = {"sent_time": clock, "lost": True}
            else:
                in_flight[next_seq_num] = {"sent_time": clock, "lost": False}

            next_seq_num += 1

        # Check for timeout on the oldest unacknowledged packet (base)
        if base in in_flight:
            packet_info = in_flight[base]
            if packet_info.get("lost", False) or (clock >= packet_info["sent_time"] + timeout):
                log(f"SENDER   TIMEOUT for base packet {base} -> GOBACK-N: resending from {base} to {next_seq_num - 1}")
                clock += timeout

                # Go-Back-N retransmits all packets currently in flight from base onwards
                for p_idx in range(base, next_seq_num):
                    m.record_retransmit()
                    log(f"SENDER   RETRANSMIT packet {p_idx}")
                    m.record_sent()

                    retrans_pkt = make_data_packet(p_idx, f"data-{p_idx}")
                    if not ch.send(retrans_pkt):
                        log(f"CHANNEL  retransmitted packet {p_idx} LOST")
                        in_flight[p_idx]["sent_time"] = clock
                        in_flight[p_idx]["lost"] = True
                    else:
                        in_flight[p_idx]["sent_time"] = clock
                        in_flight[p_idx]["lost"] = False
                continue

        # Simulate receiving cumulative ACK for base
        clock += delay
        if base in in_flight and not in_flight[base].get("lost", False):
            ack_pkt = make_ack_packet(base)
            if ch.send(ack_pkt):
                log(f"RECEIVER sent cumulative ACK for up to packet {base}")
                log(f"SENDER   received ACK {base} -> sliding window forward")
                base += 1
                delivered_count += 1
                m.record_delivered()
            else:
                m.record_ack_lost()
                log(f"CHANNEL  ACK for packet {base} LOST")
        else:
            clock += 2

    summary_data = m.summary()
    summary_data["completion_time"] = clock
    summary_data["delivery_rate"] = 100.0 * delivered_count / num_packets
    return summary_data


if __name__ == "__main__":
    res = run_go_back_n()
    print("\n--- SUMMARY (Go-Back-N) ---")
    print(f"Packets delivered   : {res['packets_delivered']} ({res.get('delivery_rate', 100.0):.1f}%)")
    print(f"Total transmissions : {res['packets_sent']}")
    print(f"Retransmissions     : {res['retransmissions']}")
    print(f"Completion time     : {res['completion_time']} time units")