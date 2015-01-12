# To Do
Things that still need to be done, or at least might be useful if done.

## Rate Limiting
I have an implementation of rate limiting that handles 429 "Too Many Requests" from the server and also implements a throttling policy designed to prevent you from hitting that limit as you get close (by observing the `X-Rate-Limit-Remaining` headers returned by the server).

At the present time the NumerousApp server isn't enforcing the rate limits so I have been unable to test this code. Therefore I'm not releasing it yet. Once NumerousApp starts enforcing rate limits I will publish the rate limit aware code.

## Exception Wrap Subclass
By design the Numerous and NumerousMetric classes bubble up most errors as Exceptions and do not hide low-level errors some of which are a little silly. 

For example, deleting a metric photo when the metric has no photo causes a NumerousError exception, code 404. Arguably that error should be ignored. Along the same lines, deleting an interaction that doesn't exist causes a NumerousError exception with code 200 (OK). This is because the server returns code 204 (No Response) when an interaction is successfully deleted (so this is used as the "expected good response" code) and returns code 200 ("OK") when the specified interaction doesn't exist. This is understandable from a semantic invariant point of view - the interaction doesn't exist in either case after the call, so "OK" is a perfectly reasonable response. 

However it's worth noting that the server is quite inconsistent on this (e.g., 404 for deleting a metric photo that doesn't exist vs 200 for deleting an event that doesn't exist).

It seemed best to allow all these exceptions and raw idiosyncrasies to bubble up in case you needed to act on them for some reason. However, in the cases where you don't really want to know all this detail it can be a pain. And arguably some of it might be server-implementation-specific and hiding some of those details might be a Good Thing.

So I think there should be two subclasses, NumerousWrap and NumerousMetricWrap, that would do things like this:

    class NumerousWrap(Numerous):
        def ping(self):
            try:
                Numerous.ping(self)
            except NumerousAuthError:
                return False
            return True

and so forth, overriding (wrapping) just those methods that raise exceptions and handling the "we don't really care" cases accordingly.

## More convenience functions
It would be nice (for interactive / debugging / testing / development) to be able to access a metric by label name, e.g.

    m = nr.metric(metricByName('bozo'))

Obviously names aren't guaranteed to be unique. C'est la vie; the metricByName() function would just arbitrarily return one of them (or could throw an exception). It would be handy if metricByName() did some wildcarding too.

## caching?
Wondering if it is worth creating a caching class that would allow you to do a bunch of things to a metric and then commit() the results. Seems like a lot of work for no good reason though. I've gone back and forth on this.

## namespace vs dict
Similarly I've gone back and forth on whether it would be good to allow

    m = nr.metric('123123123')
    print(m.description)

vs what you have to do now:

    m = nr.metric('123123123')
    mdict = m.read(dictionary=True)
    print(mdict['description'])

a similar question exists for just letting you do:

    m = nr.metric('123123123')
    print(m['label'])

My problem with both of these ideas is that the operation would involve talking to the server so it's a lot more expensive than "Just accessing an attribute" would seem to imply. Also it can throw exceptions of course so that's also an argument (I think) against making this that implicit unless maybe it is combined with the cache concept.

Right now you solve all of those problems yourself by fetching the dictionary with `m.read(dictionary=True)` and just operating on the dictionary, and eventually putting it back accordingly (though you have to know whether you need to do `m.write` vs `m.update` or possibly both but that's how the NumerousApp API works).

