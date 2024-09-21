"""
Skript zum Import und zur Platzierung von Bezier-Linien aus dem BezierAirfoilDesigner
https://github.com/marc-frank/BezierAirfoilDesigner/releases/tag/v0.9.7 von Marc Frank. Author bluenote79


Version in der es folgende Optionen gibt:
a) Einhängen über zwei Punkte wobei der zuerst gewählte die Nase vorgibt.
    - Optionale Angabe eines Bemaßungsparameters.
    - Spiegelung über Paramater invx* und invy* in den Favoriten.
    - * = zu vergebenes Parameter-suffix (nur Buchstaben). Doppelte Parameter gleichen Namens sind nicht zulässig.
b) Einhägen an einem Punkt von dem horizontal ausgerichtet wird.
    - Drehbar um den Punkt.
    - Wurzeltiefe nach eiggegebenem Parameter, sonst 100 mm.
    - * = zu vergebenes Parameter-suffix (nur Buchstaben). Doppelte Parameter gleichen Namens sind nicht zulässig.
c) Zeichnung vom Ursprung der xy-Ebene (kein Punkt).
    - Frei verschiebbar.
    - Wurzeltiefe nach eingegebenem Parameter, sonst 100.
    - * = zu vergebenes Parameter-suffix (nur Buchstaben).  Doppelte Parameter gleichen Namens sind nicht zulässig.

Wichtige Parameter finden sich unter den Favoriten:

root* = Wurzeltiefe
invx*, invy*: Spiegelungen
yoben*9, yunten*9 = Abstand der Punkte an der Endleiste von der Wurzellinie (ggf. neg. Vorzeichen benutzen).

* = suffix


"""

import adsk.core, adsk.fusion, adsk.cam, traceback
import re
import os

COMMAND_ID = "Airfoil"
SE01_SELECTION1_COMMAND_ID = "select nose points"
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
            try:
                sel0 = input1.selection(0)
                if  sel0.isValid == True:
                    nose = sel0.entity
            except:
                nose = 0
                pass

            try:
                sel1 = input1.selection(1) 
                if sel1.isValid == True:
                    tail = sel1.entity
            except:
                tail = 0
                pass
            
            input2 = inputs[1]
            input3 = inputs[2]

            foil = Foil()
            foil.Execute(nose, tail, input2.value, input3.value)
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
    def Execute(self, nose, tail, suf, param_drive):

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
            
            o = list(reversed(oben))
            u = list(reversed(unten))

            try:
                if 10 != len(oben) or 10 != len(unten):
                    pass
            except:
                ui.messageBox(
                    f'Splinedegree of the file does not match 9 (detected: top {len(oben)} points, bottom{len(unten)} points instead of 10')

            return o, unten

        dlg = ui.createFileDialog()
        dlg.title = 'Open bez.dat File'
        dlg.filter = 'Airfoil bez.dat files (*.dat);;All Files (*.*)'
        if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
            return

        filename = dlg.filename

        wurzeltiefe = 10   # Wird bei Bamaßung geändert, Units sind hier immer cm
        
        if nose != 0:
            sketchT = nose.parentSketch
            point_nose = nose
            halb_ausrichten = True
        else:
            sketchT = sketches.add(root.xYConstructionPlane)
            halb_ausrichten = False

        if tail != 0:
            point_tail = tail
            ausrichten = True
        else:
            ausrichten = False

        if ausrichten is True:
            line_sehne = sketchT.sketchCurves.sketchLines.addByTwoPoints(point_nose, point_tail)
            line_sehne.isConstruction = False
            wurzeltiefe = line_sehne.length
    
        if str(suf).isalpha() is False:
            ui.messageBox("suffix contains signs other than alphanum")
        else:
            pass

        linex = sketchT.sketchCurves.sketchLines.addByTwoPoints(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(100, 0, 0))
        linex.isConstruction = True
        linex.isFixed = True

        
        liney = sketchT.sketchCurves.sketchLines.addByTwoPoints(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(0, 1, 0))
        liney.isConstruction = True
        liney.isFixed = True

        def createParam(design, name, value, units, comment):
            userValue = adsk.core.ValueInput.createByReal(value)
            newParam = design.userParameters.add(name, userValue, units, comment)
            _user_parameters[name] = newParam

        dim = sketchT.sketchDimensions
        driver_name = "root" + str(suf)
        driver_val = wurzeltiefe

        controlPoints1 = []
        controlPoints2 = []

        # create "random" sketchPoints to get a degree 3 spline (api generates only 3 or 5 degree)
        p1 = adsk.core.Point3D.create(0.1, 1, 0)
        p2 = adsk.core.Point3D.create(0.33, 1.2, 0)
        p3 = adsk.core.Point3D.create(0.66, 1.2, 0)
        p4 = adsk.core.Point3D.create(0.1, 1, 0)

        p5 = adsk.core.Point3D.create(0.1, -1, 0)
        p6 = adsk.core.Point3D.create(0.33, -1.2, 0)
        p7 = adsk.core.Point3D.create(0.66, -1.2, 0)
        p8 = adsk.core.Point3D.create(0.1, -1, 0)

        controlPoints1.append(p1)
        controlPoints1.append(p2)
        controlPoints1.append(p3)
        controlPoints1.append(p4)

        controlPoints2.append(p5)
        controlPoints2.append(p6)
        controlPoints2.append(p7)
        controlPoints2.append(p8)

        # sketch curves
        curve1 = sketchT.sketchCurves.sketchControlPointSplines.add(controlPoints1, 3)
        curve2 = sketchT.sketchCurves.sketchControlPointSplines.add(controlPoints2, 3)

        # set curves to degree 9, this adds up to a sum of 10 points each
        curve1.degree = 9
        curve2.degree = 9

        coll1 = adsk.core.ObjectCollection.create()
        coll2 = adsk.core.ObjectCollection.create()
        coll3 = adsk.core.ObjectCollection.create()

        for i in range(len(controlPoints1)):
            coll1.add(controlPoints1[i])
            controlPoints1[i].isFixed = True
            coll3.add(controlPoints1[i])
            coll2.add(controlPoints2[i])
            coll3.add(controlPoints2[i])
            controlPoints2[i].isFixed = True
        
        createParam(design, driver_name, driver_val, "", "root" + str(suf))
        _user_parameters[driver_name].isFavorite = True
        createParam(design, "invx" + str(suf), 1, "", "switch to bottom")
        _user_parameters["invx" + str(suf)].isFavorite = True
        createParam(design, "invy" + str(suf), 1, "", "switch to bottom1")
        _user_parameters["invy" + str(suf)].isFavorite = True

        def create_parameters(data, side):
            name_collection = []
            
            for i in range(0, 10):
                x = "xdat" + str(side) + str(suf) + str(i)
                y = "ydat" + str(side) + str(suf) + str(i)
                px = float(data[i][0])
                py = float(data[i][1]) ############
                createParam(design, str(x), px, "mm", "")
                createParam(design, str(y), py, "mm", "")
                xc = "x" + str(side) + str(suf) + str(i)
                yc = "y" + str(side) + str(suf) + str(i)
                name_collection.append((xc, yc))
                pxc = float(data[i][0]) * driver_val
                pyc = float(data[i][1]) * driver_val
                createParam(design, str(xc), pxc, "mm", "")
                _user_parameters[str(xc)].expression = str(x) + " * root" + str(suf) + "*invy" + str(suf)
                createParam(design, str(yc), pyc, "mm", "")
                _user_parameters[str(yc)].expression = str(y) + "  * root" + str(suf) + "*invx" + str(suf)
                if i == 9:
                    _user_parameters[str(yc)].isFavorite = True

            return name_collection


        oben, unten = get_profile(filename)
        names_oben = create_parameters(oben, "oben")
        names_unten = create_parameters(unten, "unten")

        textPoint = adsk.core.Point3D.create(0, 1, 0)

        def dim_pointsx(coll, names):

            for i in range(0, 10):
                coll.controlPoints[i].isFixed = False
                dim.addOffsetDimension(liney, coll.controlPoints[i], textPoint, True)                 
                dim[-1].parameter.expression = _user_parameters[names[i][0]].name
                coll.controlPoints[i].isFixed = True
               
        def dim_pointsy(coll, names):

            for i in range(0, 10):
                coll.controlPoints[i].isFixed = False
                dim.addOffsetDimension(linex, coll.controlPoints[i], textPoint, True)
                dim[-1].parameter.expression = _user_parameters[names[i][1]].name

        dim_pointsx(curve2, names_unten)
        dim_pointsy(curve2, names_unten)
        dim_pointsx(curve1, names_oben)
        dim_pointsy(curve1, names_oben)

        linex.isFixed = False
        liney.isFixed = False

        sketchT.geometricConstraints.addCoincident(liney.startSketchPoint, curve1.controlFrameLines[0].startSketchPoint)
        sketchT.geometricConstraints.addCoincident(liney.endSketchPoint, curve1.controlFrameLines[0].endSketchPoint)

        liney.deleteMe

        sketchT.geometricConstraints.addCoincident(liney.startSketchPoint, linex.startSketchPoint)
        dim.addAngularDimension(linex, liney, textPoint, True)

        dim[-1].parameter.expression = "90 deg"
        
        if halb_ausrichten is True:
            sketchT.geometricConstraints.addCoincident(liney.startSketchPoint,point_nose)
        
        if ausrichten is True:
            dim.addDistanceDimension(linex.endSketchPoint, point_tail, 0, textPoint, True)
            dim[-1].value = 0
        
        if param_drive != "":
            _user_parameters[str(driver_name)].expression = str(param_drive) + " * 0.1 / mm"
            _user_parameters[str(driver_name)].isFavorite = True
            for parameter in design.allParameters:
                if parameter.name == str(param_drive):
                    parameter.isFavorite = True
 
        if ausrichten is False:
            if param_drive == "":
                dim.addDistanceDimension(linex.endSketchPoint, linex.startSketchPoint, 0, textPoint, True)
                dim[-1].value = 10
                dim[-1].parameter.name = "wurzeltiefe" + str(suf)
                for parameter in design.allParameters:
                    if parameter.name == "wurzeltiefe" + str(suf):
                        parameter.isFavorite = True
                        temp = "root" + str(suf)
                        _user_parameters[str(temp)].expression = "wurzeltiefe" + str(suf) + " * 0.1 / mm"
                        _user_parameters[str(temp)].isFavorite = False
            else:
                _user_parameters[str(driver_name)].expression = str(param_drive) + " * 0.1 / mm"
                _user_parameters[str(driver_name)].isFavorite = True
                for parameter in design.allParameters:
                    if parameter.name == str(param_drive):
                        parameter.isFavorite = True
                        dim.addDistanceDimension(linex.endSketchPoint, linex.startSketchPoint, 0, textPoint, True)
                        dim[-1].parameter.name = "wurzeltiefe" + str(suf)                     
                        for parameter in design.allParameters:
                            if parameter.name == "wurzeltiefe" + str(suf):
                                parameter.expression = str(param_drive) + "  / mm"

       
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

            i1 = inputs.addSelectionInput(SE01_SELECTION1_COMMAND_ID, SE01_SELECTION1_COMMAND_ID, "select points")
            i1.addSelectionFilter(adsk.core.SelectionCommandInput.SketchPoints)
            i1.setSelectionLimits(0, 2)
            i2 = inputs.addStringValueInput(ST02_INPUT_COMMAND_ID, ST02_INPUT_COMMAND_ID, "suffix")
            i3 = inputs.addStringValueInput(ST03_INPUT_COMMAND_ID, ST03_INPUT_COMMAND_ID, "")

            inst_text = """ <p><strong>Instructions:</strong></p> \
                            <p>Create sketch and select nose (first) and optional tail (second) point.</p> \
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
