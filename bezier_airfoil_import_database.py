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

Die Profildatenbank wird im Windows/Mac-Benutzerverzeichnis unter dem Namen airfoil_data.db

Wichtige Parameter finden sich unter den Favoriten:

root* = Wurzeltiefe
invx*, invy*: Spiegelungen
yoben*9, yunten*9 = Abstand der Punkte an der Endleiste von der Wurzellinie (ggf. neg. Vorzeichen benutzen).

* = suffix


"""

import adsk.core, adsk.fusion, adsk.cam, traceback
import sqlite3
import re
import os

COMMAND_ID = "Airfoil"

B1_BUTTON = "import"
B2_BUTTON = "delete"
D1_DROPDOWN = "Airfoils"

SE01_SELECTION1_COMMAND_ID = "optional points"
ST02_INPUT_COMMAND_ID = "unique suffix"
ST03_INPUT_COMMAND_ID = "driving dimension"

_handlers = []

_user_parameters = {}

ui = None
app = adsk.core.Application.get()
if app:
    ui = app.userInterface


DATABASE = os.path.join(os.environ['USERPROFILE'], 'airfoil_data.db')

try:
    DATABASE = os.path.join(os.environ['USERPROFILE'], 'airfoil_data.db')
except:
    home_directory = os.path.expanduser( '~' )
    DATABASE = os.path.join(home_directory, "airfoil_data.db" )


product = app.activeProduct
design = adsk.fusion.Design.cast(product)
root = design.rootComponent
sketches = root.sketches
planes = root.constructionPlanes

global foil_id
foil_id = ""


class FoilCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            command = args.firingEvent.sender
            inputs = command.commandInputs

            input1 = inputs[1]
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
            
            input2 = inputs[2]
            input3 = inputs[3]

            foil = Foil()
            foil.Execute(nose, tail, input2.value, input3.value)

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))



class FoilCommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        
        global foil_id
        
        try:
            eventArgs = adsk.core.InputChangedEventArgs.cast(args)
            inputs = eventArgs.inputs
            cmdInput = eventArgs.input

            # onInputChange for click Button
            if cmdInput.id == 'import':
                
                db = sqlDatabase(DATABASE)

                dlg = ui.createFileDialog()
                dlg.title = 'Open bez.dat File'
                dlg.filter = 'Airfoil bez.dat files (*.dat);;All Files (*.*)'
                if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
                    return

                filename = dlg.filename
                                
                def format_file_path(file_path):
                    abs_path = os.path.abspath(file_path)
                    return abs_path

                formatted_path = format_file_path(filename)
                db.create_airfoil_table()
                db.read_airfoil_from_bez(formatted_path)
    
                DROPDOWN_ITEMS: adsk.core.ListItems = eventArgs.inputs.itemById('Airfoils').listItems
                DROPDOWN_ITEMS.clear()

                airfoil_list = db.get_sorted_airfoils()
               
                for i in range(len(airfoil_list)):
                    #if airfoil_list[i] != "sqlite_sequence":
                    DROPDOWN_ITEMS.add(str(airfoil_list[i]), True, '')


            if cmdInput.id == 'Airfoils':
  
                objectItems = cmdInput.selectedItem
                foil_id = objectItems.name

            if cmdInput.id == 'delete':
                
                db = sqlDatabase(DATABASE)
                db.create_airfoil_table()
                db.delete_airfoil(foil_id)

                DROPDOWN_ITEMS: adsk.core.ListItems = eventArgs.inputs.itemById('Airfoils').listItems
                DROPDOWN_ITEMS.clear()
                
                airfoil_list = db.get_sorted_airfoils()
 
                for i in range(len(airfoil_list)):
                    DROPDOWN_ITEMS.add(str(airfoil_list[i]), True, '')
                
                if len(airfoil_list) == 0:
                    DROPDOWN_ITEMS.classType

        except:
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

       
        db = sqlDatabase(DATABASE)
        oben, unten = sqlDatabase.get_airfoil_coordinates(db, str(foil_id))
        #ui.messageBox(str(oben))

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

            global dropdown_items


            cmd = adsk.core.Command.cast(args.command)

            onExecute = FoilCommandExecuteHandler()
            args.command.execute.add(onExecute)
            _handlers.append(onExecute)

            onDestroy = FoilCommandDestroyHandler()
            args.command.destroy.add(onDestroy)
            _handlers.append(onDestroy)
        
            onInputChanged = FoilCommandInputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            _handlers.append(onInputChanged) 

            inputs = args.command.commandInputs

            tabCmdInput1 = inputs.addTabCommandInput('tab_1', 'Settings')
            tab1ChildInputs = tabCmdInput1.children

            i1 = tab1ChildInputs.addSelectionInput(SE01_SELECTION1_COMMAND_ID, SE01_SELECTION1_COMMAND_ID, "select points")
            i1.addSelectionFilter(adsk.core.SelectionCommandInput.SketchPoints)
            i1.setSelectionLimits(0, 2)
            i2 = tab1ChildInputs.addStringValueInput(ST02_INPUT_COMMAND_ID, ST02_INPUT_COMMAND_ID, "suffix")
            i3 = tab1ChildInputs.addStringValueInput(ST03_INPUT_COMMAND_ID, ST03_INPUT_COMMAND_ID, "")
            
            inst_text1 = ""
            tab1ChildInputs.addTextBoxCommandInput('fullWidth_textBox', '', inst_text1, 12, True)

            tabCmdInput2 = inputs.addTabCommandInput('tab_2', 'Database')
            tab2ChildInputs = tabCmdInput2.children
            
            tab2ChildInputs.addBoolValueInput(B1_BUTTON, B1_BUTTON, False, "", True)
            tab2ChildInputs.addBoolValueInput(B2_BUTTON, B2_BUTTON, False, "", True)

            dropdownInput = tab2ChildInputs.addDropDownCommandInput(D1_DROPDOWN, D1_DROPDOWN, adsk.core.DropDownStyles.TextListDropDownStyle)
            dropdown_items = dropdownInput.listItems
            dropdownInput.maxVisibleItems = 20
            dropdownInput.isFullWidth

            db = sqlDatabase(DATABASE)

            db.create_airfoil_table() 
            airfoil_list = db.get_sorted_airfoils()
           
            for i in range(len(airfoil_list)):
                dropdown_items.add(str(airfoil_list[i]), False, '')

            inst_text2 = ""
            tab2ChildInputs.addTextBoxCommandInput('fullWidth_textBox', '', inst_text2, 12, True)

            tabCmdInput3 = inputs.addTabCommandInput('tab_3', 'Info')
            tab3ChildInputs = tabCmdInput3.children
            
            inst_text3 = """ <br><p><strong>Instructions:</strong></p> \
                            <p>Create sketch and select nose (optional first point) and tail (optional second) point.</p> \
                            <p>put in a unique suffix (only letters)</p> \
                            <p>put in a driving parameter like d1 if you wish.</p> \
                            <p>Select degree 9 *.bez.dat (10 Points each side) generated with <a href="https://github.com/marc-frank/BezierAirfoilDesigner">BezierAirfoilDesigner</a> by M. Frank from Database</p>
                        """
            tab3ChildInputs.addTextBoxCommandInput('fullWidth_textBox', '', inst_text3, 18, True)

            textinp = "suffix"

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def run(context):
    try:

        commandDefinitions = ui.commandDefinitions

        cmdDef = ui.commandDefinitions.itemById(COMMAND_ID)
        if not cmdDef:
            cmdDef = ui.commandDefinitions.addButtonDefinition(COMMAND_ID, 'Bezier Airfoil Import', 'Bezier Airfoil Import')
        onCommandCreated = FoilCommandCreatedHandler()

        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)

        db = sqlDatabase(DATABASE)
        db.create_airfoil_table()
        
        cmdDef.execute()
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class sqlDatabase:
    def __init__(self, db):
        # Initialisiert die Datenbankverbindung und speichert den Pfad zur Datenbank
        self.db = db
        self.conn = sqlite3.connect(self.db)

    def create_airfoil_table(self):
        try:
            c = self.conn.cursor()
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS airfoil_data (
                    airfoil_name TEXT PRIMARY KEY,
                    x1 REAL, y1 REAL,
                    x2 REAL, y2 REAL,
                    x3 REAL, y3 REAL,
                    x4 REAL, y4 REAL,
                    x5 REAL, y5 REAL,
                    x6 REAL, y6 REAL,
                    x7 REAL, y7 REAL,
                    x8 REAL, y8 REAL,
                    x9 REAL, y9 REAL,
                    x10 REAL, y10 REAL,
                    x11 REAL, y11 REAL,
                    x12 REAL, y12 REAL,
                    x13 REAL, y13 REAL,
                    x14 REAL, y14 REAL,
                    x15 REAL, y15 REAL,
                    x16 REAL, y16 REAL,
                    x17 REAL, y17 REAL,
                    x18 REAL, y18 REAL,
                    x19 REAL, y19 REAL
                )
            ''')

            self.conn.commit()
            #print("Tabelle 'airfoil_data' erfolgreich erstellt.")

        except sqlite3.Error as e:
            print(f"Fehler beim Erstellen der Tabelle: {e}")

    def read_airfoil_from_bez(self, file_path):
            try:
                with open(file_path, 'r') as file:
                    lines = file.readlines()
                    
                    airfoil_name = lines[0].strip()
                    
                    coordinates = []
                    for line in lines[1:20]:
                        x, y = map(float, line.split())
                        coordinates.append((x, y))
                    
                    self.insert_or_update_airfoil(airfoil_name, coordinates)
            except FileNotFoundError:
                print(f"Die Datei {file_path} wurde nicht gefunden.")
            except Exception as e:
                print(f"Fehler beim Lesen der Datei '{file_path}': {e}")


    def insert_or_update_airfoil(self, airfoil_name, coordinates):
        try:
            c = self.conn.cursor()

            c.execute('SELECT COUNT(*) FROM airfoil_data WHERE airfoil_name = ?', (airfoil_name,))
            exists = c.fetchone()[0] > 0

            flat_coordinates = [coord for pair in coordinates for coord in pair]

            if exists:
                update_query = f'''
                    UPDATE airfoil_data
                    SET {", ".join([f"x{i + 1} = ?, y{i + 1} = ?" for i in range(len(coordinates))])}
                    WHERE airfoil_name = ?
                '''
                c.execute(update_query, (*flat_coordinates, airfoil_name))
                print(f"Koordinaten für '{airfoil_name}' erfolgreich aktualisiert.")
            else:
                insert_query = f'''
                    INSERT INTO airfoil_data (
                        airfoil_name, {", ".join([f"x{i + 1}, y{i + 1}" for i in range(len(coordinates))])}
                    ) VALUES (?, {", ".join(["?"] * (len(coordinates) * 2))})
                '''
                c.execute(insert_query, (airfoil_name, *flat_coordinates))
                print(f"Koordinaten für '{airfoil_name}' erfolgreich eingefügt.")

            self.conn.commit()

        except sqlite3.Error as e:
            print(f"Fehler beim Verarbeiten des Airfoils '{airfoil_name}': {e}")

    def get_airfoil_coordinates(self, airfoil_name):
        try:
            c = self.conn.cursor()

            c.execute(f'''
                SELECT x1, y1, x2, y2, x3, y3, x4, y4, x5, y5, 
                       x6, y6, x7, y7, x8, y8, x9, y9, x10, y10,
                       x11, y11, x12, y12, x13, y13, x14, y14, 
                       x15, y15, x16, y16, x17, y17, x18, y18, x19, y19 
                FROM airfoil_data
                WHERE airfoil_name = ?
            ''', (airfoil_name,))

            result = c.fetchone()
            if result:

                coordinates = [(result[i], result[i + 1]) for i in range(0, len(result), 2)]

                top = coordinates[:10]
                bottom = coordinates[9:]
                top_r = list(reversed(top))

                return top_r, bottom
            else:
                print(f"Airfoil '{airfoil_name}' nicht gefunden.")
                return None, None

        except sqlite3.Error as e:
            print(f"Fehler beim Abrufen der Koordinaten für '{airfoil_name}': {e}")
            return None, None

    def get_sorted_airfoils(self):
        try:
            c = self.conn.cursor()
            c.execute('SELECT airfoil_name FROM airfoil_data ORDER BY LOWER(airfoil_name) ASC')
            airfoil_names = [row[0] for row in c.fetchall()]
            return airfoil_names
        except sqlite3.Error as e:
            print(f"Fehler beim Abrufen der sortierten Airfoils: {e}")
            return []

    def delete_airfoil(self, airfoil_name):
        try:
            c = self.conn.cursor()
            c.execute('DELETE FROM airfoil_data WHERE airfoil_name = ?', (airfoil_name,))
            self.conn.commit()
            print(f"Airfoil '{airfoil_name}' erfolgreich gelöscht.")

        except sqlite3.Error as e:
            print(f"Fehler beim Löschen des Airfoils '{airfoil_name}': {e}")

    def close(self):
        self.conn.close()
        print("Datenbankverbindung geschlossen.")
