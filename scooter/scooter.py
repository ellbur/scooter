# encoding=utf-8

from __future__ import print_function
from collections import namedtuple as nt
import os
import sys
import shutil
from glob import glob
from subprocess import Popen, PIPE
import re
import cPickle
import treewatcher
import time
import hashlib
import types
from quickstructures import *
from quickfiles import *
from ellbureasyrun import *
import traceback
from exceptions import BaseException
from fcntl import fcntl, F_GETFL, F_SETFL
from select import select
import os, sys
import tempfile
import atexit
from threading import Thread

# http://stackoverflow.com/questions/1151658/python-hashable-dicts
class hashable_dict(dict):
    def __hash__(self):
        return hash(tuple(sorted(self.iteritems())))
    def __eq__(self, other):
        return tuple(sorted(self.iteritems())) == tuple(sorted(other.iteritems()))

class PTuple(tuple):
    def __floordiv__(self, pat):
        return self.flatmap(lambda _: _//pat)
    def flatmap(self, func):
        res = []
        for _ in self:
            res.extend(func(_))
        return PTuple(res)
    
def augment(the_obj, the_name, the_field):
    class Augmented:
        def __getattr__(self, name):
            if name == the_name:
                return the_field
            else:
                attr = getattr(the_obj, name)
                # This is where I think python made a mistake. Method binding should be done
                # at `.` time.
                if isinstance(attr, types.MethodType):
                    return types.MethodType(attr.im_func, self, type(self))
                else:
                    return attr
            
        def __setattr__(self, name, next):
            if name == the_name:
                raise NotImplementedError
            else:
                return setattr(the_obj, name, next)
    return Augmented()
    
class BuildFailed(Exception):
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg
    def __repr__(self): return self.msg
    def __str__(self): return self.msg

class Command(nt('Command', ['func', 'args', 'kwargs'])):
    def __call__(self):
        return self.func(*self.args, **dict(self.kwargs))
    
def spy(hl, into=sys.stdout):
    flags = fcntl(hl, F_GETFL)
    fcntl(hl, F_SETFL, flags | os.O_NONBLOCK)

    all = ''

    while True:
        select([hl], [], [])
        data = hl.read()
        if len(data) == 0: break
        into.write(data)
        into.flush()
        all = all + data
    
    return all

stream = spy

def run(cmd, echo=True, verbose=False, env={}, into=None, wd=None, wait=True, capture=False, stderr=None, objcache=None):
    cmd = tuple(cmd)
    sinks = [ ]
    cmd_no_sinks = [ ]
    for token, i in zip(cmd, range(len(cmd))):
        if isinstance(token, SINK):
            seed = ' '.join(map(str, cmd + (str(i),)))
            objcache.mkdirs()
            sink_file = objcache / (hashlib.sha1(seed).hexdigest() + token.extension)
            sinks.append(sink_file)
            cmd_no_sinks.append(sink_file)
        else:
            cmd_no_sinks.append(token)
    full_env = dict(os.environ)
    for k in env: full_env[k] = env[k]
    if echo and not verbose:
        print('\033[34m' + abbrev(cmd_no_sinks) + '\033[0m', file=sys.stderr) # ]]
    elif echo:
        print('\033[34m' + str(cmd_no_sinks) + ' (in ' + str(wd) + ')' + '\033[0m', file=sys.stderr) # ]]
    sys.stdout.flush()
    if capture:
        sink = PIPE
    else:
        sink = open(str(into), 'w') if into!=None else None
    cwd = str(wd) if wd != None else None
    if isinstance(stderr, basestring):
        stderr = open(stderr, 'w')
    proc = Popen(map(str, cmd_no_sinks), env=full_env, stdout=sink, stderr=stderr, cwd=cwd)
    if wait or len(sinks) > 0:
        code = proc.wait()
        if into != None: sink.close()
        if code != 0:
            raise BuildFailed(' '.join(cmd_no_sinks) + ' returned ' + str(code) + ' exit status')
        if capture:
            return proc.communicate()[0]
        elif len(sinks) > 0:
            return tuple(sinks)
        else:
            return None
    else:
        return None
    
class Build:
    def __init__(self, watchdirs, objcache, verbose=False, cache_size=1000, show_why_rerun=False):
        self.watchdirs = watchdirs
        self.objcache = objcache
        self.cache = { }
        self.cache_size = 1000
        self.cache_changed = False
        self.verbose = verbose
        self.show_why_rerun = show_why_rerun
        
    def save(self):
        raise NotImplementedError
    
    def __del__(self):
        try:
            self.save()
        except:
            traceback.print_exc()
            raise
        
    def run(self, cmd, echo=True, env={}, also_depends=(), wd=None, into=None, cache=True, verbose=False):
        if into != None:
            p(into).make_parents()
        if cache:
            return self.do_args(also_depends, run, cmd, echo=echo, verbose=self.verbose or verbose, env=hashable_dict(env), wd=wd, into=into, objcache=self.objcache)
        else:
            run(cmd, echo=echo, verbose=self.verbose, env=hashable_dict(env), wd=wd, into=into)
        
    def easyrun(self, *cmd, **kwargs):
        wd = kwargs.get('wd', None)
        return self.run(clean(cmd, wd), **kwargs)
    
    def do_args(self, also_depends, func, *args, **kwargs):
        return self.do_command(Command(func, tuple(args), tuple(sorted(kwargs.iteritems()))), also_depends)
        
    def do_command_with_explicit_dependencies(self, key, runner):
        if key in self.cache:
            if self.cache[key].is_up2date(show_why_rerun=self.show_why_rerun):
                return self.cache[key].result
        else:
            if self.show_why_rerun:
                print('Re-running because not in cache')
        res, dependencies = runner()
        self.cache[key] = CacheEntry(cmd, res, dependencies)
        self.cache_changed = True
        if len(self.cache) > self.cache_size*2:
            self.prune_cache()
        return res
        
    def do_command(self, cmd, also_depends):
        if cmd in self.cache:
            if self.cache[cmd].is_up2date(show_why_rerun=self.show_why_rerun):
                return self.cache[cmd].result
        else:
            if self.show_why_rerun:
                print('Re-running because not in cache')
        res, acc = treewatcher.run_watching_files(cmd, map(str, self.watchdirs))
        touched = t(acc.created) + t(acc.deleted) + t(acc.accessed) + t(acc.modified) + t(map(str, also_depends))
        self.cache[cmd] = CacheEntry(cmd, res, touched)
        self.cache_changed = True
        if len(self.cache) > self.cache_size*2:
            self.prune_cache()
        return res
    
    def prune_cache(self):
        # TODO
        pass
    
    def watching(self, also):
        if isinstance(also, Path):
            also = [also]
        old_watching = self.watchdirs
        new_watching = list(self.watchdirs) + list(also)
        next = augment(self, 'watchdirs', new_watching)
        return next
    
    def print_cache(self):
        for command in self.cache:
            entry = self.cache[command]
            print(entry.command)
            for f, sha1 in entry.file_sha1s:
                print('   ' + str(f) + '(' + str(sha1)[:5] + ')')
    
class CacheEntry:
    def __init__(self, command, result, touched_paths):
        self.command    = command
        self.result     = result
        self.file_fingerprints = [
            (_, file_fingerprint(_)) for _ in touched_paths
        ]
        
    def is_up2date(self, show_why_rerun=False):
        good = True
        for file, old_fingerprint in self.file_fingerprints:
            if not is_fingerprint_up2date(file, old_fingerprint):
                if show_why_rerun:
                    print('Re-running because %s has changed' % (file,))
                return False
        else:
            return True
    
def file_fingerprint(path):
    if not os.path.exists(str(path)):
        return (0, '0' * 40)
    else:
        s = os.stat(path)
        if os.path.isdir(str(path)):
            return (0, 'd' * 40)
        elif s.st_size > 500e6:
            return (s.st_mtime, 'b' * 40)
        else:
            return (s.st_mtime, hashlib.sha1(open(str(path), 'r').read()).hexdigest())
    
def is_fingerprint_up2date(path, fingerprint):
    mtime, sha1 = fingerprint
    
    if not os.path.exists(str(path)):
        return fingerprint == (0, '0' * 40)
    else:
        s = os.stat(path)
        if os.path.isdir(str(path)):
            return fingerprint == (0, 'd' * 40)
        elif s.st_size > 500e6:
            return fingerprint == (s.st_mtime, 'b' * 40)
        else:
            if s.st_mtime != mtime:
                return fingerprint[1] == hashlib.sha1(open(str(path), 'r').read()).hexdigest()
            else:
                return True
    
def file_sha1(path):
    if not os.path.exists(str(path)):
        return '0' * 40
    elif os.path.isdir(str(path)):
        return 'd' * 40
    elif os.stat(path).st_size > 500e6:
        return 'b' * 40
    else:
        return hashlib.sha1(open(str(path), 'r').read()).hexdigest()
    
class BuildHere(Build):
    def __init__(self, here, watchdirs=None, verbose=False, cache=None, cache_size=1000, show_why_rerun=False):
        here = p(here).dir
        self.here = here
        if watchdirs == None:
            watchdirs = [here]
        if cache == None:
            cache = here / '.buildcache'
        self.cachefile = cache
        Build.__init__(self, watchdirs, here/'.objcache', verbose, cache_size, show_why_rerun)
        try:
            try:
                self.cache = cPickle.load(open(str(self.cachefile), 'r'))
            except IOError as e:
                if e.errno == 2:
                    self.cache = { }
                    pass
                else:
                    raise e
        except:
            print('Loading build cache failed. Will start with empty cache.')
            self.cache = { }
        
    def save(self):
        if self.cache_changed:
            self.cache_changed = False
            with open(str(self.cachefile), 'w') as sink:
                cPickle.dump(self.cache, sink)
        
    def mkobj(self, srcs, ext):
        if isinstance(srcs, str): srcs = p(srcs)
        if isinstance(srcs, Path): srcs = [srcs]
        assert all(isinstance(_, Path) for _ in srcs)
        catted = ''.join(_.realpath for _ in srcs)
        return self.here / '.objcache' / (hashlib.sha1(catted).hexdigest() + ext)
    
def indent(str, amount):
    return re.sub('^(?=.)', ' ' * amount, str, flags=re.MULTILINE)

def sink_to_temp(content, key='', **opts):
    path = p(tempfile.gettempdir()) / hashlib.sha1(key).hexdigest()
    atexit.register(lambda: os.unlink(str(path)))
    open(str(path), 'w').write(content)
    return p(path)
    
def do_build(op):
    try:
        try:
            op()
        except RunFailed as rf:
            raise BuildFailed(str(rf))
    except BuildFailed as bf:
        print()
        print('\033[4m\033[1m\033[31mBuild failed:\033[0m ') # ]]]]
        print()
        print(indent(str(bf), 4))
        print()
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        print('\033[4m\033[1m\033[31mInterrupted\033[0m ') # ]]]]
        print()
        sys.exit(1)

build = do_build
    
def on_new_thread(func):
    th = Thread(None, func)
    th.start()
    return th

def edit(initial_text):
    path = Path.mktemp()
    editor = os.getenv('EDITOR')
    if editor == None:
        editor = 'nano'
    open(str(path), 'w').write(initial_text)
    Popen([editor, str(path)]).wait()
    return open(str(path)).read()

def charstream(hl):
    while True:
        c = hl.read(1)
        if not c: break
        yield c

