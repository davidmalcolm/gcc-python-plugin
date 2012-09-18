#include <stdlib.h>
#include <string.h>

#if 1
void double_free(void *ptr)
{
  free(ptr);

  /* BUG: double-free: */
  free(ptr);
}
#endif


#if 1
void unchecked_malloc(void)
{
  void *ptr = malloc(4096);
  memset(ptr, 0, 4096);
}
#endif

#if 1
int correct_usage(void)
{
  void *ptr = malloc(4096);
  if (!ptr)
    return -1; /* FIXME: with a plain return we have a BB with no gimple, and that breaks my checker */
  memset(ptr, 0, 4096);
  free(ptr);
  return 0;
}
#endif

#if 1
int two_ptrs(void)
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
#endif

#if 1
void fancy_control_flow(int i, int j)
{
  int k;
  void *ptr;
  for (k = i; k < j; k++) {
    switch(k) {
    case 0:
      ptr = malloc(1024);
      break;
    case 1:
      break;
    case 2:
      break;
    default:
      break;
    }
  }
  memset(ptr, 0, 4096);
  free(ptr);
}
#endif

#if 1
void foo(void *ptr);

void use_after_free(int i)
{
  void *p;

  p = malloc(1024);
  if (p) {
    free(p);
    foo(p);
  }
}
#endif
