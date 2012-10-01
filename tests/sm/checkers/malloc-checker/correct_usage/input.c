#include <stdlib.h>
#include <string.h>

int test(void)
{
  void *ptr = malloc(4096);
  if (!ptr)
    return -1; /* FIXME: with a plain return we have a BB with no gimple, and that breaks my checker */
  memset(ptr, 0, 4096);
  free(ptr);
  return 0;
}
