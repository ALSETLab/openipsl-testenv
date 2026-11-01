package UnitProbe "Models with a unit error on purpose, to show whether OpenModelica's --unitChecking can fail"
  model WrongUnit "A voltage equated to a current"
    Modelica.Units.SI.Voltage v = 1 "Voltage";
    Modelica.Units.SI.Current i "Current, set equal to a voltage (wrong on purpose)";
  equation
    i = v "Unit error on purpose";
  end WrongUnit;

  model WrongUnitDer "A derivative in V/s set equal to s*V"
    parameter Modelica.Units.SI.Time T = 1 "Time constant";
    Modelica.Units.SI.Voltage x(start = 1, fixed = true) "State";
  equation
    der(x) = -T*x "Unit error on purpose: should be -x/T";
  end WrongUnitDer;

  model RightUnit "The same first-order lag written consistently"
    parameter Modelica.Units.SI.Time T = 1 "Time constant";
    Modelica.Units.SI.Voltage x(start = 1, fixed = true) "State";
  equation
    der(x) = -x/T "Consistent";
  end RightUnit;
end UnitProbe;
