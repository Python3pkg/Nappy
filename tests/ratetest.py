#!/usr/bin/python3
#
# Test program whose primary goal is to test voluntary throttling.
#
import argparse
import numerous
import time

#
# arguments:
#    -c credspec  : the usual
#    -m metric    : use metric as the test metric (see discussion below)
#    -n amt       : iterations of test (can be -1 for infinite)
#    -t limit     : limit on how many throttles (exit when reached)
#    -q           : quiet - no output unless you specifically rqst (e.g. stats)
#    -Y           : do NOT synchronize to top of API rate minute
#    -D           : debug flag
#    --capdelay   : force the volmaxdelay path (code coverage hack)
#    --statistics : display statistics when done
#
# With no arguments at all this loops over a default number of API calls
# and computes the effective API-per-minute rate.  Essentially it tests
# the voluntary throttling code. The rate should asymptomically approach
# the 300/minute theoretical max. 
#
# Note that you can get HIGHER rates than this if you don't sync to the top
# of the API rate minute (-Y) or if you run the test for too few iterations.
# For example, -n 20 will run very fast and not hit any limits and report
# an API/minute rate that you'd never get if you performed thousands of calls.
#
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--credspec')
parser.add_argument('-D', '--debug', action="count")
parser.add_argument('-m', '--metric')
parser.add_argument('-n', '--ncalls', type=int, default=1500)
parser.add_argument('-t', '--throttled', type=int, default=-1)
parser.add_argument('-Y', '--nosync', action="store_true")
parser.add_argument('-q', '--quiet', action="store_true")
parser.add_argument('--capdelay', action="store_true")
parser.add_argument('--statistics', action="store_true")

args = parser.parse_args()

#
# This sleeps until you have a fresh API allocation at the "top" of the minute
#

def sync_to_top_of_api_rate(nr):
    nr.ping()             # just anything to cause an API call
    if nr.statistics['rate-reset'] > 0:
        time.sleep(nr.statistics['rate-reset'])


nr = numerous.Numerous(apiKey=numerous.numerousKey(args.credspec))
if args.statistics:
    nr.statistics['serverResponseTimes'] = [0] * 5 # keep extra response times

testmetric = None

if args.metric:
    #  - attempt to use it as a metric ID. If that works, use that metric.
    #  - then attempt to look it up ByLabel 'STRING'
    #  - then attempt to look it up ByLabel 'ONE' (regexp processing will work)
    for mt in [ 'ID', 'STRING', 'ONE' ]:
        try:
            testmetric = nr.metricByLabel(args.metric, matchType = mt)
            if testmetric:
                break
        except numerous.NumerousError:   # can potentially get "conflict"
            pass


# At this point either we found a metric (not None) or we have to create one.
# If we have to create it, use the args.metric as the label, if given.
deleteIt = False
if not testmetric:
    attrs = { 'private' : True,
              'description' : 'used by throttle rate test. Ok to delete'
            }
    testmetric = nr.createMetric(args.metric or 'trate-temp-metric', 0, attrs=attrs)
    deleteIt = True

if args.debug:
    nr.debug(10)


if (not args.quiet) and (args.ncalls > 300):
    print("Performing {} calls; expect this to take roughly {:.1f} minutes".format(args.ncalls, (args.ncalls/300.0)+1))

if not args.nosync:
    sync_to_top_of_api_rate(nr)



# To test the voluntary rate throttling, what we do is:
# Bang on a metric continuously writing something to it
# Stop as soon as we get voluntarily throttled N times
#

smallest_rate_remaining = 100000000

# if you wanted us to force the "maximum delay cap" branch of the code
# we need to use up as many APIs as quickly as possible and get down
# to a very small number left. To do that we actually have to turn off
# the voluntary throttling until we get the APIs remaining to a small number
if args.capdelay:
    sync_to_top_of_api_rate(nr)
    noVol = lambda nr, tp, td, up: \
                (tp['result-code'] == 429) and up[0](nr, tp, up[1], up[2])

    k = numerous.numerousKey(args.credspec)
    nrX = numerous.Numerous(apiKey=k, throttle=noVol)
    ignored = nrX.user()
    while nrX.statistics['rate-remaining'] > 3:
        ignored = nrX.user()



n_ops = 0
t0 = time.time()
while True:
    ignored = testmetric.read()
    n_ops += 1

    if nr.statistics['rate-remaining'] < smallest_rate_remaining:
        smallest_rate_remaining = nr.statistics['rate-remaining']

    # if we were told to bomb out after a certain amount of throttles...
    s = nr.statistics
    if args.throttled > 0:
        thd = s['throttleVoluntaryBackoff'] + s['throttle429']
        if thd >= args.throttled:
            break

    # if we were told to bombout after n operations...
    if args.ncalls > 0 and n_ops >= args.ncalls:
        break

t1 = time.time()

if not args.quiet:
    print("Smallest rate remaining was: ", smallest_rate_remaining)
    print("Performed {:.2f} operations per minute".format((n_ops*60.0)/(t1-t0)))

if args.statistics:
    for k in nr.statistics:
        print("{:>24s}: {}".format(k, nr.statistics[k]))

if deleteIt:
    testmetric.crushKillDestroy()
