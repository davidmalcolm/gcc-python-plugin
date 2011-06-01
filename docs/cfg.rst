Working with functions and control flow graphs
==============================================

Many of the plugin events are called for each function within the source code
being compiled.  Each time, the plugin passes a :py:class:`gcc.Function`
instance as a parameter to your callback, so that you can work on it.

You can get at the control flow graph of a :py:class:`gcc.Function` via its
``cfg`` attribute.  This is an instance of :py:class:`gcc.Cfg`.

.. py:class:: gcc.Function

   Wrapper around one of GCC's ``struct function *``

   .. py:attribute:: cfg

      An instance of :py:class:`gcc.Cfg` for this function (or None during early
      passes)

   .. py:attribute:: decl

      The declaration of this function, as a :py:class:`gcc.Tree`

.. py:class:: gcc.Cfg

  A ``gcc.Cfg`` is a wrapper around GCC's `struct control_flow_graph`.

  It has attributes ``entry`` and ``exit``, both of which are instances of
  :py:class:`gcc.BasicBlock`.

  You can use ``gccutils.cfg_to_dot`` to render a gcc.Cfg as a graphviz
  diagram.  It will render the diagram, showing each basic block, with
  source code on the left-hand side, interleaved with the "gimple"
  representation on the right-hand side.  Each block is labelled with its
  index, and edges are labelled with appropriate flags.

    .. figure:: sample-cfg.png
       :scale: 50 %
       :alt: image of a control flow graph

       A sample CFG bitmap rendered by::

          dot = gccutils.cfg_to_dot(fun.cfg)
	  gccutils.invoke_dot(dot)

       on this C code::

          int
          main(int argc, char **argv)
          {
              int i;

              printf("argc: %i\n", argc);

              for (i = 0; i < argc; i++) {
                  printf("argv[%i]: %s\n", argv[i]);
              }

              helper_function();

              return 0;
          }



.. py:class:: gcc.BasicBlock

  A ``gcc.BasicBlock`` is a wrapper around GCC's `basic_block` type.

  .. py:attribute:: index

     The index of the block (an int), as seen in the cfg_to_dot rendering.

  .. py:attribute:: preds

     The list of predecessor :py:class:`gcc.Edge` instances leading into this
     block

  .. py:attribute:: succs

     The list of successor :py:class:`gcc.Edge` instances leading out of this
     block

  .. py:attribute:: phi_nodes

     The list of :py:class:`gcc.GimplePhi` phoney functions at the top of this
     block, if appropriate for this pass, or None

  .. py:attribute:: gimple

     The list of :py:class:`gcc.Gimple` instructions, if appropriate for this
     pass, or None


.. py:class:: gcc.Edge

  A wrapper around GCC's `edge` type.

  .. py:attribute:: src

     The source :py:class:`gcc.BasicBlock` of this edge

  .. py:attribute:: dest

     The destination :py:class:`gcc.BasicBlock` of this edge

  .. various EDGE_ booleans also
