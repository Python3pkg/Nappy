
from numerous import Numerous

MyKey = "nmrs_1Wblahblah"         # your personal NumerousApp API key
MyMetric = "5746205777638039629"  # ID of a metric you have access to

nr = Numerous(apiKey=MyKey)
metric = nr.metric(MyMetric)

print (metric.read())

# other ways to handle API keys
#
# If you want to just rely on NUMEROUSAPIKEY in the environment:
#
#   nr = Numerous()
#
# If you have a "cred_string" in any of the forms described in shell-cmd/nr.py:
#
# from numerous import Numerous, numerousKey
# nr = Numerous(apiKey=numerousKey(cred_string))
#
