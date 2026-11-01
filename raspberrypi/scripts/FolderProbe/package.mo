package FolderProbe "Which Resources/Library/<folder> omc links and loads: every copy of libFolderProbe.so returns its own number"
  function probeValue "Number of the library copy that was loaded"
    input Real t "Time, so that the call is not evaluated at translation";
    output Real y "Folder number compiled into the library";
  external "C" y = folder_probe_value(t)
    annotation (Library="FolderProbe", LibraryDirectory="modelica://FolderProbe/Resources/Library");
  end probeValue;

  model M "Calls the external function once per step"
    Real y "Folder number of the loaded library";
  equation
    y = probeValue(time);
  end M;
end FolderProbe;
