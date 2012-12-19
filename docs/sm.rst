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
The language resembles C with embedded fragments of Python and some other
syntactic elements.

Identifiers follow the same rules as both Python and C: a letter or
underscore, followed by zero or more letters, numbers or underscores.

Case is significant.

Reserved words, which can't be used as identifiers:
  * sm
  * decl
  * stateful
  * true, false:
  * any_pointer, any_expr
  * pat

Fragments of Python are enclosed in pairs of braces e.g.::

   {{ error("%s called with NULL as 1st argument" % fn) }}

Such Python fragments can have arbitrary amounts of leading whitespace, so
long as nothing is indented less that the first non-whitespace line.  For
example, within this pattern-match rule:

.. code-block:: c

   ptr.null:
     { *ptr }
       => {{
               # This fragment of Python code starts in column 10
               # and so that is treated as the left margin for Python
               # indentation purposes
               pass
          }};

Whitespace is ignored elsewhere in the script.

C-style comments can occur anywhere except within Python fragments, and are ignored:

.. code-block:: c

   ptr.null:
     { *ptr }
       =>
         /* This is a C-style comment */
         {{ error("dereference of NULL pointer %s" % ptr) }}


Top-level structures
^^^^^^^^^^^^^^^^^^^^
A .sm script consists of one or more sm checkers.

A checker is declared with "sm" and a name, and the content is enclosed in braces:

.. code-block:: c

   sm my_first_checker {
   }

   sm another_checker {
   }

   sm yet_another_checker {
   }

Within a checker are four types of high-level clause:

   * declarations of expressions that can be matched on in C code

   * named patterns, describing a rule for pattern-matching code and giving
     it a name

   * "global" fragments of Python code, enclosed in double-braces, for use
     in creating helper functions

   * pattern-matching rules, expressing patterns to detect when data is in
     a particular state, and what to do when the pattern is encountered

For example:

.. code-block:: c

   sm example_checker {
       /* Here are some declarations: */
       stateful decl any_pointer ptr;
       decl any_expr x;

       /* Here is a named pattern: */
       pat deref { *ptr } | { ptr[x] };

       /* Here is a global fragment of Python code: */
       {{
           # Helper function for a checker that can only be run on
           # constant integer expressions:
           def is_known_int(var):
              import gcc
              return isinstance(var.gccexpr, gcc.IntegerCst)
       }}

       /* Here are some pattern-matching rules: */
       ptr.*:
         { ptr = malloc() } =>  ptr.unchecked;

       ptr.*:
         { ptr = 0 } =>  ptr.null;

       ptr.unchecked, ptr.null, ptr.nonnull:
           { ptr == 0 } => true=ptr.null, false=ptr.nonnull
         | { ptr != 0 } => true=ptr.nonnull, false=ptr.null
         ;

       ptr.unchecked:
         { *ptr }
           => {{
                 error('use of possibly-NULL pointer %s' % ptr,
                       # "CWE-690: Unchecked Return Value to NULL Pointer Dereference"
                       cwe='CWE-690')
              }}, ptr.nonnull;

   }


Declarations
^^^^^^^^^^^^
Declarations describe elements that may be used when pattern matching
fragments of C code.  They are of the form::

   decl TYPE NAME;

where TYPE can be one of `any_expr` or `any_pointer`, and NAME is an
identifier.

One of the declarations should be prepended with "stateful", indicating that
this is the expression whose state is being tracked.

Examples:

  .. code-block:: c

    stateful decl any_pointer ptr;
    decl any_expr x;


Named patterns
^^^^^^^^^^^^^^
Named patterns describe a rule for pattern-matching code and give it a name
(which must follow the rules for identifiers given above).  This allows you
to abstract away some of the inner details of a match, and avoid repeating
yourself.

Examples:

.. code-block:: c

   /* Patterns that detect upper-bound and lower-bound checks: */
   pat check_ub { x < y } | { x <= y };
   pat check_lb { x > y } | { x >= y };
   pat check_eq { x == y };
   pat check_ne { x != y };


Pattern-matching rules
^^^^^^^^^^^^^^^^^^^^^^
A pattern-matching rule describes a set of states in which to search for
the pattern, the coding pattern to search for, and the outcome when such a
pattern is encountered when the relevant expressions are in the given state.

For example:

.. code-block:: c

   ptr.unknown, ptr.null, ptr.nonnull:
       { ptr == 0 } => true=ptr.null, false=ptr.nonnull
     | { ptr != 0 } => true=ptr.nonnull, false=ptr.null
     ;

States
******

The states are a comma-separated list of one of more state names, followed
by a colon, specifying in which states the rule should be run:

.. code-block:: c

   ptr.unknown, ptr.null, ptr.nonnull:

State names are either identifiers or two identifiers with a period between
them.

You can also use a "*" character as a wildcard to indicate that a match can
happen in all states:

.. code-block:: c

   ptr.*:

The start state has the name of the stateful decl with ".start" appended.
For example, given a stateful decl named ptr:

.. code-block:: c

   stateful decl any_pointer ptr;

all pointers implicitly start in the state "ptr.start".

.. note::

  Currently there is no additional significance to these two forms of state
  name, though I have followed the convention of making the first part of
  the state name match that of the stateful declaration).

Patterns
********

After the list of state names are the patterns and their outcomes, separated
by an ASCII-art arrow ("=>").

You can supply more than one pattern/outcome pair for a list of states,
separating them with the vertical bar character "|".

The pattern/outcome list should be terminated by a semicolon (even if
there's just one pattern/outcome pair.

.. code-block:: c

       { ptr == 0 } => true=ptr.null, false=ptr.nonnull
     | { ptr != 0 } => true=ptr.nonnull, false=ptr.null
     ;

The matching pattern can take various forms.  It can be a fragment of C code
enclosed in braces:

.. code-block:: c

    /* Assignments: */
    { q = 0 }
    { str = "hello world" }
    { a = b }

    /* Invocation of a specific named function: */
    { ptr = malloc(sz) }
    { free(ptr) }

    /* Comparison of a declaration against a value: */
    { ptr == 0 }
    { ptr != 0 }
    { a < b }
    { a <= b }
    { a > b }
    { a >= b }

    /* Dereference of a pointer: */
    { *ptr }

    /* Array access: */
    { arr[x] }

    /* Any usage of a value: */
    { ptr }

You can also use named patterns to avoid repetition:

.. code-block:: c

    pat check_ub { x < y } | { x <= y };
    pat check_lb { x > y } | { x >= y };

    x.has_lb:
        check_ub => true=x.ok
      | check_lb => false=x.ok
      ;
    x.has_ub:
        check_ub => false=x.ok
      | check_lb => true=x.ok
      ;

You can supply more than one pattern, separating them with vertical bar
characters ("|") to signify "or":

.. code-block:: c

   { x < y } | { x <= y }


There are also some special patterns, referenced by wrapping them in a pair
of dollar characters:

$leaked$
$$$$$$$$

This special pattern matches whenever a value is lost e.g. the values of
locals at the end of function:

.. code-block:: c

  ptr.nonnull:
    $leaked$ => { error("leak of %s" % ptr) }

.. warning::

   The `$leaked$` pattern is only a placeholder for now, and doesn't work
   properly

$arg_must_not_be_null$
$$$$$$$$$$$$$$$$$$$$$$

This special pattern matches whenever a function marked with `GCC's nonnull
attribute <http://gcc.gnu.org/onlinedocs/gcc-4.0.0/gcc/Function-Attributes.html>`_
is called, for each parameter so marked:

.. code-block:: c

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

Outcomes
********
The outcome of a pattern match is generally either a transition to a given
state, or a fragment of Python code.

You can provide a state name, in which case the value matching the stateful
declaration will transition to that state:

.. code-block:: c

   /* Example of transitioning to named state "ptr.unchecked" */
   ptr.*:
       { ptr = malloc() } => ptr.unchecked;

An outcome for a conditional can be guarded with "true" or "false": the
outcome will only be taken for the relevant value of the conditional.

For example, in this pattern rule, x will only transition to the state
"x.ok" along the path in which x equalled a given value.  It won't change
state along the "not equal" path:

.. code-block:: c

   /* Example of an outcome guarded by "true=" */
   x.tainted, x.has_lb, x.has_ub:
      { x == a } => true=x.ok

You can provide more than one outcome, separated by commas:

.. code-block:: c

   /* Example of outcomes guarded by "true=" and "false=" */
   x.tainted:
      { x < y } => true=x.has_ub, false=x.has_lb

All applicable outcomes are run, so that you can have both a Python fragment
and a named state:

.. code-block:: c

  /*
     Example of both a Python outcome (to issue an error), and a
     transition to a named state (since we only want to warn about the first
     dereference)
   */
  ptr.unchecked:
    { *ptr }
      => {{
            error('use of possibly-NULL pointer %s' % ptr,
                  # "CWE-690: Unchecked Return Value to NULL Pointer Dereference"
                  cwe='CWE-690')
         }}, ptr.nonnull;

Python API
----------

You can embed Python in two ways within an sm file: within a top-level clause
in the checker, and as an outcome when a pattern is matched:

.. code-block:: c

   sm example_checker {
       stateful decl any_pointer ptr;

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
above fragment is run and matches for `q` on this C code:

.. code-block:: c

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

   .. warning::

      Be careful when using keyword arguments to add attributes to a state:
      each set of attributes is effective its own instance of a state, and
      the implementation will need to do more work for every possible state
      created.

      In particular, the implementation is only guaranteed to terminate when
      there a finite number of states: Python fragments that try to
      manipulate states in complicated ways are likely to send the
      implementation into an infinite loop.

.. py:data:: state

   The current state.  The attribute `name` gives the name of the state,
   and other attributes that were provided as keyword arguments of
   :py:func:`set_state` can be looked up as regular python attributes.

   For example, this fragment from `sizeof_allocation.sm` calls into a
   Python function ("check_size") when a pointer of known size is assigned
   to another pointer, looking up the saved size via `state.size`:

   .. code-block:: c

     ptr.sized:
       { other_ptr = ptr } =>
         {{
              check_size(other_ptr, allocated_size=state.size)
         }};

.. note::

   The implementation makes no guarantees as to the number of times a given
   Python outcome will be called: it may be called many times, only once
   (and have its effects cached), or not at all.  Avoid side-effects in
   such Python code (such as writing to disk).


The grammar
===========
High-level rules::

   # start of grammar:
   checker : sm
           | sm checker

   sm : SM ID LBRACE smclauses RBRACE

   smclauses : smclause
             | smclauses smclause

   smclause : optional_stateful decl declkind ID SEMICOLON
   # e.g. "stateful decl any_pointer ptr;"
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

Declarations::

   empty :

   optional_stateful : STATEFUL
                     | empty

   declkind : "any_expr"
            | "any_pointer"

Pattern-matching rules::

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
