
from scooter import *

if sys.version_info >= (3, 0):
    unicode = str

def compile_gcc(build, src, obj, opts, include_dirs=(), system_include_dirs=(), cc='gcc'):
    return build.watching([src.dir] + [_ for _ in map(p, list(include_dirs)) if _.exists] + [_ for _ in map(p, list(system_include_dirs)) if _.exists]).easyrun(cc, '-c', '-o', obj, (opts, t(('-I', d) for d in include_dirs), t(('-isystem', d) for d in system_include_dirs)), src)

def link_gcc(build, objs, bin, opts, ld='gcc', libs=()):
    if isinstance(bin, PTuple) or isinstance(bin, list) or isinstance(bin, tuple):
        if len(bin) != 1:
            raise ValueError('bin is %s having %d elements; should have exactly 1' % (bin, len(bin)))
    return build.watching(set(_.dir for _ in objs)).easyrun(ld, '-o', bin, opts, objs, libs)

def build_gcc(build, sources, bin, opts, gcc='gcc', extra_objects=(), libs=()):
    if isinstance(extra_objects, str): extra_objects = (extra_objects,)
    if isinstance(extra_objects, unicode): extra_objects = (extra_objects,)
    if isinstance(extra_objects, Path): extra_objects = (extra_objects,)
    
    objects = [ ]
    for s in sources:
        objects.append(compile_gcc(build, s, SINK('.o'), opts, cc=gcc)[0])
            
    link_gcc(build, objects + list(map(p, extra_objects)), bin, opts, libs=libs, ld=gcc)

def run_gcc(build, sources, opts, gcc='gcc', into=None):
    bin = build.mkobj(sources, '')
    build_gcc(build, sources, bin, opts, gcc=gcc)
    easyrun(bin, into=into)

