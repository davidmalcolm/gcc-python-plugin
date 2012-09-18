extern void *never_call_this(void);

void test1(void)
{
  void *ptr = never_call_this();
}

void test2(void)
{
  /* empty */
}
