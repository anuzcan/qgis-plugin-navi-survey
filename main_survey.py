import os

from PyQt5 import uic
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMessageBox

from qgis import utils
from qgis.core import Qgis, QgsApplication, QgsProject, QgsSettings, QgsMessageLog, QgsVectorLayer

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
		self.dock.buttonIni_plugin.clicked.connect(self.initPlugin)
		self.dock.setRotationButton.clicked.connect(self.rotationMap)
		self.dock.zoomInbutton.clicked.connect(self.zoomInMapCanvas)
		self.dock.zoomOutbutton.clicked.connect(self.zoomOutMapCanvas)
		self.dock.buttonSelectLayer.clicked.connect(self.SelectLayerSurvey)
		self.dock.buttonCreateLayer.clicked.connect(self.CreateLayerSurvey)
		self.dock.buttonGpsActive.clicked.connect(self.start_Read)
		self.dock.buttonGpsDesactive.clicked.connect(self.stop)
		self.dock.setVisualHelp.clicked.connect(self.visual)
		self.dock.buttonClose_plugin.clicked.connect(self.closePlugin)
		self.dock.meterFilter_edit.valueChanged.connect(self.valueChanged_Filter)
		self.dock.comboBox_Fix.currentIndexChanged.connect(self.select_fixMode)

		# Rellenar las opciones de captura
		fixMode = ["FIX","FLOAT","SINGLE"]
		self.dock.comboBox_Fix.addItems(fixMode)

		# Botones bloqueados inicialmente
		self.dock.setRotationButton.setEnabled(False)
		self.dock.setVisualHelp.setEnabled(False)
		self.dock.buttonGpsActive.setEnabled(False)
		self.dock.buttonGpsDesactive.setEnabled(False)
		self.dock.buttonSelectLayer.setEnabled(False)
        
		self.read_setting()                                     # Lee configuracion almacenada

		#Definicion de banderas
		self.flatPluginActive = False
		self.flatGPSactive = False
		self.flatRotationMap = False
		self.flatSurveyContinuos = False
		self.flatGuia = False
		self.layerActive = False
		self.firt_point = False

		#self.timer = QTimer()
		#self.timer.timeout.connect(self.funcion)
		#self.timer.start(1000)
		#self.timer.stop()

	def unload(self): 

		self.iface.removeToolBarIcon(self.action)
		del self.action

	def run(self):					# Iniciamos plugin en interfaz

		if self.flatPluginActive:
			self.closePlugin()
			self.flatPluginActive =False
		
		else:
			self.iface.addDockWidget( Qt.RightDockWidgetArea, self.dock )   # Agregamos panel a interface
			self.testSignal()
			self.flatPluginActive = True

	def initPlugin(self):

		self.testSignal()                                       # Se comprueba que se disponga de un dispositivo valido conectado

	def read_setting(self):                                     # Leer configuraciones almacenadas

		s = QgsSettings()
		indexFilter = s.value("plugin_navi/indexFilter", 0)
		self.dock.comboBox_Fix.setCurrentIndex(int(indexFilter))
		self.meterFilter = float( s.value("plugin_navi/meterFilter", 2) )
		self.dock.meterFilter_edit.setValue( self.meterFilter )         # El dato es almacenado como texto, y debe pasarce como un float

	def store_setting(self):                                    # Almacenar configuraciones al cerrar seccion
		
		s = QgsSettings()
		s.setValue("plugin_navi/indexFilter", self.dock.comboBox_Fix.currentIndex())
		s.setValue("plugin_navi/meterFilter", round( self.dock.meterFilter_edit.value(), 2 ))   # El dato en el control se ha de guardar como 2 cifras  

	def testSignal(self):                                       # Rutina comprobar GPS Correctamento conectado

		self.connectionList = QgsApplication.gpsConnectionRegistry().connectionList()
        
		if self.connectionList == []:                           # Si no se encuentra ningun dispositivo gps disponible
			utils.iface.messageBar().pushMessage("Error ","Dispositivo GPS no Conectado",level=Qgis.Critical,duration=3)
			self.flatGPSactive = False

		else:                                                   # Dispositivo gps detectado
			utils.iface.messageBar().pushMessage("OK ","Dispositivo GPS Encontrado",level=Qgis.Info,duration=3)

			self.rumbo = direction(clockwise=True)                  # Variable para procesar rumbo y distancias entre puntos
			self.guia_recorrido = guide(self.iface.mapCanvas())     # Manipulador de sistema de guia visual

			self.GPS = self.connectionList[0]                   # Identifica coneccion activa
			self.GPS.stateChanged.connect(self.status_changed)  # Conecta signal con recepcion de dato nuevo
			self.GPS.destroyed.connect(self.connectionLost)     # En caso de desconeccion dispara rutina

			self.dock.buttonIni_plugin.setEnabled(False)            
			self.dock.setRotationButton.setEnabled(True)        # Habilitamos rotacion de mapa                             
			self.dock.setVisualHelp.setEnabled(True)
            
			if self.layerActive == True:
				self.dock.buttonGpsActive.setEnabled(True)
				self.dock.buttonGpsDesactive.setEnabled(True)
				self.dock.buttonSelectLayer.setEnabled(False)
            
			else:
				self.dock.buttonSelectLayer.setEnabled(True)

			self.flatGPSactive = True
            
	def status_changed(self,gpsInfo):
        
		if self.GPS.status() == 3:                              # Si se recibe nueva ubicacion GPS

			now = gpsInfo.utcDateTime.currentDateTime().toString(Qt.TextDate)
			self.showFix( self.dock.lineEdit, gpsInfo.quality )
            
			#print(gpsInfo.vacc)

			if self.firt_point == False:                                      # condicional para evitar buche de primer dato
				self.rumbo.new_point(gpsInfo.longitude,gpsInfo.latitude)
				self.firt_point = True
            
			else:                                                   # Determinamos angulo y distacion con respecto al punto anterior
				angulo = self.rumbo.angle_to(gpsInfo.longitude,gpsInfo.latitude)
				distancia = self.rumbo.distance(gpsInfo.longitude,gpsInfo.latitude)
                
				if distancia >= self.meterFilter:                                           # Si la distancia es mayor a la minima establecida

					self.rumbo.new_point(gpsInfo.longitude,gpsInfo.latitude)  # Sustituimos ultimo punto

					if self.flatRotationMap == True:                                        # Rotamos Mapa si se encuentra activada
						utils.iface.mapCanvas().setRotation(360 - angulo)                   
                    
					if self.flatSurveyContinuos == True and gpsInfo.quality in self.fix:
						self.layerSurvey.add_point( now, gpsInfo.longitude, gpsInfo.latitude, gpsInfo.elevation, gpsInfo.quality, len(gpsInfo.satPrn))

					if self.flatGuia == True:                   # Rutina de guia visual del recorrido
						self.guia_recorrido.erase()             # borramos lineas anteriores
						self.guia_recorrido.paint(gpsInfo.longitude, gpsInfo.latitude, angulo)                
        
	def connectionLost(self):

		try:
			self.GPS.stateChanged.disconnect(self.status_changed)
		except:
			pass

		utils.iface.messageBar().pushMessage("Error ","Perdida Conexion",level=Qgis.Critical,duration=5)
		self.guia_recorrido.erase()
		self.firt_point = False
		self.flatGPSactive = False
        
		self.dock.buttonGpsActive.setEnabled(False)
		self.dock.buttonGpsDesactive.setEnabled(False)
		self.dock.setRotationButton.setEnabled(False)        # Habilitamos rotacion de mapa                             
		self.dock.buttonSelectLayer.setEnabled(False)
		self.dock.setVisualHelp.setEnabled(False)                                   
		self.dock.buttonIni_plugin.setEnabled(True)

	def valueChanged_Filter(self):
		self.meterFilter = round(self.dock.meterFilter_edit.value(),2)                  # tomamos valor de filtro de distancia configurado

	def select_fixMode(self):
		self.fix = self.set_filter( self.dock.comboBox_Fix.currentText() )  

	def SelectLayerSurvey(self):                                # Seleccionar capa para almacenar los puntos colectados

		# Creamos la instancia de capa a editar, pasando la capa seleccionada en el combo_box y el parametro minimo de calidad de resolucion de gps  
		self.layerSurvey = layerMake( QgsProject().instance().mapLayersByName(self.dock.mMapLayerComboBox.currentText())[0] )        
        
		if self.layerSurvey.validate_layer():                     # Comprobamos que la seleccion de la capa sea correcta
			if self.flatGPSactive:
				self.dock.buttonGpsActive.setEnabled(True)                                      # Habilitamos el inicio de captura
				self.dock.buttonGpsDesactive.setEnabled(True)
				self.dock.buttonSelectLayer.setEnabled(False)                                   # Deshabilitamos la seleccion de capa
				self.dock.buttonSelectLayer.setStyleSheet("QPushButton {background-color : orange;}")
				self.dock.buttonCreateLayer.setEnabled(False)

			self.firt_point = False
			self.layerActive = True

		else:                                                   # Fallo de configuracion de capa selecionada
			utils.iface.messageBar().pushMessage("Advertencia "," Capa selecionada no valida",level=Qgis.Warning,duration=5)

	def CreateLayerSurvey(self):
		datetime = QDateTime.currentDateTime().toString()
		datetime = datetime.split(" ")
		name = "Puntos_" + datetime[1] + "/" + datetime[2] + "/" + datetime[4] + "_" + datetime[3]
		mem_layer = QgsVectorLayer("Point?crs=epsg:3857",name,"memory")
		QgsProject.instance().addMapLayer(mem_layer)
		utils.iface.setActiveLayer(mem_layer)
    
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
			self.dock.comboBox_Fix.setEnabled(False)
			self.flatSurveyContinuos = True                 # Habilita la captura de puntos

		else:
			self.dock.buttonGpsActive.setStyleSheet("QPushButton{background-color : lightgrey;}")
			self.dock.buttonGpsActive.setText('Captura')
			self.dock.comboBox_Fix.setEnabled(True)
			self.flatSurveyContinuos = False                # Deshabilita la captura de puntos

	def stop(self):                                         # Rutina finalizacion captura de puntos

		self.dock.buttonGpsActive.setStyleSheet("QPushButton{background-color : lightgrey;}")
		self.dock.buttonGpsActive.setText('Captura')
		self.dock.buttonGpsActive.setEnabled(False)
		self.dock.buttonGpsDesactive.setEnabled(False)
		self.dock.buttonSelectLayer.setEnabled(True)
		self.dock.buttonSelectLayer.setStyleSheet("QPushButton {background-color : lightgrey;}")
		self.dock.comboBox_Fix.setEnabled(True)
		self.dock.buttonCreateLayer.setEnabled(True)
        
		self.flatSurveyContinuos = False                    # Deshabilita la captura de puntos

	def set_filter(self,Filter):

		if Filter == 'FIX':
			return [4]

		elif Filter == 'FLOAT':
			return [5,4]

		elif Filter == 'SINGLE':
			return [-1,1,5,4]

	def closePlugin(self):                                  # Rutina de finalizacion plugin
    
		self.stop()

		self.flatPluginActive =False
		self.firt_point = False                                   # Restablecer primer punto
        
		self.dock.buttonIni_plugin.setEnabled(True)
		self.dock.setRotationButton.setEnabled(False)
		self.dock.setVisualHelp.setEnabled(False)
		self.dock.buttonSelectLayer.setEnabled(False)

		if self.flatGPSactive:
			self.GPS.stateChanged.disconnect(self.status_changed)
			self.guia_recorrido.erase()
        
		self.store_setting()                                # Almacenar configuraciones
		self.dock.close()                                   # Cierra plugin
