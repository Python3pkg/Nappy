# NumerousApp Python API

This class implements the NumerousApp API in python. You can read and write metrics ("numbers" you have set up in Numerous), create comments on metrics, access metric event streams, delete metrics, change your subscriptions, etc.

Also there is a Unix/Linux [shell command](https://github.com/outofmbufs/Nappy/wiki/Shell-Command) "nr" that gives you command-line access to most functions of the NumerousApp APIs.

The code works in either major version (2.x or 3.x) of python.

# Contents

* [APIKey Management](https://github.com/outofmbufs/Nappy/wiki/APIKey-Management)
* [Numerous class](https://github.com/outofmbufs/Nappy/wiki/Numerous-class)
* [NumerousMetric class](https://github.com/outofmbufs/Nappy/wiki/NumerousMetric-class)
* [Exceptions](https://github.com/outofmbufs/Nappy/wiki/Exceptions)
* [Rate Limits](https://github.com/outofmbufs/Nappy/wiki/Rate-Limits)
* [Shell Command](https://github.com/outofmbufs/Nappy/wiki/Shell-Command)
* [Test Suite](https://github.com/outofmbufs/Nappy/wiki/Test-Suite)
* [To Do](https://github.com/outofmbufs/Nappy/wiki/To-Do)

# Getting started
Get your API key from the NumerousApp on your mobile device. It's in Settings/Developer Info.

Put that key into a file such as ~/.mycred and set the NUMEROUSAPIKEY environment variable accordingly:
```
% echo nmrs_3xblahblahblah > ~/.mycred
% NUMEROUSAPIKEY=~/.mycred export NUMEROUSAPIKEY
```

See [APIKey Management](https://github.com/outofmbufs/Nappy/wiki/APIKey-Management) for nine thousand other ways you can handle the API key.

Get your metric ID -- you will find this in _Developer Info_ in the settings panel on any individual metric.

Now write code like this:
```
import numerous
nr = numerous.Numerous()
m = nr.metric('234203820395828234')
print(m.read())
m.write(77)
```

Or create a metric like this:
```
m = nr.createMetric('MyMetricName')
m.write(17)
```
This creates a public metric with label 'MyMetricName' on the server and sets its value to 17. See [createMetric](https://github.com/outofmbufs/Nappy/wiki/Numerous-class#createmetriclabel-valuenone-attrs) for more details.
