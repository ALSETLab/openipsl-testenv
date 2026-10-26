"""list_classes.py - print every class of the IEEE_CIGRE packages, in package.order order (packages first), plus the
two UsersGuide classes the branch edits; the class list of the Windows round-2 validation (its scripts/list_classes.py,
unchanged logic).

    /usr/bin/python3 -I list_classes.py <.../OpenIPSL> > classes.txt
"""
import os
import sys

root = sys.argv[1]


def walk(folder, prefix, out):
    out.append(prefix)
    order = os.path.join(folder, "package.order")
    if not os.path.exists(order):
        return
    for name in open(order, encoding="utf-8").read().split():
        sub = os.path.join(folder, name)
        if os.path.isdir(sub):
            walk(sub, prefix + "." + name, out)
        else:
            out.append(prefix + "." + name)


classes = []
walk(os.path.join(root, "Electrical", "Controls", "IEEE_CIGRE"), "OpenIPSL.Electrical.Controls.IEEE_CIGRE", classes)
walk(os.path.join(root, "Tests", "Controls", "IEEE_CIGRE"), "OpenIPSL.Tests.Controls.IEEE_CIGRE", classes)
classes += ["OpenIPSL.UsersGuide.References", "OpenIPSL.UsersGuide.Publications"]
print("\n".join(classes))
