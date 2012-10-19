#include <stdlib.h>

struct foo {
  char buffer[128];
};

struct bar {
  char buffer[256];
};

struct foo *test(void)
{
  return (struct foo*)malloc(sizeof(struct bar));
  /* not a reportable bug: although the sizeof() is wrong, the size is large
     enough, and some code does runtime size calculation that we don't want to
     issue a false positive over */
}
