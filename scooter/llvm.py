
from scooter import *

def c_to_llvm(build, src, asm, opts, clang='clang'):
    return build.watching(src.dir).easyrun('clang', opts, '-S', src, '-emit-llvm', '-o', asm)
    
def llvm_link(build, inputs, linked, opts, link='link'):
    watchdirs = [_.dir for _ in inputs]
    return build.watching(watchdirs).easyrun(link, opts, inputs, '-o', linked)

def llvm_opt(build, input, output, opts, opt='opt'):
    return build.watching(input.dir).easyrun(opt, '-O3', opts, input, '-o', output)

def llvm_to_c(build, asm, c, opts, llc='llc'):
    return build.watching(asm.dir).easyrun(llc, '-march=c', '-o', c, asm)

def llvm_build_to_c(build, sources, c,
        clang='clang', link='link', opt='opt', llc='llc'):
    asms = []
    for s in sources:
        asm = mkobj(s, '.ll')
        asms.append(asm)
        c_to_llvm(build, s, asm, [], clang=clang)
    
    linked = mkobj(asms, '.bc')
    llvm_link(build, asms, linked, [], link=link)
    opted = mkobj(linked, '.bc')
    llvm_opt(build, linked, opted, [], opt=opt)
    llvm_to_c(build, opted, c, [], llc=llc)

