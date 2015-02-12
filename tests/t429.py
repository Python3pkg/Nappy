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

# This being a test program, we have some definite hackery going on in here.
# The wrapper:
#  * counts the number of 429 errors encountered
#  * hacks the 'voluntary' limit so it never happens
#  * exports the entire tparams just for informational/debug
#
def throttleWrap(nr, tparams, td, up):
    td['parameters'] = tparams.copy()
    if tparams['result-code'] == 429:        # count the 429 codes we see
        td['429'] = td.get('429',0) + 1      # (defensive in case not initialized)
    sysTd = up[1]
    sysTd['voluntary'] = -1                  # so we'll never voluntary backoff
    return up[0](nr, tparams, sysTd, up[2])  # invoke system default throttle


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

throttled = {}
nr = numerous.Numerous(apiKey=k, throttle=throttleWrap, throttleData=throttled)

testmetric = None

if args.metric:

    #     - first attempt to use it as a metric ID. If that works, use that metric.
    try:
        testmetric = nr.metric(args.metric)
        ignored = testmetric.read()    # just testing validity, with exceptions raised
    except:
        testmetric = None

    #     - then attempt to look it up ByLabel 'STRING'
    if not testmetric:
        try:
            testmetric = nr.metricByLabel(args.metric, matchType='STRING')
            ignored = testmetric.read()
        except:
            testmetric = None

    #     - then attempt to look it up ByLabel 'ONE' (regexp processing will work)
    if not testmetric:
        try:
            testmetric = nr.metricByLabel(args.metric, matchType='ONE')
            ignored = testmetric.read()
        except:
            testmetric = None


# At this point either we found a metric (not None) or we have to create one.
# If we have to create it, use the args.metric as the label, if given.
deleteIt = False
if not testmetric:
    attrs = { 'private' : True,
              'description' : 'used by t429 throttle testing program. Ok to delete'
            }
    testmetric = nr.createMetric(args.metric or 't429-temp-metric', 0, attrs=attrs)
    deleteIt = True


# reset the throttle data in case we incurred any 429 above! :)
throttled['429'] = 0

if args.debug:
    nr.debug(10)

# if we're printing statistics, this makes Numerous keep the last N times
# (instead of just the last 1 which is the default). It's the size of the
# array that determines how many times to record
if args.statistics:
    nr.statistics['serverResponseTimes'] = [0]*10    # last 10

while throttled['429'] < args.n429 and args.limit != 0:
    ignored = testmetric.read()
    if args.limit > 0:               # because -1 means "forever"
        args.limit -= 1

if args.statistics:
    print(nr.statistics)
    print(throttled)

if deleteIt:
    testmetric.crushKillDestroy()
