class Packet:
    def __init__(self, seq, data, is_ack=False):
        self.seq = seq
        self.data = data
        self.is_ack = is_ack

    # Allows dictionary-style access (e.g., pkt['seq']) for backward compatibility
    def __getitem__(self, key):
        if key == 'seq': return self.seq
        if key == 'data': return self.data
        if key == 'is_ack': return self.is_ack
        raise KeyError(key)


def make_data_packet(seq, data):
    return Packet(seq, data, is_ack=False)


def make_ack_packet(seq):
    return Packet(seq, data=None, is_ack=True)