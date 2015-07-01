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
#    -Y           : synchronize to top of API rate minute
#    -D           : debug flag
#    --statistics : display statistics when done
#
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--credspec')
parser.add_argument('-D', '--debug', action="count")
parser.add_argument('-m', '--metric')
parser.add_argument('-n', '--ncalls', type=int, default=-1)
parser.add_argument('-t', '--throttled', type=int, default=-1)
parser.add_argument('-Y', '--sync', action="store_true")
parser.add_argument('-q', '--quiet', action="store_true")
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





# To test the voluntary rate throttling, what we do is:
# Bang on a metric continuously writing something to it
# Stop as soon as we get voluntarily throttled N times
#

smallest_rate_remaining = 100000000

if args.sync:
    sync_to_top_of_api_rate(nr)

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
    print("Performed {} operations per minute".format((n_ops*60.0)/(t1-t0)))

if args.statistics:
    print(nr.statistics)

if deleteIt:
    testmetric.crushKillDestroy()
