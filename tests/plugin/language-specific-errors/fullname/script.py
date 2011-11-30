# -*- coding: utf-8 -*-
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

# Verify that an attempt to use the "fullname" attribute outside of C++
# is gracefully handled

import gcc

class TestPass(gcc.GimplePass):
    def execute(self, fn):
        print('fn: %r' % fn)
        print('  fn.decl.name: %r' % fn.decl.name)
        # This ought to raise a RuntimeError
        print('  fn.decl.fullname: %r' % fn.decl.fullname)

test_pass = TestPass(name='test-pass')
test_pass.register_after('cfg')
