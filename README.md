# Nappy - python NumerousApp API 

A python class implementing the [NumerousApp](http://www.numerousapp.com) [APIs](http://docs.numerous.apiary.io).

Available on pip: `pip install numerous`

The source here on github is the current/newest; what you get from pip (pypi) is the stable "released" version and so tends to lag behind the github code. Choose accordingly.

Example code:

```
nr = numerous.Numerous()
metric = nr.metricByLabel('SomeMetricOfYours')
print(metric['value'])
```

## Wiki / Documentation
See the [Wiki](https://github.com/outofmbufs/Nappy/wiki) for interface documentation.
## python versions

Works on both python2 and python3.

## New in version 1.6.1
* NumerousMetric() constructor accepts new "embed" format URL now as metric ID.
* PERFORMANCE: Keep-alive works properly, server requests much faster now
* Several minor bug fixes

## New in version 1.6.0
* Fine grained permissions support
* Fixed exception raised when multiple matches in metricByLabel
* Improved debug() function
* Improved subfield/event notation handling in shell-cmd/nr.py
* Switched to MIT license (less restrictive than BSD)

## Getting started

Example code:

```
from numerous import Numerous

MyKey = "nmrs_3Vblahblah"         # your personal NumerousApp API key
MyMetric = "5746205777638039629"  # ID of a metric you have access to

nr = Numerous(apiKey=MyKey)
metric = nr.metric(MyMetric)

print (metric.read())             # current value

# can also access values this way
label = metric['label']

metric.write(1)
metric.like()
metric.comment("we all live in a yellow submarine")

for j in metric.stream():
    print(j)                      # each j is a dict for a stream item

```

## Dependencies
You must have the **requests** library installed ("pip install requests").

## Installing

This package is available on pip:

    pip install numerous      # python
    pip3 install numerous     # python3

Alternatively, you can just copy numerous.py into a directory on your PYTHONPATH (system dependent main library location or you can put it in ~/lib and set your PYTHONPATH appropriately).

## shell-cmd directory

There are two commands in the shell-cmd directory:
* nr (files: nr and nr.py) - general purpose Numerous metric program
* nrd - small program to display your Numerous metrics

The file shell-cmd/nr is a simple wrapper and might not even be needed
at all depending on how you installed everything. If you installed the
numerous.py file using pip (or pip3) so that it is in your system
library path then you can delete the "nr" file and rename "nr.py" to
"nr" and just use the python file directly.

If you installed the numerous.py file into your own personal directory
tree somewhere (e.g., ~/lib/numerous.py) then you will want to keep
the shell wrapper and edit it accordingly. This is all somewhat
self-explanatory if you look at the files.

The "nrd" file is a simple python program that will display your Numerous metrics ("nrd" means "Numerous Display"). I did not supply you with a PYTHONPATH wrapper (like nr vs nr.py); if you need to it is fairly self-explanatory how to make one similar to how nr vs nr.py work. 

## About API Keys
You get your API key from your NumerousApp app on your phone/iPad/etc. Go to Settings, go into Developer Info, and there it is. Be careful with this; at this time there is no way to change your key so if you let other people have it that's game over for your account.

Once you have this key you can just hard-code your API key in as the above example shows. The class also provides a convenience function numerousKey which lets you provide some *data* that will be used to get your API key in a variety of ways:

    from numerous import numerousKey

* **k = numerousKey(s)** The key ("k") will come from the string ("s") you provide, either as a naked key (i.e., the string) or in JSON form (as described below). In the trivial case this is a no-op (e.g. k = numerousKey('nmrs4Zblahblah') is identical to k = 'nmrs4Zblahblah'). 

* **k = numerousKey('@-')** The key will come from reading sys.stdin (until EOF). Note that the data read could either be a "naked" key or a JSON representation. This is true for all remaining cases as well.

* **k = numerousKey(somethingReadable)** The duck-typed "somethingReadable" will be read: k = somethingReadable.read() and then processed as a naked key or as JSON.

* **k = numerousKey('/blah')** The named file will be read().

* **k = numerousKey('.blah')** The named file will be read(). Any name starting with a single (or more) dot characters works, so './blah', and '../blah' and so forth also work.

* **k = numerousKey('@blah')** The named file 'blah' (not '@blah') will be read(). This is another way to access files in the current directory (vs prefixing them with a './'). Also if for some demented reason you want the key to come from a file named '@-', '@@-' would do the trick. 

* **k = numerousKey(None)** The data will come from the environment variable NUMEROUSAPIKEY, which itself in turn can take on all of the above forms (e.g., a file name, a JSON object, etc).

The data obtained from the above sources can either be a naked key (e.g., the file could contain the key) OR it can also be a JSON object. This lets you store keys for multiple types of systems in a single file (JSON object) for example. If the data looks like JSON then the API key will be sought under the key 'NumerousAPIKey'. You can override that in the numerousKey call if you really need to.

Finally, the Numerous() constructor itself will invoke numerousKey(None) for you if you don't specify an API key. This is a convenient way to get a Numerous object going using the NUMEROUSAPIKEY environment variable rather than hardcoding the key into the code.

In practice what this means is: 

 * make a file ~/.numerousCred
 * put your API key into that file
 * set your environment variable NUMEROUSAPIKEY=~/.numerousCred

After that:

    from numerous import Numerous
    nr = Numerous()

will do exactly what you want. Or some other examples:

    # open file example
    from numerous import Numerous, numerousKey
    nr = Numerous(apiKey=numerousKey(open('AFileContainingAKey')))

    # JSON example
    from numerous import Numerous, numerousKey
    k = numerousKey('{ "NumerousAPIKey" : "nmrs4Zblahblah" }')
    nr = Numerous(apiKey=k)

See the numerousKey() function for variations on how you might get the key (as described above).

If you look at the shell-cmd/nr.py file you will see how this is used (to basically allow a user to specify the API key any of those ways via a command line option).

Arguably this doesn't belong in numerous.py and belongs in a more general "credentials management" library/class that could be used for all sorts of things like this. If it being in the library bothers your sense of purity, you don't have to use it. And if it bothers you enough, delete it from your copy. :)

## Miscellaneous Notes

* shell-cmd: If you install numerous.py using pip you can just use the "nr" and "nr.py" commands as-is (the "nr" wrapper is redundant). If you manually install the class library then you should examine "nr" and set the PYTHONPATH appropriately.

* shell-cmd/nr LANG: The NumerousApp API will sometimes return strings with the ellipsis ("...") unicode character. If you are running on a system that defaults LANG to C (I saw this on FreeBSD) you'll get an encoding exception when using the shell command ("nr") when this character occurs.  Set environment variable LANG to en_US.UTF-8 or similar as appropriate.

