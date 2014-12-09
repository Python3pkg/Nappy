# Nappy - NumerousApp API class for python

A python class implementing the [NumerousApp](http://www.numerousapp.com) [APIs](http://docs.numerous.apiary.io).

## python versions

Works on both python2 and python3.

## Dependencies
You must have the **requests** library installed ("pip install requests").

## Installing
This is not yet integrated into pip (that's next). For now just download numerous.py and copy it into your python library directory. 

I use ~/lib and set my PYTHONPATH but of course you can also copy it into the (system-dependent) library location.

If you want to use the shell command **nr** download that (and **nr.py**) and install it in your ~/bin and be sure to set the PYTHONPATH appropriately (see **nr** script itself)

## Getting started

Example code:

```
from numerous import Numerous

MyKey = "nmrs_3Vblahblah"         # your personal NumerousApp API key
MyMetric = "5746205777638039629"  # ID of a metric you have access to

nr = Numerous(apiKey=MyKey)
metric = nr.metric(MyMetric)

print (metric.read())             # current value

metric.write(1)
metric.like()
metric.comment("we all live in a yellow submarine")

for j in metric.stream():
    print(j)                      # each j is a dict for a stream item

```

## Miscellaneous Notes

* LANG: The NumerousApp API will sometimes return strings with the ellipsis ("...") unicode character. If you are running on a system that defaults LANG to C (I saw this on FreeBSD) you'll get an encoding exception from python when this character occurs.  Set environment variable LANG to en_US.UTF-8 or similar as appropriate.

