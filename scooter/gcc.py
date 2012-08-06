
from scooter import *

def compile_gcc(build, src, obj, opts):
    return build.watching([src.dir]).easyrun('gcc', '-c', '-o', obj, opts, src)

def link_gcc(build, objs, bin, opts):
    return build.watching(set(_.dir for _ in objs)).easyrun('gcc', '-o', bin, opts, objs)

def build_gcc(build, sources, bin, opts):
    objects = [ ]
    for s in sources:
        obj = mkobj(s, '.o')
        objects.append(obj)
        compile_gcc(build, s, obj, opts)
            
    link_gcc(build, objects, bin, opts)

