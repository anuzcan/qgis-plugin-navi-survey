import os

from PyQt5 import uic
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMessageBox

from qgis import utils
from qgis.core import Qgis, QgsApplication, QgsProject, QgsSettings

from .layerMake import layerMake, direction, guide

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
        self.dock.buttonGpsActive.clicked.connect(self.start_Read)
        self.dock.buttonGpsDesactive.clicked.connect(self.stop)
        self.dock.setVisualHelp.clicked.connect(self.visual)
        self.dock.buttonClose_plugin.clicked.connect(self.closePlugin)

        # Rellenar las opciones de captura
        select_fixMode = ["FIX","FLOAT","SINGLE"]
        self.dock.comboBox_Fix.addItems(select_fixMode)

        # Botones bloqueados inicialmente
        self.dock.buttonGpsActive.setEnabled(False)
        self.dock.buttonGpsDesactive.setEnabled(False)
        self.dock.setRotationButton.setEnabled(False)

        #Definicion de banderas
        self.device = False 
        self.flatRotationMap = False
        self.flatSurveyContinuos = False
        self.flatGuia = False
        self.i = True

        self.timer = QTimer()                                   # Timer usado para leer dispositivo cada segundo
        self.timer.timeout.connect(self.read_Device)

        self.timerDevice = QTimer()                             # Timer usado para esperar dispositivo se este perdio la conexion
        self.timerDevice.timeout.connect(self.testSignal)

        self.rumbo = direction(clockwise=True)                  # Variable para procesar rumbo y distancias entre puntos
        self.guia_recorrido = guide(self.iface.mapCanvas())     # Manipulador de sistema de guia visual

    def unload(self): 

        self.iface.removeToolBarIcon(self.action)
        del self.action

    def run(self):                                              # Iniciamos plugin en interfaz
        
        self.read_setting()                                     # Lee configuracion almacenada        
        self.testSignal()                                       # Se comprueba que se disponga de un dispositivo valido conectado
                    
        self.iface.addDockWidget( Qt.RightDockWidgetArea, self.dock )   # Agregamos panel a interface

    def read_setting(self):                                             # Leer configuraciones almacenadas

        s = QgsSettings()
        indexFilter = s.value("plugin_navi/indexFilter", 0)
        self.dock.comboBox_Fix.setCurrentIndex(int(indexFilter))
        self.meterFilter = float( s.value("plugin_navi/meterFilter", 2) )
        self.dock.meterFilter_edit.setValue( self.meterFilter )         # El dato es almacenado como texto, y debe pasarce como un float

    def store_setting(self):                                    # Almacenar configuraciones al cerrar seccion
        s = QgsSettings()
        s.setValue("plugin_navi/indexFilter", self.dock.comboBox_Fix.currentIndex())
        s.setValue("plugin_navi/meterFilter", round( self.dock.meterFilter_edit.value(), 2 ))   # El dato en el control se ha de guardar como 2 cifras  

    def SelectLayerSurvey(self):                                # Seleccionar capa para almacenar los puntos colectados

        # Creamos la instancia de capa a editar, pasando la capa seleccionada en el combo_box y el parametro minimo de calidad de resolucion de gps  
        self.layerSurvey = layerMake( QgsProject().instance().mapLayersByName(self.dock.mMapLayerComboBox.currentText())[0],
            filt = self.dock.comboBox_Fix.currentText() )        

        if self.layerSurvey.error == False:                     # Comprobamos que la seleccion de la capa sea correcta
            
            if self.device == True:                             # Comprobamos que este gps conectado
                self.meterFilter = round(self.dock.meterFilter_edit.value(),2)                  # tomamos valor de filtro de distancia configurado
                self.dock.buttonGpsActive.setEnabled(True)                                      # Habilitamos el inicio de captura
                self.dock.buttonSelectLayer.setEnabled(False)                                   # Deshabilitamos la seleccion de capa
                self.dock.buttonSelectLayer.setStyleSheet("QPushButton {background-color : orange;}")
                self.dock.comboBox_Fix.setEnabled(False)                                        # Deshabilitamos seleccionar tomo de solucion gps
        
        else:                                                   # Fallo de configuracion de capa selecionada
            utils.iface.messageBar().pushMessage("Advertencia "," Capa selecionada no valida",level=Qgis.Warning,duration=5)


    def testSignal(self):                                       # Rutina comprobar GPS Correctamento conectado

        self.connectionList = QgsApplication.gpsConnectionRegistry().connectionList()
        
        if self.connectionList == []:                           # Si no se encuentra ningun dispositivo gps disponible
            utils.iface.messageBar().pushMessage("Error ","Dispositivo GPS no Conectado",level=Qgis.Critical,duration=3)
            self.dock.setRotationButton.setEnabled(False)       # Desahabilita rotacion de mapa
            
            self.timerDevice.stop()
            self.timerDevice.start(10000)
            
            self.device = False
            return -1

        else:                                                   # Dispositivo gps detectado
            utils.iface.messageBar().pushMessage("OK ","Dispositivo GPS Encontrado",level=Qgis.Info,duration=3)
            self.timer.start(1000)                              # Iniciamos lectura de gps capa 1 seg
            self.timerDevice.stop()                             # Detenemos timer de busqueda de dispositivo
            self.device = True

            self.dock.setRotationButton.setEnabled(True)        # Habilitamos rotacion de mapa                             
            return 1

    def read_Device(self):                                      # Rutina captura y almacenamiento de punto en capa
        
        try:
            GPSInformation = self.connectionList[0].currentGPSInformation()
            now = GPSInformation.utcDateTime.currentDateTime().toString(Qt.TextDate)        # Extraer informacion fecha y hora UTC, calidad de resolucion
        
            self.showFix( self.dock.lineEdit, GPSInformation.quality )                  # Mostrar calidad de resolucion de informacion GPS

            if self.i == True:                                      # condicional para evitar buche de primer dato
                self.rumbo.new_point(GPSInformation.longitude,GPSInformation.latitude)
                self.i = False
            
            else:                                                   # Determinamos angulo y distacion con respecto al punto anterior
                angulo = self.rumbo.angle_to(GPSInformation.longitude,GPSInformation.latitude)
                distancia = self.rumbo.distance(GPSInformation.longitude,GPSInformation.latitude)

                if distancia >= self.meterFilter:                                           # Si la distancia es mayor a la minima establecida

                    self.rumbo.new_point(GPSInformation.longitude,GPSInformation.latitude)  # Sustituimos ultimo punto

                    if self.flatRotationMap == True:                                        # Rotamos Mapa si se encuentra activada
                        utils.iface.mapCanvas().setRotation(360 - angulo)                   
                    
                    if self.flatSurveyContinuos == True:                                    
                        self.layerSurvey.add_point( now,
                            GPSInformation.longitude,
                            GPSInformation.latitude,
                            GPSInformation.elevation,
                            GPSInformation.quality,
                            len(GPSInformation.satPrn)  )                                   # Almacenamos nuevo punto en la capa seleccionada si activada

                    if self.flatGuia == True:                   # Rutina de guia visual del recorrido

                        self.guia_recorrido.erase()             # borramos lineas anteriores
                        self.guia_recorrido.paint(GPSInformation.longitude, GPSInformation.latitude, angulo)

        except:                                                 # Si error al leer gps
            utils.iface.messageBar().pushMessage("Error ","Perdida Conexion",level=Qgis.Critical,duration=10)
            self.guia_recorrido.erase()
            
            self.timer.stop()                                   
            self.timerDevice.start(10000)
            return -1

        
    def zoomInMapCanvas(self):                              # Rutina acercar mapa
        utils.iface.mapCanvas().zoomByFactor(0.8)

    def zoomOutMapCanvas(self):                             # Rutina alejar mapa
        utils.iface.mapCanvas().zoomByFactor(1.2)
    
    def showFix(self, parent, fix):                         # Ayuda visual estado de calidad de los datos del gps

        if fix in [-1,1]:
            parent.setText('SINGLE')
            parent.setStyleSheet("background-color: rgb(255, 0, 0);color: rgb(255, 255, 255);")
        if fix in [5]:
            parent.setText('FLOAT')
            parent.setStyleSheet("background-color: rgb(255, 128, 0);color: rgb(255, 255, 255);")
        if fix in [4]:
            parent.setText('FIX')
            parent.setStyleSheet("background-color: rgb(0, 255, 0);color: rgb(255, 255, 255);")

    def rotationMap(self):                                  # Bandera para activar rotacion

        if self.flatRotationMap == False:
            self.dock.setRotationButton.setStyleSheet("QPushButton {background-color : green;}")
            self.flatRotationMap = True

        else:
            self.dock.setRotationButton.setStyleSheet("QPushButton{background-color : lightgrey;}")
            utils.iface.mapCanvas().setRotation(0)          # Restablecemos rotacion 0 del mapa
            self.flatRotationMap = False

    def visual(self):
        if self.flatGuia == False:
            self.dock.setVisualHelp.setStyleSheet("QPushButton {background-color : orange;}")
            self.flatGuia = True
        else:
            self.guia_recorrido.erase()
            self.dock.setVisualHelp.setStyleSheet("QPushButton {background-color : lightgrey;}")
            self.flatGuia = False

    def start_Read(self):                                   # Rutina inicializar toma de puntos

        if self.flatSurveyContinuos == False:
            self.dock.buttonGpsActive.setStyleSheet("QPushButton {background-color : red;}")
            self.dock.buttonGpsActive.setText('Detener')
            
            self.dock.buttonGpsDesactive.setEnabled(True)
            self.flatSurveyContinuos = True                 # Habilita la captura de puntos

        else:
            self.dock.buttonGpsActive.setStyleSheet("QPushButton{background-color : lightgrey;}")
            self.dock.buttonGpsActive.setText('Captura')
            
            self.flatSurveyContinuos = False                # Deshabilita la captura de puntos

    def stop(self):                                         # Rutina finalizacion captura de puntos

        self.dock.buttonGpsActive.setStyleSheet("QPushButton{background-color : lightgrey;}")
        self.dock.buttonGpsActive.setText('Captura')
        self.dock.buttonGpsActive.setEnabled(False)
        self.dock.buttonGpsDesactive.setEnabled(False)
        
        self.dock.buttonSelectLayer.setEnabled(True)
        self.dock.buttonSelectLayer.setStyleSheet("QPushButton {background-color : lightgrey;}")
        
        self.dock.comboBox_Fix.setEnabled(True)
        self.guia_recorrido.erase()
        self.flatSurveyContinuos = False                    # Deshabilita la captura de puntos

    def closePlugin(self):                                  # Rutina de finalizacion plugin

        if self.device == True:                             # Si dispositivo activo
            self.timer.stop()                               # Detener Timer
            self.i = True                                   # Restablecer primer punto

        else:
            self.timerDevice.stop()                         # Si dispositivo ausente desabilitar timer busqueda
        
        self.stop()
        self.store_setting()                                # Almacenar configuraciones
        self.dock.close()                                   # Cierra plugin