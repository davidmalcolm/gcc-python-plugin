Notes on JSON serialization of error reports
============================================

At the top level::

   {
       # Path to the source file being analyzed:
       "filename": "libcpychecker_html/test/example1/bug.c", 

       # The particular function containing the error:
       "function": {
           # The range of lines within the above file:
           "lines": [
               6, 
               22
           ], 
           # Name of the function:
           "name": "make_a_list_of_random_ints_badly"
       }, 

       # List of error reports within the function:
       "reports": []
   }

Within an individual report::

        # This is an individual report
        {
            # Description of the problem:
            "message": "ob_refcnt of '*item' is 1 too high", 

            # Severity of the problem: warning vs error
            "severity": "warning", 

            # List of states
            "states": []

            # List of notes
            "notes": []
        }

Locations within the source code are expressed as ranges i.e. a pair of
values::

                    "location": [
                        {
                            "column": 1, 
                            "line": 22
                        }, 
                        {
                            "column": 1, 
                            "line": 22
                        }
                    ], 

where both column and line are 1-based.  However, in the current implementation
they are all just points (i.e. both start and end are always equal).  (Fixing
this would be difficult, but not impossible, I think).


Notes convey high-level information about the message::

                {
                    "location": [
                        {
                            "column": 1, 
                            "line": 22
                        }, 
                        {
                            "column": 1, 
                            "line": 22
                        }
                    ], 
                    "message": "was expecting final ob_refcnt to be N + 1 (for some unknown N)"
                }

Notes are arguably not well-designed, and it's something of a misfeature that
states and notes are separate.


The list of states is ordered, representing the sequence of states of a path
through the function that demonstrates the bug.

Example of a state::

                {
                    # Where are we within the source code?
                    "location": [
                        {
                            "column": 10, 
                            "line": 14
                        }, 
                        {
                            "column": 10, 
                            "line": 14
                        }
                    ],

                    # A descriptive message of what happens immediately after
                    # this state (possibly empty or null if this transition is
                    # unremarkable):
                    "message": "when PyList_New() succeeds", 


                    # Variables and their values at this point within the
                    # program's execution
                    "variables": {}
                 }

Another example of a state::

                {
                    # Where are we within the source code?
                    # Ideally all locations will be non-null, but GCC can make
                    # this difficult
                    "location": null, 

                    # A descriptive message of what happens immediately after
                    # this state (possibly empty or null if this transition is
                    # unremarkable):
                    "message": "",

                    # Variables and their values at this point within the
                    # program's execution
                    "variables": {}
                }


Variables within a states "variables" dict::

                        # The name of the variable, or an expression:
                        "count": {
                            # The underlying C type:
                            "gcctype": "int", 

                            # The internal type of the value as seen by the
                            # analyzer:
                            "kind": "WithinRange", 

                            # For a "WithinRange", the range of possible
                            # values:
                            "maxvalue": 2147483647, 
                            "minvalue": -2147483648, 

                            # Where did this value come from?
                            "value_comes_from": [
                                {
                                    "column": 26, 
                                    "line": 10
                                }, 
                                {
                                    "column": 26, 
                                    "line": 10
                                }
                            ]
                        }, 

Some other kinds of value:

  * "kind": "UninitializedData"

    This value hasn't been written to yet: accessing
    this would be a bug


  * "kind": "RefcountValue"

     Example data::

                        "PyLongObject.ob_refcnt": {
                            "actual_ob_refcnt": {
                                "lower_bound_of_other_refs": 0, 
                                "refs_we_own": 2
                            }, 
                            "expected_ob_refcnt": {
                                "pointers_to_this": [
                                    "PyListObject.ob_item[0]"
                                ]
                            }, 
                            "gcctype": "Py_ssize_t", 
                            "kind": "RefcountValue", 
                            "value_comes_from": [
                                {
                                    "column": 22, 
                                    "line": 18
                                }, 
                                {
                                    "column": 22, 
                                    "line": 18
                                }
                            ]
                        }, 

     Fields:

        * "actual_ob_refcnt"
        
           the actual value of the ob_refcnt field, split into the references
           that the function owns ("refs_we_own"), plus a
           "lower_bound_of_other_refs" which can probably be ignored (it exists
           so that we can prove that some Py_DECREF(obj) invocations
           don't deallocate the object: even though the function might not own
           any refs on obj, other things might)

           "refs_we_own" is of most interest to the user::

                            "actual_ob_refcnt": {
                                "lower_bound_of_other_refs": 0, 
                                "refs_we_own": 2
                            }, 

        * "expected_ob_refcnt"

           information on what the ob_refcnt field *ought* to be.

           Contains a single field, "pointers_to_this", which is a list of all
           pointers to the object::

                            "expected_ob_refcnt": {
                                "pointers_to_this": [
                                    "PyListObject.ob_item[0]"
                                ]
                            }, 

           In theory, "refs_we_own" ought to equal the
           length of this list: the user is interested in when they're
           non-equal

  * "kind": "ConcreteValue"

     A specific known value (either integer or float)::

        "value": 0, 

  * "kind": "WithinRange", 

     A integer value within a specifc range::

        "maxvalue": 2147483647, 
        "minvalue": 1, 

     For large values it may make sense to print these in hexadecimal form
     (e.g. "0x7fffffff" rather than "2147483647")

  * "kind": "PointerToRegion", 
    
    A non-NULL pointer.  The target field describes what it's pointing at::

       "target": "PyListObject", 

  * "kind": "GenericTpDealloc", 

    FWIW, this is a destructor callback for deallocating a PyObject*: the
    analyzer knows that if this callback is called, the object will be
    deallocated









