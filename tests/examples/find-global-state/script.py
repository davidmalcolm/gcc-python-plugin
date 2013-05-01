#   Copyright 2013 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2013 Red Hat, Inc.
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

def on_pass_execution(p, fn):
    if p.name == '*free_lang_data':
        for var in gcc.get_variables():
            type_ = var.decl.type

            # Don't bother warning about an array of const e.g.
            # const char []
            if isinstance(type_, gcc.ArrayType):
                item_type = type_.dereference
                if hasattr(item_type, 'const'):
                    if item_type.const:
                        continue

            gcc.inform(var.decl.location,
                       'global state "%s %s" defined here'
                       % (type_, var.decl))

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
