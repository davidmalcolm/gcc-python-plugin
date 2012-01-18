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

# Shared code for gcc-python-plugin's generate-*-c.py, where the code
# is specific to gcc-python-plugin

from cpybuilder import PyTypeObject, with_gcc_extensions

def indent(lines):
    return '\n'.join('    %s' % line for line in lines.splitlines())

class PyGccWrapperTypeObject(PyTypeObject):
    """
    A PyTypeObject that's also a PyGccWrapperTypeObject
    (with metaclass PyGccWrapperMetaType)
    """
    def __init__(self, *args, **kwargs):
        PyTypeObject.__init__(self, *args, **kwargs)
        self.ob_type = '&PyGccWrapperMetaType'

    def c_defn(self):
        result = '\n'
        result += 'PyGccWrapperTypeObject %(identifier)s = {\n' % self.__dict__
        result += self.c_src_field_value('wrtp_base',
                                         '{\n        .ht_type = {\n%s}' % indent(indent(self.c_initializer())))
        result += '    },\n'
        result += self.c_src_field_value('wrtp_mark',
                                         'wrtp_mark_for_%s' % self.struct_name,
                                         cast='wrtp_marker')
        result += '};\n'
        result +='\n'
        return result


