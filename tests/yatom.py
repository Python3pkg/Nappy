#!/usr/bin/python3
#
# Yet another NumerousApp atomicity test program.
# Can test atomicity of ADD operation and "OnlyIfChanged"
#
import argparse
import numerous
import queue
import threading
import time

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
#    tID    - thread ID (only really used for debugging)
#    mID    - the ID of the metric we should be banging on
#    n      - the number of calls to make
#    wargs  - arguments to pass to the metric.write() (aside from newval)
#    q      - queue for output results that will be picked up in main thread
#    evts   - two events used to synchronize start:
#                 evts[0] will be signalled here when ready to go
#                 evts[1] will be signalled by main thread when time to go
#
def tester(k, tId, mID, n, wargs, q, evts):
    # excessively clever lambda that bypasses the voluntary throttle of
    # system default policy while still using it for the 429
    nr = numerous.Numerous(apiKey=k, throttle= lambda nr, tp, td, up:
            (tp['result-code'] == 429) and up[0](nr, tp, up[1], up[2]))

    testmetric = nr.metric(mID)

    # one time to prime the pump, avoid TCP connect overhead during test, etc.
    ignored = testmetric.read()

    # Let the main thread know we got to this staging point
    evts[0].set()

    # and wait for everyone else to get there too (set() by main thread)
    evts[1].wait()

    for i in range(n):
        try:
            t0 = time.time()
            v = testmetric.write(1, **wargs)
            dt = time.time() - t0
        except numerous.NumerousMetricConflictError:
            dt = time.time() - t0
            v = "NoChange"
        q.put({'thread': tId,
               'result': v,
               'timestamps': [ t0, dt ]})

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
thread_objs = []
go_event = threading.Event()
threads_ready = []
nthreads = args.parallel
for i in range(nthreads):

    trdy_event = threading.Event()          # individual thread ready signal
    threads_ready.append(trdy_event)

    nToWrite = args.nwrites//args.parallel
    # account for residue, some threads will write 1 extra
    if i < (args.nwrites%args.parallel):
        nToWrite += 1

    evts = (trdy_event, go_event)
    threadArgs = (apiKey, i, testmetric.id, nToWrite, wargs, outputQ, evts)
    thread_objs.append(threading.Thread(target=tester, args=threadArgs))

# start all the threads...
for t in thread_objs:
    t.start()

# wait for all of them to get poised...
# they might not happen in this order but it really doesn't matter;
# one way or another we just wait for them all
for i in range(nthreads):
    threads_ready[i].wait()


# ok they've all reached the point of signalling they are ready to start
# banging on the server. Let them loose. The point of this little dance
# was to attempt to maximize the chance of multiple requests flying to
# the server all at once (to whatever extent our machine can do that)
#

go_event.set()

# wait for all the threads
# we don't know that they will finish in this order (duh) but it doesn't
# matter (duh); the point is that we need to join all of them so we know they
# have all finished
for t in thread_objs:
    t.join()

# get all the results
results = []
while True:
    try:
        results.append(outputQ.get(block=False))
    except queue.Empty:
        break

# and now just print all their results, if requested
if args.verbose:
    print (results)

exitStatus = 0

if args.testtype == "ADD":
    if testmetric.read() != args.nwrites:
        exitStatus = 1
        if not args.quiet:
            print("Wrong final value: {}".format(testmetric.read()))
elif args.testtype == "ONLY":
    changes = 0
    for x in results:
        if x['result'] != "NoChange":
            changes += 1

    if changes != 1:
        exitStatus = 1
        if not args.quiet:
            print("It changed {} times instead of the expected once.".format(changes))

if deleteIt and (exitStatus == 0):
    testmetric.crushKillDestroy()

exit(exitStatus)


