# This code is modified sparingly from https://github.com/migurski/NokiaWebGL


from openframeworks import *

import os.path
from struct import unpack, pack
from math import log, pow, pi, ceil
from urlparse import urljoin
from urllib import urlopen

from ModestMaps.Geo import Location, MercatorProjection, deriveTransformation
from ModestMaps.Providers import IMapProvider
from ModestMaps.Core import Coordinate

def fromNokia(x, y, zoom):
	""" Return column, row, zoom for Nokia x, y, z.
	"""
	row = int(pow(2, zoom) - y - 1)
	col = x
	return col, row, zoom

def toNokia(col, row, zoom):
	""" Return x, y, z for Nokia tile column, row, zoom.
	"""
	x = col
	y = int(pow(2, zoom) - row - 1)
	return x, y, zoom

def coordinatePath(coord):
	"""
	"""
	x, y, z = toNokia(int(coord.column), int(coord.row), int(coord.zoom))

	#
	# maximum number of digits in row or column at this zoom
	# and a zero-padded string format for integers.
	#
	len = ceil(log(2 ** z) / log(10))
	fmt = '%%0%dd' % len

	row, col = fmt % y, fmt % x

	if len == 4:
		dir = '%s%s/%s%s' % (row[0:2], col[0:2], row[2:3], col[2:3])
	elif len == 5:
		dir = '%s%s/%s%s' % (row[0:2], col[0:2], row[2:4], col[2:4])
	elif len == 6:
		dir = '%s%s/%s%s/%s%s' % (row[0:2], col[0:2], row[2:4], col[2:4], row[4:5], col[4:5])
	else:
		raise BadZoom('len = %d unsupported' % len)

	return '%(z)d/%(dir)s/map_%(z)d_%(y)d_%(x)d' % locals()

def coordinateHeights(tile_coord):
	"""
	"""
	lut_coord = tile_coord.zoomTo(13).container() # height lookup tables exist only at z13
	server = 'bcde'[int(lut_coord.row + lut_coord.column + lut_coord.zoom) % 4]
	path = coordinatePath(lut_coord)

	url = 'http://%(server)s.maps3d.svc.nokia.com/data4/%(path)s.lut' % locals()

	data = urlopen(url).read()
	zoom = tile_coord.zoom - lut_coord.zoom

	#
	# Skip to the beginning of the correct zoom level in the mipmap
	#

	dim = 2**zoom, 2**zoom
	off = sum([0] + [4**i for i in range(zoom)])

	#
	# Skip to the correct row in the mipmap zoom level, but use the "col"
	# value because the data is actually stored on its side, west-up.
	#

	col = tile_coord.column - lut_coord.zoomTo(tile_coord.zoom).column
	off += int(col) * 2**zoom

	#
	# Skip to the correct column in the mipmap zoom level, but use the "row"
	# value because the data is actually stored on its side, west-up.
	#

	row = tile_coord.row - lut_coord.zoomTo(tile_coord.zoom).row
	off += 2**zoom - int(row + 1)

	#
	# Read bottom and top heights in meters.
	#

	bottom, top = unpack('<HH', data[off*4:off*4+4])

	return bottom, top

def extract_vertices(data, count, bottom, top):
	"""
	"""
	zxy_data, uv_data = data[:count*12], data[count*12:]

	zxy_values = [unpack('<fff', zxy_data[off:off+12]) for off in range(0, count*12, 12)]
	uv_values = [unpack('<ff', uv_data[off:off+8]) for off in range(0, count*8, 8)]

	scale = (top - bottom) / 2**16
	vertices = [(x/256, y/256, (bottom + scale*z)/256, u, v) for ((z, x, y), (u, v)) in zip(zxy_values, uv_values)]

	return vertices

def extract_faces(data, count):
	"""
	"""
	triangles = [unpack('<HHH', data[off:off+6]) for off in range(0, count*6, 6)]

	return triangles

def get_projection():
	''' Return the correct spherical mercator project for Nokia.
	'''
	# the spherical mercator world tile covers (-π, -π) to (π, π)
	t = deriveTransformation(-pi, pi, 0, 0, pi, pi, 1, 0, -pi, -pi, 0, 1)
	return MercatorProjection(0, t)

def get_tile_data(coord):
	"""
	"""
	server = 'bcde'[int(coord.row + coord.column + coord.zoom) % 4]
	path = coordinatePath(coord)

	url = 'http://%(server)s.maps3d.svc.nokia.com/data4/%(path)s.n3m' % locals()

	#
	# Attempt to load the data.
	#

	data = urlopen(url).read()

	if not data:
		return ()

	#
	# Lookup the bottom and top of the tile data in meters, and convert
	# that to a scale value for the raw z-axis based on current latitude.
	#
	proj = get_projection()

	lat_span = abs(proj.coordinateLocation(coord).lat - proj.coordinateLocation(coord.down()).lat)
	meter_span = 6378137 * pi * lat_span / 180.0

	bottom, top = coordinateHeights(coord)

	bottom, top = bottom * 2**16 / meter_span, top * 2**16 / meter_span

	#
	# Count the textures in the data.
	#

	(textures, ) = unpack('<i', data[4:8])

	#
	# Pick out the vertices for the geometry,
	# as lists of (x, y, z, u, v) coordinates.
	#

	off = 12
	vertex_blocks = [unpack('<ii', data[off:off+8]) for off in range(off, off + textures * 8, 8)]
	vertex_data = [extract_vertices(data[start:], count, bottom, top) for (start, count) in vertex_blocks]

	for i in range(textures):
		tex_info = [i, len(vertex_data[i])]
		tex_info += map(min, zip(*vertex_data[i]))
		tex_info += map(max, zip(*vertex_data[i]))

	#
	# Pick out the faces for each texture as triples of vertex indexes.
	#

	off = 12 + textures * 8
	face_blocks = [unpack('<ii', data[off:off+8]) for off in range(off, off + textures * 16, 16)]
	face_data = [extract_faces(data[start:], count) for (start, count) in face_blocks]


	for i in range(textures):
		face_info = [i, len(face_data[i])]
		face_info += map(min, zip(*face_data[i]))
		face_info += map(max, zip(*face_data[i]))

	#
	# Pick out the filenames of the JPEG textures,
	# stored as ASCII strings deeper in the file.
	#

	off = 12 + textures * 8
	bitmap_blocks = [unpack('<ii', data[off+8:off+16]) for off in range(off, off + textures * 16, 16)]
	imagename_blocks = [(start + 1, unpack('<B', data[start:start+1])[0]) for (index, start) in bitmap_blocks]
	image_names = [data[start:start+length] for (start, length) in imagename_blocks]
	image_urls = [urljoin(url, name) for name in image_names]

	#
	# Return a list of tuples, each with three items:
	# 1. list of vertices, (x, y, z, u, v)
	# 2. list of faces, 3-tuple of vertex indexes
	# 3. texture image URL
	#

	return zip(vertex_data, face_data, image_urls)

class BadZoom (Exception): pass


class MyApp(object):

	def __init__(self):
		pass

	def go(self):

		self.p = get_projection()

		# self.lat, self.lon = 37.804310, -122.271164
		# self.zoom = 16

		print self.lat, self.lon, self.zoom

		self.loc = Location(self.lat, self.lon)

		print self.loc

		self.coord = self.p.locationCoordinate(self.loc).zoomTo(self.zoom)

		print self.coord

		self.textures = get_tile_data(self.coord)

		#
		# Output .obj files and JPEGs locally.
		#

		if os.path.exists('../../../data/objs/LAT%d_LON%d_Z%d.obj' % (self.lat, self.lon, self.zoom)) == False:

			obj = open('../../../data/objs/LAT%d_LON%d_Z%d.obj' % (self.lat, self.lon, self.zoom), 'w')
			obj.write('o LAT%d_LON%d_Z%d\n' % (self.lat, self.lon, self.zoom))
			obj.write('\nmtllib LAT%d_LON%d_Z%d.mtl\n' % (self.lat, self.lon, self.zoom))

			mtl = open('../../../data/objs/LAT%d_LON%d_Z%d.mtl' % (self.lat, self.lon, self.zoom), 'w')

			lastnumvert = 1
			for (i, (vertices, faces, image_url)) in enumerate(self.textures):

				obj.write('\ng mesh%d =====================\n' % (i))
				obj.write('usemtl mtl%d' % (i))

				obj.write("\n# List of vertices (x y z)\n")
				for (x, y, z, u, v) in vertices:
					obj.write('v %.1f %.1f %.1f\n' % (x, y, z))

				obj.write("\n\n# List of texture coordinates (u v)\n")
				for (x, y, z, u, v) in vertices:
					obj.write('vt %.6f %.6f\n' % (u, v))

				obj.write("\n\n# List of face definitions\n")
				for (v0, v1, v2) in faces:
					obj.write('f %d/%d %d/%d %d/%d\n' % (v0+lastnumvert, v0+lastnumvert, v1+lastnumvert, v1+lastnumvert, v2+lastnumvert, v2+lastnumvert))
				lastnumvert += len(vertices)

				mtl.write("newmtl mtl%d\n" % (i))
				mtl.write("map_Ka LAT%d_LON%d_Z%d_%d.jpg\n"  % (self.lat, self.lon, self.zoom, i))
				mtl.write("map_Kd LAT%d_LON%d_Z%d_%d.jpg\n"  % (self.lat, self.lon, self.zoom, i))

				jpg = open('../../../data/objs/LAT%d_LON%d_Z%d_%d.jpg' % (self.lat, self.lon, self.zoom, i), 'w')
				jpg.write(urlopen(image_url).read())
				jpg.close()

			mtl.close()
			obj.close();

			print "SAVED"
		else:
			print "ALREADY EXISTS"
