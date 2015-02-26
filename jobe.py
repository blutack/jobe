#!/usr/bin/env python3

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
    def __init__(self, job_id):
        self.job_id = job_id
        
    def spawn(self, detach):
        proc = sp.Popen(["python3", os.path.realpath(__file__), self.job_id], stdout=sp.PIPE, stderr=sp.PIPE, stdin=sp.PIPE)
        
        if not detach:
            stdout, stderr = proc.communicate()
            
            p.debug(stdout)
            p.debug(stderr)      
    
    def execute(self, config, repo):
        if config.wait > 0:
            time.sleep(config.wait)
        proc = sp.Popen(config.command, stdout=repo.open_file("stdout.log"), 
                stderr=repo.open_file("stderr.log"), cwd=repo.work_dir, shell=True)
        proc.wait()
        with repo.open_file("exitcode.log") as exit_file:
            print(proc.returncode, file=exit_file)
    
    def run(self):
        with Repo(repo_dir) as repo:
            repo.clone()
            repo.checkout(self.job_id)
            config = Config(repo, p)
            self.execute(config, repo)
            repo.add_all()
            repo.commit("Job complete")
            repo.push()
    
class Printer:
    verbose = False
    
    info = lambda _, output: print('\033[94m>>> ' + output + '\033[0m')
    ok = lambda _, output: print('\033[92m>>> ' + output + '\033[0m')
    warn = lambda _, output: print('\033[93m>>> ' + output + '\033[0m')   
    err = lambda _, output: print('\033[91m>>> ' + output + '\033[0m')
    banner = lambda self: self.info("JOBE - git\'in the job done")
    
    def debug(self, output):
        if self.verbose:
            self.warn(str(output)) 

class Repo:    
    def __init__(self, location):
        self.location = location
    
    def __enter__(self):
        self.__tmp_dir = tempfile.TemporaryDirectory()
        self.work_dir = self.__tmp_dir.name
        return self
        
    def __exit__(self, type, value, traceback):
        self.__tmp_dir.cleanup()
        
    def reset(self):
        p.debug("Rolling back master")
        self.checkout("master")

        f = self.open_file("jobe.ini", 'a+')
        
        if f.read() != sample_config or len(os.listdir(self.work_dir)) > 2:
                f.close()
                self.git("rm -f *")
                
                with self.open_file("jobe.ini", 'w') as new_sample:
                    new_sample.write(sample_config)
                
                self.add("jobe.ini")
                self.commit("JOBE ready for submissions.")
            
    def open_file(self, file_name, mode = 'w+'):
        return open(os.path.join(self.work_dir, file_name), mode)
        
    def clone(self):
        self.git("clone " + self.location + " " + self.work_dir)
    
    def branch(self, branch_name):
        self.git("checkout -b " + branch_name)
        
    def checkout(self, branch_name):
        self.git("checkout " + branch_name)
        
    def add_all(self):
        self.git("add -A")
        
    def add(self, file_name):
        self.git("add " + file_name)
    
    def commit(self, message):
        self.git("commit -a -m '" + message + "'")
        
    def push(self, branch = "--all"):
        print(self.git("push " + branch))
        
    def short_hash(self):
        return self.git("rev-parse --short HEAD")
        
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
            return
            
        self.command = self.config_file['jobe'].get('command')
        
        self.job_id = self.config_file['jobe'].get('name', 'job') + '-' + repo.short_hash()
        
        self.timeout = self.config_file['jobe'].get('timeout', 10)
        
        self.detach = self.config_file['jobe'].getboolean('detach', False)
        p.verbose = self.config_file['jobe'].getboolean('verbose', False)
        
        self.run_at = self.config_file['jobe'].get('run_at')
        self.run_at = datetime.strptime(self.run_at, "%Y-%m-%dT%H:%M:%S.%f")
        
        self.wait = (self.run_at - datetime.now()).total_seconds()
        self.valid = True

def branch_only_master():
    lines = sys.stdin.readlines()
    p.debug(lines)
    refs = lines[0].split(' ')
    return len(lines) == 1 and "refs/heads/master" in refs[2]
    
if __name__ == "__main__":
    p = Printer()
    
    repo_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
    
    if len(sys.argv) <= 1:
        # Standard push
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
            p.warn("Push only to master to create jobs")

    else:
        w = Worker(sys.argv[1])
        w.run()
        
    sys.exit(0)
