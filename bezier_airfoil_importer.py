"""
Skript zum Import und zur Platzierung von Bezier-Linien aus dem BezierAirfoilDesigner
https://github.com/marc-frank/BezierAirfoilDesigner/releases/tag/v0.9.7 von Marc Frank. Author bluenote79

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
    ui = app.userInterface

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
            foil.Execute(sel0, sel1, input3.value)
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

            for abschnitt in text.split("\n\n"):
                koordinaten = find_koord.findall(abschnitt)

                if not koordinaten:
                    continue

            oben = [[float(koordinaten[i][0]), float(koordinaten[i][1]), 0.0] for i in
                    range(0, int(0.5 * (len(koordinaten) + 1)))]
            unten = [[float(koordinaten[i][0]), float(koordinaten[i][1]), 0.0] for i in
                     range(int(0.5 * (len(koordinaten) - 1)), len(koordinaten))]

            try:
                if 10 != len(oben) or 10 != len(unten):
                    pass
            except:
                ui.messageBox(
                    f'Splinedegree of the file does not match 9 (detected: top {len(oben)} points, bottom{len(unten)} points instead of 10')

            return oben, unten

        dlg = ui.createFileDialog()
        dlg.title = 'Open bez.dat File'
        dlg.filter = 'Airfoil bez.dat files (*.dat);;All Files (*.*)'
        if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
            return

        filename = dlg.filename

        line_sehne = sel0.entity
        line_oben = sel1.entity

        # detect the orientation of the lines if they don't have coincident constraines
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

        midline = adsk.core.Vector3D.create(wurzeltiefe, 0, 0)
        midlineto = start.geometry.vectorTo(ende.geometry)
        midlinerotationMatrix = adsk.core.Matrix3D.create()
        midlinerotationMatrix.setToRotateTo(midline, midlineto, z_axe)

        sketchTest = line_sehne.parentSketch
        datei = os.path.basename(filename)
        sketchTest.name = f'{datei}_{round(endleiste_soll * 10, 2)}_mm tail_gap'

        pointplus = adsk.core.Point3D.create(1, 1, 0)
        pointminus = adsk.core.Point3D.create(1, -1, 0)
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
        if pointminusdist < pointplusdist:

            for i in range(len(bezoben)):
                bezoben[i][1] = -bezoben[i][1]
                bezunten[i][1] = -bezunten[i][1]
        else:
            pass



        coll = adsk.core.ObjectCollection.create()
        controlPoints1 = []
        controlPoints2 = []

        # create "random" sketchPoints to get a degree 3 spline (api generates only 3 or 5 degree)
        p1 = adsk.core.Point3D.create(1, 1, 0)
        p2 = adsk.core.Point3D.create(2, 2, 0)
        p3 = adsk.core.Point3D.create(3, 3, 0)
        p4 = adsk.core.Point3D.create(4, 4, 0)

        p5 = adsk.core.Point3D.create(2, -1, 0)
        p6 = adsk.core.Point3D.create(3, -2, 0)
        p7 = adsk.core.Point3D.create(4, -3, 0)
        p8 = adsk.core.Point3D.create(5, -4, 0)

        controlPoints1.append(p1)
        controlPoints1.append(p2)
        controlPoints1.append(p3)
        controlPoints1.append(p4)

        controlPoints2.append(p5)
        controlPoints2.append(p6)
        controlPoints2.append(p7)
        controlPoints2.append(p8)

        # sketch curves
        curve1 = sketchTest.sketchCurves.sketchControlPointSplines.add(controlPoints1, 3)
        curve2 = sketchTest.sketchCurves.sketchControlPointSplines.add(controlPoints2, 3)

        # set curves to degree 9, this adds up to a sum of 10 points each
        curve1.degree = 9
        curve2.degree = 9

        # vector to move nose to (1 | 1) and back to origin for not to get in conflict with the origin when using move function (caused some problems)
        point11 = adsk.core.Point3D.create(1, 1, 0)
        vector11 = adsk.core.Vector3D.create(1, 1, 0)
        to_orig = point11.vectorTo(adsk.core.Point3D.create(0, 0, 0))


        def move_function(curve, data):

            for p in range(len(curve.controlPoints)):  # 0

                point = curve.controlPoints[p]
                vector_m = adsk.core.Vector3D.create(data[p][0] * wurzeltiefe, data[p][1] * wurzeltiefe, 0.0)
                # find out the coordinates of the controlPoints and create vector to origi
                vector_p = adsk.core.Vector3D.create(-1 * point.geometry.x, -1 * point.geometry.y, 0)

                # avoid the origin because it creates constraints that will screw up the curves so move to x + 1 and y +1
                # one first, add the data from the bez.dat and than subtract the detected values then go to startingPoint
                # of the line
                point.move(vector11)
                point.move(vector_m)
                point.move(vector_p)
                point.move(to_orig)
                coll.add(point)

        move_function(curve1, bezoben)
        move_function(curve2, bezunten)

        sketchTest.move(coll, midlinerotationMatrix)
        sketchTest.move(coll, transform)

        for point in sketchTest.sketchPoints:
            point.isFixed = True

        # close tail if there is a gap
        lines = sketchTest.sketchCurves.sketchLines
        if endleiste_soll != 0:
            el = lines.addByTwoPoints(coll[0], coll[-1])


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

            i1 = inputs.addSelectionInput(SE01_SELECTION1_COMMAND_ID, SE01_SELECTION1_COMMAND_ID, "select line")
            i1.addSelectionFilter(adsk.core.SelectionCommandInput.SketchLines)
            i1.addSelectionFilter(adsk.core.SelectionCommandInput.SketchLines)
            i2 = inputs.addSelectionInput(SE02_SELECTION2_COMMAND_ID, SE02_SELECTION2_COMMAND_ID, "select line")
            i2.addSelectionFilter(adsk.core.SelectionCommandInput.SketchLines)
            i2.addSelectionFilter(adsk.core.SelectionCommandInput.SketchLines)
            i3 = inputs.addValueInput(IN01_INPUT1_COMMAND_ID, IN01_INPUT1_COMMAND_ID, "mm",
                                      adsk.core.ValueInput.createByReal(0.0))

            inst_text = """ <p><strong>Instructions:</strong></p> \
                            <p>Create sketch with two coincident lines at right angle.</p> \
                            <p>root line goes from nose to tail, perpendicular line leads to airfoil top.</p> \
                            <p>Select the tail gap size.</p> \
                            <p>Select degree 9 *.bez.dat generated with <a href="https://github.com/marc-frank/BezierAirfoilDesigner">BezierAirfoilDesigner</a> by M. Frank</p>
                        """

            instructions = inputs.addTextBoxCommandInput('errMessageUniqueID', 'Message', '', 10, True)
            instructions.isFullWidth = True
            instructions.formattedText = inst_text

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
            cmdDef = commandDefinitions.addButtonDefinition(COMMAND_ID, 'Creates Spline on selected Lines',
                                                            'Creates Spline on selected Lines')
        onCommandCreated = FoilCommandCreatedHandler()

        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)
        inputs = adsk.core.NamedValues.create()
        cmdDef.execute(inputs)
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
