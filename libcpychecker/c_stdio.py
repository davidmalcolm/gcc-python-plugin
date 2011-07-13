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

# Checking of C's stdio functions
# Only partial coverage so var
import gcc

from absinterp import AbstractValue, ConcreteValue, InvalidlyNullParameter

class InternalCheckerError(Exception):
    pass

class UnrecognizedFunction(InternalCheckerError):
    def __init__(self, fnname):
        self.fnname = fnname

    def __str__(self):
        return 'Unrecognized function: %r' % self.fnname

c_stdio_functions = [
    'fopen',
    'fclose',
]

class NonNullFilePtr(AbstractValue):
    def __init__(self, stmt):
        self.stmt = stmt

    def __str__(self):
        return 'non-NULL (FILE*) acquired at %s' % self.stmt

    def __repr__(self):
        return 'NonNullFilePtr(%r)' % self.stmt

def handle_c_stdio_function(state, fnname, stmt):
    if fnname == 'fopen':
        # The "success" case:
        file_ptr = NonNullFilePtr(stmt)
        success = state.make_assignment(stmt.lhs,
                                        file_ptr,
                                        '%s() succeeded' % fnname)
        success.dest.acquire(file_ptr)

        # The "failure" case:
        failure = state.make_assignment(stmt.lhs,
                                        NullPtrValue(stmt),
                                        '%s() failed' % fnname)

        return [success, failure]
    elif fnname == 'fclose':
        expr = state.eval_expr(stmt.args[0])
        if isinstance(expr, NonNullFilePtr):
            result = state.make_assignment(stmt.lhs,
                                           AbstractValue(gcc.Type.int(), stmt),
                                           '%s() succeeded' % fnname) # FIXME errno handling!
            result.release(expr)
            return [result]
        elif isinstance(expr, NullPtrValue):
            raise InvalidlyNullParameter(fnname, 1, expr)
        else:
            result = state.make_assignment(stmt.lhs,
                                           AbstractValue(gcc.Type.int(), stmt),
                                           '%s() succeeded' % fnname) # FIXME errno handling!
            result.dest.release(expr)
            return [result]
    else:
        # We claimed to handle this function, but didn't:
        raise UnrecognizedFunction(fnname)
