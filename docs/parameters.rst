Working with GCC's tunable parameters
=====================================

GCC has numerous tunable parameters, which are integer values, tweakable at
the command-line by:

.. code-block:: bash

   --param <name>=<value>

A detailed description of the current parameters (in GCC 4.6.0) can be seen at
http://gcc.gnu.org/onlinedocs/gcc-4.6.0/gcc/Optimize-Options.html#Optimize-Options
(search for "--param" on that page; there doesn't seem to be an anchor to the list)

The parameters are visible from Python scripts using the following API:

.. py:function:: gcc.get_parameters()

    Returns a dictionary, mapping from the option names to :py:class:`gcc.Parameter` instances

.. py:class:: gcc.Parameter

   .. py:attribute:: option

      (string) The name used with the command-line --param switch to set this value

   .. py:attribute:: current_value

      (int/long)

   .. py:attribute:: default_value

      (int/long)

   .. py:attribute:: min_value

      (int/long) The minimum acceptable value

   .. py:attribute:: max_value

      (int/long) The maximum acceptable value, if greater than min_value

   .. py:attribute:: help

      (string) A short description of the option.

