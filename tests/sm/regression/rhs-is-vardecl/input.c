extern const char *char_ptr;

int test(void)
{
  if (strcmp("literal", char_ptr))
    return 1;
  return 0;
}
