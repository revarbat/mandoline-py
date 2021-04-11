all::	cube.gcode sphere.gcode 3DBenchy.gcode Voron_Design_Cube_v7.gcode xyzHollowCalibrationCubeV2.gcode

clean::
	rm -f *.gcode

%.gcode::	%.stl
	/usr/bin/python3 ../mandoline/__init__.py $<
		
