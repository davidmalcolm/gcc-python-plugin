#include <stdlib.h>
#include <string.h>

int test(void)
{
  void *p = malloc(4096);
  void *q = malloc(4096);
  if (p) {
    memset(p, 0, 4096); /* Not a bug: checked */
  } else {
    memset(q, 0, 4096); /* BUG: not checked */
  }
  free(p);
  free(q);
  return 0;
}
