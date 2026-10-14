
class Packet:
<<<<<<< HEAD
    def __init__(self, seq, data, is_ack=False):
=======
    def __init__(self, seq, data=None, is_ack=False):
>>>>>>> e569d3e (Clean up Python cache tracking)
        self.seq = seq
        self.data = data
        self.is_ack = is_ack

<<<<<<< HEAD
    # Allows dictionary-style access (e.g., pkt['seq']) for backward compatibility
    def __getitem__(self, key):
        if key == 'seq': return self.seq
        if key == 'data': return self.data
        if key == 'is_ack': return self.is_ack
=======
    def __getitem__(self, key):
        if key == 'seq':
            return self.seq
        if key == 'data':
            return self.data
        if key == 'is_ack':
            return self.is_ack
>>>>>>> e569d3e (Clean up Python cache tracking)
        raise KeyError(key)


def make_data_packet(seq, data):
    return Packet(seq, data, is_ack=False)


def make_ack_packet(seq):
<<<<<<< HEAD
    return Packet(seq, data=None, is_ack=True)
=======
    return Packet(seq, data=None, is_ack=True)
>>>>>>> e569d3e (Clean up Python cache tracking)
