#!/usr/bin/env python3
"""Generate Model/tension-block.feb — the FEBio Spike reference model.

A 10 x 2 x 2 mm block of neo-Hookean material, meshed 10 x 2 x 2 with
hex8 elements (40 elements, 99 nodes). The x=0 face is fully fixed; the
x=10 face is prescribed +1.0 mm in x (10% uniaxial tension) over one
static step (10 increments). Well-posed and analytically checkable:
the maximum nodal displacement must come out at exactly 1.0 mm and the
stress state is (nearly) uniform uniaxial tension.
"""
import os

NX, NY, NZ = 10, 2, 2  # elements per axis


def nid(i, j, k):
    # i: 0..NX (x), j: 0..NY (y), k: 0..NZ (z)
    return 1 + i + (NX + 1) * j + (NX + 1) * (NY + 1) * k


nodes = []
for k in range(NZ + 1):
    for j in range(NY + 1):
        for i in range(NX + 1):
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
pulled = [nid(NX, j, k) for k in range(NZ + 1) for j in range(NY + 1)]

out = []
out.append('<?xml version="1.0" encoding="ISO-8859-1"?>')
out.append('<febio_spec version="4.0">')
out.append('\t<Module type="solid"/>')
out.append('\t<Control>')
out.append('\t\t<analysis type="static"/>')
out.append('\t\t<time_steps>10</time_steps>')
out.append('\t\t<step_size>0.1</step_size>')
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
out.append('\t\t<material id="1" name="BlockMat" type="neo-Hookean">')
out.append('\t\t\t<density>1</density>')
out.append('\t\t\t<E>10</E>')
out.append('\t\t\t<v>0.3</v>')
out.append('\t\t</material>')
out.append('\t</Material>')
out.append('\t<Mesh>')
out.append('\t\t<Nodes name="Block">')
for i, x, y, z in nodes:
    out.append(f'\t\t\t<node id="{i}">{x:g},{y:g},{z:g}</node>')
out.append('\t\t</Nodes>')
out.append('\t\t<Elements type="hex8" name="Block">')
for i, conn in elems:
    out.append(f'\t\t\t<elem id="{i}">' + ','.join(str(c) for c in conn) + '</elem>')
out.append('\t\t</Elements>')
out.append('\t\t<NodeSet name="Fixed">' + ','.join(str(n) for n in fixed) + '</NodeSet>')
out.append('\t\t<NodeSet name="Pulled">' + ','.join(str(n) for n in pulled) + '</NodeSet>')
out.append('\t</Mesh>')
out.append('\t<MeshDomains>')
out.append('\t\t<SolidDomain name="Block" mat="BlockMat"/>')
out.append('\t</MeshDomains>')
out.append('\t<Boundary>')
out.append('\t\t<bc name="FixLeft" type="zero displacement" node_set="Fixed">')
out.append('\t\t\t<x_dof>1</x_dof>')
out.append('\t\t\t<y_dof>1</y_dof>')
out.append('\t\t\t<z_dof>1</z_dof>')
out.append('\t\t</bc>')
out.append('\t\t<bc name="PullRight" type="prescribed displacement" node_set="Pulled">')
out.append('\t\t\t<dof>x</dof>')
out.append('\t\t\t<value lc="1">1.0</value>')
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

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Model', 'tension-block.feb')
with open(path, 'w') as f:
    f.write('\n'.join(out) + '\n')
print(f'wrote {path}: {len(nodes)} nodes, {len(elems)} elements')
