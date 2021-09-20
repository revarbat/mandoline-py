all::	cube.gcode sphere.gcode cube.off.gcode cube.obj.gcode cube.ply.gcode cube.3mf.gcode cube.3mfm.gcode cube.3mj.gcode \
   3DBenchy.gcode Voron_Design_Cube_v7.gcode xyzHollowCalibrationCubeV2.gcode 

clean::
	rm -f *.gcode

%.gcode::	%.stl
	/usr/bin/python3 ../mandoline/__init__.py $<

cube.off.gcode:	cube.off
	/usr/bin/python3 ../mandoline/__init__.py -o "$<.gcode" $< 

cube.obj.gcode:	cube.obj
	/usr/bin/python3 ../mandoline/__init__.py -o "$<.gcode" $< 

cube.amf.gcode:	cube.amf
	/usr/bin/python3 ../mandoline/__init__.py -o "$<.gcode" $< 

cube.ply.gcode:	cube.ply
	/usr/bin/python3 ../mandoline/__init__.py -o "$<.gcode" $< 

cube.3mf.gcode:	cube.3mf
	/usr/bin/python3 ../mandoline/__init__.py -o "$<.gcode" $< 

cube.3mfm.gcode:	cube.3mfm
	/usr/bin/python3 ../mandoline/__init__.py -o "$<.gcode" $< 

cube.3mj.gcode:	cube.3mj
	/usr/bin/python3 ../mandoline/__init__.py -o "$<.gcode" $< 

