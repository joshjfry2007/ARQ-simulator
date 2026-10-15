# experiments.py
# Final experiment run: sweeps the data-loss probability for all three protocols,
# saves the numbers to results/loss_sweep.csv and draws charts into results/.
#
# Run:  python experiments.py
# Needs: pip install matplotlib

import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")            # draw to files, no window needed
import matplotlib.pyplot as plt

import compare

LOSS_LEVELS = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
ACK_LOSS = 0.10
RUNS = 20                        # runs averaged per point (seeds 42..61)
OUT = "results"

CHARTS = [
    ("Retransmissions", "Retransmissions (packets)", "retransmissions_vs_loss.png"),
    ("Completion time", "Completion time (time units)", "completion_time_vs_loss.png"),
    ("Throughput (pkt/unit)", "Throughput (packets per time unit)", "throughput_vs_loss.png"),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    names = [n for n, _ in compare.PROTOCOLS]
    data = {n: {} for n in names}                    # data[protocol][metric] = [values per loss level]

    for loss in LOSS_LEVELS:
        cfg = argparse.Namespace(packets=100, loss=loss, ack_loss=ACK_LOSS,
                                 window=4, timeout=4, seed=42, runs=RUNS)
        res = compare.run_all(cfg)
        for n in names:
            for metric, value in res[n].items():
                data[n].setdefault(metric, []).append(value)
        print(f"done: loss = {loss:.2f}")

    # ---- CSV
    metrics = list(data[names[0]].keys())
    with open(os.path.join(OUT, "loss_sweep.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["protocol", "loss_prob"] + metrics)
        for n in names:
            for i, loss in enumerate(LOSS_LEVELS):
                w.writerow([n, loss] + [round(data[n][m][i], 3) for m in metrics])

    # ---- Charts
    for metric, ylabel, filename in CHARTS:
        plt.figure(figsize=(7, 4.5))
        for n, marker in zip(names, ["o", "s", "^"]):
            plt.plot([l * 100 for l in LOSS_LEVELS], data[n][metric], marker=marker, label=n)
        plt.xlabel("Data packet loss probability (%)")
        plt.ylabel(ylabel)
        plt.title(f"{metric} vs packet loss (ACK loss {int(ACK_LOSS * 100)}%, window 4, {RUNS} runs)")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(OUT, filename), dpi=150)
        plt.close()

    print(f"\nSaved CSV and {len(CHARTS)} charts in the '{OUT}' folder.")


if __name__ == "__main__":
    main()