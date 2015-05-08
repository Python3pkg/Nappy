#!/usr/bin/python3
#
# Yet another NumerousApp atomicity test program.
# Can test atomicity of ADD operation and "OnlyIfChanged"
#
import argparse
import numerous
import queue
import threading

#
# arguments:
#    -c credspec  : the usual
#    -n num       : total number of requests to send to server
#    -m metric    : use metric as the test metric (see discussion below)
#    -p parallel  : number of threads run in parallel (default is 10)
#    -D           : debug flag
#    -q           : quiet - don't display anything (just exit status)
#    -v           : verbose - display extra stuff
#
# (Exactly) One non-optional argument must be given:
#        ADD - to run the ADD version of the test
#        ONLY - to run the OnlyIfChanged version of the test
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
parser.add_argument('-n', '--nwrites', type=int, default=50)
parser.add_argument('-D', '--debug', action="count")
parser.add_argument('-m', '--metric')
parser.add_argument('-p', '--parallel', type=int, default=10)
parser.add_argument('-q', '--quiet', action="store_true")
parser.add_argument('-v', '--verbose', action="store_true")
parser.add_argument('testtype', choices=['ADD', 'ONLY'])
args = parser.parse_args()

# sanity on parallel threads ... can't be less than 1
if args.parallel < 1:
    args.parallel = args.nwrites

# can't usefully be more than nwrites
if args.parallel > args.nwrites:
    args.parallel = args.nwrites

#
# This is the test function that is run in an individual thread, potentially
# in parallel (multiple threads running this function).
#
# Note in particular that we instantiate a local Numerous(), so it will
# be per-thread (versus the toplevel global one used to set up the test
# conditions). Similarly we instantiate a local metric (from the
# test metric's ID), again so it will be local to this thread vs shared
# across all the threads.
#
# The arguments are:
#    k      - the Numerous API key
#    mID    - the ID of the metric we should be banging on
#    n      - the number of calls to make
#    wargs  - arguments to pass to the metric.write() (aside from newval)
#    q      - queue for output results that will be picked up in main thread
#
def tester(k, mID, n, wargs, q):
    # excessively clever lambda that bypasses the voluntary throttle of
    # system default policy while still using it for the 429 
    nr = numerous.Numerous(apiKey=k, throttle= lambda nr, tp, td, up:
            (tp['result-code'] == 429) and up[0](nr, tp, up[1], up[2]))

    testmetric = nr.metric(mID)
    for i in range(n):
        try:
            v = testmetric.write(1, **wargs)
        except numerous.NumerousMetricConflictError:
            v = "NoChange"
        q.put(v)

apiKey = numerous.numerousKey(args.credspec)
nrMain = numerous.Numerous(apiKey=apiKey)

testmetric = None

if args.metric:
    #  - first attempt to use it as a metric ID. If works, use that metric.
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
    a = { 'private' : True,
          'description' : 'used by yatom testing program. Ok to delete'
        }
    testmetric = nrMain.createMetric(args.metric or 'yatom-temp', 0, attrs=a)
    deleteIt = True

if args.debug:
    if args.debug > 1:
        nrMain.debug(10)
    else:
        nrMain.debug(1)

# always start the testmetric at zero
testmetric.write(0)

# the arguments to pass to the metric.write() routine
if args.testtype == "ADD":
    wargs = { 'add' : True }
elif args.testtype == "ONLY":
    wargs = { 'onlyIf' : True }
else:
    print("Bad testtype",args.testtype)
    exit(1)


#
# create one thread per "parallel" specified.
# Each thread will separately instantiate its own nr and its own copy
# of a metric object (all referring back to the same metric on the server)
# Each thread will put a resulting value on the outputQ when it is done.

#

outputQ = queue.Queue()

# create the threads...
theThreads = []
for i in range(args.parallel):
    nToWrite = args.nwrites//args.parallel
    # account for residue, some threads will write 1 extra
    if i < (args.nwrites%args.parallel):
        nToWrite += 1
    
    threadArgs = (apiKey, testmetric.id, nToWrite, wargs, outputQ)
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
if args.verbose:
    while True:
        try:
            print(outputQ.get(block=False))
        except queue.Empty:
            break

exitStatus = 0

if args.testtype == "ADD":
    if testmetric.read() != args.nwrites:
        exitStatus = 1
        if not args.quiet:
            print("Wrong final value: {}".format(testmetric.read()))

if deleteIt:
    testmetric.crushKillDestroy()

exit(exitStatus)


