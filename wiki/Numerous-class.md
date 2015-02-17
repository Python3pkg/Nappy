# class Numerous

The Numerous class is how you get started:

    from numerous import Numerous
    nr = Numerous()

If you call `Numerous()` with no arguments, then the apiKey will come from the NUMEROUSAPIKEY environment variable. See the discussion of [`numerousKey()`](https://github.com/outofmbufs/Nappy/wiki/APIKey-Management) for details on how that works. If you don't want to use the NUMEROUSAPIKEY environment variable (or the other `numerousKey()` data sources) you can just specify an apiKey yourself:

    nr = Numerous(apiKey="nmrs_4V23js92bsdf")

By default the server is located at 'api.numerousapp.com' but if you need to override this for any reason:

    nr = Numerous(server='testbed.someotherserver.com')

In addition to `apiKey` and `server` it is also possible to specify a custom rate-limiting/throttle policy. See [Rate Limits](https://github.com/outofmbufs/Nappy/wiki/Rate-Limits) for details.

## Public Attributes

* `serverName` - informational only. The fully qualified domain name of the server. Changing this has no effect (you need to set it at constructor time).

* `agentString` - the user agent string that gets sent to the server with every request. You can set this to whatever you want although there's no really good reason to change it. It has no effect at the server.

* `statistics` - a dictionary containing counters and information about the internal workings of the class and might be useful to examine for testing or debugging. These are instantiated only as needed (so make at least one API call before examining this if you want to see what it contains).

## Methods

* metric(metricId) - instantiate a NumerousMetric object.
* metricByLabel(labelspec, matchType='FIRST') - alternate way to instantiate a NumerousMetric object by looking up a label instead of using an ID.
* createMetric(label, value=None, attrs={}) - create a new metric (and return a NumerousMetric object).
* metrics(userId=None) - get subscribed-to metrics
* user(userId=None) - get Numerous user information.
* userPhoto(imageDataOrOpenFile, mimeType="image/jpeg") - set your user photo.
* subscriptions(userId=None) - get your metric subscriptions.
* mostPopular(count=None) - get the list of the most popular metrics.
* ping() - test your connectivity to the Numerous server.
* debug(lvl=1) - Turn on/off debugging output.

## General Exceptions
Any API that communicates with the server can raise these specific Exceptions:
* NumerousAuthError: Authentication failure. Likely cause: API key is (or has become) no good.
* NumerousError: Any other server error including HTTP failures.

Other Exceptions are also possible, especially various lower-level exceptions you might see from network libraries if you lose network connectivity.

### metric(metricId)
Example usage:

    # nr is a Numerous() 
    m = nr.metric('9201292516052673667')      # specifying a metric ID

Instantiates a NumerousMetric object with the given metric ID. Typically you either "just know" the metric ID (e.g., for a particular metric you created/defined) or you found it via other API calls.

Note that this method does not do any validation on the metricId. If the metricId is bogus you won't know until later when you perform operations with the resulting NumerousMetric.

In addition to the standard/numeric metric ID you can specify one of these alternate forms:
```
# Numerous App-specific metric URL:
m = nr.metric('nmrs://metric/299336148273384') 

# the "self" API link in the metric attributes:
m = nr.metric('https://api.numerousapp.com/metrics/299336148273384')

# the web view URL:
m = nr.metric('http://n.numerousapp.com/m/1b8xa7fjg92r')

# a dictionary containing an 'id' field
# so, for example, this works to print all your metrics:
for mdict in nr.metrics():
    m = nr.metric(mdict)
    print(m)

# a dictionary containing a 'metricId' field, such as
# the dictionary returned by the subscriptions method:
for sb in nr.subscriptions():
    m = nr.metric(sb)
    print(m)
```

If the passed-in metricId looks like a URL then the tail end of that URL is taken, with base36 decoding in the case of the web-view URL. No sanity checking is performed on this acceptance of the tail-end of the URL; if you have provided a bogus URL you will find out when you go to use the metric (see `validate` if you care).

If the passed-in metricId isn't a URL but is indexable and contains a key 'metricId' or 'id', those will be used (in that order of preference).

Otherwise, and this is the normal/expected case, the passed-in metricId should just be a string representation of the actual metric ID.

In no case is the server contacted. This simply instantiates a `NumerousMetric` object and associates it with the given ID.

### metricByLabel(labelspec, matchType='FIRST')
Example usage:

    # nr is a Numerous()
    m = nr.metricByLabel('xyz')    

This will look up your metrics (via the nr.metrics() iterator) and search for one with a label containing 'xyz' _anywhere within the label_ (see below for how to control the matching rules). If a metric is found the corresponding NumerousMetric object is returned (else None).

There are five `matchType` values you can specify and three of them (including the default) treat the `labelspec` as a generalized unanchored regular expression. For example:

    m = nr.metricByLabel('a')

will match ANY metric that has an 'a' in its label. By default the `matchType` is 'FIRST' so the above call will return whatever metric happens to occur first (in an arbitrary server-defined order) and has the letter 'a' in its label, anywhere. 

To match only a metric whose name is exactly 'a' you would have to specify:

    m = nr.metricByLabel('^a$')

which is almost equivalent to

    m = nr.metricByLabel('a', matchType='STRING')

except that the 'STRING' variant will throw an exception if there are multiple matches (whereas the other variant returns an arbitrarily-defined first match)

The five valid values for matchType are:

* matchType='FIRST' - the default. The `labelspec` is used as a python regular expression and a corresponding NumerousMetric() object is instantiated based on the first metric label that matches. There is no way to predict what match will be 'FIRST' if there are multiple metrics that match.

* matchType='ONE' - Your entire metric list (i.e., what nr.metrics() iterates) is searched. If there is exactly one match the corresponding NumerousMetric() is returned. If there is more than one match then an exception (`NumerousMetricConflictError`) is thrown. 

* matchType='BEST' - the "best" match is returned, defined arbitrarily in an implementation-specific way.

* matchType='STRING' - in this case `labelspec` is treated as an ordinary string and it must exactly match one metric label. In other words the matching criteria is the string comparison `str1 == str2` with no regexp interpretation. If it matches more than one metric label a `NumerousMetricConflictError` will be thrown.

* matchType=`ID` - `labelspec` is treated as a metric ID, not as a label at all. However, unlike calling `nr.metric()` directly, this method does ensure that the resulting metric is accessible. In other words, this calls `m.validate()` for you, and will return `None` rather than an invalid metric object. 

Please note that `matchType` values are all upper-case and are case-sensitive. Specifying `matchType='One'` for example will throw an exception.

For `matchType` 'FIRST', 'BEST', or 'ONE' the `labelspec` is a python regular expression interpreted using the [`search`](https://docs.python.org/3/library/re.html#re.search) method from the python `re` class. This means it will match any substring of the label unless you specifically anchor it with `^` (start of label) or `$` (end of label). Any regular expression syntax understood by `re.search` may be used in `labelspec`.

In general, the `metricByLabel` method is mostly useful as a convenience when experimenting interactively in a python session. If used "for real" be aware that any `matchType` except for 'FIRST' requires iterating through the entire set of your metrics (metrics produced by the `nr.metrics` iterator). This requires at least one extra server API invocation and may require more if you have many metrics. Also there is no guarantee of label uniqueness; you can easily create two metrics with the same label. You may want to use the `matchType` 'ONE' to catch an ambiguous match.

### createMetric(label, value=None, attrs={})
Example usage:

    # nr is a Numerous()
    m = nr.createMetric("bozo", value=17, attrs={ "description" : "the clown" })

Creates a new metric on the server and returns a corresponding NumerousMetric object. The `label` argument is required; `value` is optional (default 0) and `attrs` is optional. Unspecified metric attributes will default as described in the NumerousApp API documentation. Note, in particular, that the server default for "private" is False.

### metrics(userId=None)
Example usage:

    # nr is a Numerous()
    for md in nr.metrics():
        print(md['label'],md['id'])

Iterator. Yields the metrics (in attribute dictionary form) for the given user (default is yourself).

### user(userId=None)
Example usage:

    # nr is a Numerous()
    u = nr.user()
    print(u['fullName'])

Returns a dictionary of user attributes as described in the NumerousApp API documentation. If a userId is specified, returns the dictionary for that user; otherwise it returns the dictionary for the user corresponding to the API key used with `nr`.


### userPhoto(imgInfo, mimeType="image/jpeg")
Example usage:

    # nr is a Numerous()
    u = nr.userPhoto(open('something.jpg','rb'))    # set user's photo from an opened image file

    # or also can set it from raw image data
    # (this example is not a complete image)
    photoData = b"\x47\x49\x46\x38\x39\x61 ... and so forth"
    u = nr.userPhoto(photoData, mimeType="image/gif")

Sets the user's photo from `imgInfo` which should either be an open file or raw image bytes. Note that in python3 you must open the file in 'rb' mode to avoid translation of the image bytes into Unicode (this is a generic python3 issue not specific to the Numerous class methods).

Returns the updated user attributes.

### subscriptions(userId=None) 
Example usage:

    # nr is a Numerous()
    for s in nr.subscriptions():
        print(s)

    # get subscriptions for some other user
    for s in nr.subscriptions(userId='3479283572920175101'):
        print(s)

This is an iterator which returns the subscription objects for yourself or another user. Each subscription object is a dictionary containing attributes as described in the NumerousAPI documentation.

Here is a simple program that would print out the raw values of all of the metrics you are subscribed to (all of the metrics that normally show when you bring up the Numerous app on your phone):

    from numerous import Numerous
    nr = Numerous()     # gets credential information from NUMEROUSAPIKEY environment variable

    for s in nr.subscriptions():
        m = nr.metric(s['metricId'])
        mDict = m.read(dictionary=True)         # get the entire dictionary of the metric
        print(mDict['label'], mDict['value'])   # really should do more formatting

As described in the API documentation, the server may return your subscriptions in multiple "chunks" if you have a lot of them. The subscriptions() method performs lazy fetching as needed. No call to the server is made until you request the first subscription from the iterator, and subsequent chunks (if any) are not fetched until you iterate past the subscriptions that were returned in the first chunk. All of this is handled transparently inside the `subscription()` method.

Additional specific Exceptions:
* NumerousChunkingError: An unexpected server error occurred while fetching any chunk of subscriptions other than the first chunk. This error is never "expected" but it can happen if the server returns an error while we are fetching the second or subsequent "chunk" of subscriptions. Essentially this is communicating an iteration that has been interrupted by some server or network error and is therefore incomplete. 
* An error that occurs on the first chunk will raise one of the standard exceptions such as NumerousError or NumerousAuthError. Note that if you attempt to get the subscriptions from a non-existent userId you will get a `NumerousError` exception and the code will be 403 (HTTP Forbidden). 

### mostPopular(count=None)
Example usage:

    # nr is a Numerous()
    populars = nr.mostPopular(count=3)

    print("The most popular metric is {}".format(populars[0]['label']))

Returns a list of the `count` most-popular metrics, sorted by number of subscribers. This is not an iterator; it returns the full list. There is an undocumented server-imposed limit on `count`; at the time of this writing the server will not return more than 20 metrics via the API.

### ping()
Example usage:

    # nr is a Numerous()
    nr.ping()

Verifies connectivity with the NumerousApp server by performing some operation (that has no side effects, such as reading the user object). If the operation succeeds, `ping()` returns True. If the operation fails an exception is raised. Thus the following code is ineffective:

    if not nr.ping():
        print("Cannot contact server")

The proper way to write that is:

    try:
        nr.ping()
    except NumerousError as e:
        print("Cannot contact server. Reason: {}".format(e.reason))

Strictly speaking other exceptions might be raised, especially if the problem is a lower-level networking problem (e.g., if the network connection is offline); write your `except` clauses more generally if catching these is important to you (vs having them cause an uncaught exception). Or, more simply, just a naked `nr.ping()` call (not wrapped inside a `try`) and allow any Exceptions to cause a fatal exit error.

### debug(lvl=1)
Example usage:

    # nr is a Numerous
    prev = nr.debug(1)
    nr.ping()
    nr.debug(prev)

would end up showing you what operation is used for ping, for example.
