# Bezier Airfoil import

## This skript adds an airfoil from [Bezier Airfoil Designer](https://tooomm.github.io/github-release-stats/?username=Marc-Frank&repository=BezierAirfoilDesigner) by [Marc Frank](https://github.com/marc-frank) to Fusion 360 from dat.bez-file fitting to selected sketchlines.

**Install:**
1. In Fusion 360 go to Utilities > ADD-INS > Skripts and Add-Ins.
2. Create a new script (chose Script, Python and bezier_airfoil_importer as name)
3. Right click on the script > Open file location
4. Overwrite the bezier_airfoil_importer.py with the one from here.

**Usage:**
1. Make a sketch with two construction lines:
   - first line will go from the nose to the tail or the point right between the endpoints if the airfoil is not closed.
   - second lines starting point must be coincident to the first lines starting point.
   - lines must have perpendicular constraints
   - the coincidence shows the script where to put the nose, the second line directs towards the upper side of the airfoil
2. Start the skript and select the lines.
3. Click OK
4. Choose a degree 9 dat.bez from Bezier Airfoil Designer

##Version p2.

Different concept using parameters in Fusion:
3 Options.
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
