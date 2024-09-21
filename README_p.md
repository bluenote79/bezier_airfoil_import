##Version -p: Different concept using parameters in Fusion:##

You have three options:
a) Place airfoil selecting two points from a sketch (first at nose, second at tail).
    - optional input of parameter for rootlength.
    - parameters in fusion for mirroring invx* und invy* under favorites.
    - * = unique suffix for all parameters nessessary (only letters allowed)
b) Place airfoil selecting one point (nose).
    - rotation around point possible
    - rootlength by parameter input or 100 mm
    - * = unique suffix for all parameters nessessary (only letters allowed)
c) Zeichnung vom Ursprung der xy-Ebene (kein Punkt).
    - movable in all directions
    - rootlength by parameter input or 100 mm
    - * = unique suffix for all parameters nessessary (only letters allowed)

Important parameters available under favorites in fusion 360:

root* = rootlength
invx*, invy*: mirrors
yoben*9, yunten*9 = distance of endpoints to rootline, alter to get a tail gap (in some scenarios negative values must be used).

* = suffix
