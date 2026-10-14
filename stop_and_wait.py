import random
from packet import make_data_packet, make_ack_packet
from channel import Channel
from metrics import Metrics


def run_stop_and_wait(num_packets=10, loss_prob=0.2, ack_loss_prob=0.2,
                      timeout=8, delay=2, seed=42, verbose=True, max_retries=50):
    random.seed(seed)
    clock = 0
    expected_seq = 0
    delivered = []

    # Initialize shared Channel and Metrics instances
    ch = Channel(packet_loss_prob=loss_prob, ack_loss_prob=ack_loss_prob)
    m = Metrics()

    def log(msg):
        if verbose:
            print(f"[t={clock:>4}] {msg}")

    for i in range(num_packets):
        seq = i % 2
        data = f"data-{i}"
        attempts = 0
        acked = False

        while not acked:
            if attempts > max_retries:
                log(f"GIVE UP on packet {i}")
                break

            pkt = make_data_packet(seq, data)
            m.record_sent()

            if attempts == 0:
                log(f"SENDER   sent packet {i} (seq={seq})")
            else:
                m.record_retransmit()
                log(f"SENDER   RETRANSMIT packet {i} (seq={seq}), attempt {attempts + 1}")
            attempts += 1

            # Use Member B's shared Channel.send() method for data packet
            if not ch.send(pkt):
                log(f"CHANNEL  data packet {i} LOST")
                clock += timeout
                log(f"SENDER   TIMEOUT (no ACK for seq={seq})")
                continue

            clock += delay
            if pkt.seq == expected_seq:  # receiver
                delivered.append(pkt.data)
                expected_seq = 1 - expected_seq
                m.record_delivered()
                log(f"RECEIVER got seq={seq}, delivered '{data}'")
            else:
                m.record_duplicate()
                log(f"RECEIVER got DUPLICATE seq={seq}, discarded (re-sending ACK)")

            ack = make_ack_packet(pkt.seq)
            log(f"RECEIVER sent ACK (seq={ack.seq})")

            # Use Member B's shared Channel.send() method for ACK packet
            if not ch.send(ack):
                m.record_ack_lost()
                log(f"CHANNEL  ACK for seq={seq} LOST")
                clock += (timeout - delay)
                log(f"SENDER   TIMEOUT (no ACK for seq={seq})")
                continue

            clock += delay
            log(f"SENDER   received ACK (seq={seq}) -> packet {i} done")
            acked = True

    # Pull final metrics dictionary from Member B's Metrics class
    summary_data = m.summary()
    summary_data["completion_time"] = clock
    summary_data["delivery_rate"] = 100.0 * len(delivered) / num_packets
    return summary_data


def print_summary(res):
    print("\n--- SUMMARY (Stop-and-Wait) ---")
    print(f"Packets delivered   : {res['packets_delivered']}  ({res.get('delivery_rate', 100.0):.1f}%)")
    print(f"Total transmissions : {res['packets_sent']}")
    print(f"Retransmissions     : {res['retransmissions']}")
    print(f"ACKs lost           : {res['ack_lost']}")
    print(f"Duplicates discarded: {res['duplicates']}")
    print(f"Completion time     : {res['completion_time']} time units")


if __name__ == "__main__":
    result = run_stop_and_wait(num_packets=10, loss_prob=0.2, ack_loss_prob=0.2, seed=1)
    print_summary(result)