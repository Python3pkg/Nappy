# class NumerousMetric
The more common way to instantiate a NumerousMetric is via the `metric()` method in class `Numerous`. However you can also instantiate a NumerousMetric this way if you prefer:

    m = NumerousMetric(id, nr)

where `id` should be a string representation of a metric ID and `nr` should be a `Numerous()`. So, for example:

    nr = Numerous()
    m = NumerousMetric('123123123', nr)   # equivalent to m = nr.metric('123123123')

would set up m as a NumerousMetric with metric ID '123123123'. 

See the `metric` method in class `Numerous` for a more complete discussion of allowable types of metric IDs.

As a shorthand, although it is not normally recommended, you can even skip creating the Numerous object and just do this:

    m = numerous.NumerousMetric('123123123')

which will work as long as you have set up your NUMEROUSAPIKEY environment variable. The `NumerousMetric` constructor will call `numerous.Numerous()` for you in this case. So it's a nice short way to create a metric when all you need to do is some sort of one liner like:

    numerous.NumerousMetric('123123123').write(99)

to just update metric '123123123' to the value 99. Note, however, that each metric you instantiate this way gets its own brand new Numerous() object. Not recommended unless you really are just doing a one-shot update.

## Public Attributes
* `id` - the metric ID (string form)
* `nr` - the Numerous() object used to talk to the server.

## Exceptions
All of the methods that talk to the server can raise NumerousError or any of the subclasses (e.g., NumerousAuthError).

A few notes about error codes: in general, an invalid metric ID will cause an error 400 (Bad Request) if the metric ID is ill-formed, and error 404 (Not Found) if the metric ID "looks like" a metric ID but doesn't correspond to an accessible metric. These are, of course, determined by the server and may be implementation-specific observations.

Thus:

    m = NumerousMetric('123123123', nr)
    m.read()

is likely to raise a NumerousError with `code` 404 (assuming '123123123' doesn't exist as a valid metric ID), whereas: 

    m = NumerousMetric('totallyBogus', nr)
    m.read()

is likely to raise a NumerousError with `code` 400.

You can use the `validate` method if you need to try to figure out whether a given metric is accessible without worrying about these sorts of details.

## Methods
* read
* write
* Accessing cached fields with [ ]
* Human-readable string conversion `__str__`
* validate
* events
* stream
* interactions
* subscriptions
* subscription
* subscribe
* update
* like
* sendError
* comment
* photo
* photoDelete
* event
* eventDelete
* interaction
* interactionDelete
* label
* webURL
* appURL
* photoURL
* crushKillDestroy

### read(dictionary=False)
Example usage:

    v = m.read()

Reads the current value of the metric from the server. Returns the metric value, or returns the entire metric attribute dictionary if `dictionary=True`.

### write(newval, onlyIf=False, add=False, dictionary=False, updated=None)
Example usage:

    m.write(17)

Writes `newval` to the metric. The additional arguments are:

* `onlyIf` - specifying `onlyIf=True` will cause the metric to only be updated if `newval` is different than the currently stored value. 

This is useful when periodically refreshing a metric value periodically in an automated fashion, as you can avoid cluttering up the metric event list with updates that are to the same value (i.e., no change). If `newval` is indeed not different than the current value then a `NumerousMetricConflictError` will be raised. So, for example:

    m.write(17)
    try:
        m.write(17, onlyIf=True)
        print("Rewrote 17")
    except NumerousMetricConflictError:
        print("No update; it was already 17")

will print the "No update" message, not the "Rewrote 17" message (assuming no one else asynchronously changed the metric while we were running this code). The onlyIf operation is implemented, atomically, as a server-side operation via the API.

* `add` - specifying `add=True` causes `newval` to be added to the current value of the metric. 

Specifying `add` is nearly equivalent to this code:

    v = m.read()
    m.write(v + newval)

however the `add` operation is implemented atomically as a server-side operation via an explicit feature of the API. Several clients simultaneously adding to a metric using `add` will always give the correct result, whereas implementing the `add` yourself via two separate read/write operations leaves a race condition that could cause an incorrect final total if multiple people are doing it to one metric at the same time.

* `dictionary=False` - specifying `dictionary=True` will return the entire **event** attribute dictionary (reflecting the event created by this write; this is NOT the updated metric state); otherwise just the naked updated value is returned (which is obvious/redundant in a plain write but might not be obvious/redundant in an ADD operation).

* `updated=None` - you can set a specific timestamp to be associated with the value being written by passing in a string such as `updated='2015-01-21T15:43:57.123Z'`. The server is very strict about the format of this timestamp string; in particular note that the fractional seconds field must be exactly three digits (no more, no fewer). This is sometimes useful if you want to load historic data into a metric (and associate specific timestamps with those data points).

Exceptions:
* As already noted, raises NumerousMetricConflictError if `onlyIf=True` and there was no value change.

### Accessing cached fields with [ ]
You can access any named metric attribute (as defined in the NumerousAPI documentation) using the python subscript `[]` notation. For example:

    lbl = m['label']
    ownerId = m['ownerId']

When you do this you will be accessing a _cached_ copy of the data. The NumerousMetric class will perform a fetch from the server if necessary (the first time you access a metric in any way). Subsequent access via the subscript method will **always** access a cached copy if that copy is available.

Cache consistency is maintained only if all of your modifications of this metric go through this particular metric object. For example, this will work correctly:

    m = nr.metric(someID)   # instantiate "m" for the given someID
    m.write(1)
    v1 = m['value']
    m.write(2)
    v2 = m['value']

In this case `v1` will be 1 and `v2` will be 2.

However, this does NOT work correctly:

    m = nr.metric(someID)
    another_m = nr.metric(someID) # same ID but different object
    x = m['value']                # read current value of m
    another_m.write(x+1)          # update it but using other object
    print(m['value'])             # will print old value

This will print the old value, as it is still cached in the `m` object and the `m` object does not know that the server was updated via `another_m`.

Obviously caching also doesn't work correctly if the metric can be updated on the server behind your back. The point of the [ ] attribute caching is just to work in the obvious/simple way for the obvious/simple cases. The cache semantics are similar to:

    mycache = m.read(dictionary=True)     # get the entire metric dictionary
    # rest of program relies on mycache for metric attributes
    # so, for example:
    print("The metric label is", mycache['label'])
   
    # if I update the metric I know I should cache it again
    m.write(88)
    mycache = m.read(dictionary=True)     # update my cache of this metric

If your application requires different cache semantics use `m.read()` every time; it always contacts the server. Note also that every `m.read()` call updates the cached copy used for `[ ]` access. This happens regardless of whether you ask for just the value (using `m.read()`) or the entire dictionary (using `m.read(dictionary=True)`). At the server API level the GET operation returns the entire dictionary every time so the `read` method automatically updates the local cached copy of the metric attributes every time.

Writing to a metric via the subscript notation is not implemented. Thus:

    m['value'] = 17

will raise an exception (`TypeError`). For now this is on purpose, as allowing it would open up the question of whether to make it a heavy operation that contacts the server each time or a light operation that would only update the local cache (and thus require some additional "commit" method to eventually force the updates to the server).

In addition to the `__getitem__` python data model method that implements the [ ] notation, the NumerousMetric class provides `__contains__` and `__iter__` methods, so the following python idioms also work:

    if 'photoURL' in m:
        print("There is a photo associated with this metric")

    for k in m:
        print("Metric attribute {} is {}".format(k,m[k]))


### Human-readable string conversion: `__str__`
Example usage:

    print(m)

Whenever you convert a NumerousMetric into a string, a human-readable representation of the metric is provided by the `__str__` python data model method. 

In some cases the server will be contacted but in general the conversion to string will be done using a cached copy of the metric data. See the `[ ]` section above for a discussion of caching. Low-level network errors may raise exceptions but all "expected" exceptions from user errors will be handled internally and will produce an appropriate string representation. So, for example:

    someMetricID = '6994758820854512451'   # assume this is a real metric ID
    m1 = nr.metric(someMetricID)
    m2 = nr.metric('bogus id')   # completely invalid id format
    m3 = nr.metric('123123123')  # correct format but not valid

    m1.write(99)

    print(m1)
    print(m2)
    print(m3)

will generate output something like

    <NumerousMetric 'someLabel' [6994758820854512451] = 99>
    <NumerousMetric **INVALID-ID** : 'bogus id'>
    <NumerousMetric **ID-NOT-FOUND** : '123123123'> 

It is a very bad decision on your part to rely on the specific format of the data in this string. It is meant for human consumption for display/debugging.

### validate()
Example usage:
    
    if not m.validate():
        print("The metric is not valid")

Returns True if the metric is accessible; returns False if the metric cannot be accessed because of problems with the metric's ID (e.g., "Not Found"). Can also raise exceptions for other reasons (e.g., NumerousAuthError if the API key is no good).

### events() / stream() / interactions() / subscriptions()
These are all similar so are all described together here. Each of these four methods is an iterator. They produce the expected items one at a time using a lazy-fetch algorithm to deal with the server's "chunking" API as described in the NumerousApp API documentation.

For example, to compute the average value of a metric that has had many updates done to it:

    n = 0
    total = 0
    for ev in m.events():
        total += ev['value']
        n += 1
    print(total/n)

There are no arguments to any of the iterators.

* events() - iterator for metric events. Events are value updates.
* interactions() - iterator for metric interactions. Interactions are comments, likes, and errors.
* stream() - iterator for the metric stream. The stream is a time-ordered merge of events and interactions.
* subscriptions() - iterator for the metric's subscriptions. 

See the NumerousApp API documentation for details about the attributes of each of these types of items.

### update(dict, overwriteAll=False)
Example usage:

    newdict = m.update({ "description" : "this is a new description of the metric" })

Updates the metric attributes on the server. Only some attributes can be updated this way; consult the NumerousApp API documentation for details. In particular, you can NOT update the `value` this way; use `write()`.

The server returns a dictionary representing all of the metrics attributes (regardless of whether they were updated or not) and that dictionary (`newdict` above) is the return value of this method.

Because of the REST nature of the API, any values you do not specify in the server's update API call will be (re)set to initial values. This is not what you usually want. Therefore this method doesn't just write the `dict` you supply, but rather reads the current metric dictionary, merges your `dict` into it, and writes the merged dictionary back to the server. 

If instead you really want your dict to just be written as-is to the server, specify `overwriteAll=True`. For example:

    m.update({ "units" : "blivets" }, overwriteAll=True)

will also have the side effect of deleting any description and setting private to False (and possibly other side effects as defined by the server's rules for metric attribute defaults).

### like()
Example usage:

    likeID = m.like()

Likes a metric. Returns the ID of the created "like" interaction. There is no unlike/dislike method but if you want to undo a like:

    m.interactionDelete(likeID)

where `likeID` is the ID returned by a previous like() operation.

### sendError(errText)
Example usage:

    errorID = m.sendError("This is the error message")

Creates an "error" interaction on a metric. Returns the ID of the created interaction.  

### comment(cmtText)
Example usage:

    cmtID = m.comment("This is the comment")

Creates a "comment" interaction on a metric. Returns the ID of the created interaction.  

### photo(imgInfo, mimeType="image/jpeg")
Example usage:

    mdict = m.photo(open('something.jpg','rb'))    # set user's photo from an opened image file

    # or also can set it from raw image data
    # (this example is not a complete image)
    photoData = b"\x47\x49\x46\x38\x39\x61 ... and so forth"
    mdict = m.photo(photoData, mimeType="image/gif")

Sets the metric's photo from `imgInfo` which should either be an open file or raw image bytes. Note that in python3 you must open the file in 'rb' mode to avoid translation of the image bytes into Unicode (this is a generic python3 issue not specific to the Numerous class methods).

Returns the updated metric attributes.

### photoDelete()
Example usage:

    m.photoDelete()

Deletes the photo from a metric. No return value. 

Exceptions:
* NumerousError - `code` 404 if there is no metric photo.

### event(evID)
Example usage:

    evdict = m.event(evID)

Returns the attributes of a single metric event. Events are value updates.

Exceptions:
* NumerousError - `code` 404 if the event does not exist.

### eventDelete(evID)
Example usage:

    m.eventDelete(evID)

Deletes the specified event from a metric.

Exceptions:
* NumerousError - `code` 404 if the event does not exist.

### interaction(interactionID)
Example usage:

    idict = m.interaction(interactionID)

Returns the attributes of a single metric interaction. Interactions are likes, comments, and errors.

Exceptions:
* NumerousError - `code` 404 if the interaction does not exist.

### interactionDelete(interactionID)
Example usage:

    m.interactionDelete(interactionID)

Deletes the specified interaction from a metric.

Exceptions:
* NumerousError - `code` 404 if the interaction does not exist.

### label()
Example usage:

    print("The metric label is {}".format(m.label()))

Convenience function. Returns the metric label. Exactly equivalent to:

    m['label']

### webURL()
Example usage:

    print("You could surf this metric with your browser here: {}".format(m.webURL()))

Convenience function. Returns the URL that can be used to access the metric value via a browser. Exactly equivalent to:

    m['links']['web']

### appURL()
Example usage:

    print("Open this metric in the Numerous App: {}".format(m.appURL()))

Creates a URL that, if accessed on a mobile device or any other system with the Numerous App installed, will launch the application to view the metric. The URL uses the nmrs:// scheme and will typically not open in a regular browser.

### photoURL()
Example usage:

    print("Here is the storage for the metric photo: {}".format(m.photoURL()))

Convenience function. Takes the 'photoURL' from the metric attributes and performs an HTTP GET on it, to resolve out any redirects. Returns the final (non-redirecting) URL. The benefit of doing this is that the final URL is accessible without any API Key, whereas the 'photoURL' attribute contains a URL which is handled by the NumerousApp API server and still requires authentication to access.

Returns None if there is no metric photo.

### crushKillDestroy()
Example usage:

    m.crushKillDestroy()

Deletes a metric from the server. Permanent. There is no undo.