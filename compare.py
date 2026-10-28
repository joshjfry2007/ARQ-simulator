# compare.py
# Runs Stop-and-Wait, Go-Back-N and Selective Repeat under IDENTICAL conditions
# for a single battery-powered IoT Sensor Node (IoT-TempNode-01) monitoring Temperature.
#
# Usage examples:
#   python compare.py
#   python compare.py --packets 100 --loss 0.1 --ack-loss 0.1 --window 4 --runs 10

import argparse
import contextlib
import io
import random
import re

from stop_and_wait import run_stop_and_wait
from go_back_n import run_go_back_n
from selective_repeat import run_simulation
from channel import Channel
from metrics import Metrics

DELAY = 1   # one-way delay (time units), fixed by selective_repeat.py


# ---------------------------------------------------------------- protocol runners
def run_sw(cfg, seed):
    return run_stop_and_wait(
        num_packets=cfg.packets,
        loss_prob=cfg.loss,
        ack_loss_prob=cfg.ack_loss,
        timeout=cfg.timeout,
        delay=DELAY,
        seed=seed,
        verbose=False,
    )


def run_gbn(cfg, seed):
    return run_go_back_n(
        num_packets=cfg.packets,
        window_size=cfg.window,
        loss_prob=cfg.loss,
        ack_loss_prob=cfg.ack_loss,
        timeout=cfg.timeout,
        delay=DELAY,
        seed=seed,
        verbose=False,
    )


def run_sr(cfg, seed):
    """Wrapper around Member B's run_simulation(): silences its prints and reads
    the values it does not return (completion time, duplicates) from its output."""
    random.seed(seed)
    ch = Channel(packet_loss_prob=cfg.loss, ack_loss_prob=cfg.ack_loss)
    m = Metrics()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run_simulation(
            total_packets=cfg.packets,
            window_size=cfg.window,
            timeout=cfg.timeout,
            channel=ch,
            metrics=m,
        )
    out = buf.getvalue()
    steps = int(re.search(r"Simulation time steps: (\d+)", out).group(1))
    r = m.summary()
    r["duplicates"] = out.count("Receiver: Duplicate packet")
    r["completion_time"] = steps - 1    # SR counts one extra step after the last ACK
    r["delivery_rate"] = 100.0 * r["packets_delivered"] / cfg.packets
    return r


PROTOCOLS = [
    ("Stop-and-Wait", run_sw),
    ("Go-Back-N", run_gbn),
    ("Selective Repeat", run_sr),
]


# ---------------------------------------------------------------- metrics
def derive(r, n):
    """Turn a raw result dict into the metrics shown in the table, including IoT Radio Energy."""
    tx_energy_mj = 15.0
    rx_energy_mj = 5.0
    idle_power_mj = 1.0

    delivered = r["packets_delivered"]
    comp_time = r["completion_time"]
    sent = r["packets_sent"]
    acks_rec = r.get("acks_received", 0)
    if acks_rec == 0:
        acks_rec = delivered  # in reliable transmission, all delivered samples are acknowledged

    e_tx = sent * tx_energy_mj
    e_rx = acks_rec * rx_energy_mj
    idle_time = max(0, comp_time - sent)
    e_idle = idle_time * idle_power_mj
    total_energy_mj = e_tx + e_rx + e_idle
    energy_per_sample = (total_energy_mj / delivered) if delivered > 0 else 0.0

    return {
        "Delivery (%)": r["delivery_rate"],
        "Transmissions": r["packets_sent"],
        "Retransmissions": r["retransmissions"],
        "Retrans. overhead (%)": 100.0 * r["retransmissions"] / n,
        "Duplicates discarded": r["duplicates"],
        "ACKs lost": r["ack_lost"],
        "Completion time": r["completion_time"],
        "Throughput (pkt/unit)": r["packets_delivered"] / r["completion_time"],
        "IoT Energy (mJ)": total_energy_mj,
        "Energy / Reading (mJ)": energy_per_sample,
    }


def run_all(cfg):
    """Run every protocol cfg.runs times (seeds seed, seed+1, ...) and average."""
    results = {}
    for name, fn in PROTOCOLS:
        rows = []
        for k in range(cfg.runs):
            raw = fn(cfg, cfg.seed + k)
            # sanity checks: these must hold for a correct protocol
            if raw["packets_delivered"] != cfg.packets:
                print(
                    f"WARNING: {name} (seed {cfg.seed + k}) delivered "
                    f"{raw['packets_delivered']}/{cfg.packets} packets"
                )
            if raw["packets_sent"] - raw["retransmissions"] != cfg.packets:
                print(
                    f"WARNING: {name} (seed {cfg.seed + k}) transmissions - retransmissions "
                    f"!= number of packets (counting bug)"
                )
            rows.append(derive(raw, cfg.packets))
        results[name] = {
            key: sum(r[key] for r in rows) / len(rows) for key in rows[0]
        }
    return results


def print_table(results, cfg):
    names = [n for n, _ in PROTOCOLS]
    metrics = list(results[names[0]].keys())
    w0 = max(len(k) for k in metrics) + 2
    wc = 18

    dev_id = getattr(cfg, "device_id", "IoT-TempNode-01")
    metric_name = getattr(cfg, "metric", "temperature").capitalize()

    print("\n" + "=" * (w0 + wc * len(names)))
    print(" IoT TELEMETRY ARQ PROTOCOL BENCHMARK")
    print(f" Target Device   : {dev_id}")
    print(f" Monitored Metric: {metric_name} (°C)")
    print(" IoT RF Link     : Low-Power Wireless (802.15.4 / LoRa) -> Gateway")
    print("=" * (w0 + wc * len(names)))
    print(
        "CONFIGURATION: packets={}  loss={}  ack_loss={}  window={}  timeout={}  "
        "delay={}  seed={}  runs={}".format(
            cfg.packets,
            cfg.loss,
            cfg.ack_loss,
            cfg.window,
            cfg.timeout,
            DELAY,
            cfg.seed,
            cfg.runs,
        )
    )
    print(
        "(values are averages over {} run{})\n".format(
            cfg.runs, "" if cfg.runs == 1 else "s"
        )
    )
    print("Metric".ljust(w0) + "".join(n.rjust(wc) for n in names))
    print("-" * (w0 + wc * len(names)))
    for k in metrics:
        print(k.ljust(w0) + "".join(f"{results[n][k]:{wc}.2f}" for n in names))
    print("-" * (w0 + wc * len(names)))
    print()


def get_args():
    p = argparse.ArgumentParser(
        description="Compare ARQ protocols for IoT Sensor Node Telemetry"
    )
    p.add_argument("--device-id", type=str, default="IoT-TempNode-01")
    p.add_argument("--metric", type=str, default="temperature")
    p.add_argument("--packets", type=int, default=100)
    p.add_argument("--loss", type=float, default=0.1)
    p.add_argument("--ack-loss", type=float, default=0.1)
    p.add_argument("--window", type=int, default=4)
    p.add_argument("--timeout", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--runs", type=int, default=1)
    return p.parse_args()


if __name__ == "__main__":
    cfg = get_args()
    print_table(run_all(cfg), cfg)
