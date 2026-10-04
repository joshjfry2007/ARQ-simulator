import random

class channel:
    
    def __init__(self, pack_loss_prob = 0.0, ack_loss_prob=0.0):
        self.packet_loss_prob = pack_loss_prob;
        self.ack_loss_prob = ack_loss_prob;
    

    def send(self, packet):
        if packet.is_ack:
            loss_probability = self.ack_loss_prob
        else:
            loss_probability = self.pack_loss_prob

        if random.random() < loss_probability:
            return False
        return True