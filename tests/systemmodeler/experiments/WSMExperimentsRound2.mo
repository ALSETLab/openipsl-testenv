package WSMExperimentsRound2 "Diagnostic variants for the round-2 System Modeler verification of the IEEE/CIGRE DLL branch (1244ae93; not part of OpenIPSL)"
  extends Modelica.Icons.Package;

  model EMTPTransformerOpen "GFM.Components.EMTPTransformer alone, all six terminals open (the class as validated; round 1 E.2 control)"
    extends OpenIPSL.Electrical.Controls.IEEE_CIGRE.GFM.Components.EMTPTransformer;
  end EMTPTransformerOpen;

  model EMTPTransformerWinding1Loaded "EMTPTransformer with each winding 1 terminal grounded through 1 Ohm, the delta terminals open (round 1 E.2)"
    OpenIPSL.Electrical.Controls.IEEE_CIGRE.GFM.Components.EMTPTransformer t;
    Modelica.Electrical.Analog.Basic.Resistor ra(R=1);
    Modelica.Electrical.Analog.Basic.Resistor rb(R=1);
    Modelica.Electrical.Analog.Basic.Resistor rc(R=1);
    Modelica.Electrical.Analog.Basic.Ground g;
  equation
    connect(t.Ay, ra.p);
    connect(t.By, rb.p);
    connect(t.Cy, rc.p);
    connect(ra.n, g.p);
    connect(rb.n, g.p);
    connect(rc.n, g.p);
  end EMTPTransformerWinding1Loaded;

  model EMTPTransformerOpenNoInitFilters "EMTPTransformer alone, terminals open, the three voltage filters with init = NoInit (round 1 E.2; instances renamed phaseA..C by D.4)"
    extends OpenIPSL.Electrical.Controls.IEEE_CIGRE.GFM.Components.EMTPTransformer(
      phaseC(nonIdealTransformer(filter(init=Modelica.Blocks.Types.Init.NoInit))),
      phaseB(nonIdealTransformer(filter(init=Modelica.Blocks.Types.Init.NoInit))),
      phaseA(nonIdealTransformer(filter(init=Modelica.Blocks.Types.Init.NoInit))));
  end EMTPTransformerOpenNoInitFilters;

  model EMTPTransformerZeroSeqOpen "GFM.Components.EMTPTransformerZeroSeq alone, terminals open (the sibling that validates)"
    extends OpenIPSL.Electrical.Controls.IEEE_CIGRE.GFM.Components.EMTPTransformerZeroSeq;
  end EMTPTransformerZeroSeqOpen;

  model UnitCheckNegativeControl "Wrong on purpose: a current set equal to a voltage; System Modeler's unit check must warn"
    Modelica.Units.SI.Voltage v = 1 + time "A voltage";
    Modelica.Units.SI.Current i "A current";
  equation
    i = v;
  end UnitCheckNegativeControl;
end WSMExperimentsRound2;
