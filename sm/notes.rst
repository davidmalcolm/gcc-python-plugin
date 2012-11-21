Implementation Notes
====================
Ideally, we're modelling the state of all variables in the code, which can
be thought of as a state tuple, and the "perfect" solution would be to model
the flow through the "exploded" supergraph.  e.g. for 3 vars a, b, c, we
start at the entry node with (a, b, c) as (start, start, start).  We would
then iteratively find all state tuples for all nodes.

In this ideal world we would walk through this V-dimensional space (where V
is the number of variables), determining the precise shape of the visitable
subset at each statement in the supergraph.

However, we can't do this, as it explodes: for V vars and S states there are
S ** V possible state tuples.  e.g. for 10 variables and 5 states there
are 5 ** 10 = roughly 9.7 million possible state tuples.  I'd hoped that this
would be relatively sparse, but it can readily be exploded by a series of:

   if (foo()) v1 = stateA(); else v1 = stateB();
   if (foo()) v2 = stateA(); else v2 = stateB();
   ...
   if (foo()) vN = stateA(); else vN = stateB();

which gives 2^N states tuples, even if we constrain by function "scope".

e.g. for vars: a, b and states: start, foo, bar, baz

all possible states: e.g.

       a: start | foo | bar | baz
--------+-------+-----+-----+-----
b:start |   Y   |     |     |
b:foo   |   Y   |     |     |
b:bar   |       |  Y  |     | Y
b:baz   |       |     |     |

where Y (for "yes") marks a reachable combination

Given that this is not computationally feasible, we need a simpler approach.

Abstract domain
---------------
Possible states for var at a given supergraph node:

   a : some subset of S
   b : some subset of S

This is analogous to the interval domain over integers: we merely know the
(ranges of) possible values of the vars; we don't model any interaction
between those ranges.

Doing this gives us an overapproximation; for example, this precise solution

       a: start | foo | bar | baz
--------+-------+-----+-----+-----
b:start |   Y   |     |     |
b:foo   |   Y   |     |     |
b:bar   |       |  Y  |     | Y
b:baz   |       |     |     |

would be modelled as:

   a: {start, foo, baz}
   b: {start, foo, bar}

which expands to this:

       a: start | foo | bar | baz
--------+-------+-----+-----+-----
b:start |   Y   |  E  |     | E
b:foo   |   Y   |  E  |     | E
b:bar   |   E   |  Y  |     | Y
b:baz   |       |     |     |

where the "E" (for error) indicate the false positives due to the
over-approximation.
