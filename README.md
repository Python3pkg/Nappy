# Nappy - python NumerousApp API 

A python class implementing the [NumerousApp](http://www.numerousapp.com) [APIs](http://docs.numerous.apiary.io).

## python versions

Works on both python2 and python3.

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

## Dependencies
You must have the **requests** library installed ("pip install requests").

## Installing

This package is available on pip:

   pip install numerous

Alternatively, you can just copy numerous.py into a directory on your PYTHONPATH (system dependent main library location or you can put it in ~/lib and set your PYTHONPATH appropriately).

If you want to use the shell command **nr** download that (and **nr.py**) and install it in your ~/bin and be sure to set the PYTHONPATH appropriately (see **nr** script itself)

## Miscellaneous Notes

* shell-cmd: If you install numerous.py using pip you can just use the "nr" and "nr.py" commands as-is (the "nr" wrapper is redundant). If you manually install the class library then you should examine "nr" and set the PYTHONPATH appropriately.

* shell-cmd/nr LANG: The NumerousApp API will sometimes return strings with the ellipsis ("...") unicode character. If you are running on a system that defaults LANG to C (I saw this on FreeBSD) you'll get an encoding exception when using the shell command ("nr") when this character occurs.  Set environment variable LANG to en_US.UTF-8 or similar as appropriate.

