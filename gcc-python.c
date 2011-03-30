#include <gcc-plugin.h>

int plugin_is_GPL_compatible;

#include "plugin-version.h"

static const char* event_name[] = {
#define DEFEVENT(NAME) \
  #NAME, 
# include "plugin.def"
# undef DEFEVENT
};

static void
my_callback(enum plugin_event event, void *gcc_data, void *user_data)
{
  printf("%s:%i:my_callback(%s, %p, %p)\n", __FILE__, __LINE__, event_name[event], gcc_data, user_data);
}

#define DEFEVENT(NAME) \
static void my_callback_for_##NAME(void *gcc_data, void *user_data) \
{ \
     my_callback(NAME, gcc_data, user_data); \
}
# include "plugin.def"
# undef DEFEVENT

int
plugin_init (struct plugin_name_args *plugin_info,
             struct plugin_gcc_version *version)
{
    if (!plugin_default_version_check (version, &gcc_version)) {
          return 1;
    }

    printf("%s:%i:plugin_init\n", __FILE__, __LINE__);

#define DEFEVENT(NAME) \
    if (NAME != PLUGIN_PASS_MANAGER_SETUP &&         \
        NAME != PLUGIN_INFO &&                       \
	NAME != PLUGIN_REGISTER_GGC_ROOTS &&         \
	NAME != PLUGIN_REGISTER_GGC_CACHES) {        \
    register_callback(plugin_info->base_name, NAME,  \
		      my_callback_for_##NAME, NULL); \
    }
# include "plugin.def"
# undef DEFEVENT

  
    //    register_callback (plugin_info->base_name, PLUGIN_ALL_PASSES_START,
    //		       my_callback, NULL); 
    //    register_callback (plugin_info->base_name, PLUGIN_ALL_PASSES_END,
    //		       my_callback, NULL); 
    return 0;
}
