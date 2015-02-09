#!/usr/bin/python3

import json
import sys
import os
import argparse
import string
import time
from numerous import Numerous, numerousKey, \
                     NumerousError, NumerousAuthError, NumerousMetricConflictError


#
# usage
#  nr [ -c credspec ] [ -t limit ] [-D] [-jknNqw+ISEMPB] [-y] [ m1 [v1] ]...
#  nr [ -c credspec ] [-Dnq] -I --delete m1 interaction1 ...
#  nr [ -c credspec ] [-Dnq] -E --delete m1 event1 ...
#  nr [ -c credspec ] [-Dnq] -P --delete m1 ...
#  nr [ -c credspec ] [-Dq] --killmetric m1 ...
#  nr [ -c credspec ] [-Dqj][-U]
#  nr [ -c credspec ] [-Dqj][-UPw] photo-file
#  nr -V
#
# Perform Numerous operations on metrics
#
# A Numerous API key ("credentials") is required; you either specify it
# via -c or via the environment variable NUMEROUSAPIKEY.
#
# Using -c:
#
#   ANY OF THESE FORMS:
#       -c @filename     the creds come from the named file "filename"
#       -c /filename      ... we simply assume no NumerousAPI keys
#       -c ./filename     ... start with '@' '.' or '/'
#
#       So you only need the '@' (which gets stripped) if you are specifying
#       a relative path that does not start with . or /
#       Note too that  -c ~/.somefile works because the shell
#       expands the tilde (so there is a leading '/' by the time seen here)
#
#       The file should contain a JSON object with a key "NumerousAPIKey".
#       The APIKey comes from your numerous app - inside the app see
#       settings/developer info.
#
#       The JSON object may (obviously) contain other things but only
#       the NumerousAPIKey will be used in this script.
#
#       It is permissible, but not really recommended, to simply have
#       a "naked" APIKey by itself in place of the full JSON object.
#
#   OTHER FORMS:
#       -c @-            the creds come from stdin (JSON or naked)
#
#       -c anythingElse  the creds are anythingElse (JSON or naked)
#
# Without -c the credentials come from environment variable:
#
#      NUMEROUSAPIKEY     (exact same format options as the -c credspec)
#
# None of this is terribly secure but it is what it is
#
# If option -k/--key is given, after all this happens the NumerousAPIKey
# will be printed. This is sometimes useful in other scripts as a way
# to extract the key from "wherever". No other operations are performed.
#
# If -n is specified, the metric IDs should be names ("labels") instead
# of internal identifiers. The "metricByLabel()" method from class Numerous()
# will be used to look up the metric, with matchType=STRING (no regexp). If
# there are multiple matches that will be reported (and aborted).
#
# Alternatively -N will look the metric up as a regexp, with matchType=ONE.
# As with -n there must be exactly one match.
#
# Note that metricByLabel() can be expensive, but it is (sometimes) convenient.
#
# If -w (--write) is specified, SOMETHING will be written. That something is
# either metric value itself, or with another option:
#
#     -+ (--plus) : the metric value will be ADDED to
#        FYI: implemented atomically by the NumerousApp server
#     -E (--event) : an event is written ... equivalent to naked -w
#     -I (--interaction) : an interaction (comment/like/error) will be written
#     -P (--photo) : a photo is attached to the metric. value1 MUST
#                    be a filename. A mimeType will be inferred.
#     -M (--metric) : a metric is CREATED or UPDATED.
#        To create a metric, the name (m1) MUST begin with a '+' which
#        will be stripped ("+NewName" becomes "NewName"). The "-n" flag
#        is not required (and has no effect in this case). To update a
#        metric just specify its metric ID (no '+') or name (-n and no '+')
#
#        value1 MUST be present and should be a JSON object; it will
#        be sent as the metric data per the API. (Use '{}' for defaults).
#        Two other forms are accepted besides JSON:
#            a naked value number -- e.g. 17
#            the word "private"
#        A naked number such as 17 is equivalent to '{ "value" : 17 }'.
#        The word private is equivalent to '{ "private" : true }' (and
#        value 0 which is implied). The default for private is false. There
#        is no shorthand for specifying private AND a non-zero initial value;
#        use full on JSON for that.
#
#        When updating a metric the current fields will be read and the
#        fields you specify will be modified and written (PUT) back. Thus
#        for example, you can change just the description of a metric and
#        preserve all of its other current parameters. The underlying API
#        requires a PUT of the complete new object; this handles that for you.
#
#        Note It is an error to specify any value on a metric UPDATE.
#        You must use the regular -w method for writing to a metric value.
#
#        You can create/update multiple metrics (m2/v2 etc)
#
# Note that you still have to specify -w with -M. There's not really a
# particularly good reason for this; it's just how I did it, simply to
# preserve the rule that -w means m1/v1 pairs in the arguments while
# no -w means the arguments are all metric IDs. Naked -M
# by itself is the same as no options and means just read metrics.
#
# If -y is specified the flag "onlyIfChanged" will be set on the updates.
# This flag is an error if used on anything other than a metric value write.
# NOTE: This is NOT atomic at the server as of Oct2014 and the Numerous
#       people say they aren't sure they can ever make it so
#
# If you are writing a metric value and you format the "value" like this:
#            "EPOCHTIME: mm/dd/yy hh:mm:ss"
#             (double quotes are not part of the format; I'm merely
#              pointing out the argument must be one "word")
# then the value written to the metric will be the given date converted
# into epochtime (UNIX "seconds since 1970"). This is what you want when
# updating a "timer" type of metric.
#
# Without -w:
#      -B (--subscriptions) : subscriptions will be read.
#         * If no metric IDs are given your entire set of subscriptions
#           will be read.
#         * As a special case, -Bn and no metric IDs will simply display a list
#           of metricID and name. This is useful for finding the metric IDs of all
#           the metrics you are subscribed to (have put into your display) in the App.
#
#         * Otherwise the subscription parameters on a particular
#           metric(s) are read. NOTE: It is not currently possible to write
#           subscriptions from this command (not yet implemented)
#
#      -E (--event) : the events will be read.
#         Events are value changes.
#         You can read a SINGLE event by ID using the field notation:
#                -E 7834758745[245235235]
#         (metric ID and [eventID]) and you can use -n notation for the metricID:
#                -E metname[245235235]
#
#      -I (--interaction) : interactions will be read.
#         Interactions are everything other than value changes
#         You can read a SINGLE interaction by ID using the field notation
#
#      -S (--stream) : the stream will be read
#         The stream is events and interactions together
#
#      -P (--photo) : the URL for the photo will be displayed
#
#      -U If no other arguments given, your user info will be read
#         With arguments ("m1" values though they aren't metrics) then
#         the user info for those ID(s) will be read. Field selection works
#         or the entire thing is displayed in JSON.
#
# When writing something, the m1/v1... command line arguments
# should be metric/value pairs. They will be written (plain -w) or
# ADDed (-+) (NumerousAPI ADD action), or sent as Interactions (-I)
# (e.g., comments and such).
#
# When writing values to metrics, the value must simply be a naked number.
# When writing other types (e.g., interactions) the value can (usually should)
# be a JSON. Note that it has to be ONE shell argument so use quotes carefully.
#
# Without -w, if -S or -I is specified the Stream collection or the
# Interactions collection will be read.
#
# Without any -w/-S/-I etc options the specified metrics (m1...) will be read
#
# If you are reading something you can specify which element you want
# displayed using brackets after the ID. So, for example:
#    nr 258495834583459[label]
#
# will display the label element of metric 258495834583459 instead
# of its value. For convenience, subdictionaries will also be automatically
# indexed to whatever degree makes sense (if there is ambiguity you will get
# the "first match" however that is defined by many unknown factors). This
# use case is mostly intended for doing things like 258495834583459[web]
# to display the web URL (which itself is inside the "links" dictionary).
#
# When using the [] feature be careful of escaping/quoting/etc.
# This feature does mean that if you foolishly put a '[' in the actual label
# of your metric you can't get at that metric by name with this program.
# (You can still access it by numeric ID of course). I did not bother to
# implement any escape such as [[
#
# It is (of course) far better to use the [] feature to access a particular
# field (e.g., commentBody) of the stream and similar outputs than it is to
# pipe the "human output" to awk '{print $2}' or similar hacks.
#
# Finally, with no operations and no metric IDs (m1 etc) at all, a list
# of metric IDs is read from the server and printed out
#
# If -j is specified, output will be JSON. Else bare. Note that field
# selection doesn't happen on JSON output -- you always get the whole thing.
#
# If "-t limit" is specified, reads on collections will stop at limit
#
# If -D (--debug) is specified, debugging (HTTP in particular) output is on
#
# If -V is specified, a version string is printed (and nothing else is done)
#
# If -q is specified, no "normal" output is generated. Some error cases
# or unhandled exceptions might still cause output, but no server interaction
# that "works" (which includes the server returning a "normal" error) will
# generate output. You *can* specify quiet even where it sort of makes no
# sense (e.g., reading a variable and quiet), perhaps you just want to
# test the exit code (so we allow that combination).
#
# Interactions (comments/likes/errors), photos, and events (value updates) can
# be deleted using the --delete form. There is no "short option"
# (single letter) flavor of --delete on purpose. Specify -I to delete
# an interaction or -E to delete an event, and give the metric ID and item ID
# There is no "val" for --delete --P
#
# Lastly, the metric itself can be deleted but to avoid mistakes with --delete
# causing misery this is done with --killmetric. The syntax is:
#
#       nr --killmetric m1 [ m2... ]
#
# and ONLY the flags -D (debug) and/or -q (quiet) are valid. In particular
# you CANNOT kill a metric by name, you must first look up its numeric Id.
#
# Examples:
#
#   WRITE 17 to MyVar and 42 to MyOtherVar:
#       nr -w -n MyVar 17 MyOtherVar 42
#
#       Credentials come from the environment.
#       There will be at least one extra API call to translate the
#       variable names into IDs (there could be multiple calls if the
#       user has enough variables to make the server segment the replies)
#
#   SAME, using a credentials file:
#       nr -c ~/.ncred -w -n MyVar 17 MyOtherVar 42
#
#   ADD 1 to a given metric:
#       nr -w+ 3662358291300702287 1
#
#   COMMENT: writes the comment "bozo the clown" to XYZ.
#       nr -wI -n XYZ '{ "kind": "comment", "commentBody": "bozo the clown" }'
#
#   COMMENT: simple case
#       nr -wI -n XYZ 'bozo the clown'
#
#       as a special case hack a "naked" interaction (not a JSON)
#       will be taken as a comment. So this is identical to previous example.
#
# You can use -I to send any valid type of interaction. So, for example:
#
#   ERROR:
#       nr -wI 53349538495834 '{ "kind": "error", "commentBody": "error stuff" }'
#       (note that numerous uses commentBody for error details too)
#
#   LIKE:
#       nr -wI 53349538495834 '{ "kind": "like" }'
#
#   CREATE: create a metric
#       nr -wM +NewM1 '{}' +NewM2 '{ "value" : 17, "private" : true }'
#
#       creates NewM1 with default values and NewM2 with initial
#       value 17 and private (the API default for private is false)
#       Outputs the ID of the created metric (or -1 if error)
#
#   UPDATE: set a metric's description
#       nr -wM -n XYZ '{ "description": "i am a little teapot" }'
#
#   DISPLAY INTERACTIONS:
#       nr -Ij -n MyVar
#
#       Display the interactions collection in JSON
#
#   DISPLAY the 100 most recent Stream items:
#       nr -S -t 100 -n MyVar
#
#   USING FIELDS: Translate SomeName into its metric id:
#       nr -n 'SomeName[id]'
#
#       will display the numeric metric ID for SomeName
#
#   GETTING THE WEB ADDRESS OF A METRIC
#       nr '34552988823401[web]'
#
#       would display the web URL of the given metric. Note that this
#       uses the "find any key match anywhere" feature because the
#       field called "web" is actually in a subdictionary of the "links"
#
#   USING FIELDS WITH EVENTS
#       nr -E --limit 1 'SomeName[value]'
#
#       is a silly way to get at the current value of SomeName using the
#       fields feature and the limit feature.
#
#   DELETE AN EVENT (id 23420983483332)
#       nr --delete -E 34552988823401 23420983483332
#

parser = argparse.ArgumentParser()
parser.add_argument('-V', '--version', action="store_true")
parser.add_argument('-c', '--credspec')
parser.add_argument('-j', '--json', action="store_true")
parser.add_argument('-n', '--name', action="store_true")
parser.add_argument('-N', '--regexp', action="store_true")
parser.add_argument('-q', '--quiet', action="store_true")
parser.add_argument('-w', '--write', action="store_true")
parser.add_argument('-t', '--limit', type=int, default=-1)
parser.add_argument('-D', '--debug', action="count")
parser.add_argument('--delete', action="store_true")
parser.add_argument('-U', '--user', action="store_true")
parser.add_argument('--statistics', action="store_true")  # info/debugging support
wgx = parser.add_mutually_exclusive_group()
wgx.add_argument('-+', '--plus', action="store_true")
wgx.add_argument('-E', '--event', action="store_true")
wgx.add_argument('-B', '--subscriptions', dest="subs", action="store_true")
wgx.add_argument('-I', '--interaction', action="store_true")
wgx.add_argument('-S', '--stream', action="store_true")
wgx.add_argument('-M', '--metric', action="store_true")
wgx.add_argument('-P', '--photo', action="store_true")
wgx.add_argument('-y', '--onlyIf', action="store_true")
wgx.add_argument('-k', '--key', action="store_true")
wgx.add_argument('--killmetric', action="store_true")
parser.add_argument('keyvals', nargs='*', metavar='key [value]')

args = parser.parse_args()

#
# clean up / sanitize some of the argument semantics
#

if args.version:
    print(Numerous(None).agentString)
    exit(1)


# regexp implies name
if args.regexp:
    args.name = True


# --delete is exclusive with MUCH of the 'wgx' exclusive
# group but not all
#   ... so couldn't use built-in exclusion features
#   ... could have just ignored, but it seems best to make sure that what
#       you specified makes total sense (especially before deleting something)
#
# and it requires either --event or --interaction or --photo
#
if args.delete:
    nope = { "write", "plus", "stream", "metric", "onlyIf", "user",
             "key", "subs", "killmetric" }
    argsDict = vars(args)
    bad = False
    for x in nope:
        if argsDict.get(x):
            print("Can't have --delete and --" + x)
            bad = True
    if bad:
        exit(1)

    if not (args.event or args.interaction or args.photo):
        print("--delete requires -E/--event, -I/--interaction, or -P/--photo")
        exit(1)


# --user has similar (but not quite the same) exclusion rules
if args.user:
    nope = { "plus", "stream", "metric", "onlyIf", "event", "interaction",
             "key", "subs", "killmetric", "name" }
    argsDict = vars(args)
    bad = False
    for x in nope:
        if argsDict.get(x):
            print("Can't have --user and --" + x)
            bad = True
    if bad:
        exit(1)

    if args.write and not args.photo:
        print("--write requires -P/--photo")
        print("(no other form of user update is implemented yet)")
        exit(1)



#
# we do not allow you to kill a metric by name. It's just too error prone
#
if args.killmetric and args.name:
    print("--killmetric ONLY works by metricId, not by name. No -n allowed.")
    exit(1)


#
# As a shortcut we allow naked -+ to mean -w+
#
if args.plus:
    args.write = True

#
# limit of -1 means infinite and I think it's cleaner to use None in code
#
if args.limit == -1:
    args.limit = None

#
# writing a user photo is a special case -- exactly one argument
#
if args.write and args.user and args.photo and len(args.keyvals) != 1:
    print("User photo update requires exactly one file name argument")
    exit(1)

if args.write and (len(args.keyvals) % 2) != 0 and not args.user:
    print("Write/update specified but arg list is not metric/value pairs")
    exit(1)

if args.write and len(args.keyvals) == 0:
    print("Write/update specified but no metric/value pairs given")
    exit(1)

#
# -y only makes sense if writing/adding
#
if args.onlyIf and not args.write:
    print("-y/--onlyIf only valid when writing a metric with -w (--write)")
    exit(1)

#
# Can't have any subfields if writing or deleting
#
if args.write or args.delete:
    for m in args.keyvals[0::2]:
        if '[' in m:
            print("Can only have subfields for reading:", m)
            exit(1)



# this convenience function implements the "it can come from almost anywhere" thing
k = numerousKey(args.credspec)

if args.key:
  # this is a hack way to just extract the API key from "wherever"
  # honestly it probably should be a separate program but here we are
  if k:
      print(k)
      exit(0)
  else:
      print("No API Key")
      exit(1)


nrServer = Numerous(apiKey=k)

if args.debug:
    if args.debug > 1:
        nrServer.debug(10)    # lol, but 10 turns on extra debug
    else:
        nrServer.debug(1)     # standard debug level

# test connectivity ... mostly to verify creds
try:
    nrServer.ping()
except NumerousAuthError:
    print("Authorization failed. Likely cause is bad credentials (API key)")
    exit(1)

#
# This function takes a string that *MIGHT* be a numeric value and
# converts it to a number, or just returns it. This is used for two reasons:
#
#   1) The Numerous server insists (quite reasonably so) that numeric values
#      come across as JSON numbers (17), not as strings ("17"). It turns out
#      the server only enforces that on some APIs and not others; but
#      we choose to be conservative in what we send regardless.
#
#   2) Implement syntax for certain special circumstances. Right now the
#      only special syntax is "EPOCHTIME: mm/dd/yy hh:mm:ss" which will
#      be converted into a UNIX epochtime (useful for "timer" metrics)
#

def valueParser(s):
    r = s                # default result is just the source

    # is it just a naked integer?
    try:
        r = int(s)
        return r
    except ValueError:
        pass

    # is it just a naked float?
    try:
        r = float(s)
        return r
    except ValueError:
        pass


    # is it the EPOCHTIME: syntax?
    EpochTimeSyntax = "EPOCHTIME: "
    if s.startswith(EpochTimeSyntax):
        sx = s[len(EpochTimeSyntax):]    # the rest of s

        # these are all the formats we'll try for converting a date stamp
        # personally I don't recommend you use the ones omitting the full
        # time but it's up to you
        dateformats = [
             "%m/%d/%Y %H:%M:%S",          # four digit year
             "%m/%d/%y %H:%M:%S",          # two digit year
             "%m/%d/%Y %H:%M",             # seconds omitted (yyyy)
             "%m/%d/%y %H:%M",             # (yy)
             "%m/%d/%Y",                   # time completely omitted (yyyy)
             "%m/%d/%y"
        ]

        # try first mm/dd/yyyy then mm/dd/yy .. could add more formats too
        for fmt in dateformats:
            try:
                r = float(time.strftime("%s", time.strptime(sx, fmt)))
                return r
            except:
                pass

        # but if we get all the way to here we know the value
        # started with the EpochTimeSyntax but did not parse.
        # throw an exception because of that.
        raise ValueError

    # fell through all the syntax possibilities so just return original
    return r



#
# FIELD notation is overloaded to either be an actual field
#       name (e.g., 'label', 'authorId', etc) or sometimes it
#       is a raw event or interaction ID and we need to know difference
# Arguably, this is a silly hack and we should have made more explicit
# command-line argument syntax to distinguish the two. But we're on a roll.
#
def isEventOrInteractionId(s):
    return s.isdigit()

#
# support function for the metric[field] concept
# Given a dictionary (usually a Numerous result) and a field name that
# is (supposedly) either in that dictionary OR in a subdictionary,
# return the field
#
def findSomethingSomewhere(d, f):
    # this could be duck typed but we do check for dict explicitly
    # otherwise the expression d[k] risks indexing a string element or
    # other iterable that isn't a dictionary. The whole thing is a bit
    # hokey but it is a damn convenient feature to be able to say
    #      MetricID[web]
    # to get at MetricID[links][web]
    #
    # Keep in mind this is all just a command line shell utility
    # so convenience trumps some other considerations
    if type(d) is not dict:
        return None
    elif f in d:
        return (d[f])
    else:
        for k in d:
            subdict = d[k]
            x = findSomethingSomewhere(subdict, f)
            if x:
                return x

    return None

#
# Get all (or up to limit) of a user's metrics
#
def getMetrics(nr, limit=None):
    n = 0
    metrics = []

    for m in nr.metrics():
        if limit and n == limit:
            break

        metrics.append(m)
        n = n + 1

    return metrics


def printStreamResults(items, fld):
    if type(items) == str:
        print(items)             # these are error messages
    else:
        for i in items:
            if fld and not isEventOrInteractionId(fld):
                print(i.get(fld,None))
            else:
                c = i.get('commentBody', None)
                a = i.get('authorId', None)
                v = i.get('value', None)
                sID = i.get('id', '??? NO ID ???')
                print(i['kind'], sID, v, i['updated'], a, "--", c)

def printEventResults(r, fld):
    if type(r) == str:
        print(r)                 # these are error messages
    else:
        for i in r:
            if fld and not isEventOrInteractionId(fld):
                print(i.get(fld,None))
            else:
                # the initial value when a metric is created 
                # does not have an authorId (is this a server bug?)
                # so we need to be careful...
                a = i.get('authorId', 'INITIAL-CREATION-VALUE')
                print(i['value'],"@",i['updated'],"by",a)

def printDeleteResults(r):
    print("%s[%s] -- %s" %(r['ID'], r['delID'], r['result']))



def getIterableStuff(m, i, limit):
    n = 0
    list = []
    for x in i:
        if limit and n == limit:
            break
        n = n + 1
        list.append(x)

    return list


# write an image file to either a metric or to the user record
def doPhotoWrite(metricOrNR, imageFName):
    try:
        f = open(imageFName, "rb")
    except IOError:
        return "cannot open: " + imageFName

    imageBytes = f.read()
    f.close()

    mimeGuess = [ ( '.jpg', 'image/jpeg' ),
                  ( '.jpeg', 'image/jpeg' ),
                  ( 'gif', 'image/gif' ),
                  ( 'png', 'image/png' ) ]


    mType = None
    for m in mimeGuess:
        if imageFName.endswith(m[0]):
            mType = m[1]
            break

    if not mType:
        mType = 'image/jpeg'    # hope for the best

    if isinstance(metricOrNR, Numerous):
        return metricOrNR.userPhoto(imageBytes, mType)
    else:
        return metricOrNR.photo(imageBytes, mType)







# XXX it is important that these keys cannot appear in a base36 encoding
#     Wow that was an obscure bug, when this was used with this mspec:
#               http://n.numerousapp.com/m/1bzm892hvg4id
#     that happened to include 'id' (the previous key used here)
#     and that false-positived an "if 'id' in mspec" test
#
# The whole way all this works is a hack that obviously grew over time :)
#
mspecIDKey = '_*id*_'
mspecFIELDKey = '_*field*_'

#
# Sometimes it is m1/v1 pairs sometimes just metrics
#
if args.write or (args.delete and not args.photo):
    metrics = args.keyvals[0::2]
    values = args.keyvals[1::2]

else:
    metrics = []
    for m in args.keyvals:
        if '[' in m and not args.killmetric:
            x = m.split('[')
            # very rudimentary syntax checks
            if len(x) != 2 or not x[1].endswith(']'):
                print("bad metric specification",m)
                exit(1)
            # nuke the trailing ']' on the field spec
            m = { mspecIDKey : x[0], mspecFIELDKey : x[1][:-1] }
        metrics.append(m)


#
# If we're doing this by name, translate the IDs first
#

resultList = []
exitStatus = 0

#
# If no keys in the argument list then:
#    If doing subscriptions, get the top-level subscriptions list
#    Otherwise get the list of all keys
#
# Otherwise read or write the values. In either case accumulate
# the resultList for subsequent output
#

if len(metrics) == 0:
    if args.subs:
        for s in nrServer.subscriptions():
            # this is a hack but if you specify -n we just display
            # the metric ID and the name this way
            if not args.quiet:               # quiet is dumb, but whatever
                if args.name:
                    id = s['metricId']
                    print("{} {}".format(id, nrServer.metric(id).label()))
                else:
                    print(s)
                    print(" ")
    elif args.user:
        u = nrServer.user()
        if not args.quiet:
            if args.json:
                print(json.dumps(u))
            else:
                print("User: {userName} [ {fullName} ], id: {id}".format(**u))

    else:
        vlist = getMetrics(nrServer, args.limit)

        # arguably "quiet" is dumb, but it does test connectivity
        if not args.quiet:
            for v in vlist:
                if args.json:
                    print(json.dumps(v))
                elif args.name:
                    print(v['id'] + " " + v['label'])
                else:
                    print(v['id'])

elif args.user and args.write and args.photo:
    v = doPhotoWrite(nrServer, args.keyvals[0])
    print (v)

else:
    while len(metrics):
        mspec = metrics.pop(0)
        if mspecIDKey in mspec:
            r = { 'ID' : mspec[mspecIDKey], 'FIELD' : mspec[mspecFIELDKey] }
        else:
            r = { 'ID' : mspec }

        # if we are creating a new metric, don't make a NumerousMetric from ID
        creatingNew = (args.write and args.metric and r['ID'][0] == '+')
        invalidMetric = False
        if creatingNew:
            r['ID'] = r['ID'][1:]     # strip the plus
            metric = None
        else:
            metric = None
            if args.name:
                if args.regexp:
                    mtype = 'ONE'
                else:
                    mtype = 'STRING'

                s = r['ID']
                try:
                    metric = nrServer.metricByLabel(s, matchType=mtype)
                except NumerousMetricConflictError as e:
                    print("More than one match: ", e.details)
                    metric = None
            if not metric:
                metric = nrServer.metric(r['ID'])
            
            # this helps humans figure out they have screwed up
            # if we were doing name translation see if the metric translated
            # Only do this when args.name because it's extra overhead so we
            # don't do it when you look more likely to be a script (because
            # you used the lower level metric ID directly)
            if args.name and not metric.validate():
                invalidMetric = True

        if invalidMetric:
            r['result'] = "ERROR / Invalid Metric: " + r['ID']
            exitStatus = 1
        elif args.delete:
            if args.photo:
                delWhat = None
                r['delID'] = "photo"
            else:
                delWhat = values.pop(0)
                r['delID'] = delWhat
            try:
                if args.event:
                    metric.eventDelete(delWhat)
                elif args.interaction:
                    metric.interactionDelete(delWhat)
                elif args.photo:
                    metric.photoDelete()
                else:                  # never happens
                    raise ValueError   # should not happen
                r['result'] = "DELETED"
            except NumerousError as v:
                exitStatus = 1
                r['result'] = "ERROR / Not Found"

        elif args.write and args.photo:
            # the matching value given is (should be) a file name
            r['result'] = doPhotoWrite(metric, values.pop(0))

        elif args.write:
            val = values.pop(0)

            # sometimes val is a JSON and sometimes it is naked
            # to simplify the rest of this turn it into something
            # that is ALWAYS a dictionary, but if it was naked we
            # put the "val" in as '__naked__' key
            try:
                jval = json.loads(val)
                # this test serves two purposes: see if it is dict-like,
                # and protect our __naked__ hack
                if '__naked__' in jval:
                    # seriously, you are a twit...
                    print("Invalid Numerous JSON given: ", val)
                    exit(1)
            except (TypeError, ValueError):
                # it was naked, or malformed.
                try:
                    jval = { '__naked__' : valueParser(val) }
                except ValueError:     # e.g., "EPOCHTIME: " bad format
                    jval = { '__naked__' : val }  # this will get dealt with below

            if args.interaction:
                # interactions are comments/likes/errors
                # if you specify a naked string it's a comment
                # you specify the other forms (or comments if you like)
                # as a JSON. Figure out what's going on ... then do it

                if '__naked__' in jval:
                    j = { 'kind': "comment", 'commentBody' : val }
                else:
                    j = jval

                if j['kind'] == "comment":
                    metric.comment(j['commentBody'])
                elif j['kind'] == "error":
                    metric.sendError(j['commentBody'])
                elif j['kind'] == "like":
                    metric.like()
                r['result'] = "OK"

            elif args.metric and not creatingNew:
                # this is the metric update case (but not create)
                # NOTE: This is for metric attributes (description etc)
                #       you cannot update the value parameter this way
                #       (server will ignore any 'value' in the json)
                # We don't implement any naked shortcut; val MUST be JSON
                if '__naked__' in jval:
                    r['result'] = "Update requires JSON for paramters"
                    exitStatus = 1
                else:
                    r['result'] = metric.update(jval)

            elif creatingNew:
                # if you specified it naked, it's just the value or "private"
                if '__naked__' in jval:
                    vp = jval.pop('__naked__')
                    if vp == "private":
                        jval['private'] = True
                        jval['value'] = 0    # this is implied by API anyway
                    else:
                        jval['value'] = vp

                metric = nrServer.createMetric(r['ID'], attrs=jval)
                if args.json:
                    r['result'] = metric.read(dictionary=True)
                else:
                    r['result'] = metric.id

            else:
                # we are writing a metric value
                try:
                    val = valueParser(val)
                    try:
                        r['result'] = metric.write(val,
                                                   onlyIf = args.onlyIf,
                                                   add = args.plus,
                                                   dictionary = args.json)
                    except NumerousMetricConflictError as e:
                        exitStatus = 1
                        if args.json:
                            r['result'] = { 'errorCode' : e.code,
                                            'errorDetails' : e.details,
                                            'errorReason' : e.reason }
                        else:
                            r['result'] = "NoChange"

                except ValueError:
                    exitStatus = 1
                    r['result'] = "Bad value syntax: '{}'".format(val)


        elif args.killmetric:
            try:
                metric.crushKillDestroy()
                r['result'] = "Deleted"
            except NumerousError as e:
                r['result'] = "FAILED " + e.reason

        elif args.interaction:
            if 'FIELD' in r and isEventOrInteractionId(r['FIELD']):
                r['result'] = [ metric.interaction(r['FIELD']) ]
            else:
                iterable = metric.interactions()
                r['result'] = getIterableStuff(metric, iterable, args.limit)

        elif args.stream:
            # no support for reading a single stream item
            # (read a single item using the interaction/event interfaces)
            iterable = metric.stream()
            r['result'] = getIterableStuff(metric, iterable, args.limit)

        elif args.event:
            if 'FIELD' in r and isEventOrInteractionId(r['FIELD']):
                r['result'] = [ metric.event(r['FIELD']) ]
            else:
                iterable = metric.events()
                r['result'] = getIterableStuff(metric, iterable, args.limit)

        elif args.photo:
            r['result'] = metric.photoURL()

        elif args.user:
            u = nrServer.user(r['ID'])
            if 'FIELD' in r:
                r['result'] = u[r['FIELD']]
            else:
                r['result'] = u

        elif args.subs:
            try:
                # metricID[+] means get all the subscriptions for the metric
                if mspecFIELDKey in mspec and mspec[mspecFIELDKey] == '+':
                    slist = []
                    for s in metric.subscriptions():
                        slist.append(s)
                    r['result'] = slist
                else:
                    d = metric.subscription()
                    if args.json:
                        r['result'] = d
                    elif mspecFIELDKey in mspec:
                        r['result'] = findSomethingSomewhere(d, mspec[mspecFIELDKey])
                    else:
                        r['result'] = d
            except NumerousError:
                exitStatus = 1
                r['result'] = None

        else:
            try:
                # always read the full dictionary... and use the entire
                # result if args.json, otherwise use any field value given or
                # in the simple case just the value
                d = metric.read(dictionary = True)
                if args.json:
                    r['result'] = d
                elif mspecFIELDKey in mspec:
                    r['result'] = findSomethingSomewhere(d, mspec[mspecFIELDKey])
                else:
                    r['result'] = d['value']
            except NumerousError:
                exitStatus = 1
                r['result'] = None

        resultList.append(r)


    #
    # display results accordingly
    #
    if not args.quiet:
        if args.json:
            j = { 'Results' : resultList }
            print(json.dumps(j))
        else:
            for r in resultList:
                rslt = r['result']
                fld = r.get('FIELD',None)
                if args.delete:
                    printDeleteResults(r)
                elif args.write:
                    print(rslt)
                elif args.interaction or args.stream:
                    printStreamResults(rslt, fld)
                elif args.event:
                    printEventResults(rslt, fld)
                else:
                    print(rslt)       # likely python dict output (use -j for JSON)



if args.statistics:
    print("Statistics:")
    for k in nrServer.statistics:
        print("{:>24s}: {}".format(k, nrServer.statistics[k]))

exit(exitStatus)
