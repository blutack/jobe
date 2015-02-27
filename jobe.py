#!/usr/bin/env python3

# JOBE - the git batch job runner

# This file is designed to run as a git post-receive hook in a bare repository
# The accompanying makefile can be used to setup a repository.

# Alternatively, create a bare git repository, add this file as post-receive
# to the hooks directory, clone the repo temporarily, touch a temporary file and push.
# JOBE will detect the invalid state and set up master ready for use.

import sys, tempfile, os, configparser, time
from datetime import timedelta, datetime
import subprocess as sp

sample_config = '''[jobe]
# Command to execute
# Can also refer to any files in this folder (i.e sh foo.sh)
command = uname -a

# Base name of your results branch
name = run_date

# Don't wait for the job to complete
detach = yes

# Time to execute the command (server timezone). 
# To execute instantly, set this to a date in the past.
run_at = 2000-01-01T12:00:00.0

# Print all debug information
verbose = no
'''

class Worker:
    """Class used to detach and execute job processes."""
    
    def __init__(self, job_id):
        self.job_id = job_id
        
    # Call this file again in a new process, detaching from original controlling process to allow git to return
    # Called from the git owned process
    def spawn(self, detach):
        """Creates a new python process for each job, passing the job id as argument."""

        proc = sp.Popen(["python3", os.path.realpath(__file__), self.job_id], stdout=sp.PIPE, stderr=sp.PIPE, stdin=sp.PIPE)
        
        if not detach:
            # TODO: Python 3.3 and newer have a timeout keyword option for communicate, which would prevent deadlocking
            stdout, stderr = proc.communicate()
            
            p.debug(stdout)
            p.debug(stderr)      
    
    def execute(self, config, repo):
        """Executes a job from the passed configuration object, blocks until complete."""
        if config.wait > 0:
            time.sleep(config.wait)
        proc = sp.Popen(config.command, stdout=repo.open_file("stdout.log"), 
                stderr=repo.open_file("stderr.log"), cwd=repo.work_dir, shell=True)
        proc.wait()
        with repo.open_file("exitcode.log") as exit_file:
            print(proc.returncode, file=exit_file)
    
    # Called from the detached process
    def run(self):
        """Checks out a branch containing a job and executes the command included."""
        with Repo(repo_dir) as repo:
            repo.clone()
            repo.checkout(self.job_id)
            config = Config(repo, p)
            self.execute(config, repo)
            repo.add_all()
            repo.commit("Job complete")
            repo.push()
    
class Printer:
    """Utility class for pretty printing."""
    verbose = False # Controls debug output
    
    info = lambda _, output: print('\033[94m>>> ' + output + '\033[0m')
    ok = lambda _, output: print('\033[92m>>> ' + output + '\033[0m')
    warn = lambda _, output: print('\033[93m>>> ' + output + '\033[0m')   
    err = lambda _, output: print('\033[91m>>> ' + output + '\033[0m')
    banner = lambda self: self.info("JOBE - git\'in the job done")
    
    def debug(self, output):
        if self.verbose:
            self.warn(str(output)) 

# Ideally this would be done using Dulwich or something, but I aimed to only depend on the standard library.
class Repo:
    """A very basic wrapper around various git operations."""
    
    def __init__(self, location):
        """Specifies a git remote url for the repo to be checked out."""
        self.location = location
    
    # Context managers to allow with Repo()... use.
    # TemporaryDirectory is only available since Python 3.2
    def __enter__(self):
        self.__tmp_dir = tempfile.TemporaryDirectory()
        self.work_dir = self.__tmp_dir.name
        return self
        
    def __exit__(self, type, value, traceback):
        self.__tmp_dir.cleanup()
        
    def reset(self):
        """Remove contents of master and replace with sample configuration."""
        p.debug("Rolling back master")
        self.checkout("master")

        f = self.open_file("jobe.ini", 'a+')
        
        if f.read() != sample_config or len(os.listdir(self.work_dir)) > 2:
                f.close() # Make sure we close the file handle before removing the file
                self.git("rm -f *")
                
                with self.open_file("jobe.ini", 'w') as new_sample:
                    new_sample.write(sample_config)
                
                self.add("jobe.ini")
                self.commit("JOBE ready for submissions.")
            
    def open_file(self, file_name, mode = 'w+'):
        return open(os.path.join(self.work_dir, file_name), mode)
        
    def clone(self):
        """Clone the repository to a temporary working directory."""
        self.git("clone " + self.location + " " + self.work_dir)
    
    def branch(self, branch_name):
        """Create a new git branch."""
        self.git("checkout -b " + branch_name)
        
    def checkout(self, branch_name):
        """Checkout an existing branch."""
        self.git("checkout " + branch_name)
        
    def add_all(self):
        """Add all new files to the branch."""
        self.git("add -A")
        
    def add(self, file_name):
        """Add a single file to the branch."""
        self.git("add " + file_name)
    
    def commit(self, message):
        """Commit with the given message."""
        self.git("commit -a -m '" + message + "'")
        
    def push(self, branch = "--all"):
        """Push branches"""
        print(self.git("push " + branch))
        
    def short_hash(self):
        """Return the git short hash for the current head."""
        return self.git("rev-parse --short HEAD")
    
    # TODO: Don't use shell=True and fix the nasty path posixisms.
    def git(self, command):
        proc = sp.Popen("git --git-dir=" + self.work_dir + "/.git" + " " + command, shell=True, cwd = self.work_dir, 
             stdout=sp.PIPE, stderr=sp.PIPE, universal_newlines=True)
        stdout, stderr = proc.communicate()
         
        p.debug(stdout)
        p.debug(stderr)
        
        return stdout

class Config:
    filename = 'jobe.ini'
    valid = False
    
    def __init__(self, repo, printer):
        self.config_file = configparser.ConfigParser()
        self.config_file.read(os.path.join(repo.work_dir, self.filename))
        
        if not 'jobe' in self.config_file:
            # Short circuit and return a config object with valid = False
            return
            
        self.command = self.config_file['jobe'].get('command')
        
        self.job_id = self.config_file['jobe'].get('name', 'job') + '-' + repo.short_hash()
        
        self.detach = self.config_file['jobe'].getboolean('detach', False)
        p.verbose = self.config_file['jobe'].getboolean('verbose', False)
        
        self.run_at = self.config_file['jobe'].get('run_at')
        self.run_at = datetime.strptime(self.run_at, "%Y-%m-%dT%H:%M:%S.%f")
        
        self.wait = (self.run_at - datetime.now()).total_seconds() # Wait time in floating point seconds until execution.
        self.valid = True

def branch_only_master():
    """Utility function to read stdin and determine whether only head is being pushed to."""
    lines = sys.stdin.readlines()
    p.debug(lines)
    refs = lines[0].split(' ')
    return len(lines) == 1 and "refs/heads/master" in refs[2]

# This isn't strictly needed as a git hook is unlikely to be used as a library
if __name__ == "__main__":
    p = Printer()
    
    # Find the local path of the jobe repository (the repository the git hook is running from)
    repo_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
    
    # TODO: check properly that any arguments are valid job ids.
    # Currently, if called with no arguments we assume it is the git process.
    # If called with a job argument, assume we are the second, detached process.
    if len(sys.argv) <= 1:
        p.banner()
        if branch_only_master():
            with Repo(repo_dir) as repo:
                repo.clone()
                config = Config(repo, p)
                
                if not config.valid:
                    p.info("Invalid config, adding sample config file.")
                    p.info("Please pull and try again.")
                    repo.reset()
                    repo.push("origin master")
                    sys.exit(0)
                    
                p.info("Received job")
                repo.branch(config.job_id)
                repo.reset()       
                repo.push()
            
                w = Worker(config.job_id)
                w.spawn(config.detach)
                p.ok("Job submitted, id " + config.job_id)
                p.ok("To retrieve your job, do:")
                p.ok("git pull --all && git checkout " + config.job_id)
        else:
            p.warn("To create a job, push only to the master branch.")

    else:
        # We are the detached process, so create a worker and run the process blocking
        w = Worker(sys.argv[1])
        w.run()
        
    sys.exit(0)
