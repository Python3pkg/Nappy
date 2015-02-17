# nrTEST

This page needs work but here's the gist of what you need to know.

The test program is in `tests/nrTEST`

If you have cloned the repository and you cd into tests, then you can run:

    NUMEROUSAPIKEY=~/.numerous ./nrTEST -D

The "-D" flag will make the test program execute using the local numerous.py library (in .. from the tests directory) and the local nr.py shell command (in ../shell-cmd from the tests directory) and it will run the tests twice - first with python version 2 and then with python version 3. 

You can use the "-Q" flag to run "quick". It's not really quick but it does skip a few of the more time-intensive tests. The arg parsing is a simple sh hack and you can't say "-QD" you have to say "-Q -D" if you want both.

You can use the "-C" flag to "continue" even after certain errors. The atomicity of ADD at the Numerous server still isn't 100% (as of this writing) and so -C allows that part of the test suite to fail without aborting the rest of the test.

It might be best to have a Numerous API Key for a "test" account because this will end up making a lot of metrics in the account during the test (though it does try to clean them up; frankly I just use my normal account and every now and then I just have to clean it up by hand if the test went awry).

