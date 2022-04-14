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
	def __init__(self,layer, point_ID = 'survey'):
		
		self.layer_to_edit = layer
		self.count = 0

	def validate_layer(self):

		layer_type = self.layer_to_edit.geometryType()
		
		if layer_type == QgsWkbTypes.PointGeometry:
			
			layerEPSG = self.layer_to_edit.crs().authid()
			crsSrc = QgsCoordinateReferenceSystem("EPSG:4326")                      # WGS 84
			crsDest = QgsCoordinateReferenceSystem(layerEPSG)                       # WGS 84 a WGS de la capa seleccionada
				
			transformContext = QgsProject.instance().transformContext()             # Crear instancia de tranformacion
			self.xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)  # Crear formulario transformacion
				
			utils.iface.setActiveLayer(self.layer_to_edit)
			
			if self.layer_to_edit.dataProvider().fieldNameIndex("id") == 0 and self.layer_to_edit.dataProvider().fields().count() == 1:
				self.layer_to_edit.dataProvider().addAttributes([
					QgsField(name = "PointName", type = QVariant.String, typeName = "text", len = 20),
					QgsField(name = "DATE", type = QVariant.String, typeName = "text", len = 30), 
					QgsField(name = "LON", type = QVariant.Double, typeName = "double", len = 23, prec = 15),
					QgsField(name = "LAT", type = QVariant.Double, typeName = "double", len = 23, prec = 15),
					QgsField(name = "ALT", type = QVariant.Double, typeName = "double", len = 7, prec = 3),
					QgsField(name = "FIX_MODE", type = QVariant.String, typeName = "int", len = 6),
					QgsField(name = "SAT_N", type = QVariant.Int, typeName = "int", len = 2)])
				
				self.layer_to_edit.updateFields()
				self.layer_to_edit.commitChanges()
				return True

			elif self.layer_to_edit.dataProvider().fields().count() == 0:
				self.layer_to_edit.dataProvider().addAttributes([
					QgsField(name = "id", type = QVariant.Int, typeName = "int", len = 10),
					QgsField(name = "PointName", type = QVariant.String, typeName = "text", len = 20),
					QgsField(name = "DATE", type = QVariant.String, typeName = "text", len = 30), 
					QgsField(name = "LON", type = QVariant.Double, typeName = "double", len = 23, prec = 15),
					QgsField(name = "LAT", type = QVariant.Double, typeName = "double", len = 23, prec = 15),
					QgsField(name = "ALT", type = QVariant.Double, typeName = "double", len = 7, prec = 3),
					QgsField(name = "FIX_MODE", type = QVariant.String, typeName = "int", len = 6),
					QgsField(name = "SAT_N", type = QVariant.Int, typeName = "int", len = 2)])
				
				self.layer_to_edit.updateFields()
				self.layer_to_edit.commitChanges()
				return True

			elif self.layer_to_edit.dataProvider().fieldNameIndex("PointName") == 1 and self.layer_to_edit.dataProvider().fields().count() == 8:
				return True

			else:
				return False

		else:
			return False


	def add_point(self,date,x,y,alt,fix_mode,sat_n,name = 'survey'):
		
		pt1 = self.xform.transform(QgsPointXY(x, y))
		fet = QgsFeature()
		fet.setGeometry(QgsGeometry.fromPointXY(pt1))

		fet.setAttributes([self.count,name,date,pt1[0],pt1[1],alt,fix_mode,sat_n])
		
		self.layer_to_edit.startEditing()
		self.layer_to_edit.addFeatures([fet])
		self.layer_to_edit.commitChanges()
		
		utils.iface.mapCanvas().refresh()

		self.count += 1
	

class direction_tools:
	def __init__(self, mapCanvas):

		crsMap = QgsCoordinateReferenceSystem(mapCanvas.mapSettings().destinationCrs().authid())
		crsGps = QgsCoordinateReferenceSystem("EPSG:4326")          
		crsCalc = QgsCoordinateReferenceSystem("EPSG:3857")                       	# WGS 84 a WGS de la capa seleccionada

		transformContext = QgsProject.instance().transformContext()             # Crear instancia de tranformacion	
		
		self.gps_to_calc_transformCoord = QgsCoordinateTransform(crsGps, crsCalc, transformContext)  		# Crear formulario transformacion
		self.gps_to_map_transformCoord = QgsCoordinateTransform(crsGps, crsMap, transformContext)
		self.calc_to_map_transformCoord = QgsCoordinateTransform(crsCalc, crsMap, transformContext)
		
		self.r_polyline = QgsRubberBand(mapCanvas, False)					# False = a no poligono a dibujar
		self.r_polyline.setWidth(1)											# Se define grosor de la linea
		self.r_polyline.setColor( QColor(0, 100, 255) )						# Color de la linea
		
		self.point_list = [] 
		self.desplazamiento = 0

	def new_point(self, lon, lat, distance):
		pt = self.gps_to_calc_transformCoord.transform(QgsPointXY(lon, lat))
		
		index = len(self.point_list)

		if index == 0:
			self.point_list.insert(0,pt)
		
		else:
			if index >= 3:
				self.point_list.pop(len(self.point_list) - 1)

			pt0x, pt0y = self.point_list[0]
			self.desplazamiento = math.sqrt((pt[0] - pt0x)**2 + (pt[1] - pt0y)**2) # Calculamos la distancia entre el ultimo punto y el nuevo punto
			
			if self.desplazamiento >= distance:
				self.point_list.insert(0,pt)
				return 1
		return 0

	def angle_to(self):
		if len(self.point_list) > 1:
			pt0x, pt0y = self.point_list[0]
			pt1x, pt1y = self.point_list[1]

			Dx = pt0x - pt1x
			Dy = pt0y - pt1y

			angle = math.degrees(math.atan2(Dy, Dx))

			if angle < 0: angle = 360 - abs(angle)
			if angle >= 360: angle %= 360
			return angle
		else:
			return 0

	def angle_pos(self):
		if len(self.point_list) >=3:
			pt0, pt1, pt2 = self.point_list
			
			Dx1 = pt0[0] - pt1[0]
			Dy1 = pt0[1] - pt1[1]
			Dx2 = pt1[0] - pt2[0]
			Dy2 = pt1[1] - pt2[1]

			angle1 = math.degrees(math.atan2(Dy1, Dx1)) 
			angle2 = math.degrees(math.atan2(Dy2, Dx2)) 
			 
			if angle1 < 0: angle1 = 360 - abs(angle1)
			if angle2 < 0: angle2 = 360 - abs(angle2)
			
			angle = ((angle1 - angle2) + angle1)
			
			if angle < 0 : angle = 360 - abs(angle)
			if angle >= 360: angle %= 360
			return angle

		else:
			return 0
	
	def point_pos(self, point, distance, angle):
		theta_rad = math.radians(angle)
  
		return float(point[0] + distance * math.cos(theta_rad)), float(point[1] + distance * math.sin(theta_rad))

	def paint(self):
		if len(self.point_list) >=3:
			points = []
			pt0, pt1, pt2 = self.point_list	
			angle = self.angle_pos()
			distance = self.desplazamiento
		
			px_map, py_map = self.calc_to_map_transformCoord.transform(pt2)
			points.append(QgsPoint(px_map, py_map))

			px_map, py_map = self.calc_to_map_transformCoord.transform(pt1)
			points.append(QgsPoint(px_map, py_map))
			
			px_map, py_map = self.calc_to_map_transformCoord.transform(pt0)
			points.append(QgsPoint(px_map, py_map))
			
			x, y = self.point_pos(pt0, distance, angle)
	
			px_map, py_map = self.calc_to_map_transformCoord.transform(QgsPointXY(x, y))			
			points.append(QgsPoint(px_map, py_map))
			
			#x, y = self.point_pos([x,y], distance, rote)
			
			#px_map, py_map = self.calc_to_map_transformCoord.transform(QgsPointXY(x, y))			
			#points.append(QgsPoint(px_map, py_map))
	
			self.r_polyline.setToGeometry(QgsGeometry.fromPolyline(points), None)


	def erase(self):
		self.r_polyline.reset(QgsWkbTypes.LineGeometry)

	
