# Exceptions

Four specific exceptions are defined:

* NumerousError. The generic Exception subclass for NumerousAPI errors.
* NumerousMetricConflictError. Subclass of NumerousError. See NumerousMetric.write()
* NumerousAuthError. Subclass of NumerousError. For API key problems.
* NumerousChunkingError. Subclass of NumerousError. Used for some types of iterator errors.

## NumerousError
The `NumerousError` exception is the general purpose exception raised by the Numerous and NumerousMetric classes when the server reports an HTTP error code or when communication fails. If `e` is a NumerousError, then:
 * `e.code` will be an HTTP error code returned by the server or by the HTTP library.
 * `e.reason` will be a text string "reason" typically matching up with `e.code`
 * `e.details` will be a dictionary containing full-details of the error; the keys in this dictionary vary depending on the error and should probably not be used except as informational/debugging information.

## NumerousMetricConflictError
Subclass of `NumerousError`. Raised when you perform a metric `write()` with `onlyIfChanged=True` and the value isn't a change. See metric `write()` for more details. This exception is also thrown by `metricByLabel` in some multiple-match cases.

## NumerousAuthError
Subclass of `NumerousError`. Raised whenever the NumerousApp server returns an HTTP 401 code. Usually means your API Key is no good (or has become no good).

## NumerousChunkingError
Subclass of `NumerousError`. Raised from any iterator method when an unexpected server error occurs while fetching any chunk of results other than the first chunk. This error is never "expected" but it can happen if the server returns an error while we are fetching the second or subsequent "chunk" of any type of collection. Essentially this is communicating an iteration that has been interrupted by some server or network error and is therefore incomplete. Note that this is never raised if the _first_ chunk fetch fails (that will raise a NumerousError or possibly a NumerousAuthError) as that indicates bad parameters for the iterator, whereas a failure partway through the chunking protocol indicates some other type of (possibly severe, definitely unexpected) problem.
