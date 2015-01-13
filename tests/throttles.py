# example alternate throttle policy implementations

#
# This throttle policy only allows N requests per M seconds.
# It is meant as a demonstration so it seems needlessly complicated.
# What this does is keep a rolling list of timestamps in the M second window.
# We also implement a policy that says if you are 3/4 of the way to the throttle
# policy limit then we slow you down to one request per second, in an attempt to
# avoid you experiencing an even longer delay to roll off a whole bunch of closely
# spaced requests.
#
# There's no belief here that this is a useful throttle policy, it's just a demo
#

import time

#
# Set this up as:
#    nr = Numerous(throttle=NperM, throttleData={'stamps' : [], 'N' : 30, 'M' : 20})
#
# which, for example, would limit you to 30 requests per 20 seconds.
#

def NperM(nr, tparams, td, up):
    now = time.time()
    stamps = td['stamps']
    M = td['M']

    popFrom = 0
    for i in range(len(stamps)):
        if stamps[i] + M >= now:
            popFrom = i
            break

    if popFrom > 0:
        stamps = stamps[popFrom:]    # pop off the "too old" timestamps

    # if we have too many then we have to wait long enough for one to roll off
    if len(stamps) > td['N']:
        # how long to sleep to get at least M seconds later than oldest stamp
        ts = max(int(stamps[0] + M - now) + 1, 1)
        time.sleep(ts)
    elif len(stamps) * 4 > td['N'] * 3:
        # we're 3/4 of the way there so slow you down a little
        time.sleep(1)

    stamps.append(now)
    td['stamps'] = stamps          # save the possibly-different stamps object back

    # we still have to compute the throttle retry, for which we use the
    # built-in support function
    return up[0](nr, tparams, up[1], up[2])


