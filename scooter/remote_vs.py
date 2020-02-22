
from easyrun import *
from collections import namedtuple as nt
import re

class RemoteVS(nt('RemoteVS', ['format_cl_command', 'run_link_command', 'path_local_to_remote', 'path_remote_to_local'])): pass

def compile_remote_vs(build, remote_vs, opts, source, object):
    cl_command = (
        '/c', opts, '/showIncludes', remote_vs.path_local_to_remote(source), '/Fo:\"%s\"' % (remote_vs.path_local_to_remote(object))
    )

    shell_command = remote_vs.format_cl_command(cl_command)
    
    def runner():
        output = easyrun(shell_command)
        lines = output.split('\n')
        dependencies = [ ]
        for line in lines:
            if line.startswith('Note: including file: '):
                dependencies.append(remote_vs.path_remote_to_local(line[22:]))
        return None, dependencies
    
    build.do_command_with_explicit_dependencies(shell_command, runner)
    
