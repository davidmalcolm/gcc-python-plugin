# -*- coding: utf-8 -*-
#   Copyright 2014 Philip Herron <redbrain@gcc.gnu.org>
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
import pprint

def gccPassHook(passname, _):
    if passname.name == '*free_lang_data':
        for i in gcc.get_translation_units ():
            gns = gcc.get_global_namespace ()
            for decl in gns.declarations:
                if decl.is_builtin is False:
                    pp = pprint.PrettyPrinter(indent=4)
                    pp.pprint (str (decl.type))
                    pp.pprint (decl.type.fields)
                    pp.pprint (decl.type.methods)

gcc.register_callback (gcc.PLUGIN_PASS_EXECUTION, gccPassHook)
