from stop_and_wait import run_stop_and_wait, print_summary

for seed in range(200):
    m = run_stop_and_wait(num_packets=10, loss_prob=0.2, ack_loss_prob=0.2,
                          seed=seed, verbose=False)
    # lost ACK -> duplicate; more retransmissions than duplicates -> a data packet was lost too
    if m["ack_lost"] > 0 and m["duplicates"] > 0 and m["retransmissions"] > m["duplicates"]:
        print(f"Good demo seed: {seed}")
        print_summary(m)
        break