import os

#Importacion de librerias 
from PyQt5 import uic
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMessageBox

from qgis import utils
from qgis.core import Qgis, QgsApplication, QgsProject

#Importacion metodos
from .layerMake import layerMake, direction, point_pos, guide

def classFactory(iface):
    return Main_Plugin(iface)

class Main_Plugin:
    def __init__(self, iface):
        self.iface = iface
        
    def initGui(self):

        #Definir icono agregar al interfaz de Qgis
        path = os.path.dirname( os.path.abspath( __file__ ) )
        icon_path = os.path.join(path,"icon.png")
        self.action = QAction(QIcon(icon_path),"&Navegacion Herramienta",self.iface.mainWindow())
        self.iface.addToolBarIcon(self.action)
        self.action.triggered.connect(self.run)

        #Cargamos la interfaz grafica
        self.dock = uic.loadUi( os.path.join( path, "dock.ui" ) )
        
        # Creamos acciones para los botones y comandos
        self.dock.setRotationButton.clicked.connect(self.rotationMap)
        self.dock.zoomInbutton.clicked.connect(self.zoomInMapCanvas)
        self.dock.zoomOutbutton.clicked.connect(self.zoomOutMapCanvas)
        self.dock.buttonSelectLayer.clicked.connect(self.SelectLayerSurvey)
        self.dock.buttonGpsActive.clicked.connect(self.star_Read)

        #Definicion de banderas
        self.device = False 
        self.flatRotationMap = False
        self.flatSurveyContinuos = False
        self.i = True

    def unload(self): 
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def run(self): # Iniciamos plugin en interfaz
        
        self.device = self.testSignal() # Se comprueba que se disponga de un dispositivo valido conectado
        #self.guide = guide(self.iface.mapCanvas())
        #self.guide.paint()
        #self.guide.erase()

        self.timerDevice = QTimer()
        self.timerDevice.timeout.connect(self.testSignal)
        #self.timerDevice.start(1000)
        #self.timerDevice.stop()


        #Si dispositivo conectado, iniciamos contador de lectura de datos
        if self.device == True:

            self.timer = QTimer()
            self.timer.timeout.connect(self.read_Device)
            self.timer.start(1000)

            self.rumbo = direction(clockwise=True) # Variable para procesar rumbo y distancias entre puntos
        
        #Agregamos panel a interface
        self.iface.addDockWidget( Qt.RightDockWidgetArea, self.dock )

        # Bloquemos de botones
        self.dock.buttonGpsActive.setEnabled(False)
        self.dock.setRotationButton.setEnabled(False)


    def testSignal(self):  # Rutina comprobar GPS Correctamento conectado

        # Registro del GPS
        self.connectionList = QgsApplication.gpsConnectionRegistry().connectionList()
        
        if self.connectionList == []: # Si no se encuentra ningun dispositivo gps disponible
            utils.iface.messageBar().pushMessage("Error ","Dispositivo GPS no Conectado",level=Qgis.Critical,duration=3)
            return -1

        else:   # Dispositivo gps detectado
            utils.iface.messageBar().pushMessage("OK ","Dispositivo GPS Encontrado",level=Qgis.Info,duration=3)
            # Habilitamos rotacion del mapa
            self.dock.setRotationButton.setEnabled(True)
            return 1

    def SelectLayerSurvey(self): # Seleccionar capa para almacenar los puntos colectados

        # Creamos la instancia de capa a editar con la capa seleccionada en el combobox del panel
        self.layerSurvey = layerMake(
            QgsProject().instance().mapLayersByName(self.dock.mMapLayerComboBox.currentText())[0],filt = 'FLOAT')

        if self.layerSurvey.error == False: # si no hay error 
            utils.iface.messageBar().pushMessage("Correcto "," Capa valida",level=Qgis.Info,duration=5)
            
            if self.device == True:
                self.dock.buttonGpsActive.setEnabled(True) # Habilitamos el inicio de captura
            
        else:
            utils.iface.messageBar().pushMessage("Advertencia "," Capa selecionada no valida",level=Qgis.Warning,duration=5)


    def read_Device(self): # Rutina captura y almacenamiento de punto en capa
        
        try:
            GPSInformation = self.connectionList[0].currentGPSInformation()
        except:
            utils.iface.messageBar().pushMessage("Error ","Perdida Conexion",level=Qgis.Critical,duration=10)
            self.timer.stop()
            self.device = False
            return -1
        
        # Extraer informacion fecha y hora UTC, calidad de resolucion
        now = GPSInformation.utcDateTime.currentDateTime().toString(Qt.TextDate)
        quality = GPSInformation.quality
        date = now[22:]+'-'+now[5:8]+'-'+now[10:12]
        time = now[13:21]

        # Mostrar calidad de resolucion de informacion GPS
        self.showFix(self.dock.lineEdit,str(quality))

        
        if self.i == True: # condicional para evitar buche de primer dato
            self.rumbo.new_point(GPSInformation.longitude,GPSInformation.latitude)
            self.i = False
        
        else:
            # Determinamos angulo y distacion con respecto al punto anterior
            angulo = self.rumbo.angle_to(GPSInformation.longitude,GPSInformation.latitude)
            distancia = self.rumbo.distance(GPSInformation.longitude,GPSInformation.latitude)

            if distancia > 1:   # Si la distancia es mayor
                if self.flatRotationMap == True:
                    utils.iface.mapCanvas().setRotation(360 - angulo)
                    self.direc.new_point(GPSInformation.longitude,GPSInformation.latitude)
                
                if flatSurveyContinuos == True:
                    # Almacenamos nuevo punto en la capa seleccionada
                    self.layerSurvey.add_point(date,time,GPSInformation.longitude,GPSInformation.latitude,GPSInformation.elevation,quality,len(GPSInformation.satPrn))
                    

    def zoomInMapCanvas(self):
        utils.iface.mapCanvas().zoomByFactor(0.8)

    def zoomOutMapCanvas(self):
        utils.iface.mapCanvas().zoomByFactor(1.2)
    
    def showFix(self, parent, fix):

        if fix == "1":
            parent.setText('SINGLE')
            parent.setStyleSheet("background-color: rgb(255, 0, 0);color: rgb(255, 255, 255);")
        if fix == "5":
            parent.setText('FLOAT')
            parent.setStyleSheet("background-color: rgb(255, 128, 0);color: rgb(255, 255, 255);")
        if fix == "4":
            parent.setText('FIX')
            parent.setStyleSheet("background-color: rgb(0, 255, 0);color: rgb(255, 255, 255);")

    def rotationMap(self):

        if self.flatRotationMap == False:

            self.dock.setRotationButton.setStyleSheet("QPushButton {background-color : green;}")
            self.flatRotationMap = True

        else:
            self.dock.setRotationButton.setStyleSheet("QPushButton{background-color : lightgrey;}")
            self.flatRotationMap = False

    
    def star_Read(self):
                                                # Rutina inicializar toma de puntos
        if self.flatSurveyContinuos == False:
            self.dock.buttonGpsActive.setStyleSheet("QPushButton {background-color : red;}")
            self.dock.buttonGpsActive.setText('Detener')
            self.flatSurveyContinuos = True

        else:
            self.dock.buttonGpsActive.setStyleSheet("QPushButton{background-color : lightgrey;}")
            self.dock.buttonGpsActive.setText('Captura')
            self.flatSurveyContinuos = False
