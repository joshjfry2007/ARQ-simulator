class Metrics:

    def __init__(self):
        self.packets_sent = 0
        self.retransmissions = 0
        self.packets_delivered = 0
        self.duplicates = 0
        self.ack_lost = 0

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

    def summary(self):
        return {
            "packets_sent": self.packets_sent,
            "retransmissions": self.retransmissions,
            "packets_delivered": self.packets_delivered,
            "duplicates": self.duplicates,
            "ack_lost": self.ack_lost
        }