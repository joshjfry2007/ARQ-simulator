import argparse


def get_config():
    parser = argparse.ArgumentParser(
        description="ARQ Simulator Configuration"
    )

    parser.add_argument(
        "--packets",
        type=int,
        default=15,
        help="Number of packets"
    )

    parser.add_argument(
        "--loss",
        type=float,
        default=0.2,
        help="Packet loss probability"
    )

    parser.add_argument(
        "--ack-loss",
        type=float,
        default=0.1,
        help="ACK loss probability"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=3,
        help="Timeout value"
    )

    parser.add_argument(
        "--window",
        type=int,
        default=4,
        help="Window size"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed"
    )

    return parser.parse_args()