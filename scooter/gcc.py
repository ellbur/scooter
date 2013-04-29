
from scooter import *

def compile_gcc(build, src, obj, opts, cc='gcc'):
    return build.watching([src.dir]).easyrun(cc, '-c', '-o', obj, opts, src)

def link_gcc(build, objs, bin, opts, ld='gcc'):
    return build.watching(set(_.dir for _ in objs)).easyrun(ld, '-o', bin, opts, objs)

def build_gcc(build, sources, bin, opts, gcc='gcc'):
    objects = [ ]
    for s in sources:
        obj = build.mkobj(s, '.o')
        objects.append(obj)
        compile_gcc(build, s, obj, opts, cc=gcc)
            
    link_gcc(build, objects, bin, opts, ld=gcc)

def run_gcc(build, sources, opts, gcc='gcc', into=None):
    bin = build.mkobj(sources, '')
    build_gcc(build, sources, bin, opts, gcc=gcc)
    easyrun(bin, into=into)

