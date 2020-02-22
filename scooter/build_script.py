
from __future__ import print_function
import argparse
from scooter import *
import os

def build_main(here):
    def c(main_function):
        parser = argparse.ArgumentParser(
            description='''Builds .''',
            formatter_class = argparse.RawTextHelpFormatter
        )
        parser.add_argument('--trace', default=False, action='store_true',
                            help='Print Python stack traces')
        parser.add_argument('--print-commands', default=False, action='store_true',
                            help='Print commands before they are run')
        parser.add_argument('--show-why-rerun', default=False, action='store_true',
                            help='Show why commands are being re-run')

        positional_names = [
            main_function.__code__.co_varnames[i]
                for i in xrange(1, main_function.__code__.co_argcount)
        ]
        
        for p in positional_names:
            parser.add_argument(p)

        args = parser.parse_args()
        
        build = BuildHere(here, show_why_rerun=args.show_why_rerun, verbose=args.print_commands)
        
        try:
            if args.trace:
                return main_function(build, *[args.__dict__[p] for p in positional_names])
            else:
                try:
                    try:
                        return main_function(build, *[args.__dict__[p] for p in positional_names])
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
        finally:
            del build

    return c

