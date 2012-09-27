
from scooter import *

def c_to_llvm(build, src, asm, opts, clang='clang'):
    return build.watching(src.dir).easyrun(clang, opts, '-S', src, '-emit-llvm', '-o', asm, also_depends=(src,))
    
def llvm_link(build, inputs, linked, opts, link='link'):
    watchdirs = [_.dir for _ in inputs] + [linked.dir]
    return build.watching(watchdirs).easyrun(link, opts, inputs, '-o', linked, also_depends=inputs)

def llvm_opt(build, input, output, opts, opt='opt'):
    return build.watching(input.dir).easyrun(opt, opts, input, '-o', output, also_depends=(input,))

def llvm_to_c(build, asm, c, opts, llc='llc'):
    c_tmp = mkobj((asm, c), '.c')
    build.watching(asm.dir).easyrun(llc, '-march=c', '-o', c_tmp, asm, also_depends=(asm,))
    sink = open(str(c), 'w')
    sink.write(open(str(c_tmp), 'r').read())
    sink.write('\n')
    sink.write('void initializeLLVM(void) { _GLOBAL__I_a(); }\n\n')
    sink.close()

def llvm_build_to_c(build, sources, c,
        clang='clang', link='llvm-link', opt='opt', llc='llc', clang_opts=(), opt_opts=()):
    asms = []
    for s in sources:
        asm = mkobj(s, '.ll')
        asms.append(asm)
        c_to_llvm(build, s, asm, clang_opts, clang=clang)
    
    linked = mkobj(asms, '.bc')
    llvm_link(build, asms, linked, [], link=link)
    opted = mkobj(linked, '.bc')
    llvm_opt(build, linked, opted, opt_opts, opt=opt)
    llvm_to_c(build, opted, c, [], llc=llc)
    
