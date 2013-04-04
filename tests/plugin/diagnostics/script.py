#   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011 Red Hat, Inc.
#
#   This is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.

import sys

import gcc

# Verify that the various error and warning methods work:

def on_pass_execution(p, fn):
    if p.name == '*warn_function_return':
        gcc.error(fn.start, 'this is an error (with positional args)')
        gcc.error(location=fn.start,
                  message='this is an error (with keyword args)')
        gcc.warning(fn.end, 'this is a warning (with positional args)',
                    gcc.Option('-Wdiv-by-zero'))
        gcc.warning(location=fn.end,
                    message='this is a warning (with keyword args)',
                    option=gcc.Option('-Wdiv-by-zero'))
        gcc.error(fn.start,
                  # These should be passed through, without triggering errors:
                  'a warning with some embedded format strings %s and %i')

        # Verify that -Wno-format was honored
        # The behavior of these flags changed in 4.8, so skip this part
        # on gcc 4.8 onwards:
        if gcc.GCC_VERSION <= 4007:
            gcc.warning(fn.end,
                        'this warning ought not to appear',
                        gcc.Option('-Wformat'))

        # Verify that we can issue an unconditional warning, with no option
        # (as per https://fedorahosted.org/gcc-python-plugin/ticket/8 ):
        gcc.warning(fn.end, 'this is an unconditional warning')
        gcc.warning(fn.end, 'this is another unconditional warning', None)

        # Verify that gcc.warning handles an object of the wrong type by
        # raising a TypeError
        try:
            gcc.warning(fn.end, 'this is another unconditional warning',
                        'this should have been a gcc.Option instance, or None')
        except TypeError:
            err = sys.exc_info()[1]
            sys.stderr.write('expected error was found: %s\n' % err)
        else:
            raise RuntimeError('expected exception was not raised')

        # Exercise gcc.inform:
        gcc.inform(fn.start, 'This is the start of the function')
        gcc.inform(fn.end, 'This is the end of the function')

# Wire up our callback:
gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)

