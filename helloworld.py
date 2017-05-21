
from numerous import Numerous

MyKey = "nmrs_1Wblahblah"         # your personal NumerousApp API key
MyMetric = "5746205777638039629"  # ID of a metric you have access to

nr = Numerous(apiKey=MyKey)
metric = nr.metric(MyMetric)

print((metric.read()))

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
# this works well with argparse, e.g. along these lines:
#
# parser = argparse.ArgumentParser()
# parser.add_argument('-c', '--credspec')
# ... other arguments ...
#
# args = parser.parse_args()
# nr = Numerous(apiKey=numerousKey(args.credspec))
#
# which will default to getting it from NUMEROUSAPIKEY (credspec None) or
# allow you to specify it via the given command line option in any of the
# forms (naked APIkey on command line, in a file, from stdin, etc)
#
