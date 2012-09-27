
from __future__ import print_function
from collections import namedtuple as nt
import os
import sys
import shutil
from glob import glob
from subprocess import Popen
import re
import pickle
import treewatcher
import time
import hashlib
import types

# http://stackoverflow.com/questions/1151658/python-hashable-dicts
class hashable_dict(dict):
    def __hash__(self):
        return hash(tuple(sorted(self.iteritems())))
    def __eq__(self, other):
        return tuple(sorted(self.iteritems())) == tuple(sorted(other.iteritems()))

class PList(list):
    def __floordiv__(self, pat):
        return self.flatmap(lambda _: _//pat)
    def flatmap(self, func):
        res = PList()
        for _ in self:
            res.extend(func(_))
        return res
    
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
    
# Tn =(.aZi =(.≤3∨øẋ, =(.aZe
class Path(nt('Path', ['path'])):
    def __repr__(self): return './' + self.path
    def __div__(self, next):
        return p(str(self) + '/' + str(next))
    @property
    def exists(self): return os.path.exists(str(self))
    def against(self, where): return './' + os.path.relpath(str(self), str(where))
    def replant(self, src, dst): return p(dst) / self.against(src)
    def indir(self, dst): return self.replant(self.dir, dst)
    def chext(self, old, new):
        assert self.path.endswith(old)
        return p(seld.path[:-len(old)] + new)
    def setext(self, new):
        prefix = re.sub(r'\.[^\.]*$', '', self.path)
        return p(prefix + new)
    @property
    def name(self): return os.path.split(os.path.realpath(str(self)))[1]
    @property
    def dir(self):
        if os.path.isdir(str(self)): return self
        else: return p(os.path.split(os.path.realpath(str(self)))[0])
    def make_parents(self):
        try:
            os.makedirs(str(self.dir))
        except OSError as e:
            if e.errno != 17: raise e
    @property
    def name(self):
        return os.path.split(os.path.realpath(str(self)))[1]
    @property
    def realpath(self):
        return os.path.realpath(str(self))
    def __floordiv__(self, pat):
        if pat == '**':
            dirs = []
            def see(_, dir, __):
                dirs.append(p(dir))
            os.path.walk(str(self), see, None)
            return PTuple(dirs)
        else:
            return PTuple(p(_) for _ in glob(str(self) + '/' + pat))
    def rm(self): os.unlink(str(self))

def p(s):
    if isinstance(s, Path): return s
    elif isinstance(s, basestring): return Path(os.path.normpath(os.path.relpath(s)))
    else: raise TypeError

class BuildFailed(Exception):
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg
    def __repr__(self): return self.msg
    def __str__(self): return self.msg

def abbrev(cmd):
    return p(cmd[0]).name + ' ... ' + ' '.join(p(_).name
        for _ in cmd[1:] if not _.startswith('-'))

class Wild: pass

def clean(cmd, wd=None, first=True):
    cleaned = []
    for c in cmd:
        if isinstance(c, Path):
            c.make_parents()
        
        if isinstance(c, Path):
            if wd != None:
                cleaned.append(c.against(wd))
            else:
                cleaned.append(str(c))
        elif isinstance(c, list) or isinstance(c, tuple):
            cleaned.extend(clean(c, wd=wd, first=first))
        else:
            cleaned.append(str(c))
        
        first = False
        
    return t(cleaned)

class Command(nt('Command', ['func', 'args', 'kwargs'])):
    def __call__(self):
        return self.func(*self.args, **dict(self.kwargs))
    
    @property
    def is_up2date(self):
        return True
    
def easyrun(*cmd, **kwargs):
    wd = kwargs.get('wd', None)
    return run(clean(cmd, wd), **kwargs)
    
def spy(hl, into=sys.stdout):
    from fcntl import fcntl, F_GETFL, F_SETFL
    from select import select
    import os, sys

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
    
def run(cmd, echo=True, verbose=False, env={}, into=None, wd=None, wait=True):
    full_env = dict(os.environ)
    for k in env: full_env[k] = env[k]
    if echo and not verbose:
        print('\033[34m' + abbrev(cmd) + '\033[0m', file=sys.stderr) # ]]
    elif echo:
        print('\033[34m' + str(cmd) + ' (in ' + str(wd) + ')' + '\033[0m', file=sys.stderr) # ]]
    sys.stdout.flush()
    sink = open(str(into), 'w') if into!=None else None
    cwd = str(wd) if wd != None else None
    proc = Popen(map(str, cmd), env=full_env, stdout=sink, cwd=cwd)
    if wait:
        code = proc.wait()
        if sink != None: sink.close()
        if code != 0:
            raise BuildFailed(' '.join(cmd) + ' returned ' + str(code) + ' exit status')
        return code
    else:
        return None
    
class Build:
    def __init__(self, watchdirs, verbose=False, cache_size=1000):
        self.watchdirs = watchdirs
        self.cache = { }
        self.cache_size = 1000
        self.verbose = verbose
        
    def save(self):
        raise NotImplementedError
    
    def __del__(self):
        self.save()
        
    def run(self, cmd, echo=True, env={}, also_depends=(), wd=None, into=None, cache=True, verbose=False):
        if into != None:
            p(into).make_parents()
        if cache:
            return self.do_args(also_depends, run, cmd, echo=echo, verbose=self.verbose or verbose, env=hashable_dict(env), wd=wd, into=into)
        else:
            run(cmd, echo=echo, verbose=self.verbose, env=hashable_dict(env), wd=wd, into=into)
        
    def easyrun(self, *cmd, **kwargs):
        wd = kwargs.get('wd', None)
        return self.run(clean(cmd, wd), **kwargs)
    
    def do_args(self, also_depends, func, *args, **kwargs):
        return self.do_command(Command(func, tuple(args), tuple(sorted(kwargs.iteritems()))), also_depends)
        
    def do_command(self, cmd, also_depends):
        if cmd.is_up2date and (cmd in self.cache):
            if self.cache[cmd].is_up2date:
                self.cache[cmd].touch()
                return self.cache[cmd].result
        res, acc = treewatcher.run_watching_files(cmd, map(str, self.watchdirs))
        touched = t(acc.created) + t(acc.deleted) + t(acc.accessed) + t(acc.modified) + t(map(str, also_depends))
        self.cache[cmd] = CacheEntry(cmd, res, touched)
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
        self.file_sha1s = [
            (_, file_sha1(_)) for _ in touched_paths
        ]
        self.timestamp  = time.time()
        
    def touch(self):
        self.timestamp = time.time()
    
    def age(self):
        return time.time() - self.timestamp
    
    @property
    def is_up2date(self):
        return all(
            file_sha1(_) == old_sha1 for _, old_sha1 in self.file_sha1s
        )
    
def file_sha1(path):
    if not os.path.exists(str(path)):
        return '0' * 40
    elif os.path.isdir(str(path)):
        return 'd' * 40
    else:
        return hashlib.sha1(open(str(path), 'r').read()).hexdigest()
        
class BuildHere(Build):
    def __init__(self, here, watchdirs=None, verbose=False, cache=None, cache_size=1000):
        self.here = here
        if watchdirs == None:
            watchdirs = [here]
        if cache == None:
            cache = here / '.buildcache'
        self.cachefile = cache
        Build.__init__(self, watchdirs, verbose, cache_size)
        try:
            self.cache = pickle.load(open(str(self.cachefile), 'r'))
        except IOError as e:
            if e.errno == 2:
                pass
            else:
                raise e
        
    def save(self):
        pickle.dump(self.cache, open(str(self.cachefile), 'w'))
        
    def mkobj(self, srcs, ext):
        if isinstance(srcs, Path): srcs = [srcs]
        assert all(isinstance(_, Path) for _ in srcs)
        catted = ''.join(_.realpath for _ in srcs)
        return self.here / '.objcache' / (hashlib.sha1(catted).hexdigest() + ext)
    
def indent(str, amount):
    return re.sub('^(?=.)', ' ' * amount, str, flags=re.MULTILINE)

def do_build(op):
    try:
        op()
    except BuildFailed as bf:
        print()
        print('\033[4m\033[1m\033[31mBuild failed:\033[0m ')
        print()
        print(indent(str(bf), 4))
        print()
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        print('\033[4m\033[1m\033[31mInterrupted\033[0m ')
        print()
        sys.exit(1)
    
t = tuple
def tt(*things): return tuple(things)

