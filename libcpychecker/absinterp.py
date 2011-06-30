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

import gcc
from gccutils import get_src_for_loc

class AbstractValue:
    def __init__(self, gcctype, stmt):
        self.gcctype = gcctype
        self.stmt = stmt

    def __str__(self):
        return '%s from %s' % (self.gcctype, self.stmt)

    def __repr__(self):
        return 'AbstractValue(%r, %r)' % (self.gcctype, self.stmt)

class PredictedError(Exception):
    pass

class InvalidlyNullParameter(PredictedError):
    # Use this when we can predict that a function is called with NULL as an
    # argument for an argument that must not be NULL
    def __init__(self, fnname, paramidx, nullvalue):
        self.fnname = fnname
        self.paramidx = paramidx # starts at 1
        self.nullvalue = nullvalue

    def __str__(self):
        return ('%s can be called with NULL as parameter %i; %s'
                % (self.fnname, self.paramidx, self.nullvalue))


class UnknownValue(AbstractValue):
    def __str__(self):
        return 'unknown %s from %s' % (self.gcctype, self.stmt)

    def __repr__(self):
        return 'UnknownValue(%r, %r)' % (self.gcctype, self.stmt)

class PtrValue:
    """An abstract (PyObject*) value"""
    def __init__(self, nonnull):
        self.nonnull = nonnull

class NullPtrValue(PtrValue):
    def __init__(self, stmt=None):
        PtrValue.__init__(self, False)
        self.stmt = stmt

    def __str__(self):
        if self.stmt:
            return 'NULL value from %s' % get_src_for_loc(self.stmt.loc)
        else:
            return 'NULL'

    def __repr__(self):
        return 'NullPtrValue()'

def describe_stmt(stmt):
    if isinstance(stmt, gcc.GimpleCall):
        if isinstance(stmt.fn.operand, gcc.FunctionDecl):
            fnname = stmt.fn.operand.name
            return 'call to %s at line %i' % (fnname, stmt.loc.line)
    else:
        return str(stmt.loc)

class NonNullPtrValue(PtrValue):
    def __init__(self, refdelta, stmt):
        PtrValue.__init__(self, True)
        self.refdelta = refdelta
        self.stmt = stmt

    def __str__(self):
        return ('non-NULL(%s refs) acquired at %s'
                % (self.refdelta, describe_stmt(self.stmt)))

    def __repr__(self):
        return 'NonNullPtrValue(%i)' % self.refdelta

class PtrToGlobal(NonNullPtrValue):
    def __init__(self, refdelta, stmt, name):
        NonNullPtrValue.__init__(self, refdelta, stmt)
        self.name = name

    def __str__(self):
        if self.stmt:
            return ('&%s acquired at %s'
                    % (self.name, describe_stmt(self.stmt)))
        else:
            return ('&%s' % self.name)

