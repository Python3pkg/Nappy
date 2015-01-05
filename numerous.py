#
# Copyright (c) 2014, Neil Webber
# All rights reserved. 
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# #################
#
# Classes for the NumerousApp API
#      Numerous       -- server-level operations
#      NumerousMetric -- individual metrics
#
# PYTHON3: 
# This code is written and maintained for python3.
#
# PYTHON2:
# I backported to python2 (only needed two minor hacks); it works. 
# I primarily develop/maintain this code using python3 but I do keep 
# running my test script against python2 as well. 
# It should work but: Caveat User.
#
# #################

import json
import sys              # only for version in user-agent string
import requests         # (cheerleading: wow this made the HTTP code simple)
import logging          # needed for debug output 

# --- - --- - --- only needed to enable HTTP debugging output
try:
  from http.client import HTTPConnection
except ImportError: 
  # You are using python2, proceed at your own risk
  from httplib import HTTPConnection
# --- - --- - --- 

_NumerousClassVersionString = "20150105.dedupe-xxx"

#
# metric object
#
# Generally you create these using the Numerous.metric() method
# so that they hang off of a particular connection to NumerousApp server.
#
class NumerousMetric:
    #
    # __APIInfo: Metric API information (URL etc details)
    # 
    # Describes endpoints for simpleAPI(see). 
    # Also contains iterator details (next URL and "list" names)
    #
    # {} substitutions are filled in via **kwargs in getAPI calls.
    # Thus, for example, {metricId} becomes the passed-in metric ID
    #
    __APIInfo = {}

    # GET this to read a stream
    __APIInfo['stream'] = {
        'endpoint' : '/v2/metrics/{metricId}/stream',
        'GET' : {
            'next' : 'next',
            'list' : 'items',
            'dupFilter' : 'id'
        }
    }

    # GET or POST events collection of a metric
    __APIInfo['events'] = {
        'endpoint' : '/v1/metrics/{metricId}/events',
        'GET' : {
            'next' : 'nextURL',
            'list' : 'events',
            'dupFilter' : 'id'
        },
        'POST' : {
            'success-codes' : [ 201 ]
        }
    }

    # GET or DELETE an individual event
    __APIInfo['event'] = {
        'endpoint' : '/v1/metrics/{metricId}/events/{eventID}',
        'DELETE' : { 'success-codes' : [ 204 ] }
    }

    # GET or POST interactions collection of a metric
    __APIInfo['interactions'] = {
        'endpoint' : '/v2/metrics/{metricId}/interactions',
        'GET' : {
            'next' : 'nextURL',
            'list' : 'interactions',
            'dupFilter' : 'id'
        },
        'POST' : {
            'success-codes' : [ 201 ]
        }
    }

    # GET or DELETE an individual interaction
    __APIInfo['interaction'] = {
        'endpoint' : '/v2/metrics/{metricId}/interactions/{item}',
        'DELETE' : { 'success-codes' : [ 204 ] }
    }

    # subscriptions collection
    __APIInfo['subscriptions'] = {
        'endpoint' : '/v2/metrics/{metricId}/subscriptions',
        'GET' : {
            'next' : 'nextURL',
            'list' : 'subscriptions'
        }
    }

    # Your specifically individual subscription on a metric
    __APIInfo['subscription'] = {
        'endpoint' : '/v1/metrics/{metricId}/subscriptions/{userId}',
        'defaults' : {
            'userId' : 'me'           # default userId for yourself ("me")
        },
        'PUT' : {
            'success-codes' : [ 200, 201 ]
        }
    }

    # GET an actual metric, or update (PUT) it (parameters, not value)
    __APIInfo['metric'] = {
        'endpoint' : '/v1/metrics/{metricId}' ,
        # no entries needed for GET/PUT because no special codes etc
        'DELETE' : {
            'success-codes' : [ 204 ]
        }
    }

    # POST a photo or DELETE it
    __APIInfo['photo'] = {
        'endpoint' : '/v1/metrics/{metricId}/photo',
        'POST' : {
            'success-codes' : [ 201 ]
        },
        'DELETE' : {
            'success-codes' : [ 204 ]
        }
    }

    # constructor ... usually invoked via Numerous.metric()
    def __init__(self, id, numerous):
        self.id = id
        self.nr = numerous

    # Just a small wrapper around nr._makeAPIcontext, to use our API table 
    # (vs the Numerous class one) and to automatically supply {metricId}
    def __getAPI(self, what, whichOp, **kwargs):
        info = self.__APIInfo[what]
        id = self.id
        return self.nr._makeAPIcontext(info, whichOp, metricId=id, **kwargs)

    # Read value of a metric.
    # Return the naked numeric value or the full dict (dictionary=True)
    def read(self, dictionary=False):
        api = self.__getAPI('metric', 'GET')
        v = self.nr._simpleAPI(api)
        return v if dictionary else v['value']

    # "Validate" a metric object.
    # There really is no way to do this in any way that carries much weight.
    # However, if a user gives you a metricId and you'd like to know if
    # that actually IS a metricId, this might be useful. Realize that
    # even a valid metric can be deleted out from under and become invalid.
    #
    # Reads the metric, catches the specific exceptions that occur for 
    # invalid metric IDs, and returns True/False. Other exceptions mean
    # something else went awry (server down, bad authentication, etc).
    def validate(self):
        try:
            ignored = self.read()
            return True
        except NumerousError as v:
            # bad request (400) is a completely bogus metric ID whereas 
            # not found (404) is a well-formed ID that simply does not exist
            if v.code == 400 or v.code == 404:
                return False
            else:                # anything else you figure out yourself!
                raise

        return False  # never happens

    # common code for the events/stream/interactions collections iterators
    def __collections(self, what):
        api = self.__getAPI(what, 'GET')
        return _Numerous_ChunkedAPIIter(self.nr, api)

    # iterator -- typical usage: for event in metric.events():
    def events(self):
        return self.__collections('events')

    # iterator
    def stream(self):
        return self.__collections('stream')

    # iterator
    def interactions(self):
        return self.__collections('interactions')

    # NOTE: This will be subscriptions for THIS metric
    #       See also Numerous.subscriptions which will operate by USER
    def subscriptions(self):
        return self.__collections('subscriptions')

    # This is an individual subscription -- namely, yours.
    # normal users can never see anything other than their own
    # subscription so there is really no point in ever supplying
    # the userId parameter (the default is all you can ever use)
    def subscription(self, userId=None):
        api = self.__getAPI('subscription', 'GET', userId=userId)
        return self.nr._simpleAPI(api)

    # Subscribe to a metric. See the API docs for what should be
    # in the dict. This function will fetch the current parameters
    # and update them with the ones you supply (because the server
    # does not like you supplying an incomplete dictionary here).
    # While in some cases this might be a bit of extra overhead
    # it doesn't really matter because how often do you do this...
    # You can, however, stop that with overwriteAll=True
    #
    # NOTE that you really can only subscribe yourself, so there
    #      really isn't much point in specifying a userId 
    def subscribe(self, dict, userId=None, overwriteAll=False):
        if overwriteAll:
            params = {}
        else:
            params = self.subscription(userId)

        for k in dict:
            params[k] = dict[k]

        api = self.__getAPI('subscription', 'PUT', userId=userId)
        return self.nr._simpleAPI(api, jdict=params)

    # write a value to a metric.
    #
    #   onlyIf=True sends the "only if it changed" feature of the NumerousAPI.
    #      -- throws NumerousMetricConflictError if no change
    #   add=True sends the "action: ADD" (the value is added to the metric)
    #   dictionary=True returns the full dictionary results.
    def write(self, newval, onlyIf=False, add=False, dictionary=False):
        j = { 'value' : newval }
        if onlyIf:
            j['onlyIfChanged'] = True
        if add:
            j['action'] = 'ADD'

        api = self.__getAPI('events', 'POST')
        try:
            v = self.nr._simpleAPI(api, jdict=j)

        except NumerousError as v:
            # if onlyIf was specified and the error is "conflict"
            # (meaning: no change), raise ConflictError specifically
            if onlyIf and v.code == 409:
                raise NumerousMetricConflictError(v.details, 0, "No Change")
            else:
                raise         # never mind, plain NumerousError is fine

        return v if dictionary else v['value']

    #
    # Write the parameters (description, etc) of a metric
    # NOTE THAT THIS IS NOT FOR SETTING THE VALUE. This is for description etc
    #
    # The server semantics are that the dict completely replaces the
    # current parameters. So you can't just update the description, you
    # have to send the entire shebang back (REST). As a convenience we
    # will do the read/modify/write for you automatically, unless you
    # specify overwriteAll=True
    #
    # NOTE WELL: if overwriteAll=True and you only send in a partial
    #            dict then all the other parameters of the metric will
    #            revert to their defaults. You rarely want that.
    #
    def update(self, dict, overwriteAll=False):
        if overwriteAll:
            newParams = {}
        else:
            newParams = self.read(dictionary=True)

        for k in dict:
            newParams[k] = dict[k]

        api = self.__getAPI('metric', 'PUT')
        return self.nr._simpleAPI(api, jdict=newParams)

    #
    # common code for writing an interaction (comment/like/error)
    #
    def __writeInteraction(self, dict):
        api = self.__getAPI('interactions', 'POST')
        v = self.nr._simpleAPI(api, jdict=dict)
        return v['id']

    #
    # "Like" a metric
    #
    def like(self):
        # a like is written as an interaction
        j = { 'kind' : 'like' }
        return self.__writeInteraction(j)

    #
    # Write an error to a metric
    #
    def sendError(self, errText):
        # an error is written as an interaction thusly:
        # (commentBody is used for the error text)
        j = { 'kind' : 'error' , 'commentBody' : errText }
        return self.__writeInteraction(j)

    #
    # Simply comment on a metric
    #
    def comment(self, ctext):
        j = { 'kind' : 'comment' , 'commentBody' : ctext }
        return self.__writeInteraction(j)

    # Write a photo to a metric
    #   imageDataOrOpenFile should either be a bytes object or an open fd
    #   Note well you most likely need to open that "rb" (python3)
    def photo(self, imageDataOrOpenFile, mimeType="image/jpeg"):
        api = self.__getAPI('photo', 'POST')
        mpart = { 'image' : ( 'image.img', imageDataOrOpenFile, mimeType) }
        v = self.nr._simpleAPI(api, multipart=mpart)
        return v

    def photoDelete(self):
        api = self.__getAPI('photo', 'DELETE')
        v = self.nr._simpleAPI(api)
        # there is no return value

    # get an individual event by ID
    def event(self, evID):
        api = self.__getAPI('event', 'GET', eventID=evID)
        return self.nr._simpleAPI(api)

    def eventDelete(self, evID):
        api = self.__getAPI('event', 'DELETE', eventID=evID)
        v = self.nr._simpleAPI(api)
        # there is no return value

    # get an individual interaction by ID
    def interaction(self, interID):
        api = self.__getAPI('interaction', 'GET', item=interID)
        return self.nr._simpleAPI(api)

    def interactionDelete(self, interID):
        api = self.__getAPI('interaction', 'DELETE', item=interID)
        v = self.nr._simpleAPI(api)
        # there is no return value

    # some convenience functions ... but all these do is query the
    # server (read the metric) and return the given field... you could
    # do the very same yourself. So I only implemented a few useful ones.
    def label(self):
        v = self.read(dictionary=True)
        return v['label']

    def webURL(self):
        v = self.read(dictionary=True)
        return v['links']['web']

    # the photoURL returned by the server in the metrics parameters
    # still requires authentication to fetch (it then redirects to the "real"
    # static photo URL). This function goes one level deeper and
    # returns you an actual, publicly-fetchable, photo URL. I have not
    # yet figured out how to tease this out without doing the full-on GET
    # (using HEAD on a photo is rejected by the server)
    def photoURL(self):
        v = self.read(dictionary=True)
        if 'photoURL' in v:
            u = self.nr._getRedirect(v['photoURL'])
        else:
            u = None
        return u

    # Be really sure you got this call correct because it cannot be undone
    # Deletes the metric from the numerous server
    def crushKillDestroy(self):
        api = self.__getAPI('metric', 'DELETE')
        v = self.nr._simpleAPI(api)
        # there is no return value

# ################
# Numerous class
# ################
#
# This is your "connection" to the server (albeit there is no connection)
# You generally just make one of these (or one per APIKey you are working with)
# Then you instantiate NumerousMetric objects off of it.
#
#

class Numerous:

    # this APIInfo is for server-level APIs (not metric APIs)
    #     -- create a Metric
    #     -- list all the Metrics
    # etc, anything not related to a specific (existing) metric

    __APIInfo = {}

    # POST to this to create a metric
    __APIInfo['create'] = { 
        'endpoint' : '/v1/metrics',
        'POST' : {
            'success-codes' : [ 201 ]
        }
    }

    # GET a user's metric collection
    __APIInfo['metrics-collection'] = {
        'endpoint' : '/v2/users/{userId}/metrics',
        'defaults' : { 
            'userId': 'me'            # default userId meaning "myself"
        },
        'GET' : {
            'next' : 'nextURL',
            'list' : 'metrics',
        }
    }

    # subscriptions at the user level
    __APIInfo['subscriptions'] = {
        'endpoint' : '/v2/users/{userId}/subscriptions',
        'defaults' : { 
            'userId': 'me'            # default userId meaning "myself"
        },
        'GET' : {
            'next' : 'nextURL',
            'list' : 'subscriptions',
        }
    }

    __APIInfo['user'] = {
        'endpoint' : '/v1/users/{userId}',
        'defaults' : { 
            'userId': 'me'            # default userId meaning "myself"
        },
        'photo' : {
            'append-endpoint' : '/photo',
            'http-method' : 'POST',
            'success-codes' : [ 201 ]
        }
    }

    # most popular metrics
    __APIInfo['popular'] = {
        'endpoint' : '/v1/metrics/popular?count={count}',
        'defaults' : { 
            'count' : 10
        }
        # no entry needed for GET because no special codes etc
    }


    #
    # This gathers all the relevant information for a given API
    # and fills in the variable fields in URLs. It returns an "api context"
    # containing all the API-specific details needed by _simpleAPI.
    #

    def _makeAPIcontext(self, info, whichOp, **kwargs):

        rslt = {}
        rslt['http-method'] = whichOp

        # Build up the substitutions from the defaults (if any) and non-None 
        # kwargs. Note: we are careful not to be modifying the underlying 
        # dictionaries (i.e., we are making a new one)
        substitutions = {}
        dflts = info.get('defaults', {})

        # copy the defaults, assume no moron put a "None" in there
        for k in dflts:
            substitutions[k] = dflts[k]   # btw don't put a None in 'defaults'

        # copy the supplied kwargs, which might have None (skip those)
        for k in kwargs:
            if kwargs[k]:
                substitutions[k] = kwargs[k]

        # this is the stuff specific to the operation, e.g.,
        # the 'next' and 'list' fields in a chunked GET
        # There can also be additional endpoint info.
        # process the endpoint appendage and copy everything else

        appendThis = ""
        endpoint = info['endpoint']
        if whichOp in info:
            opi = info[whichOp]
            for k in opi:
                if k == 'append-endpoint':
                    appendThis = opi[k]
                elif k == 'endpoint':
                    endpoint = opi[k]   # endpoint overridden on this one
                else:
                    rslt[k] = opi[k]

        # fill the {whatever} fields from defaults and kwargs
        rslt['base-url'] = (endpoint + appendThis).format(**substitutions)
        return rslt

    # 
    # server, if specified,  should be a naked FQDN 
    # (e.g., 'api.numerousapp.com')
    # 
    def __init__(self, apiKey, server='api.numerousapp.com'):
        # the serverName is just saved for informational purposes
        # the __serverURL is used with the various endpoints
        self.serverName = server
        self.__serverURL = "https://" + server
        self.authTuple = (apiKey, '')
        self.__debug = 0

        # The version string will be used for the user-agent
        pyV = "(Python {}.{}.{})".format(sys.version_info.major,
                                         sys.version_info.minor,
                                         sys.version_info.micro)

        myVersion = "NW-Python-NumerousClass/" + _NumerousClassVersionString
        self.agentString = myVersion + " " + pyV + " NumerousAPI/v2"
        self._filterDuplicates = True    # see discussion elsewhere


    # XXX This is primarily for testing; control filtering of bogus duplicates
    #     If you are calling this you are probably doing something wrong.
    def _setBogusDupFilter(self, f):
        prev = self._filterDuplicates
        self._filterDuplicates = f

    # control debugging level
    def debug(self, lvl=1):
        prev = self.__debug
        self.__debug = lvl
        HTTPConnection.debuglevel = lvl
        if lvl > 1:
            logging.basicConfig()
            logging.getLogger().setLevel(logging.DEBUG)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True
        elif lvl == 0:
            # XXX this turns off debugging but doesn't necessarily put
            #     things back to the exact way they were. Tough noogies.
            logging.getLogger().setLevel(logging.CRITICAL)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.CRITICAL)

        return prev


    # instantiate a metric hanging off this Numerous instance
    # NOTE: You can also instantiate naked metrics but they eventually 
    #       have to associate with a Numerous. So the usual way is:
    #             nr = Numerous(blah blah)
    #             m = nr.metric('123123123')
    #
    # vs m = NumerousMetric('123123123') and then m.nr = nr
    #
    # If your metricId is bogus you won't know here. You can create
    # entirely bogus metric objects, e.g.
    #
    #      m = NumerousMetric('Something Entirely Bogus')
    #
    # You will (of course) eventually get exceptions and errors when used.
    # Even with a valid metricId your metric object can still become
    # stale if someone deletes it out from under you.  One reason we do 
    # not bother to enforce "validity" here, since even if it is valid now 
    # it might not be valid anytime immediately after tested.
    #
    # If validity is important to you use metric.validate() but understand 
    # that even that is no guarantee of validity since a metric can be 
    # deleted out from under you at any time.

    def metric(self, metricId):
       return NumerousMetric(metricId, self)

    # iterator for the entire metrics collection. 
    # By default gets your own metrics list but you can specify other users
    def metrics(self, userId=None):
        info = self.__APIInfo['metrics-collection']
        api = self._makeAPIcontext(info, 'GET', userId=userId)
        return _Numerous_ChunkedAPIIter(self, api)

    # return User info (Default is yourself)
    def user(self, userId=None):
        info = self.__APIInfo['user']
        api = self._makeAPIcontext(info, 'GET', userId=userId)
        return self._simpleAPI(api)

    # you can only set your own user photo info
    def userPhoto(self, imageDataOrOpenFile, mimeType="image/jpeg"):
        info = self.__APIInfo['user']
        api = self._makeAPIcontext(info, 'photo')
        mpart = { 'image' : ( 'image.img', imageDataOrOpenFile, mimeType) }
        v = self._simpleAPI(api, multipart=mpart)
        return v
       
    # iterator for per-user subscriptions. Note: users really
    # can't get anyone's subscriptions other than their own
    def subscriptions(self, userId=None):
        info = self.__APIInfo['subscriptions']
        api = self._makeAPIcontext(info, 'GET', userId=userId)
        return _Numerous_ChunkedAPIIter(self, api)

    # return the most popular metrics (returns "count" of them; default 10)
    def mostPopular(self, count=None):
        info = self.__APIInfo['popular']
        api = self._makeAPIcontext(info, 'GET', count=count)
        return self._simpleAPI(api)

    # test/verify connectivity to the server
    def ping(self):
        # there is no server API for ping, so just do...
        ignored = self.user()
        return True      # errors throw exceptions

    #
    # Create a brand new metric on the server 
    # Returns a NumerousMetric object
    #
    # You can specify additional initial attributes; 
    # see the NumerousApp api for details. The most useful
    # initial attribute is value, e.g., { 'value' : 17 } ... this
    # is useful enough that there's also a separate convenience
    # argument you can specify: createMetric("Bozo", value=17)
    # If you specify a value via the keyword arg it overrides any
    # value in the attrs
    #
    def createMetric(self, label, value=None, attrs={}):
        api = self._makeAPIcontext(self.__APIInfo['create'], 'POST')

        j = {}
        for k in attrs:
            j[k] = attrs[k]
        j['label'] = label
        if value:
            j['value'] = value
        v = self._simpleAPI(api, jdict=j)
        m = self.metric(v['id'])

        return m


    # ALL api exchanges with the Numerous server go through here except
    # for _getRedirect() which is a special case (hack) for photo URLs 
    #
    # Any single request/response uses this; chunked APIs use
    # the iterator classes (which in turn come back and use this repeatedly)
    #
    # The api parameter dictionary specifies:
    #
    #      'base-url' - the url we use (without the https://server.com part)
    #      'http-method' - GET vs POST vs PUT etc
    #      'success-codes' - what "OK" responses are (default 200)
    #
    # The api parameter may also carry additional info used elsewhere.
    # See, for example, how the iterators work on collections.
    #
    # Sometimes you may have started with a base-url but then been given
    # a "next" URL to use for subsequent requests. In those cases pass
    # in a url and it will take precedence over the base-url if any is present
    #
    # You can pass in a dictionary jdict which will be json-ified
    # and sent as Content-Type: application/json. Or you can pass in 
    # a multipart dictionary ... this is used for posting photos
    # You should not specify both jdict and multipart
    #
    def _simpleAPI(self, api, jdict=None, multipart=None, url=None):

        # take the base url if you didn't give us an override
        if not url:
            url = api['base-url']

        # Add the https:// etc to url if needed... you normally
        # only pass in a server-relative endpoint like "/v1/blah"
        # but sometimes url is a full URL that came back from the server
        if url[0] == '/':                  # i.e. not "http..."
            url = self.__serverURL + url
                
        if jdict and not multipart:     # BTW: passing both is undefined
            hdrs = { 'Content-Type': 'application/json' }
            data = json.dumps(jdict)
        else:
            hdrs = {}
            data = None

        hdrs['User-Agent'] = self.agentString

        httpmeth = api.get('http-method','OOOPS')

        resp = requests.request(httpmeth, url,
                                auth=self.authTuple,
                                data=data,
                                files=multipart,
                                headers=hdrs)
        if self.__debug > 9:
            print(resp.text)

        goodCodes = api.get('success-codes', [ requests.codes.ok ])

        if resp.status_code in goodCodes:
            if len(resp.text) == 0:
                # On some requests that return "nothing" the server
                # returns {} ... on others it literally returns nothing.
                # Requests library doesn't like decoding zero-len JSON
                # and throws a bizarre exception; hence this explicit 
                # "Look Before You Leap" case instead of catching exception.
                rj = {}                
            else:
                try:                   # only fails if server returns junk
                    rj = resp.json()
                except ValueError:
                    # This means we've either really screwed up somehow
                    # or (more likely? less likely?) there's a server
                    # bug. In any case, we can't decipher reply...
                    # so report that
                    rj = { 'error-type' : "JSONDecode" }
                    rj['code'] = resp.status_code
                    rj['value'] = resp.text
                    rj['reason'] = "Could not decode server json"
                    rj['id'] = url;
                    raise NumerousError(rj, rj['code'], "ValueError")
        else:
            rj = { 'error-type' : "HTTPError" }
            rj['code'] = resp.status_code
            reason = resp.raw.reason   
            rj['reason'] = reason
            rj['value'] = "Server returned an HTTP error: " + reason
            rj['id'] = url

            if resp.status_code == requests.codes.unauthorized:
                raise NumerousAuthError(rj, resp.status_code, reason)
            else:
                raise NumerousError(rj, resp.status_code, reason)

        return rj

    # This is a special case ... a bit of a hack ... to determine
    # the underlying (redirected-to) URL for metric photos. The issue
    # is that sometimes we want to get at the no-auth-required actual
    # image URL (vs the metric API endpoint for getting a photo)
    #
    # This does that by (unfortunately) getting the actual image and
    # then using the r.url feature of requests library to get at what
    # the final (actual/real) URL was.

    def _getRedirect(self, url):
        r = requests.get(url, auth=self.authTuple)
        return r.url



#
# Iterator for lazy fetch of chunked NumerousApp stuff
#  - events, streams, interactions, subscriptions, and the metrics-collection
# When needed get the first chunk from the server and if you iterate
# off the end of that chunk then we get the next
#
# the apiOP contains the starting URL as well as (very importantly)
# the generalized keys for the collection list itself and the next URL
# For example, in the stream API the collection is under key 'items'
# and the next chunk URL is 'next'. This varies for each collection type
# but this logic is generic and is reusable. So it's a bit hard to follow
# but refer to the __APIInfo data for any particular API specific keys
#
class _Numerous_ChunkedAPIIter:
    def __init__(self, nr, apiOP):
        self.nr = nr
        self.__apiOP = apiOP

        # start with an empty list... the first next() will trigger
        # the "past the end" code and fetch the "next" chunk (which
        # in the initial case is the initial chunk)
        self.__list = []
        self.__nextURL = apiOP['base-url']

        # see discussion about duplicate filtering elsewhere
        self.__dupfilter = None
        if nr._filterDuplicates:
            # only set it up for the APIs where it's needed ('dupFilter' tells us)
            if 'dupFilter' in apiOP:  # no dupFilter implies no dup filtering needed
                self.__dupfilter = { 'prev' : {}, 'current' : {} }

    def __iter__(self):
        return self
 
    # XXX although py2/py3 compatibility is "discouraged", using just this
    #     and a try/except import for httplib vs http.client I was able to
    #     backport to py2. To be clear: this is a python3 file. But now 
    #     it happens to also work in python2.
    def next(self):
        return self.__next__()



    # Get the next item - the main work is done in getNextOne and this
    # wrapper implements the duplicate filtering as needed.
    #
    # A note about duplicate filtering, _filterDuplicates, etc.
    #
    # There is a bug in the NumerousApp server which can cause collections
    # to show duplicates of certain events (or interactions/stream items).
    # Explaining the bug in great detail is beyond the scope here; suffice
    # to say it only happens for events that were recorded nearly-simultaneously
    # and happen to be getting reported right at a chunking boundary.
    #
    # The ChunkedAPIIter code filters out these bogus duplicates by default.
    # Each time it is about to return an item it checks to see if it returned
    # that same item previously (dupFilter['prev']). If it has, it skips that
    # duplicate one and gets another (and another, and another... as needed).
    #
    # Pragmatically it seems extremely unlikely that duplicates could span
    # multiple chunks. The chunk size is 100 and the most duplicates I've been
    # able to artificially manufacture with test cases is 4. The server simply
    # can't process that many "simultaneous" updates on the writing side (where
    # the condition for the duplicates appearing in the result stream gets created).
    #
    # Because event streams certainly CAN (and DO) grow to be quite large, I was
    # concerned about the overall O[] cost of this filtering. Therefore, the code
    # only keeps track of the "previous" and "current" IDs based on chunk boundaries.
    # This puts an upper bound on the cost of the algorithm for large event
    # streams - the cost tops out based on the chunk size not the total stream size.
    # As long as there are never more than 100 adjacent duplicates in a chunk
    # this works (reiterating: never seen more than 4, and server performance is
    # a pragmatic limit). There is no doubt this still slows things down but really
    # it's hard to imagine that it matters much in python applications.
    #
    # The flag for turning off duplicate filtering is really meant for testing.
    #
    # Note that not all of the APIs are susceptible to the bug so not all
    # of them contain the 'dupFilter' in their API info and thus sometimes
    # self.__dupfilter is None even if nr._filterDuplicates is True.

    def __next__(self):
        r = self.__getNextOne()

        # This "while" is misleading - it's really "if __dupfilter then while true"
        while self.__dupfilter:
            thisId = r[self.__apiOP['dupFilter']]
            if thisId not in self.__dupfilter['prev']:
                self.__dupfilter['current'][ thisId ] = 1  # only the key matters
                break
            r = self.__getNextOne()     # try the next one

        return r

    def __getNextOne(self):
        try:
            r = self.__list.pop(0)

        except AttributeError:              
            # list can be None here, happens when server returns Null for
            # the list (which in turn happens sometimes when metrics are 
            # deleted during iterating). Treated silently as end of list.
            raise StopIteration()

        except IndexError:
            apiOP = self.__apiOP

            if not self.__nextURL:          # no next url was given to us
                raise StopIteration()       # this is the normal way to end

            # It's time to get the next chunk, so it's also time to slide
            # over the duplicate filtering info (if we are filtering dups)
            if self.__dupfilter:
                self.__dupfilter['prev'] = self.__dupfilter['current']
                self.__dupfilter['current'] = {}

            # try to get the next chunk
            # It really should not fail but of course with a remote
            # server anything is possible. Failure is treated as an
            # error (i.e., exception); it is not a silent end-of-list

            try:
                v = self.nr._simpleAPI(apiOP, url=self.__nextURL)
            except NumerousError as v:
                # this is a bit hokey but if you have a totally bogus
                # metric object this might be the first place you find
                # out about it... so figure out if we're actually getting
                # the very first (base-url) fetch and if so, report the
                # more generic NumerousError that might (hopefully) make
                # more sense to you
                if self.__nextURL == apiOP['base-url']:
                    if v.code == 400:      # "Bad Request" is bad metric
                        raise NumerousError(v, v.code, "Bad Metric")
                    else:
                        raise NumerousError(v, v.code, "Getting first item(s)")
                raise NumerousChunkingError(v, v.code, "Getting next chunk")

            # each collection calls its list something different
            # so that's why the list key is a parameter from apiOP
            # since v comes from the server we use get() just in case
            self.__list = v.get(apiOP['list'], [])

            # some of the APIs call this "next" and some "nextURL"
            # so that's why the next key is a parameter from apiOP
            # NOTE that at the end of the collection the server does
            #      not include this field; that's how we know we're done
            self.__nextURL = v.get(apiOP['next'], None)

            # could STILL be nothing in list if collection started empty
            # ALSO: collection items can get deleted on the server so
            # it's possible we have a nextURL yet an empty result

            try:
                r = self.__list.pop(0)
            except (IndexError, AttributeError):
                raise StopIteration()

        return r

#
# EXCEPTIONS
#
#    NumerousError
#       - general errors
#
#    NumerousMetricConflictError
#       - you attempted an onlyIf metric write and the value was no change
#
#    NumerousChunkingError
#       - something went wrong while fetching the next chunk in
#         an iterator for a collection such as the Stream, or Interactions,
#         or similar. If for example the metric got deleted while you were
#         in an iteration you might see this
#
#    NumerousAuthError
#       - your creds are no good

class NumerousError(Exception):
    def __init__(self, v, code, reason):
        self.code = code
        self.reason = reason
        self.details = v

class NumerousMetricConflictError(NumerousError):
    pass

class NumerousChunkingError(NumerousError):
    pass

class NumerousAuthError(NumerousError):
    pass
