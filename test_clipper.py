from math import *
from tkinter import *
import pyclipper

r = 200


master = Tk()
w = Canvas(master, width=r*6, height=r*4)
w.pack()

subjs = []
pco = pyclipper.PyclipperOffset(arc_tolerance=100)
for xoff in [0, int(r/0.45)]:
    subj = [
        (
            (r*(1+(sin(6*a*pi/180)-1)/3)*cos(a*pi/180)+r*2+xoff),
            (r*(1+(sin(6*a*pi/180)-1)/3)*sin(a*pi/180)+r*2)
        )
        for a in range(0, 360, 1)
    ]
    subj.append(subj[0])
    subjs.append(subj)
    subj = pyclipper.scale_to_clipper(subj, 1000)
    #pco.AddPath(subj, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)
    #pco.AddPath(subj, pyclipper.JT_SQUARE, pyclipper.ET_CLOSEDPOLYGON)
    pco.AddPath(subj, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)

solution = pco.Execute(-r/10*1000)
solution = pyclipper.scale_from_clipper(solution, 1000)

for path in subjs:
    w.create_line(path, fill="red", width=1)

for path in solution:
    path.append(path[0])
    w.create_line(path, fill="blue", width=1)

mainloop()

# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
