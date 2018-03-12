# beachhead
This is an example of a system program for PyRVA March 14, 2018 (Pi Day)

- `beachhead.py` -- the main file for the program. It does something useful, so read the comments in some detail.
- `forkdemo.py` -- a simple use of fork & wait.
- `fname.py`, `jparse.py`, and `gkflib.py` contain supporting code. I started to jam them all into one file with `beachhead`, but how useful is that?
- `Linux.Processes.pdf` -- an overly elaborate diagram explaining how Linux processes start and stop.

**Note**: I yanked `urutils.py` out of the current archive, and replaced it with 
`gkflib.py`, a similar collection of utility functions that you can find in 
[this github repo](https://github.com/georgeflanagin/gkflib) 
along with a few other things. The fuctionality of the example programs has not 
been reduced or changed.

## Running forkdemo

After you download or clone the repo, just type `python3 forkdemo.py` That's about all there is to it.

## Running beachhead

Beachhead relies on the other files being either in its directory, or in the list of directories 
defined in `PYTHONPATH`. Assuming you downloaded or cloned this repo without further manipulation,
everything (including this file) will be in the same directory. So type `python3 beachhead.py` and
you have it.
