# metrics.py
# Collects transmission metrics and computes IoT Device Radio Energy Consumption.
#
# IoT Device: Battery-operated sensor node (IoT-TempNode-01)
# Primary Metric: Radio Energy Consumption (mJ) and Energy per Telemetry Sample (mJ/sample)
#
# Standard Low-Power IoT Transceiver Specs (e.g. CC2530 / SX1276 / nRF52840):
#   - TX Energy (E_tx)    : 15.0 mJ per telemetry packet transmission
#   - RX Energy (E_rx)    : 5.0 mJ per ACK reception
#   - Idle Power (P_idle) : 1.0 mJ per time unit while awaiting ACK (active listening)


class Metrics:
    def __init__(self, tx_energy_mj=15.0, rx_energy_mj=5.0, idle_power_mj=1.0):
        self.packets_sent = 0
        self.retransmissions = 0
        self.packets_delivered = 0
        self.duplicates = 0
        self.ack_lost = 0
        self.acks_received = 0

        # Energy model parameters (milliJoules)
        self.tx_energy_mj = tx_energy_mj
        self.rx_energy_mj = rx_energy_mj
        self.idle_power_mj = idle_power_mj

    def record_sent(self):
        self.packets_sent += 1

    def record_retransmit(self):
        self.retransmissions += 1

    def record_delivered(self):
        self.packets_delivered += 1

    def record_duplicate(self):
        self.duplicates += 1

    def record_ack_lost(self):
        self.ack_lost += 1

    def record_ack_received(self):
        self.acks_received += 1

    def compute_energy(self, completion_time=0):
        """Calculate total IoT device energy consumed in milliJoules (mJ)."""
        acks_rec = self.acks_received if self.acks_received > 0 else self.packets_delivered
        e_tx = self.packets_sent * self.tx_energy_mj
        e_rx = acks_rec * self.rx_energy_mj
        idle_time = max(0, completion_time - self.packets_sent)
        e_idle = idle_time * self.idle_power_mj
        total_energy = e_tx + e_rx + e_idle
        energy_per_sample = (
            (total_energy / self.packets_delivered)
            if self.packets_delivered > 0
            else 0.0
        )
        return {
            "energy_tx_mj": round(e_tx, 2),
            "energy_rx_mj": round(e_rx, 2),
            "energy_idle_mj": round(e_idle, 2),
            "energy_total_mj": round(total_energy, 2),
            "energy_per_sample_mj": round(energy_per_sample, 2),
        }

    def summary(self, completion_time=None):
        base = {
            "packets_sent": self.packets_sent,
            "retransmissions": self.retransmissions,
            "packets_delivered": self.packets_delivered,
            "duplicates": self.duplicates,
            "ack_lost": self.ack_lost,
            "acks_received": self.acks_received,
        }
        if completion_time is not None:
            base.update(self.compute_energy(completion_time))
        return base
