# Checking of C's stdio functions
# Only partial coverage so var
import gcc

from absinterp import AbstractValue, NullPtrValue, InvalidlyNullParameter

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
        success = state.make_assignment(stmt.lhs, file_ptr)
        success.acquire(file_ptr)

        # The "failure" case:
        failure = state.make_assignment(stmt.lhs, NullPtrValue(stmt))

        return [success, failure]
    elif fnname == 'fclose':
        expr = state.eval_expr(stmt.args[0])
        if isinstance(expr, NonNullFilePtr):
            result = state.make_assignment(stmt.lhs,
                                           AbstractValue(gcc.Type.int(), stmt)) # FIXME errno handling!
            result.release(expr)
            return [result]
        elif isinstance(expr, NullPtrValue):
            raise InvalidlyNullParameter(fnname, 1, expr)
        else:
            result = state.make_assignment(stmt.lhs,
                                           AbstractValue(gcc.Type.int(), stmt)) # FIXME errno handling!
            result.release(expr)
            return [result]
    else:
        # We claimed to handle this function, but didn't:
        raise UnrecognizedFunction(fnname)
