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


