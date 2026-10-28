# config.py
# Configuration for the IoT Telemetry ARQ Simulator.

import argparse


def get_config():
    parser = argparse.ArgumentParser(
        description="ARQ Simulator Configuration - IoT Sensor Telemetry"
    )

    parser.add_argument(
        "--device-id",
        type=str,
        default="IoT-TempNode-01",
        help="IoT Sensor Device Identifier",
    )

    parser.add_argument(
        "--metric",
        type=str,
        default="temperature",
        help="Monitored physical metric",
    )

    parser.add_argument(
        "--unit",
        type=str,
        default="°C",
        help="Sensor metric engineering unit",
    )

    parser.add_argument(
        "--packets",
        type=int,
        default=15,
        help="Number of telemetry packets",
    )

    parser.add_argument(
        "--loss",
        type=float,
        default=0.2,
        help="IoT channel telemetry packet loss probability",
    )

    parser.add_argument(
        "--ack-loss",
        type=float,
        default=0.1,
        help="IoT channel ACK loss probability",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=3,
        help="Timeout value (time units)",
    )

    parser.add_argument(
        "--window",
        type=int,
        default=4,
        help="ARQ window size",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed",
    )

    parser.add_argument(
        "--tx-energy",
        type=float,
        default=15.0,
        help="IoT node TX energy per packet (mJ)",
    )

    parser.add_argument(
        "--rx-energy",
        type=float,
        default=5.0,
        help="IoT node RX energy per ACK (mJ)",
    )

    parser.add_argument(
        "--idle-power",
        type=float,
        default=1.0,
        help="IoT node idle listening energy per unit time (mJ)",
    )

    return parser.parse_args()
