# stop_and_wait.py
# Stop-and-Wait ARQ protocol simulation for IoT Telemetry Node.
#
# IoT Device: IoT-TempNode-01
# Monitored Metric: Temperature (°C)
#
# Characteristics:
#   - Pipelining: None (Window = 1)
#   - Sensor sends 1 telemetry sample, keeps radio in active listening mode until ACK.
#   - High idle listening energy and long completion time.

import random
from packet import make_data_packet, make_ack_packet, DEFAULT_DEVICE_ID, DEFAULT_METRIC
from channel import Channel
from metrics import Metrics


def run_stop_and_wait(
    num_packets=10,
    loss_prob=0.2,
    ack_loss_prob=0.2,
    timeout=8,
    delay=2,
    seed=42,
    verbose=True,
    max_retries=50,
    device_id=DEFAULT_DEVICE_ID,
    metric=DEFAULT_METRIC,
):
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
        attempts = 0
        acked = False

        while not acked:
            if attempts > max_retries:
                log(f"IoT-NODE [{device_id}] GIVE UP on telemetry packet {i}")
                break

            pkt = make_data_packet(seq, device_id=device_id, metric=metric)
            m.record_sent()

            if attempts == 0:
                log(
                    f"IoT-NODE [{device_id}] sent telemetry #{i} (seq={seq}, {metric}={pkt.value}{pkt.unit})"
                )
            else:
                m.record_retransmit()
                log(
                    f"IoT-NODE [{device_id}] RETRANSMIT telemetry #{i} (seq={seq}, {metric}={pkt.value}{pkt.unit}), attempt {attempts + 1}"
                )
            attempts += 1

            # Channel transmission of data packet
            if not ch.send(pkt):
                log(f"CHANNEL  telemetry packet {i} LOST (channel noise/interference)")
                clock += timeout
                log(f"IoT-NODE [{device_id}] TIMEOUT (no ACK received for seq={seq})")
                continue

            clock += delay
            if pkt.seq == expected_seq:  # Receiver (IoT Edge Gateway)
                delivered.append(pkt.data)
                expected_seq = 1 - expected_seq
                m.record_delivered()
                log(
                    f"GATEWAY  got seq={seq}, recorded {metric} reading: {pkt.value}{pkt.unit}"
                )
            else:
                m.record_duplicate()
                log(
                    f"GATEWAY  got DUPLICATE seq={seq}, discarded (re-sending ACK)"
                )

            ack = make_ack_packet(pkt.seq)
            log(f"GATEWAY  sent ACK (seq={ack.seq})")

            # Channel transmission of ACK packet
            if not ch.send(ack):
                m.record_ack_lost()
                log(f"CHANNEL  ACK for seq={seq} LOST in transit")
                clock += timeout - delay
                log(f"IoT-NODE [{device_id}] TIMEOUT (no ACK received for seq={seq})")
                continue

            clock += delay
            m.record_ack_received()
            log(
                f"IoT-NODE [{device_id}] received ACK (seq={seq}) -> telemetry #{i} confirmed"
            )
            acked = True

    # Pull final metrics dictionary with IoT energy metrics
    summary_data = m.summary()
    energy_data = m.compute_energy(clock)
    summary_data.update(energy_data)
    summary_data["completion_time"] = clock
    summary_data["delivery_rate"] = 100.0 * len(delivered) / num_packets
    summary_data["device_id"] = device_id
    summary_data["metric"] = metric
    return summary_data


def print_summary(res):
    print("\n--- SUMMARY: Stop-and-Wait ARQ (IoT Sensor Telemetry) ---")
    print(f"IoT Device ID          : {res.get('device_id', DEFAULT_DEVICE_ID)}")
    print(f"Monitored Metric       : {res.get('metric', DEFAULT_METRIC).capitalize()} (°C)")
    print(
        f"Packets delivered      : {res['packets_delivered']}  ({res.get('delivery_rate', 100.0):.1f}%)"
    )
    print(f"Total transmissions    : {res['packets_sent']}")
    print(f"Retransmissions        : {res['retransmissions']}")
    print(f"ACKs lost              : {res['ack_lost']}")
    print(f"Duplicates discarded   : {res['duplicates']}")
    print(f"Completion time        : {res['completion_time']} time units")
    if "energy_total_mj" in res:
        print(f"IoT Device Total Energy: {res['energy_total_mj']} mJ")
        print(f"Energy / Telemetry Pkt : {res['energy_per_sample_mj']} mJ/sample")


if __name__ == "__main__":
    result = run_stop_and_wait(
        num_packets=10, loss_prob=0.2, ack_loss_prob=0.2, seed=1
    )
    print_summary(result)
