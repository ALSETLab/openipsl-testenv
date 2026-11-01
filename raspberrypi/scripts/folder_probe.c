/* folder_probe.c: one shared library per Resources/Library/<folder> variant; FOLDER_ID tells which copy was loaded */
double folder_probe_value(double t)
{
  return FOLDER_ID + 0.0 * t;
}
