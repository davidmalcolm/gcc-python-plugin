# -*- coding: utf-8 -*-
#   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012 Red Hat, Inc.
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

# Demonstration of how to look up a struct's declaration from Python

import gcc

class TestPass(gcc.GimplePass):
    def execute(self, fn):
        print('fn: %r' % fn)
        for u in gcc.get_translation_units():
            for decl in u.block.vars:
                if isinstance(decl, gcc.TypeDecl):
                    # "decl" is a gcc.TypeDecl
                    # "decl.type" is a gcc.RecordType:
                    print('  type(decl): %s' % type(decl))
                    print('  type(decl.type): %s' % type(decl.type))
                    print('  decl.type.name: %r' % decl.type.name)
                    for f in decl.type.fields:
                        print('    type(f): %s' % type(f))
                        print('      f.name: %r' % f.name)
                        print('      f.type: %s' % f.type)
                        print('      type(f.type): %s' % type(f.type))

test_pass = TestPass(name='test-pass')
test_pass.register_after('cfg')
