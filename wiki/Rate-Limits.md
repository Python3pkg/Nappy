# Rate Limits
The NumerousApp server limits API calls to some number of calls per some period of time. Every API request made to the server returns several header elements relating to rate limiting. Although these header elements are not exposed via the Numerous class API, it is helpful to understand how they work. The two most important header elements are:

* `X-Rate-Limit-Remaining`: How many more API calls you can make without hitting the limit.
* `X-Rate-Limit-Reset`: How many seconds it will be until a new quota of API calls is given out to you.

At the time of this writing the server limit parameters are set up so that a client can make 300 calls per minute. So, for example, after you make your first API call your `X-Rate-Limit-Remaining` would be 299 and the `X-Rate-Limit-Reset` time would be somewhere between 1 and 59 seconds (implementation detail: the server seems to synchronize these to the top of the minute). At the time indicated by `X-Rate-Limit-Reset` a new quota of API calls will be allocated (`X-Rate-Limit-Remaining` will be refreshed to a higher value).

In English, this means as long as your API key generates fewer than 300 requests per minute (under the current server parameters) then you'll never see any rate limiting effects or errors.

If you exceed the rate limits the server will fail your request with an HTTP 429 "Too Many Requests" error code. If you enter this regime of response behavior the 429 error code will occur for all requests until enough time (`X-Rate-Limit-Reset`) elapses so that you get a fresh `X-Rate-Limit-Remaining`.

In extreme server overload cases you may also get an HTTP 500 "Too Busy" error code.

Rate limiting is on a "per-client" basis, which appears to mean "per API key" (not per client IP address).

## Default Throttling
To prevent you from hitting these limits, and to handle the cases where you DO hit the limits, the Numerous class implements a default rate throttling policy. The default rate throttling policy works like this:

* If you hit a 429 "Too Many Requests" limit or a 500 "Too Busy" error the client will delay for some amount of time and retry the request. This is transparent to you, you do not see the 429 or 500 code you just experience a time delay before your API call completes.

* If you are "getting close" (defined arbitrarily inside the code) to the server-communicated limit (X-Rate-Limit-Remaining) then you will be delayed a short amount of time. The idea behind this "voluntary" restraint is that not all clients (i.e., other implementations) may know how to handle the 429/500 error codes, so if we are getting close we want to voluntarily slow ourselves down for a little while to try to avoid hitting the "too many" condition if possible. Another advantage of voluntary restraint is to spread a possibly long X-Rate-Limit-Reset time across multiple API calls. One way or another if you've made too many API calls too quickly you are going to have to wait for more rate allocation, but it will seem less onerous to wait a little bit extra across multiple API calls than to wait the entire delay time on just one. 

When deciding to delay, the amount of time to wait is computed using a combination of X-Rate-Limit-Reset info (what the server told us to wait to get a new allocation of capacity) and an added exponential backoff factor based on how many times we have retried this particular request. So, for example, if you get a 429 we will wait how long the server tells us to wait plus a small amount "to be sure" (e.g., 2 extra seconds). If after that retry the code experiences ANOTHER 429 (during the retry of this same request), it will again wait however long the server has (once again) told us to wait, but will add an even longer "just to be sure" backoff time on top of that. Eventually the request will either go through or the code will give up and allow the 429 error to bubble up to you as an exception.

In practice, with multiple retries, the server-communicated X-Rate-Limit-Reset information, and the exponential backoff, there are no realistic scenarios in which you will see a 429 or 500 HTTP error come at you as an exception from an API call. You may, however, experience delays.

## Overriding the throttle policy
You can implement your own throttling policies. The documentation for this is ... in progress ... but for now I'll just point out the way you can completely disable the throttling policy:

```
nr = Numerous(throttle = lambda nr,tp,td,up: False)
```

will create a Numerous object with a no-op throttle policy. Your calls will never be delayed. They will never be retried. Any 429 "Too Many Requests" or 500 "Server Too Busy" errors from the server will cause an Exception that you can catch yourself and decide how to handle.