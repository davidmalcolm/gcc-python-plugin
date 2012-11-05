#   Copyright 2012 Matt Rice <ratmice@gmail.com>
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

# Test case for gcc.NamespaceDecl

import gcc

def indent_print(depth, thing):
  print("%s%s" % ("   " * depth, thing))

def print_namespace(ns, depth):
  attributes = ("name", "alias_of", "declarations", "namespaces")
  # [(method, arg),...]
  methods = [(gcc.NamespaceDecl.unalias, None),
	     (gcc.NamespaceDecl.lookup, "foo")]

  for attr in attributes:
    try:
      indent_print(depth, (attr, ns.__getattribute__(attr)))
    except Exception as e:
      indent_print(depth, (attr, e))

  for t in methods:
    method_name = t[0].__name__
    method = t[0]
    try:
      indent_print(depth, (method_name, method(ns, t[1])))
    except Exception as e:
      indent_print(depth, (method_name, e))

  print('')

def dump_namespaces(ns, depth):

  # ignore builtin's they would just make stdout.txt painful.
  if ns.is_builtin == False:
    print_namespace(ns, depth)

  # aliases of namespaces in particular will occur
  # within declarations, but we don't want to call
  # declarations on them (here).
  if ns.alias_of == None:
    for decl in ns.declarations:
      if type(decl) == gcc.NamespaceDecl:
        dump_namespaces(decl, depth + 1)

    # nested namespaces..
    for namespace in ns.namespaces:
      dump_namespaces(namespace, depth + 1)

def finish_unit_cb(*args, **kwargs):
  # depth of -1 to ignore the global namespace itself (because its a builtin).
  dump_namespaces(gcc.get_global_namespace(), -1)


gcc.register_callback(gcc.PLUGIN_FINISH_UNIT, finish_unit_cb)
