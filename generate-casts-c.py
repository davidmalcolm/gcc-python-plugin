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

import glob

import sys
sys.path.append('gcc-c-api')
from xmltypes import ApiRegistry, Api

COPYRIGHT_HEADER = '''
   Copyright 2013 David Malcolm <dmalcolm@redhat.com>
   Copyright 2013 Red Hat, Inc.

   This is free software: you can redistribute it and/or modify it
   under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see
   <http://www.gnu.org/licenses/>.
'''

def write_header(out):
    out.write('/* This file is autogenerated: do not edit */\n')
    out.write('/*%s*/\n' % COPYRIGHT_HEADER)
    out.write('\n')

def write_footer(out):
    out.write('''
/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
''')

def write_c(registry, c_out):
    write_header(c_out)

    c_out.write('#include <Python.h>\n')
    c_out.write('#include "gcc-python.h"\n')
    c_out.write('#include "gcc-python-wrappers.h"\n')
    c_out.write('#include "gcc-python-compat.h"\n')
    c_out.write('#include "cp/cp-tree.h"\n')
    c_out.write('#include "gimple.h"\n')

    c_out.write('#include "cp/cp-tree.h" /* for TFF_* for use by PyGccFunctionDecl_get_fullname */\n')

    c_out.write('/* op_symbol_code moved to tree-pretty-print.h in gcc 4.9\n')
    c_out.write('   but tree-pretty-print.h is only available from 4.7 onwards.  */\n')
    c_out.write('#if (GCC_VERSION >= 4009)\n')
    c_out.write('#include "tree-pretty-print.h"\n')
    c_out.write('#endif\n')

    c_out.write('#include "gcc-c-api/gcc-tree.h"\n')
    c_out.write('#include "gcc-c-api/gcc-type.h"\n')

    c_out.write('#include "autogenerated-casts.h"\n\n\n')

    tree_type = registry.lookup_type('tree')
    for subclass in tree_type.get_subclasses(recursive=True):
        c_out.write('%s\n'
                    'PyGccTree_as_%s(struct PyGccTree * self)\n'
                    '{\n'
                    '    return gcc_tree_as_%s(self->t);\n'
                    '}\n\n'
                    % (subclass.get_c_name(),
                       subclass.get_c_name(),
                       subclass.get_c_name()))
    write_footer(c_out)

def write_h(registry, h_out):
    write_header(h_out)

    h_out.write('#include <gcc-c-api/gcc-tree.h>\n')

    tree_type = registry.lookup_type('tree')
    for subclass in tree_type.get_subclasses(recursive=True):
        h_out.write('extern %s\n'
                    'PyGccTree_as_%s(struct PyGccTree * self);\n\n'
                    % (subclass.get_c_name(), subclass.get_c_name()))
    write_footer(h_out)

def main(c_filename, h_filename, xmldir):
    registry = ApiRegistry()
    for xmlfile in sorted(glob.glob(xmldir + '*.xml')):
        api = Api(registry, xmlfile)

    with open(c_filename, 'w') as c_out:
        write_c(registry, c_out)

    with open(h_filename, 'w') as h_out:
        write_h(registry, h_out)


main(c_filename=sys.argv[1],
     h_filename=sys.argv[2],
     xmldir=sys.argv[3])
