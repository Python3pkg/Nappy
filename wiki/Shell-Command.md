# nr - the shell command
This command provides shell-level access to almost the entire NumerousApp API. Accordingly it has a huge and overwhelming set of options; however, the basics are fairly straightforward. You can read and write metrics very simply with syntax like this:

    % nr 4961219002925215768
    17

which is reading the value of a metric given by an ID (e.g., 4961219002925215768 in this case), and:

    % nr -w 4961219002925215768 99
    99

shows how to write it. These two commands will suffice to integrate almost any application with NumerousApp at the shell level. Many more powerful operations are also possible with this command.

## Installation
The file shell-cmd/nr is a simple wrapper and might not even be needed at all depending on how you installed everything. Its sets PYTHONPATH to the appropriate directory and then invokes nr.py; if you installed the numerous library (numerous.py) using pip (or pip3) so that it is in your system library path then you can delete the "nr" file and rename "nr.py" to "nr" and just use that directly.

If you installed the numerous.py file into your own personal directory tree somewhere (e.g., ~/lib/numerous.py) then you will want to keep the shell wrapper and edit it accordingly. This is all somewhat self-explanatory if you look at the files.

## Using nr

### Credentials - your API Key
You need a NumerousApp API key to use nr. The best practice is to put that key into a file somewhere and then specify it to nr via the -c option. Something like this:

    % echo "nmrs_3Z82bdf934g1" > ~/.numerousCred      # do this one time
    % nr -c ~/.numerousCred                           # and pass it in like this

See [APIKey Management](https://github.com/outofmbufs/Nappy/wiki/APIKey-Management) for all the other ways you can specify an API Key.

You can go one step further and set the NUMEROUSAPIKEY environment variable to be that file name so you don't even have to give the -c option, so for example:

    % NUMEROUSAPIKEY=~/.numerousCred export NUMEROUSAPIKEY  # do this once
    % nr            

The examples throughout the rest of this document will omit the "-c ~/.numerousCred" argument and assume that you either set NUMEROUSAPIKEY or will specify the -c yourself.

### Metrics by name vs metrics by ID
The underlying NumerousApp API always accesses metrics by a unique identifier which usually looks like a long string of digits. These numeric IDs are the true identifiers of a given NumerousApp metric. Of course humans think of the "name" (which is really called a `label` in Numerous) as being the identifier of a metric. However, labels have many problems. Nothing stops you from making three metrics all with the same label. They would each have a different numeric ID but they would be impossible to tell apart from just the label. 

Despite the problems with labels, they are convenient. The nr command allows you to access metrics by name (label) using the -n option. Thus, to read a metric called 'bozo' you can do this:

    % nr -n bozo
    17

The `-n` option requires that the label match exactly. It uses the `metricByLabel` option `'STRING'` and it will report an error if there is more than one matching metric. Thus if you make more than one metric with a label of `bozo` (you can do this with your phone, for example) and then try to access them with an `nr -n` command:

    % nr -n bozo         # assume we have two metrics with label 'bozo'

you would see something like this:

    More than one match:  ('bozo', 'bozo')
    ERROR / Invalid Metric: bozo

If you have a very long label and don't want to have to type the whole thing, the nr command will do regular expression matching for you if you use the `-N` (capital N) option. In this case the string you give will be treated as an unanchored regular expression and the nr command will attempt to match it against all of the metrics that you are subscribed to.

So, for example, if you are subscribed to a metric "Austin Plaza Lofts Packet Drop" you could try this:

    % nr -N "Plaza"
    .008

and get the current reading of that metric, assuming that only one metric matched. The `-N` (capital n) option uses the `metricByLabel` option `'ONE'` so in this case the supplied label name is treated as an _unanchored_ regexp. Note that this means it matches if the supplied argument appears anywhere in any label. Thus:

    % nr -N e

will match any label of any metric of yours that happens to have the letter 'e' in it (and will most likely fail with a duplicate-match error of course). You can use the full set of regular expression constructs; the most useful are probably ".*" to match any characters, "^" to match the beginning and "$" to match the end. Thus:

    % nr -N "^A.*p$"
    .008

would likely also match "Austin Plaza Lofts Packet Drop" as shown.

If you are writing scripts it is strongly recommended that you use numeric IDs to access your metrics. As a convenient way to get a translation of metric names (labels) into IDs, specifying -n by itself will list all of your metrics and their corresponding labels:

    % nr -n
    579875221157343692 bozo
    2141579335528632068 A Random Number
    9208972516053673667 Crude Oil

For convenience/completeness "nr -N" does the exact same thing (it does not matter whether you specify lower case n or upper case N if there are no other arguments).

### Reading a metric
Simply specify the metric ID or use -n and specify a label:

    % nr -n bozo
    17

or

    % nr 579875221157343692
    17

Note that the -n command is a global option. If you are reading three metrics by name:

    % nr -n bozo 'A Random Number' 'Crude Oil'
    17
    19
    46.53

It turns out that `-n` will simply pass your "name" (label) to the NumerousApp server unchanged if it cannot translate it, so you can (sort of) combine names (labels) and IDs in one command:

    % nr -n bozo 579875221157343692
    17
    17

However this is somewhat susceptible to confusion if you (foolishly) define a metric with a label that matches some other metric's ID. So don't do both of those things (i.e., either don't define metric labels that match some other metric's ID, or don't mix/match labels and IDs while using `-n`). 

The "nr" command allows you to display a specific attribute when you read a metric so another way to translate a name (label) into an ID is:

    % nr -n 'bozo[id]'
    579875221157343692

The square brackets characters are shell metacharacters so you will usually want to quote them just to be safe. However it turns out you can almost always get away with using them naked. Proceed naked at your own risk:

    % nr -n bozo[id]
    579875221157343692

    % nr -n A Random Number[id]
    ERROR / Invalid Metric: A
    ERROR / Invalid Metric: Random
    ERROR / Invalid Metric: Number

which shows the wisdom of being in the habit of using quotes:

    % nr -n 'A Random Number[id]'
    2141579335528632068

If your metric uses square brackets in its label you are out of luck. There is no escape mechanism for preventing the "nr" command from interpreting the square bracket notation as a field reference. Use the numeric ID to access such a metric, or try games with "-N" and regular expressions.

The square bracket feature is especially useful to find the web URL of a metric:

    % nr -n 'A Random Number[web]'
    http://n.numerousapp.com/m/g9quiku9vuv8

Note that in this case the `nr` command will sub-index multiple levels for you (the 'web' attribute is really contained within a 'links' attribute and the `nr` command does not accept '[links][web]' as a syntax; rather, it just takes whatever you give in square brackets and tries to "find something somewhere" that matches it -- in practice this always does what you want but if you are concerned you are free to write python code instead).

### Display JSON
Instead of just printing the value (by default) or a specific attribute specified with square brackets, you can print the entire attribute dictionary:

    % nr -n -j bozo
    {"Results": [{"result": {"id": "579875221157343692", 
                  "unit": "", "value": 99, ... }]}

For clarity the full results have been elided; try it yourself to see everything that is in there.

You can see that the results are packaged into a few layers. That allows for the case where you've asked for multiple metrics, e.g.:

    % nr -n -j bozo 'A Random Number'

in which case the top level list structure under "Results" will have two entries, and each entry will have a "result" (the actual result from the server) and an "ID" (the identifier that was used to obtain that result). Here is a (partially elided) pretty-print of the output of that command:
```
{
    "Results": [
        {
            "ID": "579875221157343692", 
            "result": {
                "description": "is a clown", 
                "id": "579875221157343692", 
                "label": "bozo", 
                "updated": "2015-01-12T14:39:13.952Z", 
                "value": 99, 
            }
        }, 
        {
            "ID": "2141579335528632068", 
            "result": {
                "description": "Random number 0 .. 99", 
                "id": "2141579335528632068", 
                "label": "A Random Number", 
                "updated": "2015-01-06T11:27:05.554Z", 
                "value": 85, 
            }
        }
    ]
}
```
As mentioned, for brevity the complete list of attributes has not been shown above; the actual command output includes all attributes for the given metrics.

Each element of the Results array is a two-element dictionary, containing an "ID" (that was used to request the information) and a "result" (that came back from the server). 

The `-j` (or `--json`) option requests that the output be in JSON format. This generally works as a modification of almost any output request. For example to see your entire set of metrics in JSON form (one JSON object per line per metric):

    % nr -j

### Writing a value to a metric
Simple:

    % nr -w 579875221157343692 42
    42

or, if you prefer to use the label:

    % nr -w -n bozo 43
    43

The new value of the metric is output. While this is obvious in the simple case, it becomes more useful in the "add" case. The NumerousApp API includes a feature that allows you to add a value to a metric. This is expressed via the '+' (or `--plus`) option in nr:

    % nr -w -n bozo 0        # start at zero
    0
    % nr -w -n -+ bozo 1     # add one
    1
    % nr -w -n -+ bozo 1     # add one again
    2

By the way, per the usual command syntax standards, you can combine all those options together:

    % nr -wn+ bozo 1
    3

As a shorthand you can omit the -w when you are using -+, as it is implied:

    % nr -n+ bozo 1
    4

The other option on the write command is "only if it changed". The advantage (in some cases) of using this variation is that you avoid cluttering up the metric's event collection with a bunch of updates that didn't change the value.

For example, perhaps you are updating a stockquote every 15 minutes. But sometimes the markets are closed. Even if you write your automatic update code to avoid running on Saturday/Sunday and at night, sometimes the markets are closed on Mondays. Rather than clutter up the metric event collection with many events that represent no change at all you can specify "only update the metric if the value is changed". This is specified with the `-y` / `--onlyIf` option:

    % nr -nwy bozo 0
    0
    % nr -nwy bozo 0
    NoChange

Note that the exit status will be 1 in the NoChange case.

### Writing Multiple Metrics
You can write multiple metrics in one command:

    % nr -wn bozo 1 bonzo 2
    1
    2

or even write the same metric twice. This, for example, is a test of the `-y` option:

    % nr -wn bozo 0
    0
    % nr -wny bozo 1 bozo 1
    1
    NoChange

### Writing Unix Epoch Times
If your metric is a timer you can write a date/time to it using this syntax:

    % nr -wn someTimer "EPOCHTIME: 02/23/2015 15:23:31"
    1424726611.0

The syntax is the string "EPOCHTIME: " followed by `mm/dd/yyyy hh:mm:ss` which will be converted into a seconds-since-time-zero Unix timestamp as required by the Numerous server. You can use this syntax to write any metric whether it is a timer or not; the date is converted into a floating point number as shown.

### Updating metric attributes
To update the attributes of a metric use the -M option combined with -w. In general every `nr` operation that writes something requires the `-w` flag, so think of the `-M` flag in this case as specifying "what to write" while the `-w` flag is simply specifying that we are going to write _something_.

    % nr -wMn bozo '{ "description" : "has red hair" }'
    { ... json output of updated metric attributes }

You specify what to update as a JSON object with the attributes that you want to update. The command uses the `NumerousMetric.update` method which takes your attributes and merges them with the rest of the metric's attributes (by reading them from the server first). There is no syntax in the nr command for overriding the "read - merge - write" behavior (which can be overridden in the method call; there's just no syntax implemented for specifying that in this command).

Note that you cannot update the metric value this way (enforced by the NumerousApp server).

    % nr -wMn bozo '{ "value" : 62 }'

appears to work (does not return an error) but you will notice that the value is not updated. The NumerousApp server silently ignores the "value" attribute in update operations.

### Creating a Metric
Creating a metric is treated in `nr` as a variation on updating a metric. To create a metric put a '+' (plus sign) character in front of the new metric name:

    % nr -wM +bozo2 '{ "value" : 819, "private" : true }'
    968229978347882872

The '+' character is stripped off and is not part of the metric name. Obviously you cannot create a new metric by specifying an ID, so the "-n" is not required in this case (it is optional / ignored).

If you are in fact a bozo you can do things like this:

    % nr -wM ++ '{ "description" : "The label of this metric is +" }'

and then for grins

    % nr -wn -+ + +1

which won't confuse anyone except for you.

As a convenient shorthand, instead of specifying a full-on JSON set of attributes you may specify either ONE of these:

* private - Creates the metric as an unlisted (i.e., _private_) metric. The default is listed (not private). Exactly the same as if you had specified `'{ "private" : true }'`
* 2342 - (any float/integer value) - Creates the metric with the given initial value. The default is zero. Exactly the same as if you had specified `'{ "value" : 2342 }'`

So, for example:

    % nr -wM +newMetric private
    6296105586510559349

    % nr -wM +newMetric 2342
    822646564275439228

It is not possible to specify an initial value and `private` at the same time using these shorthands; you must give a JSON attribute dictionary in that case.

Please note well that `private` is setting the attribute "private" to true for you. If you are trying to use fine-grained permissions you must set the attribute "visibility" to "private", which is an entirely different thing altogether. Here is how you would set up a brand new metric `ptest` for use with fine-grained permissions:

    % nr -wM +ptest '{ "visibility" : "private" }'

You could, of course, initialize other parameters in that command as well, e.g.:

    % nr -wM +ptest '{ "visibility" : "private", "description" : "perms test" }'

You can create any type of metric but you will have to use the JSON attributes format. So, for example, you can create a timer metric this way:

    % nr -wM +newTimer '{ "kind":"timer", "value":"EPOCHTIME: 02/19/1999 11:05:53" }'

The `"value"` field in the attributes for metric creation and the value in a plain write command are the only two places the EPOCHTIME syntax is accepted for translating a date string into a number.

### Deleting a metric
You delete metrics using the `--killmetric` option. There is no single-letter option variant for this operation. Also the operation *requires* a metric ID and will not work with `-n` -- this is on purpose to protect you against the potential ambiguity inherent in metric labels.

    % nr -wM +newmetric private
    6920028165809384377

    % nr --killmetric 6920028165809384377
    Deleted

### Interactions
You read interactions using -I and write them using -wI:

    % nr -nI bozo
    like 3457529302618327156 None 2015-01-12T14:26:04.618Z 7180748783917522265 -- None
    like 6434586778323266772 None 2015-01-12T14:25:57.237Z 7180748783917522265 -- None

If you plan to do anything programmatic with this output the best practice is to use the JSON form and parse it accordingly:

    % nr -nIj bozo
    { "Results": ... output elided }

To write an interaction you must specify the kind ("like" / "error" / "comment") and any kind-specific data required ("commentBody" for error or comment). Examples:

    % nr -nIw bozo '{ "kind" : "like" }'
    % nr -nIw bozo '{ "kind" : "error" , "commentBody" : "Yikes - this is an error message" }'
    % nr -nIw bozo '{ "kind" : "comment" , "commentBody" : "This is a comment" }'

As a shorthand you can specify a "naked" string and it will be interpreted as a comment:

    % nr -nIw bozo "This is an easier way to make a comment"

Note the quotes because the comment string has to be one shell argument.

### Displaying Events
Interactions are likes, errors, and comments. Events are the value updates. You can display all the value updates for a metric:

    % nr -En 'A Random Number'
    74 @ 2015-01-12T17:43:17.438Z by 7180748783917522265
    19 @ 2015-01-12T17:13:13.581Z by 7180748783917522265
    85 @ 2015-01-12T16:43:13.972Z by 7180748783917522265
     ... much more output elided

As with interactions, if you are going to do anything programmatic with this output I strongly encourage you to use the JSON output form.

A metric that is updated frequently could have hundreds of events; you may wish to limit the output. The `--limit` option (also available as `-t`) does this:

    % nr -En --limit 2 'A Random Number'
    74 @ 2015-01-12T17:43:17.438Z by 7180748783917522265
    19 @ 2015-01-12T17:13:13.581Z by 7180748783917522265
    
That is the full, non-elided, output of the command; only the most recent two events are printed (because of the `--limit 2` command option).

Thus a silly alternate way to print out a metric value is:

    % nr -En --limit 1 'A Random Number[value]'
    74

Note that using --limit is quite preferable to piping the command into `head`. The `--limit` option will make the command stop querying the server once it has all the results it plans to print whereas piping the command into `head` will cause the command to gather all the items (possibly making many calls to the server) only for them to then be discarded on output. Use `--limit` not `head`.

### Deleting Things
You can delete events and interactions by their event or interaction ID respectively. You do that with `--delete` and either `-I` or `-E` as appropriate. 

For example if '9118113586950422173' is an event ID in the metric bozo then:

    % nr -En --delete bozo 9118113586950422173
    579875221157343692/9118113586950422173 -- Deleted

deletes that event. You have to know if you are deleting an event (`--delete -E`) or an interaction (`--delete -I`); this is just how the NumerousApp API works. 

### Suppressing output
The -q option suppresses all ordinary output. Sometimes useful in scripts when writing. You can even use -q when reading; this may or may not be silly depending on whether your goal is simply to test the exit status.

### Displaying the API key
If you need the API Key extracted via `numerousKey()` you use `-k`:

    % nr -k
    nmrs_X587wFqs8z9v

No other arguments/commands are processed.

### Getting Rate-Limiting Information
If you are curious about your rate-limit usage the `-R` flag will add it to your output:

    % nr -R -n bozo
    Remaining APIs: 299. New allocation in 20 seconds.
    17

Note that this continues to execute other nr commands (in this case reading `bozo` and reporting its value of 17).

For testing purposes it is sometimes helpful to know you have a certain amount of API allocation remaining before hitting any limits; you can use the `--ensure` flag for this:

    % nr -R --ensure 200 -n bozo
    No delay needed; have 293 operations left.
    17

Had your current API allocation been lower than 200 you might have seen:

    Delaying 27 seconds; only have 187 APIs left.
    17

If you have no other `nr` operations and just want the report or the `--ensure` action by themselves, use `-RR`:

    % nr -RR
    Remaining APIs: 293. New allocation in 47 seconds.

or

    % nr -RR --ensure 200
    No delay needed; have 247 operations left.

### Displaying Statistics
The `--statistics` option will display additional internal statistics:

    % nr -n --statistics
    579875221157343692 bozo
    2141579335528632068 A Random Number
    9208972516053673667 Crude Oil
    Statistics for <Numerous {api.numerousapp.com} @ 0x1010175c0>:
       additional-chunks: 1
          serverRequests: 3
          rate-remaining: 297
            first-chunks: 1
     serverResponseTimes: [0.285916, 0.288592, 0.27704, 0, 0, 0, 0, 0, 0, 0]
               simpleAPI: 3
              rate-reset: 50

The `serverResponseTimes` reports the last ten server on-the-wire delays in seconds (the most recent time is the first one in the list). In the above example only three requests were made so only the first three entries are non-zero and they show that over-the-wire time is taking about 280 milliseconds. This is measured from the time the library calls the underlying HTTP (`requests.request`) method to the time the results are returned.

The `serverRequests` value is the number of actual HTTP interactions sent to the server.

See the source code in `numerous.py` to understand what the rest of these mean. In particular the `--statistics` option is most useful for determining whether or not the throttle code has been called.

### Fine-Grained Permissions
If you create a metric with `visibility` "private" then no one other than you can access the metric in any way. This remains true even if they obtain the metric ID. The metric attribute `visibility` is more powerful than the metric attribute `private`. The `private` attribute simply controls whether the metric can be found via search functions or not. A metric that has `private` true can still be read by anyone who knows its ID, whereas a metric that has `visibility` "private" can only be read by the owner and by those who have been granted explicit fine-grained permissions. This terminology is, unfortunately, a bit confusing.

Thus, for example:

    % nr -wM +Public_Read_AND_Write '{ "private" : false, "writeable" : true }'

creates a metric called "Public_Read_AND_Write" that can be read or written by ANYONE in the NumerousApp world. It can be found in the "search for numbers" feature of the various apps. It is a very public metric.

This:

    % nr -wM +Public_ReadOnly '{ "private" : false }'

creates a metric called "Public_ReadOnly" that can be read by ANYONE, can be found in "search for numbers", but can only be written by you. ("writeable" defaults to false).

This:

    % nr -wM +Unlisted_Read_AND_Write '{ "private" : true, "writeable" : true }'

creates a metric called "Unlisted_Read_AND_Write" that can be read or written by ANYONE in the NumerousApp world; however, it is not listed and can't be found using the search functions. Therefore, before anyone can read or write it they have to find out its ID somehow (usually by you explicitly telling it to them, usually using the sharing function in the app). The secrecy of the ID is the entire security of this metric; once people start learning and sharing the ID of this metric the "secret" is out and anyone who gets that ID can access this metric.

Fine-grained permissions provide more control over all this. To use them you have to set the `visibility` parameter on a metric to "private", for example:

    % nr -wM +SecureMetric '{ "visibility" : "private" }'

This creates a metric called "SecureMetric" that can only be accessed by you (the metric owner). Access by anyone else is controlled by explicit permissions. See the NumerousApp API documentation for details on these permissions, but a few examples here will illustrate the basics.

If I have another user I want to allow to read this metric, I must know their userId which is a numeric string of digits. There are a variety of ways to discover that ID. Once you have it, you create a permissions resource on the given metric to set the specific level of authority you want to grant that user (for this metric). With the `nr` command you do that with the `-A` option, using a syntax that looks like this:

    % nr -n -w -A SecureMetric/853094853098452 '{ "readMetric" : true, "updateValue" : true }'

where `853094853098452` is the userId. The syntax is {metricID}/{userID} and {metricID} is either numeric or, as in the example above, can be a label if the `-n` option is also used. The second argument is a JSON representation of the permissions resource, with the attributes as described in the NumerousApp API documentation. The two most useful attributes are `readMetric` which allows reading the value of the metric (and viewing the event and interaction streams) and `updateValue` which allows writing the value of the metric (but not editing other metric parameters).

To see the permissions on a given metric just use `-A` by itself:

    % nr -n -A SecureMetric
    853094853098452 on 6366750873739623617: readMetric updateValue

The example output is "userID on metricID: " followed by a list of permissions that that user has on the metric. You can also (possibly more usefully) view these resources in json format using `-j`:

    % nr -njA SecureMetric
     ... json output would be here ...

To delete a specific permission resource from a metric use the `--delete` option (there is no single-letter form of this) like this:

    % nr -n -A --delete SecureMetric 853094853098452

which requests that the permission resource associated with userID 853094853098452 be deleted from metric SecureMetric.


### More
Still not yet documented; read the shell script source: photos, users, subscriptions, stream...