#include <stdlib.h>
#include <string.h>

static void *f(int a)
{
  if (a) {
    void *p = malloc(4096);
    return p;
  } else {
    return NULL;
  }
}

static void g(int b, void *q)
{
  if (b==2) {
    g(b, q); /* contrived infinite recursion */
  }
  free(q);
}

void h(int c)
{
  int *r = (int*)f(c);
  r[0] = 42; /* BUG: the malloc in f could have failed */
  g(c, r);
  free(r); /* BUG: doublefree here, given that g frees the ptr */
}

static int factorial(int n)
{
  if (n < 2) {
    return 1;
  } else {
    return n * factorial(n-1);
  }
}
