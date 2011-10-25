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
from gccutils import check_isinstance

# Recorded attribute data:
fnnames_returning_borrowed_refs = set()

def attribute_callback_for_returns_borrowed_ref(*args):
    if 0:
        print('attribute_callback_for_returns_borrowed_ref(%r)' % args)
    check_isinstance(args[0], gcc.FunctionDecl)
    fnname = args[0].name
    fnnames_returning_borrowed_refs.add(fnname)

def register_our_attributes():
    # Callback, called by the gcc.PLUGIN_ATTRIBUTES event
    gcc.register_attribute('cpychecker_returns_borrowed_ref',
                           0, 0,
                           False, False, False,
                           attribute_callback_for_returns_borrowed_ref)
    gcc.define_macro('WITH_CPYCHECKER_RETURNS_BORROWED_REF_ATTRIBUTE')

