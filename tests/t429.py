#!/usr/bin/python3
#
# Test program to force the throttle code to generate 429 throttling
#
# Note that generally the server doesn't respond fast enough (usually
# about 3 requests per second) for a single thread to ever hit the rate
# limit (300 per minute) by itself.
#
# For this reason I have set the default for the -p option to 3.
# Thus simply invoking this program with no options will in fact run
# a useful test:
#   - a dummy metric will be created
#   - three threads will be started and read that metric in a loop
#   - the test will end (silently) after each thread hits 1 429 condition
#
import argparse
import numerous
import threading

try:
  import queue
except:    # python2
  import Queue as queue

#
# arguments:
#    -c credspec  : the usual
#    -t limit     : maximum number of reads to do while waiting for 429s
#                   Default is infinite.
#    -n num       : get this many 429s (per thread) then exit. Default is 1.
#    -m metric    : use metric as the test metric (see discussion below)
#    -p parallel  : number of threads to run in parallel (default 3)
#    -D           : debug flag
#    --statistics : display statistics when done
#
#
# Note that it is not usually possible to generate enough traffic with
# one thread to hit the rate limit, as the server tends to operate at
# only about 3 requests per second (sequentially; but throughput scales
# with parallel requests).
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
parser.add_argument('-p', '--parallel', type=int, default=3)
parser.add_argument('--statistics', action="store_true")  # info/debugging support

args = parser.parse_args()

#
# This is the test function that is run in an individual thread, potentially
# in parallel (multiple threads running this function).
#
# Note in particular that we instantiate a local Numerous(), so it will be per-thread
# (versus the toplevel global one used to set up the test conditions).
# Similarly we instantiate a local metric (from the test metric's ID), again
# so it will be local to this thread vs shared across all the threads.
#
# The arguments are:
#    k      - the Numerous API key
#    mID    - the ID of the metric we should be reading
#    n429   - the number of times we want to see a 429 condition
#    lim    - the maximum API calls we can make to get those n429 conditions
#    q      - place (queue) for output results that will be picked up in main thread
#
def tester(k, mID, n429, lim, q):
    # excessively clever lambda that bypasses the voluntary throttle aspect of the
    # system default policy while still using the 429/500 bit
    nr = numerous.Numerous(apiKey=k, throttle= lambda nr, tp, td, up:
                (tp['result-code'] in (429, 500)) and up[0](nr, tp, up[1], up[2]))

    nr.statistics['serverResponseTimes'] = [0]*10    # keep 10, purely infomational
    testmetric = nr.metric(mID)
    expectedVal = testmetric.read()

    while nr.statistics['throttle429'] < n429 and lim != 0:
        if testmetric.read() != expectedVal:
            q.put({'error': "Huh, got a wrong value"})
            break
        if lim > 0:               # because -1 means "forever"
            lim -= 1

    q.put(nr.statistics)


apiKey = numerous.numerousKey(args.credspec)
nrMain = numerous.Numerous(apiKey=apiKey)


testmetric = None

if args.metric:
    #  - first attempt to use it as a metric ID. If that works, use that metric.
    #  - then attempt to look it up ByLabel 'STRING'
    #  - then attempt to look it up ByLabel 'ONE' (regexp processing will work)
    for mt in [ 'ID', 'STRING', 'ONE' ]:
        try:
            testmetric = nrMain.metricByLabel(args.metric, matchType = mt)
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
    testmetric = nrMain.createMetric(args.metric or 't429-temp-metric', 0, attrs=attrs)
    deleteIt = True

if args.debug:
    nrMain.debug(10)



#
# create one thread per "parallel" specified.
# Each thread will separately instantiate its own nr and its own copy
# of a metric object (all referring back to the same metric on the server)
# Each thread will put a dictionary on the outputQ when it is done, containing
# the results (the nr.statistics it generated).
#

outputQ = queue.Queue()

# create the threads...
theThreads = []
threadArgs = (apiKey, testmetric.id, args.n429, args.limit, outputQ)
for i in range(args.parallel):
    theThreads.append(threading.Thread(target=tester, args=threadArgs))

# start all the threads...
for t in theThreads:
    t.start()

# wait for all the threads
# we don't know that they will finish in this order (duh) but it doesn't
# matter (duh); the point is that we need to join all of them so we know they
# have all finished
for t in theThreads:
    t.join()

# and now just print all their results, if requested
if args.statistics:
    while True:
        try:
            print(outputQ.get(block=False))
        except queue.Empty:
            break

if deleteIt:
    testmetric.crushKillDestroy()
