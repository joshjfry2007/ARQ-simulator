class Packet:
    def __init__(self, seq_num=2, data=None, is_ack = False):
        self.seq_num = seq_num
        self.data = data
        self.is_ack = is_ack