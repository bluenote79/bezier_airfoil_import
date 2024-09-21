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
CH01_CHOICE_COMMAND_ID = "set lines to construction"
ST02_INPUT_COMMAND_ID = "suffix"
ST03_INPUT_COMMAND_ID = "driving dimension"

_handlers = []

_user_parameters = {}

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
            input4 = inputs[3]
            input5 = inputs[4]


            foil = Foil()
            foil.Execute(sel0, sel1, input3.value, input4.value, input5.value)
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
    def Execute(self, sel0, sel1, cleanup, suf, param_drive):

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

        if cleanup is True:
            
            line_sehne.isConstruction = True
            line_oben.isConstruction = True
        
        else:
            pass

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
        sketchTest.name = f'{datei}'

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

        
        # make sure upper side is oriented towards the side of the vertical line
        if pointminusdist < pointplusdist:

            for i in range(len(bezoben)):
                bezoben[i][1] = -bezoben[i][1]
                bezunten[i][1] = -bezunten[i][1]
        else:
            pass

        def createParam(design, name, value, units, comment):
            userValue = adsk.core.ValueInput.createByReal(value)
            newParam = design.userParameters.add(name, userValue, units, comment)
            _user_parameters[name] = newParam


        def createParamStr(design, name, value, units, comment):
            userValue = adsk.core.ValueInput.createByString(value)
            newParam = design.userParameters.add(name, userValue, units, comment)
            _user_parameters[name] = newParam


        wurzelname = "wurzelfaktor" + str(suf)
        createParam(design, wurzelname, wurzeltiefe, "mm", "wurzeltiefe")

        parameters = design.userParameters

        #profil_oben_x.add("punkteox", adsk.core.ValueInput.createByReal(1.75 * _user_parameters['wurzelfaktor'].value), 'mm', '')


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
                #vector_m = adsk.core.Vector3D.create(data[p][0], data[p][1], 0.0)     # * wurzeltiefe
                vector_m = adsk.core.Vector3D.create(data[p][0], data[p][1], 0.0)
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

      
        lines = sketchTest.sketchCurves.sketchLines
        
        x_axe.deleteMe()
        y_axe.deleteMe()


        dim = sketchTest.sketchDimensions
        
        constraints = sketchTest.geometricConstraints

        textPoint = adsk.core.Point3D.create(-10, 10, 0)

        dim = sketchTest.sketchDimensions

        
        def beschriftung(sketchLine, lr):
            
            sx = sketchLine.startSketchPoint.worldGeometry.x
            sy = sketchLine.startSketchPoint.worldGeometry.y
            sz = sketchLine.startSketchPoint.worldGeometry.z

            ex = sketchLine.endSketchPoint.worldGeometry.x
            ey = sketchLine.endSketchPoint.worldGeometry.y
            ez = sketchLine.endSketchPoint.worldGeometry.z
            
            if lr is True:
                if sx < ex:
                    ax = sx - 1
                else:
                    ax = ex - 1
                ay = (sy + ey) / 2
            else:
                ax = (sx + ex) / 2
                if sy < ey:
                    ay = sy - 1
                else:
                    ay = ey - 1
            
            az = (sz + ez) / 2  
            

            return adsk.core.Point3D.create(ax, ay, az)     
        

        def create_l(x1, y1, z1, x2, y2, z2, name):
            
            point1 = adsk.core.Point3D.create(x1, y1, z1)
            point2 = adsk.core.Point3D.create(x2, y2, z2)
            lines = sketchTest.sketchCurves.sketchLines
            name = lines.addByTwoPoints(point1, point2)
            name.isConstruction = True


        def create_bem(namex1, namey1, reihe, n):
            namex = str(namex1) + str(suf)
            namey = str(namey1) + str(suf)
            textPoint = beschriftung(line_sehne, False)
            parx = dim.addOffsetDimension(line_oben, coll[n], textPoint, True).value
            textPoint = beschriftung(line_sehne, True)
            pary = dim.addOffsetDimension(line_sehne, coll[n], textPoint, True).value
            createParam(design, namex, parx, "mm", "")
            createParam(design, namey, pary, "mm", "")
            xval = reihe[n][0]
            yval = reihe[n][1]

            exp1 = str(xval) + '* wurzelfaktor' + str(suf) + ' / mm'
            exp2 = str(yval) + '* wurzelfaktor' + str(suf) + ' / mm'
            _user_parameters[namex].expression = exp1
            _user_parameters[namey].expression = exp2
            dim[-2].parameter.expression = namex
            dim[-1].parameter.expression = namey


        def create_bem2(namex1, namey1, reihe, n):
            namex = str(namex1) + str(suf)
            namey = str(namey1) + str(suf)
            textPoint = beschriftung(line_sehne, False)
            parx = dim.addOffsetDimension(line_oben, coll[n+10], textPoint, True).value
            textPoint = beschriftung(line_sehne, True)
            pary = dim.addOffsetDimension(line_sehne, coll[n+10], textPoint, True).value
            createParam(design, namex, parx, "mm", "")
            createParam(design, namey, pary, "mm", "")
            xval = reihe[n][0]
            yval = reihe[n][1]

            exp1 = str(xval) + '*wurzelfaktor' + str(suf) + ' / mm'
            exp2 = str(yval) + '* -1 * wurzelfaktor' + str(suf) + ' / mm'    ## ggf hier -1 *
            _user_parameters[namex].expression = exp1
            _user_parameters[namey].expression = exp2
            dim[-2].parameter.expression = namex
            dim[-1].parameter.expression = namey



        for p in coll:
            p.isFixed = True

        coll[0].isFixed = False
        create_bem("xo0", "yo0_endleiste_oben", bezoben, 0)
        coll[1].isFixed = False
 
        create_bem("xo1", "yo1", bezoben, 1)
        coll[2].isFixed = False
        
        create_bem("xo2", "yo2", bezoben, 2)
        coll[3].isFixed = False
        create_bem("xo3", "yo3", bezoben, 3)
        coll[4].isFixed = False
        create_bem("xo4", "yo4", bezoben, 4)
        coll[5].isFixed = False
        create_bem("xo5", "yo5", bezoben, 5)
        coll[6].isFixed = False
        create_bem("xo6", "yo6", bezoben, 6)
        coll[7].isFixed = False
        create_bem("xo7", "yo7", bezoben, 7)
        coll[8].isFixed = False
        create_bem("xo8", "yo8", bezoben, 8)
        coll[9].isFixed = False
        create_bem("xo9", "yo9", bezoben, 9)
        
  
        # coll 19 und 0 = endleiste; 10 und 9 Nasenleiste
        coll[19].isFixed = False
        create_bem2("xu0", "yu0_endleiste_unten", bezunten, 9)
        coll[18].isFixed = False
        create_bem2("xu1", "yu1", bezunten, 8)
        coll[17].isFixed = False
        create_bem2("xu2", "yu2", bezunten, 7)
        coll[16].isFixed = False
        create_bem2("xu3", "yu3", bezunten, 6)
        coll[15].isFixed = False
        create_bem2("xu4", "yu4", bezunten, 5)
        coll[14].isFixed = False
        create_bem2("xu5", "yu5", bezunten, 4)
        coll[13].isFixed = False
        create_bem2("xu6", "yu6", bezunten, 3)
        coll[12].isFixed = False
        create_bem2("xu7", "yu7", bezunten, 2)
        coll[11].isFixed = False
        create_bem2("xu8", "yu8", bezunten, 1)
        coll[10].isFixed = False
        create_bem2("xu9", "yu9", bezunten, 0)

            
        if param_drive != "":

       
            _user_parameters['wurzelfaktor' + str(suf)].expression = param_drive

    




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
            i3 = inputs.addBoolValueInput(CH01_CHOICE_COMMAND_ID, CH01_CHOICE_COMMAND_ID, True, "", True)
            i4 = inputs.addStringValueInput(ST02_INPUT_COMMAND_ID, ST02_INPUT_COMMAND_ID, "suffix")
            i5 = inputs.addStringValueInput(ST03_INPUT_COMMAND_ID, ST03_INPUT_COMMAND_ID, "")





            inst_text = """ <p><strong>Instructions:</strong></p> \
                            <p>Create sketch with two coincident construction lines at right angle.</p> \
                            <p>root line goes from nose to tail, perpendicular line leads to airfoil top.</p> \
                            <p>put in a suffix (only letters)</p> \
                            <p>put in a driving parameter like d1 if you wish</p> \
                            <p>Select degree 9 *.bez.dat generated with <a href="https://github.com/marc-frank/BezierAirfoilDesigner">BezierAirfoilDesigner</a> by M. Frank</p>
                        """
            textinp = "suffix"
            instructions = inputs.addTextBoxCommandInput('errMessageUniqueID', 'Message', textinp, 10, True)
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
