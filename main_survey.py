import os

#Importacion de librerias 
from PyQt5 import uic
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMessageBox

from qgis import utils
from qgis.core import Qgis, QgsApplication, QgsProject


#Importacion metodos
from .layerMake import layerMake

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

        #Definicion de banderas 
        self.flatRotationMap = False

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def run(self):
        
        self.device = self.testSignal()
        
        #Si dispositivo conectado, iniciamos contador de lectura de datos
        if self.device == True:
            self.timer = QTimer()
            self.timer.timeout.connect(self.read_Device)
            self.timer.start(1000)

        #Agregamos panel a interface
        self.iface.addDockWidget( Qt.RightDockWidgetArea, self.dock )
        

    def testSignal(self):  # Rutina comprobar GPS Correctamento conectado

        # Registro del GPS
        self.connectionList = QgsApplication.gpsConnectionRegistry().connectionList()
        
        if self.connectionList == []:
            utils.iface.messageBar().pushMessage("Error ","Dispositivo GPS no Conectado",level=Qgis.Critical,duration=5)
            return -1

        else:
            utils.iface.messageBar().pushMessage("OK ","Dispositivo GPS Encontrado",level=Qgis.Info,duration=5)
            return 1

    def read_Device(self): # Rutina captura y almacenamiento de punto en capa
        
        try:
            GPSInformation = self.connectionList[0].currentGPSInformation()
        except:
            utils.iface.messageBar().pushMessage("Error ","Perdida Conexion",level=Qgis.Critical,duration=10)
            self.timer.stop()
            
        now = GPSInformation.utcDateTime.currentDateTime().toString(Qt.TextDate)
        self.showFix(self.dock.lineEdit,str(GPSInformation.quality))
    
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

    def SelectLayerSurvey(self):

        self.layerSurvey = layerMake(
            QgsProject().instance().mapLayersByName(self.dock.mMapLayerComboBox.currentText())[0])