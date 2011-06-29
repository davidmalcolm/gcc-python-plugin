Inspecting GCC's command-line options
=====================================

GCC's command-line options are visible from Python scripts as instances of
:py:class:`gcc.Option`.

.. py:class:: gcc.Option

   Wrapper around one of GCC's command-line options.

   You can locate a specific option using its `text` attribute::

      option = gcc.Option('-Wdiv-by-zero')

   The plugin will raise a `ValueError` if the option is not recognized.

   It does not appear to be possible to create new options from the plugin.

   .. py:attribute:: text

      (string) The text used at the command-line to affect this option
      e.g. `-Werror`.

   .. py:attribute:: help

      (string) The help text for this option (e.g. "Warn about uninitialized
      automatic variables")

   .. py:attribute:: is_driver

      (bool) Is this a driver option?

   .. py:attribute:: is_optimization

      (bool) Does this option control an optimization?

   .. py:attribute:: is_target

      (bool) Is this a target-specific option?

   .. py:attribute:: is_warning

      (bool) Does this option control a warning message?

   Internally, the class wraps GCC's `enum opt_code` (and thus a `struct cl_option`)


.. py:function:: gcc.get_option_list()

    Returns a list of all :py:class:`gcc.Option` instances.

.. py:function:: gcc.get_option_dict()

    Returns a dictionary, mapping from the option names to :py:class:`gcc.Option` instances

