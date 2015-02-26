# JOBE
The git batch runner.

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

The jobe.ini file controls execution. When master is checked out, jobe will automagically 

Why?
----
Mostly just because I wanted to see how far I could run with the idea.
But it turns out to be surprisingly interesting.
Every client has a complete history of all jobs run and the inputs, with
git hashes backing everything. It works over any transport git supports
and can be used with any git web UI. Every job executes in a clean workspace.

How Does It Work?
-----------------
A git post-receive hook looks for pushes to only the master branch.
The repo is checked out into a temporary directory and a branch created with a unique job id (using in part the master commit hash for the job). Master is reset back to just include the sample config file and committed. The repo is then pushed back, where it is ignored due to multiple branches being present.
A subprocess is started and detached which checks out the repo to a seperate temp directory, waits until execution time is reached and then adds the results to the job branch and pushes them back.

What's Missing?
---------------
* Solid error checking (there basically isn't any)
* Realtime notifications (could be easily added via email, or using ```watch "git pull --all"```)
* Some sane idea of how to handle large output files (git annex?)
* Better capture of the subprocess output
* A method for killing submitted jobs
