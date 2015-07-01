# example alternate throttle policy implementations

#
# This throttle policy disables the voluntary backoff 
# of the built-in throttle policy. It does that by simply
# not invoking the built-in policy EXCEPT if we are in 
# the 429 error condition, in which case we let the
# default policy handle it.
#
def throttleNoVoluntary(nr, tparams, td, up):
    if tparams['result-code'] == 429:
        return up[0](nr, tparams, up[1], up[2])
    return False


# you can also "spell" that this way if you really want to haha
lambda nr, tp, td, up: (tp['result-code'] == 429) and up[0](nr, tp, up[1], up[2])


#
# This throttle policy is an amusing hack that simply records the 
# http request info (which is made available to the throttle). So it's
# essentially creating a "log" of what was sent to the server.
#

def throttleWrap(nr, tparams, td, up):
    td.append((tparams['request'], tparams['result-code']))
    return up[0](nr, tparams, up[1], up[2])


#
# To use it, do this:
#
#    saved_requests = []
#    nr = Numerous(throttle=throttleWrap, throttleData=saved_requests)
#
# Then after any Numerous operation you can see the saved requests info:
#
#    nr.ping()
#    print(saved_requests)


