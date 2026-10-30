#!/usr/bin/env python3
"""Generate Model/power-beam.feb — the FEBio Studio "power" demo model.

A 50 x 8 x 8 mm cantilever beam of neo-Hookean material (same family
as tension-block.feb: E=10, v=0.3), meshed with 1 mm hex8 elements
(3200 elements, 4131 nodes). The x=0 face is fully fixed; the x=50
tip face is prescribed -22.0 mm in z (guided tip: z-dof only, so the
beam bends freely) over one static step (40 increments). The tip
drop is 44% of the beam's length, so the solved beam arcs hard -
the bend cannot be missed - and the displacement and von Mises
fields have strong gradients: displacement grows from zero at the
fixed end to its maximum at the tip, and stress peaks at the
fixed-end outer fibres and falls to zero at the neutral axis and
toward the tip. (An earlier -10 mm version solved fine but read as
nearly straight on the iPad; the load was raised, per the user's
request for a demo that visibly moves - the deformation shown is
still exactly what the solver computes, at scale 1.0.)

Node numbering is layer-major (each x cross-section numbered
consecutively) so the bundled Skyline solver's profile stays narrow
along the beam: an x-fastest numbering makes the same mesh solve
orders of magnitude slower.
"""
import os

NX, NY, NZ = 50, 8, 8  # elements per axis (1 mm elements)
TIP_DROP = -22.0       # prescribed z displacement of the tip face (mm)


def nid(i, j, k):
    # i: 0..NX (x), j: 0..NY (y), k: 0..NZ (z); x is the slowest index
    return 1 + j + (NY + 1) * k + (NY + 1) * (NZ + 1) * i


nodes = []
for i in range(NX + 1):
    for k in range(NZ + 1):
        for j in range(NY + 1):
            nodes.append((nid(i, j, k), float(i), float(j), float(k)))

elems = []
eid = 0
for k in range(NZ):
    for j in range(NY):
        for i in range(NX):
            eid += 1
            conn = [
                nid(i, j, k), nid(i + 1, j, k), nid(i + 1, j + 1, k), nid(i, j + 1, k),
                nid(i, j, k + 1), nid(i + 1, j, k + 1), nid(i + 1, j + 1, k + 1), nid(i, j + 1, k + 1),
            ]
            elems.append((eid, conn))

fixed = [nid(0, j, k) for k in range(NZ + 1) for j in range(NY + 1)]
tip = [nid(NX, j, k) for k in range(NZ + 1) for j in range(NY + 1)]

out = []
out.append('<?xml version="1.0" encoding="ISO-8859-1"?>')
out.append('<febio_spec version="4.0">')
out.append('\t<Module type="solid"/>')
out.append('\t<Control>')
out.append('\t\t<analysis type="static"/>')
out.append('\t\t<time_steps>40</time_steps>')
out.append('\t\t<step_size>0.025</step_size>')
out.append('\t\t<plot_level>PLOT_MAJOR_ITRS</plot_level>')
out.append('\t\t<solver/>')
out.append('\t</Control>')
out.append('\t<Globals>')
out.append('\t\t<Constants>')
out.append('\t\t\t<T>0</T>')
out.append('\t\t\t<R>0</R>')
out.append('\t\t\t<Fc>0</Fc>')
out.append('\t\t</Constants>')
out.append('\t</Globals>')
out.append('\t<Material>')
out.append('\t\t<material id="1" name="BeamMat" type="neo-Hookean">')
out.append('\t\t\t<density>1</density>')
out.append('\t\t\t<E>10</E>')
out.append('\t\t\t<v>0.3</v>')
out.append('\t\t</material>')
out.append('\t</Material>')
out.append('\t<Mesh>')
out.append('\t\t<Nodes name="Beam">')
for i, x, y, z in nodes:
    out.append(f'\t\t\t<node id="{i}">{x:g},{y:g},{z:g}</node>')
out.append('\t\t</Nodes>')
out.append('\t\t<Elements type="hex8" name="Beam">')
for i, conn in elems:
    out.append(f'\t\t\t<elem id="{i}">' + ','.join(str(c) for c in conn) + '</elem>')
out.append('\t\t</Elements>')
out.append('\t\t<NodeSet name="Fixed">' + ','.join(str(n) for n in fixed) + '</NodeSet>')
out.append('\t\t<NodeSet name="Tip">' + ','.join(str(n) for n in tip) + '</NodeSet>')
out.append('\t</Mesh>')
out.append('\t<MeshDomains>')
out.append('\t\t<SolidDomain name="Beam" mat="BeamMat"/>')
out.append('\t</MeshDomains>')
out.append('\t<Boundary>')
out.append('\t\t<bc name="FixLeft" type="zero displacement" node_set="Fixed">')
out.append('\t\t\t<x_dof>1</x_dof>')
out.append('\t\t\t<y_dof>1</y_dof>')
out.append('\t\t\t<z_dof>1</z_dof>')
out.append('\t\t</bc>')
out.append('\t\t<bc name="TipDrop" type="prescribed displacement" node_set="Tip">')
out.append('\t\t\t<dof>z</dof>')
out.append(f'\t\t\t<value lc="1">{TIP_DROP:g}</value>')
out.append('\t\t\t<relative>0</relative>')
out.append('\t\t</bc>')
out.append('\t</Boundary>')
out.append('\t<LoadData>')
out.append('\t\t<load_controller id="1" type="loadcurve">')
out.append('\t\t\t<interpolate>LINEAR</interpolate>')
out.append('\t\t\t<extend>CONSTANT</extend>')
out.append('\t\t\t<points>')
out.append('\t\t\t\t<point>0,0</point>')
out.append('\t\t\t\t<point>1,1</point>')
out.append('\t\t\t</points>')
out.append('\t\t</load_controller>')
out.append('\t</LoadData>')
out.append('\t<Output>')
out.append('\t\t<plotfile type="febio"/>')
out.append('\t\t<logfile/>')
out.append('\t</Output>')
out.append('</febio_spec>')

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Model', 'power-beam.feb')
with open(path, 'w') as f:
    f.write('\n'.join(out) + '\n')
print(f'wrote {path}: {len(nodes)} nodes, {len(elems)} elements')
