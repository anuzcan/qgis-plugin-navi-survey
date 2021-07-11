import math 
from qgis import utils
from qgis.gui import QgsRubberBand
from qgis.core import (Qgis, 
    QgsProject, QgsWkbTypes, 
    QgsPointXY, QgsFeature, QgsGeometry, 
    QgsField, QgsCoordinateReferenceSystem, 
    QgsCoordinateTransform,
    QgsPoint)
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QColor


class layerMake:
	def __init__(self,layer, point_ID = 'survey', filt = 'SINGLE'):
		
		self.layer_to_edit = layer
		layer_type = self.layer_to_edit.geometryType()
		self.count = 0
		self.error = 1
		self.filterPoint = self.setfilter(filt)
		
		if layer_type == QgsWkbTypes.PointGeometry:
			layerEPSG = self.layer_to_edit.crs().authid()
			crsSrc = QgsCoordinateReferenceSystem("EPSG:4326")                      # WGS 84
			crsDest = QgsCoordinateReferenceSystem(layerEPSG)                       # WGS 84 a WGS de la capa seleccionada
				
			transformContext = QgsProject.instance().transformContext()             # Crear instancia de tranformacion
			self.xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)  # Crear formulario transformacion
				
			utils.iface.setActiveLayer(self.layer_to_edit)
			self.layer_to_edit.startEditing()

			if self.layer_to_edit.dataProvider().fieldNameIndex("id") == 0 and self.layer_to_edit.dataProvider().fields().count() == 1:
				self.layer_to_edit.dataProvider().addAttributes([
				QgsField(name = "PointName", type = QVariant.String, typeName = "text", len = 20),
				QgsField(name = "DATE", type = QVariant.String, typeName = "text", len = 30), 
	            QgsField(name = "LON", type = QVariant.Double, typeName = "double", len = 23, prec = 15),
	            QgsField(name = "LAT", type = QVariant.Double, typeName = "double", len = 23, prec = 15),
	            QgsField(name = "ALT", type = QVariant.Double, typeName = "double", len = 7, prec = 3),
	            QgsField(name = "FIX_MODE", type = QVariant.String, typeName = "int", len = 6),
	            QgsField(name = "SAT_N", type = QVariant.Int, typeName = "int", len = 2)])
				self.error = -1

			elif self.layer_to_edit.dataProvider().fields().count() == 0:
				self.layer_to_edit.dataProvider().addAttributes([
					QgsField(name = "id", type = QVariant.Int, typeName = "int", len = 10),
					QgsField(name = "PointName", type = QVariant.String, typeName = "text", len = 20),
					QgsField(name = "DATE", type = QVariant.String, typeName = "text", len = 30), 
	            	QgsField(name = "LON", type = QVariant.Double, typeName = "double", len = 23, prec = 15),
	            	QgsField(name = "LAT", type = QVariant.Double, typeName = "double", len = 23, prec = 15),
	            	QgsField(name = "ALT", type = QVariant.Double, typeName = "double", len = 7, prec = 3),
	            	QgsField(name = "FIX_MODE", type = QVariant.String, typeName = "text", len = 6),
	            	QgsField(name = "SAT_N", type = QVariant.Int, typeName = "int", len = 2)])
				self.error = -1

			elif self.layer_to_edit.dataProvider().fields().count() == 8:
				self.error = -1

			else:
				self.error = 1

			self.layer_to_edit.updateFields()
			self.layer_to_edit.commitChanges()			
		
		else:
			self.error = 1


	def add_point(self,date,x,y,alt,fix_mode,sat_n,name = 'survey'):
		
		if fix_mode in self.filterPoint:
			pt1 = self.xform.transform(QgsPointXY(x, y))
			fet = QgsFeature()
			fet.setGeometry(QgsGeometry.fromPointXY(pt1))

			fet.setAttributes([self.count,name,date,pt1[0],pt1[1],alt,fix_mode,sat_n])
		
			self.layer_to_edit.startEditing()
			self.layer_to_edit.addFeatures([fet])
			self.layer_to_edit.commitChanges()
		
			utils.iface.mapCanvas().refresh()

			self.count += 1
	

	def setfilter(self,Filter):

		if Filter == 'FIX':
			return [4]

		elif Filter == 'FLOAT':
			return [5,4]

		elif Filter == 'SINGLE':
			return [-1,1,5,4]

class direction:
	def __init__(self, rotation=0, clockwise=False):

		crsSrc = QgsCoordinateReferenceSystem("EPSG:4326")          
		crsDest = QgsCoordinateReferenceSystem("EPSG:3857")                       # WGS 84 a WGS de la capa seleccionada
		transformContext = QgsProject.instance().transformContext()             # Crear instancia de tranformacion
		self.xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)  # Crear formulario transformacion
		
		self.rotation = rotation
		self.clockwise = clockwise

	def new_point(self, lon, lat):
		self.pt1 = self.xform.transform(QgsPointXY(lon, lat))

	def distance(self, lon, lat):
		pt2 = self.xform.transform(QgsPointXY(lon, lat))
		distance = math.sqrt((pt2[0] - self.pt1[0])**2 + (pt2[1] - self.pt1[1])**2)
		return distance

	def angle_to(self, lon, lat):
		pt2 = self.xform.transform(QgsPointXY(lon, lat))

		if abs(self.rotation) > 360:
			self.rotation %= 360

		Dx = pt2[0] - self.pt1[0]
		Dy = pt2[1] - self.pt1[1]
		angle = math.degrees(math.atan2(Dx, Dy))

		if self.clockwise:
			angle -= self.rotation
			return angle if angle > 0 else angle + 360
		else:
			angle = (360 - angle if angle > 0 else -1 * angle) - self.rotation
			return angle if angle > 0 else angle + 360


class guide:
	def __init__(self,mapCanvas):

		crsSrc = QgsCoordinateReferenceSystem("EPSG:4326")          
		crsDest = QgsCoordinateReferenceSystem("EPSG:3857")                       	# WGS 84 a WGS de la capa seleccionada
		transformContext = QgsProject.instance().transformContext()             	# Crear instancia de tranformacion
		self.transformCoord = QgsCoordinateTransform(crsSrc, crsDest, transformContext)  		# Crear formulario transformacion
		self.invert_transformCoord = QgsCoordinateTransform(crsDest, crsSrc, transformContext)
		#print(mapCanvas.mapSettings().destinationCrs().authid()) 					# Imprime sistema de coordenadas de el lienzo de trabajo
		
		self.r_polyline = QgsRubberBand(mapCanvas, False)					# False = a no poligono a dibujar
		self.r_polyline.setWidth(2)											# Se define grosor de la linea
		self.r_polyline.setColor( QColor(0, 100, 255) )						# Color de la linea
	
	def paint(self, longitud, latitud, angulo):

		origen = self.transformCoord.transform(QgsPointXY(longitud, latitud))
		proyect_point = self.point_pos(origen,1,angulo,clockwise=True)

		destino = self.invert_transformCoord.transform(QgsPointXY(proyect_point[0],proyect_point[1]))
		points = [QgsPoint(longitud, latitud), QgsPoint(destino[0], destino[1])]
		
		self.r_polyline.setToGeometry(QgsGeometry.fromPolyline(points), None)

	def erase(self):
		self.r_polyline.reset(QgsWkbTypes.LineGeometry)

	def point_pos(self, origin, amplitude, angle, rotation=0, clockwise=False):
		if abs(rotation) > 360:
			rotation %= 360
		if clockwise:
			rotation *= -1
		if clockwise:
			angle -= rotation
			angle = angle if angle > 0 else angle + 360
		else:
			angle = (360 - angle if angle > 0 else -1 * angle) - rotation
			angle = angle if angle > 0 else angle + 360

		theta_rad = math.radians(angle)
		return float(origin[0] + amplitude * math.sin(theta_rad)), float(origin[1] + amplitude * math.cos(theta_rad))

		# https://stackoverrun.com/es/q/10271498
