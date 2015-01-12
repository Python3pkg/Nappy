# class Numerous

The Numerous class is how you get started:

    from numerous import Numerous
    nr = Numerous()

If you call `Numerous()` with no arguments, then the apiKey will come from the NUMEROUSAPIKEY environment variable. See the discussion of [`numerousKey()`](https://github.com/outofmbufs/Nappy/wiki/APIKey-Management) for details on how that works. If you don't want to use the NUMEROUSAPIKEY environment variable (or the other `numerousKey()` data sources) you can just specify an apiKey yourself:

    nr = Numerous(apiKey="nmrs_4V23js92bsdf")

By default the server is located at 'api.numerousapp.com' but if you need to override this for any reason:

    nr = Numerous(server='testbed.someotherserver.com')

## Public Attributes

The only public attribute is `serverName` and it is informational only:

    nr = Numerous()
    print("Using {} as the server".format(nr.serverName))

once you have instantiated a Numerous() setting `serverName` to anything else will NOT change the server being used.

## Methods

* metric(metricId) - instantiate a NumerousMetric object.
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
    u = nr.photo(open('something.jpg','rb'))    # set user's photo from an opened image file

    # or also can set it from raw image data
    # (this example is not a complete image)
    photoData = b"\x47\x49\x46\x38\x39\x61 ... and so forth"
    u = nr.photo(photoData, mimeType="image/gif")

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

Returns a list of the `count` most-popular metrics, sorted by numer of subscribers. This is not an iterator; it returns the full list. There is an undocumented server-imposed limit on `count`; at the time of this writing the server will not return more than 20 metrics via the API.

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

Strictly speaking other exceptions might be raised, especially if the problem is a lower-level networking problem (e.g., if the network conenction is offline); write your `except` clauses more generally if catching these is important to you (vs having them cause an uncaught exception). Or, more simply, just a naked `nr.ping()` call (not wrapped inside a `try`) and allow any Exceptions to cause a fatal exit error.

### debug(lvl=1)
Example usage:

    # nr is a Numerous
    prev = nr.debug(1)
    nr.ping()
    nr.debug(prev)

would end up showing you what operation is used for ping, for example.

