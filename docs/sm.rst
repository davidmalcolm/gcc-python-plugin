.. Copyright 2012 David Malcolm <dmalcolm@redhat.com>
   Copyright 2012 Red Hat, Inc.

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

.. _sm:

.. we'll use
     :language: c
   within the markup, though that's obviously not the real language.

Usage example: state machine checker
====================================

The state machine checker provides a domain specific language that enables
you to add new warnings to GCC.  The language is currently known as "sm"

Programs in the language express simple state machines: each item of data
in the source being analyzed can have a state associated with it.  When
the code matches certain patterns, an item of data can potentially
transition to another state, or a fragment of handler code can be invoked,
typically to emit an error message.

You can use this to write simple scripts that express the rules of an API.

Examples
--------

Checking malloc usage
^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: ../sm/checkers/malloc_checker.sm
  :language: c

.. (not the real language)


Example script: checking sizes of allocated data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: ../sm/checkers/sizeof_allocation.sm
  :language: c


Example script: checking for tainted data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: ../sm/checkers/taint.sm
  :language: c

Invoking the checker
--------------------

.. FIXME: gcc-with-sm [*.sm] other args

   does this do LTO by default?


Syntax
------

The sm language
---------------
A .sm script consists of one or more sm checkers::

   sm my_first_checker {
   }

   sm another_checker {
   }

   sm yet_another_checker {
   }

.. TODO: Within a checker you should declare

Identifiers follow the same rules as both Python and C: a letter or
underscore, followed by zero or more letters, numbers or underscores.

Case is significant.

Reserved words, which can't be used as identifiers:
  * sm
  * decl
  * state
  * true, false:
  * any_pointer, any_expr
  * pat

Fragments of Python are enclosed in pairs of braces e.g.::

   {{ error("%s called with NULL as 1st argument" % fn) }}

Such Python fragments can have arbitrary amounts of leading whitespace, so
long as nothing is indented less that the first non-whitespace line::

   ptr.null
     => {{
             # This fragment of Python code starts in column 10
             # and so that is treated as the left margin for Python
             # indentation purposes
             pass
        }};

Whitespace is ignored elsewhere in the script.

C-style comments can occur anywhere except within Python fragments, and are ignored::

   ptr.null
     =>
       /* This is a C-style comment */
       {{ error("dereference of NULL pointer %s" % ptr) }}

Python API
----------

You can embed Python in two ways within an sm file: within a top-level clause
in the checker, and as an outcome when a pattern is matched::

   sm example_checker {
       state decl any_pointer ptr;

       {{
           # Example of top-level Python.  This will be run once when the
           # checker starts, and can be use for defining helper functions:
           def some_helper_function(a):
               pass
       }}

       ptr.null:
         { *ptr } =>
           {{
               # Example of a Python fragment used when a pattern is matched
               # in a particular state:
               if some_helper_function(ptr):
                   error("dereference of NULL pointer %s" % ptr)
           }};
   }

When a python fragment is called, the locals() will contain values for the
relevant named declarations for the given match.  For example, when the
above fragment is run and matches for `q` on this C code::

   *q = 0;

`ptr` is set up for you as an object such that str(ptr) == "q", and hence
this python code::

   error("dereference of NULL pointer %s" % ptr)

leads to this error message::

   dereference of NULL pointer q

The following API is available from within such a fragment:

.. py:function:: error(msg, cwe=None)

   Emit an error message.

   Optionally, an ID can be provided describing
   the error within the `Common Weakness Enumeration
   <http://cwe.mitre.org/index.html>`_ dictionary.

   :param msg: the error message to be emitted
   :type msg: str
   :param cwe: ID of the error, e.g. "CWE-690"
   :type cwe: str or None

.. py:function:: set_state(name, **kargs)

   Set the state to the one with the given name, potentially adding extra
   key/value pairs to the state.

   For example, at the bottom of this helper function from
   `sizeof_allocation.sm` the checker calls `set_state` supplying a `size`
   keyword argument, annotating the "ptr.sized" state with a specific size
   value, which can later be accessed as an attribute of the
   :py:data:`state` variable::

      def check_size(ptr, allocated_size):
          import gcc
          type_pointed_to = ptr.type.dereference
          if not isinstance(type_pointed_to, gcc.VoidType):
              required_size = type_pointed_to.sizeof
              if allocated_size < required_size:
                  error("allocation too small: pointer to %s (%i bytes)"
                        " initialized with allocation of %i bytes"
                        % (type_pointed_to, required_size, allocated_size),
                        cwe="CWE-131") # "Incorrect Calculation of Buffer Size"

          # Handle cases where the cast happens on another line:
          set_state("ptr.sized", size=int(allocated_size))


.. py:data:: state

   The current state.  The attribute `name` gives the name of the state,
   and other attributes that were provided as keyword arguments of
   :py:func:`set_state` can be looked up as regular python attributes.

   For example, this fragment from `sizeof_allocation.sm` calls into a
   Python function ("check_size") when a pointer of known size is assigned
   to another pointer, looking up the saved size via `state.size`::

     ptr.sized:
       { other_ptr = ptr } =>
         {{
              check_size(other_ptr, allocated_size=state.size)
         }};


Special patterns
----------------
Special patterns are denoted by pairs of dollar signs:

$leaked$
^^^^^^^^
This special pattern matches whenever a value is lost e.g. the values of
locals at the end of function::

  ptr.nonnull:
    $leaked$ => { error("leak of %s" % ptr) }

.. warning::

   The `$leaked$` pattern is only a placeholder for now, and doesn't work
   properly

$arg_must_not_be_null$
^^^^^^^^^^^^^^^^^^^^^^

This special pattern matches whenever a function marked with `GCC's nonnull
attribute <http://gcc.gnu.org/onlinedocs/gcc-4.0.0/gcc/Function-Attributes.html>`_
is called, for each parameter so marked::

  ptr.null:
    $arg_must_not_be_null$
      => {{
            error('NULL pointer %s passed as argument %i to %s',
                  % (ptr, argnumber, function),
                  # "CWE-690: Unchecked Return Value to NULL Pointer Dereference"
                  cwe='CWE-690')
         }};

The following variables are set up as locals for use by the Python code:

   * argindex: (int) the index of the argument that was matched (0-based)

   * argnumber: (int) the number of the argument that was matched (1-based)

   * function: (:py:class:`gcc.FunctionDecl`): the function that was called

   * parameter: (:py:class:`gcc.ParmDecl`): the parameter that was matched.
     This is only set for functions whose *definitions* are available (as
     opposed to merely the *declaration*)


The grammar
===========
High-level rules::

   # start of grammar:
   checker : sm
           | sm checker

   sm : SM ID LBRACE smclauses RBRACE

   smclauses : smclause
             | smclauses smclause


   empty :

Declarations::

   optional_state : STATE
                  | empty

   declkind : "any_expr"
            | "any_pointer"

   optional_state DECL declkind ID SEMICOLON
   # e.g. "state decl any_pointer ptr;"
   # e.g. "decl any_expr x;"

   smclause : PAT ID pattern SEMICOLON
   smclause : PYTHON
   smclause : statelist COLON patternrulelist SEMICOLON
       # e.g.
       #   ptr.unknown, ptr.null, ptr.nonnull:
       #      { ptr == 0 } => true=ptr.null, false=ptr.nonnull
       #    | { ptr != 0 } => true=ptr.nonnull, false=ptr.null
       #    ;
       #

   statelist : statename
             | statename COMMA statelist
       # e.g.
       #   ptr.unknown, ptr.null, ptr.nonnull

   patternrulelist : patternrule
                   | patternrule PIPE patternrulelist
       # e.g.
       #      { ptr == 0 } => true=ptr.null, false=ptr.nonnull
       #    | { ptr != 0 } => true=ptr.nonnull, false=ptr.null

   patternrule : pattern ACTION outcomes
       # e.g. "{ ptr = malloc() } =>  ptr.unknown"
       # e.g. "$leaked$ => ptr.leaked"

   statename : ID DOT ID
             | ID

Various kinds of pattern::

   pattern : LBRACE cpattern RBRACE
       # e.g.
       #   { ptr = malloc() }

   pattern : ID
       # e.g.
       #   checked_against_0

   pattern : DOLLARPATTERN
       # e.g.
       #   $leaked$

   pattern : pattern PIPE pattern
       # e.g.
       #   $leaked$ | { x == 0 }

Various kinds of "cpattern"::

   cpattern : ID ASSIGNMENT LITERAL_STRING
            | ID ASSIGNMENT LITERAL_NUMBER
            | ID ASSIGNMENT ID
       # e.g. "q = 0"

   cpattern : ID ASSIGNMENT ID LPAREN fncall_args RPAREN
       # e.g. "ptr = malloc()"

   fncall_arg : ID
              | LITERAL_STRING
              | LITERAL_NUMBER

   nonempty_fncall_args : fncall_arg
                        | fncall_args COMMA fncall_arg

   fncall_args : nonempty_fncall_args

   fncall_args : empty

   cpattern : ID LPAREN fncall_args RPAREN
       # e.g. "free(ptr)"

   cpattern : ID COMPARISON LITERAL_NUMBER
            | ID COMPARISON ID
       # e.g. "ptr == 0"

   cpattern : STAR ID
       # e.g. "*ptr"

   cpattern : ID LSQUARE ID RSQUARE
       # e.g. "arr[x]"

   cpattern : ID
       # e.g. "ptr"

The various outcomes when a pattern matches::

   outcomes : outcome
            | outcome COMMA outcomes
       # e.g. "ptr.unknown"

   outcome : statename
       # e.g. "ptr.unknown"

   outcome : "true" ASSIGNMENT outcome
           | "false" ASSIGNMENT outcome
       # e.g. "true=ptr.null"

   outcome : PYTHON
       # e.g. "{ error('use of possibly-NULL pointer %s' % ptr)}"

.. ::

   t_ACTION     = r'=>'
   t_LPAREN     = r'\('
   t_RPAREN     = r'\)'
   t_LBRACE     = r'{'
   t_RBRACE     = r'}'
   t_LSQUARE     = r'\['
   t_RSQUARE     = r'\]'
   t_COMMA      = r','
   t_DOT        = r'\.'
   t_COLON      = r':'
   t_SEMICOLON  = r';'
   t_ASSIGNMENT = r'='
   t_STAR       = r'\*'
   t_PIPE       = r'\|'

   def t_COMPARISON(t):
       r'<=|<|==|!=|>=|>'
       return t

   def t_LITERAL_NUMBER(t):
       r'(0x[0-9a-fA-F]+|\d+)'
       try:
           if t.value.startswith('0x'):
               t.value = long(t.value, 16)
           else:
               t.value = long(t.value)
       except ValueError:
           raise ParserError(t.value)
       return t

   def t_LITERAL_STRING(t):
       r'"([^"]*)"|\'([^\']*)\''
       # Drop the quotes:
       t.value = t.value[1:-1]
       return t
