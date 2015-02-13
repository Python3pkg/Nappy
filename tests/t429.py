#!/usr/bin/python3
#
# Test program to force the throttle code to generate 429 throttling
#
# Note that generally the server doesn't respond fast enough (usually
# about 3 requests per second) for one of these programs to ever get over
# the rate limit (300 per minute) by itself.
#
# Therefore, to actually see the throttling code work you will likely have to
# start 2, maybe 3, of these in parallel.
#
# TODO: Build that into this code with threads ;)
#
import argparse
import numerous

#
# arguments:
#    -c credspec : the usual
#    -t limit    : maximum number of reads to do while waiting for 429s
#    -n num      : get this many 429s then exit
#    -m metric   : use metric as the test metric (see discussion below)
#    -D          : debug flag
#
# If no metric is supplied, the program will create its own metric and use it
# and delete that metric on normal exit (any abnormal exit won't delete it)
#
# If a metric argument is supplied, the program will:
#     - first attempt to use it as a metric ID. If that works, use that metric.
#     - then attempt to look it up ByLabel 'STRING'
#     - then attempt to look it up ByLabel 'ONE' (regexp processing will work)
#     - then simply use it as a label for a created metric
#
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--credspec')
parser.add_argument('-t', '--limit', type=int, default=-1)
parser.add_argument('-n', '--n429', type=int, default=1)
parser.add_argument('-D', '--debug', action="count")
parser.add_argument('-m', '--metric')
parser.add_argument('--statistics', action="store_true")  # info/debugging support

args = parser.parse_args()

k = numerous.numerousKey(args.credspec)

def throttleNoVoluntary(nr, tp, td, up):
    if tp['result-code'] in (429, 500):
        return up[0](nr, tp, up[1], up[2])
    else:
        return False

nr = numerous.Numerous(apiKey=k, throttle=throttleNoVoluntary)

# alternate lambda way to "spell" that
#nr = numerous.Numerous(apiKey=k,
#              throttle= lambda nr, tp, td, up:
#                (tp['result-code'] in (429, 500)) and up[0](nr, tp, up[1], up[2]))

testmetric = None

if args.metric:
    #  - first attempt to use it as a metric ID. If that works, use that metric.
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
              'description' : 'used by t429 throttle testing program. Ok to delete'
            }
    testmetric = nr.createMetric(args.metric or 't429-temp-metric', 0, attrs=attrs)
    deleteIt = True


if args.debug:
    nr.debug(10)

# if we're printing statistics, this makes Numerous keep the last N times
# (instead of just the last 1 which is the default). It's the size of the
# array that determines how many times to record
if args.statistics:
    nr.statistics['serverResponseTimes'] = [0]*10    # last 10

expectedVal = testmetric.read()

while nr.statistics['throttle429'] < args.n429 and args.limit != 0:
    if testmetric.read() != expectedVal:
        print("Huh, got a wrong value")
        exit(1)
    if args.limit > 0:               # because -1 means "forever"
        args.limit -= 1

if args.statistics:
    print(nr.statistics)

if deleteIt:
    testmetric.crushKillDestroy()
