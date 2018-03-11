# -*- coding: utf-8 -*-
""" play with fork """

import os
import random
import signal
import sys
import time

# Remember -- pids are certain to be unique.
pids = set()

for i in range(0, 10):

    # If you put the random call in the child, they will each get
    # the same nap time because they each have identical copies
    # of the random number generator and its initial state.
    nap = round(10*random.random() + 1, 3)
    pid = os.fork()

    if pid > 0:
        # if pid is greater than zero, this is the parent process. We
        # only need to have some new children.
        pids.add(pid)
        continue

    elif pid == 0:
        # if pid is zero, then this is the child, and like most newborns
        # about all we do is sleep.
        sys.stderr.write("I am {}, your {}th worst nightmare for the next {} sec.\n".format(
            os.getpid(), i, nap))
        time.sleep(nap)
        sys.exit(random.choice(range(0,16)))

    else:
        # This is really really really bad.
        sys.stderr.write("fork() failed {}. It looks more like a spoon()\n".format(pid))
        continue

sys.stderr.write("All children forked.\n")

while len(pids):
    sys.stderr.write("waiting ...\n")
    pid, result = os.wait()
    signal_number = result % 256
    exit_status = result // 256
    sys.stderr.write("Child {}, killed by signal {}, exits with {}\n".format(
        pid, signal_number, exit_status))
    pids.remove(pid)

sys.exit(os.EX_OK)
