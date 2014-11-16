
from numerous import Numerous

MyKey = "nmrs_1Wblahblah"         # your personal NumerousApp API key
MyMetric = "5746205777638039629"  # ID of a metric you have access to

nr = Numerous(apiKey=MyKey)
metric = nr.metric(MyMetric)

print (metric.read())
