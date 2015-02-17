# Determining Your API Key
You get your API key from your NumerousApp app on your phone/iPad/etc. Go to Settings, go into Developer Info, and there it is. Be careful with this; at this time Numerous provides no way to change your key so if you let other people have it that's game over for your account.

HTTP Basic Authentication (using your API Key) is used (over https) as described in the NumerousApp API [Authentication](http://docs.numerous.apiary.io/#authentication) documentation.

## For the impatient
Just do this at the shell:

    echo "yourAPIkeyHere" > ~/.numerousCred
    NUMEROUSAPIKEY=~/.numerousCred export NUMEROUSAPIKEY

In other words, make a file with your "nmrs_blah3v9483blah" key in it and set environment variable NUMEROUSAPIKEY to point at that file.

Then use the default key management:

    from numerous import Numerous
    nr = Numerous()

and you are ready to go. Numerous will pick up your key from the file named by the NUMEROUSAPIKEY environment variable.

The remainder of this page contains more details on ways to manage your key.

## numerousKey() convenience function

Once you have the API key you have to decide how to store it and how to provide it to the Numerous() constructor. A convenience function `numerousKey()` assists with this:

    from numerous import numerousKey

The `numerousKey()` function will work with a key provided either as a "naked" string or as a JSON object. In the simplest case you store your API key in a file and provide that file name to `numerousKey()`. For example:

    # Shell command - do this one time to set up your file
    % echo nmrs_4V23js92bsdf > .mykey

    # python code - this is one way to access the key from the .mykey file
    k = numerousKey(".mykey")
    nr = Numerous(apiKey=k)

You might find it convenient to have one credentials file with keys from various servers in it; to help with that the numerousKey function will also accept a JSON object and will look for the APIKey under a `'NumerousAPIKey'` entry. So, for example, if you have a file .multikeys that looks like this:

    % cat .multikeys
    {
      "NumerousAPIKey" : "nmrs_4V23js92bsdf",
      "SomeOtherKey" : "XBr5ojb906t6mrrV733qUg",
      "alternateKey" : "nmrs_8X617djsb9742h"
    }

then `numerousKey` still works:

    k = numerousKey(".multikeys")
    nr = Numerous(apiKey=k)

If for some reason you need to store the key under a different identifier, you can change that:

    k = numerousKey(".multikeys", credsAPIKey="alternateKey")

would pull the "alternateKey" found in the ".multikeys" file.

Of course if you have more complex requirements you can just get the key on your own any way you want and supply it to `Numerous(apiKey=whatever)` yourself.

### Data sources

The numerousKey() function will get its data (the naked key or the JSON) from any of these sources, specified via the argument as described:

* **k = numerousKey(None)** - the environment variable NUMEROUSAPIKEY will be used. If it doesn't exist then the function returns None (which will likely eventually lead to an authentication exception). If NUMEROUSAPIKEY does exist, then its content string is used as if it had been supplied as the argument to numerousKey (and so it can be any of the remaining forms, albeit NUMEROUSAPIKEY="@-" would be a bit odd, but all other forms are useful).

Whether the source argument was supplied as an actual argument or came from NUMEROUSAPIKEY in the environment, it is then treated according to what it looks like:

* **k = numerousKey('@-')** The key data comes from reading sys.stdin (using sys.stdin.read())
* **k = numerousKey('/blah')** The named file will be read().
* **k = numerousKey('.blah')** The named file will be read(). Any name starting with a single (or more) dot characters works, so './blah', and '../blah' and so forth also work.
* **k = numerousKey('@blah')** The named file 'blah' (not '@blah') will be read(). This is another way to access a file in the current directory.

If the argument isn't a string in any of the above forms, it can be an open file:

* **k = numerousKey(someOpenFile)** 

in which case the data comes from calling someOpenFile.read() (and the data can, of course, be a naked API key or a JSON at that point). Any object with a .read() method can be supplied, but note that exactly one call to read() (with no arguments) will be made. When you supply an open file object in this way the file is NOT closed by numerousKey().

Finally:

* **k = numerousKey(someString)** - the argument is treated as a string (a naked key or a JSON). Note that if you supply an actual key string then this becomes a no-op. So **k = numerousKey("nmrs_4V23js92bsdf")** is the same as **k = "nmrs_4V23js92bsdf"** (this is sometimes still useful as a generalized case especially for commands using argparse methods to supply the credential source information).

### Integration with the Numerous() constructor

A call to Numerous() with no argument (i.e., specify a None value for apiKey) causes the constructor to invoke numerousKey(None) for you. This is a convenient way to get a Numerous object going using the NUMEROUSAPIKEY environment variable rather than hardcoding the key into the code.

In practice what this means is:

    make a file ~/.numerousCred
    put your API key into that file
    set your environment variable NUMEROUSAPIKEY=~/.numerousCred

After that:

    from numerous import Numerous
    nr = Numerous()

will instantiate a Numerous object using the apiKey found in the .numerousCred file as specified by the environment variable NUMEROUSAPIKEY. 

You could strip this all the way down to putting your key directly into the environment:

    % NUMEROUSAPIKEY=nmrs_blah2348v754blah python myprogram.py

and still just use `nr = Numerous()`; however, doing so potentially exposes your key to anyone who can view process status on the machine (environment variables can be viewed) so this usually isn't a good idea on general principles.

Additional examples:

    # open file example
    from numerous import Numerous, numerousKey
    nr = Numerous(apiKey=numerousKey(open('AFileContainingAKey')))

    # JSON example
    from numerous import Numerous, numerousKey 
    k = numerousKey('{ "NumerousAPIKey" : "nmrs_4V23js92bsdf" }')
    nr = Numerous(apiKey=k)
