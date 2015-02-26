# JOBE
The git batch runner.
Job scheduling the git way.

Requirements
------------
* Python 3.3 or later
* git
* make

Get Started
-----------
```
git clone https://github.com/blutack/jobe
cd jobe && make setup
git clone jobe.git client
```

Why?
----
Mostly just because I wanted to see how far I could run with the idea.
But it turns out to be surprisingly interesting.
Every client has a complete history of all jobs run and the inputs, with
git hashes backing everything. It works over any transport git supports
and can be used with any git web UI.

What's Missing?
---------------
* Solid error checking (there basically isn't any)
* Realtime notifications (could be easily added via email, or using ```watch "git pull --all"```)
* Some sane idea of how to handle large output files (git annex?)
