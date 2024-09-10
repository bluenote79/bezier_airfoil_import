"""
Skript zum Import und zur Platzierung von Bezier-Linien aus dem BezierAirfoilDesigner https://github.com/marc-frank/BezierAirfoilDesigner/releases/tag/v0.9.7 von Marc Frank.
Author bluenote79

"""



import adsk.core, adsk.fusion, adsk.cam, traceback
import re
import os

COMMAND_ID = "Airfoil"
SE01_SELECTION1_COMMAND_ID = "rootline"
SE02_SELECTION2_COMMAND_ID = "perpendicular line"
IN01_INPUT1_COMMAND_ID = "tail gap"


_handlers = []
ui = None
app = adsk.core.Application.get()
if app:
    ui  = app.userInterface

product = app.activeProduct
design = adsk.fusion.Design.cast(product)
root = design.rootComponent
sketches = root.sketches
planes = root.constructionPlanes


class FoilCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            command = args.firingEvent.sender
            inputs = command.commandInputs
          
            input1 = inputs[0]
            sel0 = input1.selection(0)
            input2 = inputs[1]
            sel1 = input2.selection(0)
            input3 = inputs[2]
          

            foil = Foil()
            foil.Execute(sel0, sel1, input3.value);
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class FoilCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            adsk.terminate()
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class Foil:
    def Execute(self, sel0, sel1, endleiste_soll):

        def get_profile(filename):
            with open(filename, encoding="utf-8") as a:
                text = a.read()

            # Koordinaten auslesen und zusammenfügen als Tupel
            muster = r"-?\d+\.\d{3,}"

            find_koord = re.compile(fr"^\s*({muster})\s*({muster})\s*$", flags=re.MULTILINE)

            abschnitte = []
            for abschnitt in text.split("\n\n"):  # nach zeilen teilen
                koordinaten = find_koord.findall(abschnitt)

                if not koordinaten:
                    continue

                # abschnitte.append([[float(x), float(y), 0.0] for x, y in koordinaten])

            oben = [[float(koordinaten[i][0]), float(koordinaten[i][1]), 0.0] for i in range(0, int(0.5 * (len(koordinaten) +1)))]
            unten = [[float(koordinaten[i][0]), float(koordinaten[i][1]), 0.0] for i in range(int(0.5 * (len(koordinaten) -1)), len(koordinaten))]

            return oben, unten
        

        dlg = ui.createFileDialog()
        dlg.title = 'Open bez.dat File'
        dlg.filter = 'Airfoil bez.dat files (*.dat);;All Files (*.*)'
        if dlg.showOpen() != adsk.core.DialogResults.DialogOK :
            return
        
        filename = dlg.filename
        
        line_sehne = sel0.entity
        line_oben = sel1.entity

        ss = app.measureManager.measureMinimumDistance(line_sehne.startSketchPoint, line_oben.startSketchPoint).value
        se = app.measureManager.measureMinimumDistance(line_sehne.startSketchPoint, line_oben.endSketchPoint).value
        ee = app.measureManager.measureMinimumDistance(line_sehne.endSketchPoint, line_oben.endSketchPoint).value
        es = app.measureManager.measureMinimumDistance(line_sehne.endSketchPoint, line_oben.startSketchPoint).value

        distances = [ss, se, ee, es]
        m_dist = min(distances)

        
        if line_sehne.startSketchPoint == line_oben.startSketchPoint or ss == m_dist:
                start = line_sehne.startSketchPoint
                ende = line_sehne.endSketchPoint
                start2 = line_oben.startSketchPoint
                ende2 = line_oben.endSketchPoint
        elif line_sehne.startSketchPoint == line_oben.endSketchPoint or se == m_dist:
                start = line_sehne.startSketchPoint
                ende = line_sehne.endSketchPoint
                start2 = line_oben.endSketchPoint
                ende2 = line_oben.startSketchPoint
        elif line_sehne.endSketchPoint == line_oben.endSketchPoint or ee == m_dist:
                start = line_sehne.endSketchPoint
                ende = line_sehne.startSketchPoint
                start2 = line_oben.endSketchPoint
                ende2 = line_oben.startSketchPoint
        elif line_sehne.endSketchPoint == line_oben.startSketchPoint or es == m_dist:
                start = line_sehne.endSketchPoint
                ende = line_sehne.startSketchPoint
                start2 = line_oben.startSketchPoint
                ende2 = line_oben.endSketchPoint
        
        wurzeltiefe = line_sehne.length

        vector = adsk.core.Vector3D.create(start.geometry.x, start.geometry.y)

        transform = adsk.core.Matrix3D.create()
        transform.translation = vector

        point_mid_el = adsk.core.Point3D.create(wurzeltiefe, 0.0, 0.0)
        point_mid_el.transformBy(transform)

        axes = root.constructionAxes
        axisInput = axes.createInput()
        axisInput.setByTwoPoints(start, ende)
        axes.add(axisInput)
        axisInput.setByTwoPoints(start2, ende2)
        axes.add(axisInput)

        x_axe = axes[0]
        x_dir = x_axe.geometry.direction
        y_axe = axes[1]
        y_dir = y_axe.geometry.direction
        z_axe = x_dir.crossProduct(y_dir)

        midline = start.geometry.vectorTo(point_mid_el)
        midlineto = start.geometry.vectorTo(ende.geometry) 
        midlinerotationMatrix = adsk.core.Matrix3D.create()
        midlinerotationMatrix.setToRotateTo(midline, midlineto, z_axe)

        sketchTest = line_sehne.parentSketch
        
        pointplus  = adsk.core.Point3D.create(1, 1, 0)
        pointminus  = adsk.core.Point3D.create(1, -1, 0)
        pointplus.transformBy(midlinerotationMatrix)
        pointplus.transformBy(transform)
        pointminus.transformBy(midlinerotationMatrix)
        pointminus.transformBy(transform)

        pointminusdist = app.measureManager.measureMinimumDistance(pointminus, ende2.geometry).value
        pointplusdist = app.measureManager.measureMinimumDistance(pointplus, ende2.geometry).value
        
        scaleMatrix = adsk.core.Matrix3D.create()
        scaleMatrix.setCell(0, 0, wurzeltiefe)
        scaleMatrix.setCell(1, 1, wurzeltiefe)
        
        bezoben, bezunten = get_profile(filename)

        def tail_gap(oben, unten, endleiste_soll):
            
            half = (endleiste_soll * 0.5) / wurzeltiefe

            oben[0][1] = half
            unten[-1][1] = -half

            return oben, unten
        
        bezoben, bezunten = tail_gap(bezoben, bezunten, endleiste_soll)

        # make sure upper side is oriented towards the side of the vertical line
        if  pointminusdist < pointplusdist:

            for i in range(len(bezoben)):
                bezoben[i][1] = -bezoben[i][1]
                bezunten[i][1] = -bezunten[i][1]
        else:
            pass

        sketchCurves = sketchTest.sketchCurves
        
        def draw_spline(points):

            knots = [0, 0, 0, 0]

            for i in range(1, len(points) -3):
                knots.append(i)
            
            knots = [*knots, knots[-1] + 1, knots[-1] + 1, knots[-1] + 1, knots[-1] + 1]

            # Create the arrays for the nurbs
            controlPoints=[]
            for p in points:
                point = adsk.core.Point3D.create(*p)
                point.transformBy(scaleMatrix)
                point.transformBy(midlinerotationMatrix)
                point.transformBy(transform)
                controlPoints.append(point)
                sketchTest.sketchPoints.add(point)    # optional - show our control points in the sketch

            return controlPoints, knots
       
        controlPoints, knots = draw_spline(bezoben)
        controlPoints2, knots2 = draw_spline(bezunten)

        nurbsCurve = adsk.core.NurbsCurve3D.createNonRational(controlPoints, 3, knots, False)
        sketchCurves.sketchFixedSplines.addByNurbsCurve(nurbsCurve)
        nurbsCurve2 = adsk.core.NurbsCurve3D.createNonRational(controlPoints2, 3, knots2, False)
        sketchCurves.sketchFixedSplines.addByNurbsCurve(nurbsCurve2)
       
        lines = sketchTest.sketchCurves.sketchLines
        
        if endleiste_soll != 0:
            lines.addByTwoPoints(controlPoints[0], controlPoints2[-1])
             

class FoilCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args: adsk.core.CommandEventArgs):
        try:

            onExecute = FoilCommandExecuteHandler()
            args.command.execute.add(onExecute)
            _handlers.append(onExecute)

            onDestroy = FoilCommandDestroyHandler()
            args.command.destroy.add(onDestroy)
            _handlers.append(onDestroy)

            inputs = args.command.commandInputs
      
            i1 = inputs.addSelectionInput(SE01_SELECTION1_COMMAND_ID, "Sehnenlinie", "select line")
            i1.addSelectionFilter(adsk.core.SelectionCommandInput.SketchLines)
            i1.addSelectionFilter(adsk.core.SelectionCommandInput.SketchLines)
            i2 = inputs.addSelectionInput(SE02_SELECTION2_COMMAND_ID, "ortogonale oben", "select line")
            i2.addSelectionFilter(adsk.core.SelectionCommandInput.SketchLines)
            i2.addSelectionFilter(adsk.core.SelectionCommandInput.SketchLines)
            i3 = inputs.addValueInput(IN01_INPUT1_COMMAND_ID, "Endleiste Dicke", "mm", adsk.core.ValueInput.createByReal(0.0))

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def run(context):
    try:
        
        if not design:
            ui.messageBox('No active Fusion design')
            return

        commandDefinitions = ui.commandDefinitions

        cmdDef = commandDefinitions.itemById(COMMAND_ID)
        if not cmdDef:
            cmdDef = commandDefinitions.addButtonDefinition(COMMAND_ID,'Creates Spline on selected Lines','Creates Spline on selected Lines')
        onCommandCreated = FoilCommandCreatedHandler()
        
        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)
        inputs = adsk.core.NamedValues.create()
        cmdDef.execute(inputs)
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

