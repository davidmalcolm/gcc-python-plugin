# -*- coding: utf-8 -*-
#   Copyright 2012, 2013 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012, 2013 Red Hat, Inc.
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

# Verify that the topological sort code in gccutils works
import gcc

def on_pass_execution(p, fn):
    if p.name == '*free_lang_data':
        from gccutils import sorted_callgraph
        index = {}
        for i, cgn in enumerate(sorted_callgraph()):
            index[cgn.decl.name] = i
        assert index['a'] < index['e']
        assert index['a'] < index['c']

        assert index['d'] < index['a']
        assert index['d'] < index['b']
        assert index['d'] < index['c']

        assert index['g'] < index['c']

        assert index['j'] < index['f']



gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
