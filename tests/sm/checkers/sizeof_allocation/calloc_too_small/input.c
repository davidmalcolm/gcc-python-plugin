#include <stdlib.h>

struct foo {
  char buffer[1024];
};

struct bar {
  char buffer[128];
};

struct foo *test(void)
{
  return (struct foo*)calloc(4, sizeof(struct bar));
  /* BUG: sizeof(bar), rather than sizeof(foo), hence not enough space */
}
