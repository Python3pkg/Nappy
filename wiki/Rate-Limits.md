# Rate Limits
The NumerousApp server limits API calls to some number of calls per minute (300 calls per minute at the time of this writing). Exceeding the rate limit causes _throttling_ -- requests to server fail and return a specific error telling the client to back off for some period of time.

The Numerous class handles throttling transparently so that applications never see errors caused by throttling. Instead they just experience time delay.

## How it works internally
The Numerous class looks at two rate-limiting elements in the server HTTP response:

* `X-Rate-Limit-Remaining`: How many API calls you have left.
* `X-Rate-Limit-Reset`: Seconds until more API calls will be given out to you.

So, for example, after your first API call `X-Rate-Limit-Remaining` would typically be 299 and the `X-Rate-Limit-Reset` time would be somewhere between 1 and 59 seconds.

> Implementation detail: the server seems to synchronize the reset time to the top of the minute.
> It is not a rolling 60 second window.

At `X-Rate-Limit-Reset` seconds into the future `X-Rate-Limit-Remaining` will be refreshed to its maximum value.

Thus, in general, as long as your API key generates fewer than 300 requests per minute you will never see any rate limiting effects or errors. But if you exceed the rate limits then the server will respond to your requests with an HTTP 429 "Too Many Requests" error. When this happens the Numerous class does not return that error to you; instead it internally delays (sleeps) and then automatically retries the request. You will not see the 429 error or even know that a retry happened; all you will know is your request (hopefully) succeeded but took extra time. 

**Note that the limit applies per API key**; multiple processes or indeed even multiple IP addresses accessing the server all under the same API key will all be counted against the same rate-limit. If you write an application that only generates a few API calls at a very slow rate it can definitely still receive 429 errors if there are other applications operating under the same API key. They could potentially use up your rate allocation and your low-frequency program would then experience the rate limiting error if it is not prepared to handle it.

## Default Throttling
To prevent you from hitting these limits, and to handle the cases where you DO hit the limits, the Numerous class implements a default rate throttling policy. The default rate throttling policy works like this:

* If you hit a 429 "Too Many Requests" limit the client will delay for some amount of time and retry the request. This is transparent to you, you do not see the 429 error you just experience a time delay before your API call completes.

* If you are "getting close" (defined arbitrarily inside the code) to the server-communicated limit (X-Rate-Limit-Remaining) then you will be delayed a short amount of time. The idea behind this "voluntary" restraint is that not all clients (i.e., other implementations) may know how to handle the 429 error code, so if we are getting close we want to voluntarily slow ourselves down for a little while to try to avoid hitting the "too many" condition if possible. Another advantage of voluntary restraint is to spread a possibly long X-Rate-Limit-Reset time across multiple API calls. One way or another if you've made too many API calls too quickly you are going to have to wait for more rate allocation, but it will seem less onerous to wait a little bit extra across multiple API calls than to wait the entire delay time on just one. 

When deciding to delay, the amount of time to wait is computed using a combination of X-Rate-Limit-Reset info (what the server told us to wait to get a new allocation of capacity) and an added exponential backoff factor based on how many times we have retried this particular request. So, for example, if you get a 429 we will wait how long the server tells us to wait plus a small amount "to be sure" (e.g., 2 extra seconds). If after that retry the code experiences ANOTHER 429 (during the retry of this same request), it will again wait however long the server has (once again) told us to wait, but will add an even longer "just to be sure" backoff time on top of that. Eventually the request will either go through or the code will give up and allow the 429 error to bubble up to you as an exception.

In practice, with multiple retries, the server-communicated X-Rate-Limit-Reset information, and the exponential backoff, there are no realistic scenarios in which you will see rate limiting errors come at you as an exception from an API call. You may, however, experience delays.

## Overriding the throttle policy
The default throttle policy can be replaced by a custom policy specified at Numerous() construction time. Custom throttle policies can completely replace the built-in default policy or can also simply augment it by performing some decisions and deferring others to the built-in policy.

A custom throttle function is called after **every** API interaction with the server. It is called with four arguments corresponding to this interface:

```
def throttleExample(nr, tparams, td, up):
    # do something here
    return False        # see text; return True or False
```

It is **very important** to note and understand that the throttle function is invoked **after** the API interaction with the server, not before. 

The four throttle function arguments are:
* `nr` - The Numerous() object. Most throttle functions won't need this but it is provided anyway.
* `tparams` - A dictionary containing data about the request and the rate limit fields returned by the server.
* `td` - Arbitrary data specific to the custom throttle function. This gets specified when the throttle function is first set up.
* `up` - Parameters required to call "up" the chain. Used by throttle policies that want to invoke the system default throttle policy in some cases.

The return value controls the retry logic. If the throttle function returns False then no further actions are taken and the response from the server becomes the eventual response for the API method invoked.

If the throttle function returns True then the API response from the server will be discarded and the original API call will be retried. It is only proper to return True when the response from the server is an error code (e.g. 429 / "Too Many Requests"); a throttle function erroneously returning True when the underlying API call actually succeeded is likely to cause obscure bugs. For example, returning True when the API call was a `metric.comment()` invocation that succeeded will cause the API code to retry the request and set a second, identical comment. Indeed simply always returning True will break the API completely and trap it in an infinite retry loop.

>As an aside: the code that invokes throttle policies contains an arbitrary retry 
>limit, partially to guard against this scenario; however, it is still true that 
>mistakenly returning True can break things in very obscure ways. Be very careful when 
>implementing a custom throttle policy function.

As already mentioned, a throttle function is invoked **after** each and every API interaction with the server. The function's job is to handle specific error codes such as "429 / Too Many Requests" and also possibly make other policy decisions about API rates.   

The `tparams` dictionary contains the following keys with data as described:
* `tparams['attempt']` - The attempt number. This will be zero if the attempt is the first time through for this particular operation. If, for example, the server returned a 429 error code and the throttle function returned True (requesting a retry), then the next time through `tparams['attempt']` would be 1.
* `tparams['result-code']` - the (integer) HTTP result code that came back from the server.
* `tparams['resp']` - the complete `requests` library HTTP Response object.
* `tparams['rate-remaining']` - the (integer) value of X-Rate-Limit-Remaining returned by the NumerousApp server. In some error cases it is possible for this to be missing in the server response in which case this parameter will be -1.
* `tparams['rate-reset']` - the (integer) value of X-Rate-Limit-Reset returned by the NumerousApp server. In some error cases it is possible for this to be missing in the server response in which case this parameter will be -1.
* `tparams['debug']` - the (integer) debug level set in the Numerous() object. Zero is no debugging.
* `tparams['request']` - a dictionary containing general information about the specific request that was made. Note: this is not a `requests` object; it is simply a dictionary containing two keys: 'http-method' indicates what type of operation was performed (e.g., 'GET', 'POST', etc) and 'url' contains the complete URL.

The `td` parameter passed to a throttle function comes from whatever was specified when the throttle function was set up. Given a throttle function `throttleExample` defined as above, the Numerous() call to install it as a throttle function looks like this:

```
nr = Numerous(throttle = throttleExample)
```

If the throttle function needs some data (for policy decisions or whatever purpose) that can be supplied as `throttleData` at constructor time, and it becomes the `td` parameter at invocation time. So, for example:

```
def bozoThrottle(nr, tparams, td, up):
    print(td)
    return False

nr = Numerous(throttle = bozoThrottle, throttleData="bozo the clown!")
```

would, quite annoyingly, cause "bozo the clown!" to be printed after every single API request was sent to the NumerousApp server.

Finally, the `up` parameter is a triple containing:
* `up[0]` - the system default throttle policy function.
* `up[1]` - the `td` parameter to be supplied to the `up[0]` function.
* `up[2]` - the `up` parameter to be supplied to the `up[0]` function.

At the present time there is no way to stack/unstack throttle policies (they can only be set up at Numerous() construction time); however this interface allows for an eventual "chain" of such policies if that makes sense in the future.

Given all this information, we can now write a no-op custom throttle policy that simply invokes the original system default policy but counts API invocations (as an example):

```
invocationCounts = { 'counter' : 0 }

def throttleWrapper(nr, tparams, td, up):
    td['counter'] += 1
    return up[0](nr, tparams, up[1], up[2])

nr = Numerous(throttle = throttleWrapper, throttleData=invocationCounts)
```

after that, looking at invocationCounts['counter'] would tell you how many times API requests had been sent to the server.

Another example could be to impose a 10 second delay on any authorization failure (HTTP 401 "Unauthorized"). That could look like this:
```
def delayAuthFailure(nr, tparams, td, up):
    if tparams['result-code'] == 401:
        time.sleep(10)
        return False        # no retry either
    else:
        # everything else defer to default handler
        return up[0](nr, tparams, up[1], up[2])  


nr = Numerous(throttle=delayAuthFailure, apiKey='boguskey')

nr.ping()   # will fail with an exception but also take an extra 10 seconds to do so

```

## Useful Custom Throttles

Given all this, it is still likely that the most useful custom throttle policy is the "no throttling" policy, which would implement no limits on API calls and simply allow the 429 ("Too Many Requests") errors from the server to bubble back up as NumerousError exceptions if they occur. Such a policy can be specified with this trivial lambda:

```
nr = Numerous(throttle = lambda nr,tp,td,up: False)
```

The second-most useful custom throttle policy might be one that disables the voluntary throttling and only backs off when the server specifically requires you to. You can accomplish that by writing a custom throttle function that only passes control to the built-in policy if there is an actual 429 error, and otherwise just returns False (no retry needed and of course no delay implemented in the policy). At the risk of being too cute with `lambda` that can still be accomplished without even writing a formal function and just specifying it in the Numerous() call this way:

```
nr = Numerous(throttle = lambda nr,tp,td,up: 
     (tp['result-code'] == 429) and up[0](nr, tp, up[1], up[2])
```

Though it might be more clearly expressed in a function:

```
def throttleNoVoluntary(nr, tp, td, up):
    if tp['result-code'] == 429:
      	return up[0](nr, tp, up[1], up[2])
    else:
        return False

nr = Numerous(throttle = throttleNoVoluntary)
```

## Pushing the Envelope: Server Errors 500/504
When subjected to unusually heavy loads the NumerousApp server will sometimes return an HTTP 504 "Gateway Timeout" error. It may also return a more generic HTTP 500 "Server Error" error.

>The NumerousApp support staff confirms that although the server is hosted on a service 
>that scales with increasing demand load, there are still some preset limits on the
>range of acceptable loads. You might think of this as "sanity check" the scaling service
>enforces in case something crazy causes a request storm at the server. This does mean, however,
>that sometimes unexpectedly-large or sudden increases in demand cause a temporary provisioning
>problem that leads to these server errors

It is likely, but by no means semantically guaranteed, that such server errors imply that the API operation was never completed and that it might be appropriate to delay for some period of time and try again. This can be implemented in a throttle function as shown here:

```
# CAUTION: DO NOT USE THIS WITHOUT UNDERSTANDING THE IMPLICATIONS
#          OF POSSIBLE NON-IDEMPOTENT API DUPLICATION
def throttleRetryServerErrors(nr, tp, td, up):
    if tp['result-code'] in (500, 504):
        # The server failed -- usually because of high load.
        # Delay an arbitrary amount of time and try again.
        # XXX Hope this doesn't cause a duplicate API operation.
        time.sleep(45)     # arbitrary; might be better keyed off attempt number
        return True        # and do a retry
    # all other cases let the built-in policy handle it
    else:                
      	return up[0](nr, tp, up[1], up[2])
```

If you use this throttle, be aware that there is the possibility that your API calls might get duplicated. For many API calls this really doesn't matter:

```
    m.write(17)
    m.write(17)
```

has the same net effect as just a single call `m.write(17)` would. Such an API call is **idempotent** and can be executed more than once without changing its semantics (in the case of writing a fixed value to a metric we are ignoring the possibility of race conditions with other writers or readers, in which case arguably executing the API twice changes the semantics but if there is no locking the semantics are already ill-defined). Here are the primary non-idempotent NumerousApp operations:

* Using the `add=True` or `onlyIf=True` option on write. In the case of `add` the difference between doing the API twice vs once is obvious; in the case of `onlyIf` the difference is the subtle one of whether or not the operation succeeds or fails with NumerousMetricConflictError.
* Setting a comment or an error on a metric. Duplicating the API call will result in duplicated comments or errors visible in the metric's stream. It's not clear whether likes are counted (which would be non-idempotent) or just a zero/non-zero thing (which would be idempotent).
* Creating a metric.

Conceptually we could expand the logic in the throttle function to look at the request details and only do a retry on the idempotent requests. That is left as an exercise for someone else (it's not entirely trivial but you'd have to parse the request URL enough to understand which operation was being requested; perhaps it wouldn't be unreasonable to extend the APIInfo table with an idempotent flag and supply this to the throttle policy). In practice if all you are doing is reading/writing a metric and you really want the operation to succeed even in the face of HTTP 500/504 "server overloaded" errors you could use the above throttle to provide that for you.