from stop_and_wait import run_stop_and_wait, print_summary

for seed in range(200):
    m = run_stop_and_wait(num_packets=10, loss_prob=0.2, ack_loss_prob=0.2,
                          seed=seed, verbose=False)
    if (m["first_try_success"] > 0 and m["data_lost"] > 0
            and m["ack_lost"] > 0 and m["duplicates"] > 0):
        print(f"Good demo seed: {seed}")
        print_summary(m)
        break