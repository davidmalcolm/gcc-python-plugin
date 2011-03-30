#include <gcc-plugin.h>

int plugin_is_GPL_compatible;

#include "plugin-version.h"

int
plugin_init (struct plugin_name_args *plugin_info,
             struct plugin_gcc_version *version)
{
    if (!plugin_default_version_check (version, &gcc_version)) {
          return 1;
    }

    printf("%s:%i:plugin_init", __FILE__, __LINE__);
  
    //register_callback (plugin_info->base_name, PLUGIN_PASS_MANAGER_SETUP, NULL, &pass_info);
    return 0;
}
