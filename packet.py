# packet.py
# Models packets exchanged between a battery-powered IoT Sensor Node
# and an IoT Edge Gateway, carrying telemetry for 1 monitored metric (Temperature).

import math

DEFAULT_DEVICE_ID = "IoT-TempNode-01"
DEFAULT_METRIC = "temperature"
DEFAULT_UNIT = "°C"


def generate_sensor_reading(seq: int) -> float:
    """Generate a realistic ambient temperature reading for sequence number `seq`."""
    base_temp = 24.0
    variation = 3.5 * math.sin(seq * 0.3) + ((seq * 3) % 7) * 0.1
    return round(base_temp + variation, 2)


class Packet:
    """Packet class representing either an IoT telemetry data frame or an ACK frame.

    IoT Device: IoT-TempNode-01
    Monitored Metric: Temperature (°C)
    """

    def __init__(
        self,
        seq,
        data=None,
        is_ack=False,
        device_id=DEFAULT_DEVICE_ID,
        metric=DEFAULT_METRIC,
        value=None,
        unit=DEFAULT_UNIT,
    ):
        self.seq = seq
        self.is_ack = is_ack
        self.device_id = device_id
        self.metric = metric
        self.unit = unit

        if is_ack:
            self.data = None
            self.value = None
        else:
            if value is not None:
                self.value = value
            elif isinstance(data, (int, float)):
                self.value = float(data)
            else:
                self.value = generate_sensor_reading(seq)

            # Keep self.data formatted for backwards-compatible string access
            if data is not None and not str(data).startswith("data-"):
                self.data = data
            else:
                self.data = f"{self.device_id}[{self.metric}={self.value}{self.unit}, seq={seq}]"

    def __getitem__(self, key):
        if key == "seq":
            return self.seq
        if key == "data":
            return self.data
        if key == "is_ack":
            return self.is_ack
        if key == "device_id":
            return self.device_id
        if key == "metric":
            return self.metric
        if key == "value":
            return self.value
        if key == "unit":
            return self.unit
        raise KeyError(key)

    def __repr__(self):
        if self.is_ack:
            return f"ACK(seq={self.seq})"
        return (
            f"IoTTelemetry(dev={self.device_id}, {self.metric}={self.value}{self.unit}, seq={self.seq})"
        )


def make_data_packet(
    seq,
    data=None,
    device_id=DEFAULT_DEVICE_ID,
    metric=DEFAULT_METRIC,
    value=None,
):
    return Packet(
        seq,
        data=data,
        is_ack=False,
        device_id=device_id,
        metric=metric,
        value=value,
    )


def make_ack_packet(seq):
    return Packet(seq, data=None, is_ack=True)
