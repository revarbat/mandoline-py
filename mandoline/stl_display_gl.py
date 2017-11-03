import math

from pyquaternion import Quaternion

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    from OpenGL.GLUT import *
except:
    print(''' Error PyOpenGL not installed properly !!''')
    sys.exit(  )


class StlDisplayGL(object):
    """Class to read, write, and validate STL file data."""

    def __init__(self, stl_data):
        """Initialize with empty data set."""
        self.stl_data = stl_data
        self.wireframe = False
        self.show_facets = True
        self.perspective = True
        self.boundsrad = 1.0
        self.cx, self.cy, self.cz = 0.0, 0.0, 0.0
        self.width, self.height = 800, 600
        self._xstart, self._ystart = 0, 0
        self._model_list = None
        self._errs_list = None
        self._grid_list = None
        self._mouse_btn = GLUT_LEFT_BUTTON
        self._mouse_state = GLUT_UP
        self._action = None
        self.reset_view()

    def reset_view(self):
        self._view_q = Quaternion(axis=[0, 0, 1], degrees=25)
        self._view_q *= Quaternion(axis=[1, 0, 0], degrees=55)
        self._xtrans, self._ytrans= 0.0, 0.0
        self._zoom = 1.0

    def _gl_set_color(self, side, color, shininess=0.33):
        glMaterialfv(side, GL_AMBIENT_AND_DIFFUSE, color)
        glMaterialfv(side, GL_SPECULAR, color)
        glMaterialf(side, GL_SHININESS, int(127*shininess))
        glColor4fv(color)

    def _draw_backdrop(self):
        if self._grid_list:
            return

        xcm = int(math.ceil((self.stl_data.points.maxx - self.stl_data.points.minx) / 10.0)+2)
        ycm = int(math.ceil((self.stl_data.points.maxy - self.stl_data.points.miny) / 10.0)+2)
        zcm = int(math.ceil((self.stl_data.points.maxz - self.stl_data.points.minz) / 10.0)+2)
        zmin = self.cz - ((self.stl_data.points.maxz - self.stl_data.points.minz) / 2.0)
        ox = self.cx - xcm/2.0 * 10
        oy = self.cy - ycm/2.0 * 10

        self._grid_list = glGenLists(1)
        glNewList(self._grid_list, GL_COMPILE)

        glDisable(GL_CULL_FACE)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);

        # Draw reference axes
        glLineWidth(2.0)
        self._gl_set_color(GL_FRONT_AND_BACK, [0.0, 0.0, 0.0, 1.0], shininess=0.0)
        glBegin(GL_LINES)
        glVertex3fv([ox, oy, zmin])
        glVertex3fv([ox + 10, oy, zmin])
        glEnd()
        glBegin(GL_LINES)
        glVertex3fv([ox, oy, zmin])
        glVertex3fv([ox, oy + 10, zmin])
        glEnd()
        glBegin(GL_LINES)
        glVertex3fv([ox, oy, zmin])
        glVertex3fv([ox, oy, zmin+10])
        glEnd()

        # Draw dark squares of 1cm build plate grid
        self._gl_set_color(GL_FRONT_AND_BACK, [0.2, 0.2, 0.7, 0.3], shininess=0.75)
        for gx in range(xcm):
            for gy in range(ycm):
                if (gx + gy) % 2 == 0:
                    continue
                x1 = ox + gx * 10
                y1 = oy + gy * 10
                x2 = x1 + 10
                y2 = y1 + 10
                glBegin(GL_POLYGON)
                glVertex3fv([x1, y1, zmin-0.1])
                glVertex3fv([x2, y1, zmin-0.1])
                glVertex3fv([x2, y2, zmin-0.1])
                glVertex3fv([x1, y2, zmin-0.1])
                glEnd()

        # Draw light squares of 1cm build plate grid
        self._gl_set_color(GL_FRONT_AND_BACK, [0.5, 0.5, 0.9, 0.3], shininess=0.75)
        for gx in range(xcm):
            for gy in range(ycm):
                if (gx + gy) % 2 != 0:
                    continue
                x1 = ox + gx * 10
                y1 = oy + gy * 10
                x2 = x1 + 10
                y2 = y1 + 10
                glBegin(GL_POLYGON)
                glVertex3fv([x1, y1, zmin-0.1])
                glVertex3fv([x2, y1, zmin-0.1])
                glVertex3fv([x2, y2, zmin-0.1])
                glVertex3fv([x1, y2, zmin-0.1])
                glEnd()

        glEndList()

    def _draw_model(self):
        if self._model_list:
            return
        # Draw model facets.
        cp = (self.cx, self.cy, self.cz)
        self._model_list = glGenLists(1)
        glNewList(self._model_list, GL_COMPILE)
        for facet in self.stl_data.get_facets():
            if facet.count == 1:
                glBegin(GL_POLYGON)
                glNormal3fv(tuple(facet.norm))
                for vertex in facet.vertices:
                    glVertex3fv(tuple(vertex-cp))
                glEnd()
        glEndList()

    def _draw_errors(self):
        if self._errs_list:
            return

        self._errs_list = glGenLists(1)
        glNewList(self._errs_list, GL_COMPILE)

        # Draw error facets.
        cp = (self.cx, self.cy, self.cz)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        self._gl_set_color(GL_FRONT_AND_BACK, [1.0, 0.5, 0.5, 1.0], shininess=0.0)
        for facet in self.stl_data.get_facets():
            if facet.count != 1:
                glBegin(GL_POLYGON)
                glNormal3fv(tuple(facet.norm))
                for vertex in facet.vertices:
                    glVertex3fv(tuple(vertex-cp))
                glEnd()
        for facet in self.stl_data.get_facets():
            if facet.count != 1:
                glBegin(GL_POLYGON)
                glNormal3fv([-x for x in facet.norm])
                for vertex in reversed(facet.vertices):
                    glVertex3fv(tuple(vertex-cp))
                glEnd()

        # draw error facet edges.
        glLineWidth(4.0)
        self._gl_set_color(GL_FRONT_AND_BACK, [0.8, 0.0, 0.0, 1.0], shininess=0.0)
        for edge in self.stl_data.get_edges():
            if edge.count != 2:
                # Draw bad edges in a highlighted color.
                glBegin(GL_LINES)
                for vertex in edge:
                    glVertex3fv(tuple(vertex-cp))
                glEnd()
        glEndList()

    def _gl_display(self):
        #gluLookAt(0, 0, 4.0 * self.boundsrad / self._zoom,  0, 0, 0,  0, 1, 0)

        glClearColor(0.6, 0.6, 0.6, 0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glPushMatrix()
        glTranslate(self._xtrans, self._ytrans, 0)
        scalefac = self._zoom * (1.0 if self.perspective else 1.333)
        glScale(scalefac, scalefac, scalefac)
        glMultMatrixd(self._view_q.transformation_matrix.reshape(16))

        self._draw_model()
        self._draw_errors()
        self._draw_backdrop()

        if not self.wireframe:
            glLineWidth(1.0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            self._gl_set_color(GL_FRONT, [0.2, 0.5, 0.2, 1.0], shininess=0.333)
            self._gl_set_color(GL_BACK, [0.7, 0.4, 0.4, 1.0], shininess=0.1)
            glEnable(GL_CULL_FACE)
            glCullFace(GL_BACK)
            glCallList(self._model_list)
            glCullFace(GL_FRONT)
            glCallList(self._model_list)
        if self.wireframe or self.show_facets:
            glLineWidth(1.0)
            glDisable(GL_CULL_FACE)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glEnable(GL_POLYGON_OFFSET_FILL)
            glPolygonOffset(-1.0, 1.0);
            self._gl_set_color(GL_FRONT_AND_BACK, [0.0, 0.0, 0.0, 1.0], shininess=0.0)
            glCallList(self._model_list)
            glDisable(GL_POLYGON_OFFSET_FILL)
        glCallList(self._errs_list)
        glCallList(self._grid_list)  # draw last because transparent

        glPopMatrix()
        glFlush()
        glutSwapBuffers()
        glutPostRedisplay()

    def _gl_reshape(self, width, height):
        """window reshape callback."""
        glViewport(0, 0, width, height)

        xspan = self.stl_data.points.maxx - self.stl_data.points.minx
        yspan = self.stl_data.points.maxy - self.stl_data.points.miny
        zspan = self.stl_data.points.maxz - self.stl_data.points.minz

        self.boundsrad = r = 0.5 * max(xspan, yspan, zspan) * math.sqrt(2.0)
        self.cx = (self.stl_data.points.minx + self.stl_data.points.maxx) / 2.0
        self.cy = (self.stl_data.points.miny + self.stl_data.points.maxy) / 2.0
        self.cz = (self.stl_data.points.minz + self.stl_data.points.maxz) / 2.0

        winrad = .5 * min(width, height) / r
        w, h = width / winrad, height / winrad

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if self.perspective:
            gluPerspective(40.0, width/float(height), 1.0, min(1000.0, 10.0 * r))
        else:
            glOrtho(-w, w, -h, h, 1.0, min(1000.0, 10.0 * r))

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(0, 0, 4.0 * self.boundsrad,  0, 0, 0,  0, 1, 0)

        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
        glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 1.0*self.boundsrad, 4.0*self.boundsrad, 0.0])
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHTING)
        glEnable(GL_NORMALIZE)
        glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)

    def _gl_keypressed(self, key, x, y):
        if key == b'\033':
            sys.exit()
        elif key == b'r':
            self.reset_view()

        elif key == b'\x17':
            self._ytrans += 10.0
        elif key == b'\x13':
            self._ytrans -= 10.0
        elif key == b'\x04':
            self._xtrans += 10.0
        elif key == b'\x01':
            self._xtrans -= 10.0

        elif key == b'w':
            q = Quaternion(axis=[1, 0, 0], degrees=5)
            self._view_q = (self._view_q * q).unit
        elif key == b's':
            q = Quaternion(axis=[1, 0, 0], degrees=-5)
            self._view_q = (self._view_q * q).unit
        elif key == b'd':
            q = Quaternion(axis=[0, 1, 0], degrees=-5)
            self._view_q = (self._view_q * q).unit
        elif key == b'a':
            q = Quaternion(axis=[0, 1, 0], degrees=5)
            self._view_q = (self._view_q * q).unit

        elif key == b'q':
            q = Quaternion(axis=[0, 0, 1], degrees=-5)
            self._view_q = (self._view_q * q).unit
        elif key == b'e':
            q = Quaternion(axis=[0, 0, 1], degrees=5)
            self._view_q = (self._view_q * q).unit

        elif key == b'=':
            self._zoom *= 1.05
            self._zoom = min(10.0,max(0.1,self._zoom))
        elif key == b'-':
            self._zoom /= 1.05
            self._zoom = min(10.0,max(0.1,self._zoom))

        elif key == b'1':
            self.wireframe = True
            self.show_facets = True
        elif key == b'2':
            self.wireframe = False
            self.show_facets = True
        elif key == b'3':
            self.wireframe = False
            self.show_facets = False

        elif key == b'4':
            self._view_q = Quaternion(axis=[1, 0, 0], degrees=0)
        elif key == b'5':
            self._view_q = Quaternion(axis=[1, 0, 0], degrees=180)
        elif key == b'6':
            self._view_q = Quaternion(axis=[1, 0, 0], degrees=-90)
            self._view_q *= Quaternion(axis=[0, 0, 1], degrees=180)
        elif key == b'7':
            self._view_q = Quaternion(axis=[1, 0, 0], degrees=90)
        elif key == b'8':
            self._view_q = Quaternion(axis=[0, 0, 1], degrees=90)
            self._view_q *= Quaternion(axis=[1, 0, 0], degrees=90)
        elif key == b'9':
            self._view_q = Quaternion(axis=[0, 0, 1], degrees=-90)
            self._view_q *= Quaternion(axis=[1, 0, 0], degrees=90)
        elif key == b'0':
            self._view_q = Quaternion(axis=[0, 0, 1], degrees=25)
            self._view_q *= Quaternion(axis=[1, 0, 0], degrees=55)

        elif key == b'p':
            self.perspective = not self.perspective
            self._gl_reshape(glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT))
        glutPostRedisplay()

    def _gl_mousebutton(self, button, state, x, y):
        w, h = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        cx, cy = w/2.0, h/2.0
        self._mouse_state = state
        if state == GLUT_DOWN:
            self._xstart = x
            self._ystart = y
            self._mouse_btn = button
            if button == GLUT_LEFT_BUTTON:
                if glutGetModifiers() == GLUT_ACTIVE_SHIFT:
                    self._action = "ZOOM"
                elif glutGetModifiers() == GLUT_ACTIVE_CTRL:
                    self._action = "TRANS"
                elif math.hypot(cx-x, cy-y) > min(w,h)/2:
                    self._action = "ZROT"
                else:
                    self._action = "XYROT"
            elif button == GLUT_RIGHT_BUTTON:
                self._action = "TRANS"
            elif button == 3:
                self._zoom *= 1.01
                self._zoom = min(10.0,max(0.1,self._zoom))
            elif button == 4:
                self._zoom /= 1.01
                self._zoom = min(10.0,max(0.1,self._zoom))
        else:
            self._action = None
        glutPostRedisplay()

    def _gl_mousemotion(self, x, y):
        w, h = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        cx, cy = w/2.0, h/2.0
        dx = x - self._xstart
        dy = y - self._ystart
        r = 5.0 * self.boundsrad / min(w, h)
        if self._action == "TRANS":
            self._xtrans += dx * r
            self._ytrans -= dy * r
        elif self._action == "ZOOM":
            if dy >= 0:
                self._zoom *= (1.0 + dy/100.0)
            else:
                self._zoom /= (1.0 - dy/100.0)
            self._zoom = min(10.0,max(0.1,self._zoom))
        elif self._action == "XYROT":
            qx = Quaternion(axis=[0, 1, 0], degrees=-dx*360.0/min(w,h))
            qy = Quaternion(axis=[1, 0, 0], degrees=-dy*360.0/min(w,h))
            self._view_q = self._view_q * qx * qy
            self._view_q = self._view_q.unit
        elif self._action == "ZROT":
            oldang = math.atan2(self._ystart-cy, self._xstart-cx)
            newang = math.atan2(y-cy, x-cx)
            dang = newang - oldang
            qz = Quaternion(axis=[0, 0, 1], radians=dang)
            self._view_q = self._view_q * qz
            self._view_q = self._view_q.unit
        self._xstart = x
        self._ystart = y
        glutPostRedisplay()

    def gui_show(self, wireframe=False, show_facets=True):
        self.wireframe = wireframe
        self.show_facets = show_facets

        glutInit(sys.argv)
        glutInitWindowSize(self.width, self.height)
        glutInitDisplayMode(GLUT_DEPTH | GLUT_DOUBLE | GLUT_RGBA)
        glutCreateWindow("STL Show")
        glutDisplayFunc(self._gl_display)
        glutKeyboardFunc(self._gl_keypressed)
        glutMouseFunc(self._gl_mousebutton)
        glutMotionFunc(self._gl_mousemotion)
        glutReshapeFunc(self._gl_reshape)

        # Use depth buffering for hidden surface elimination.
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)

        # cheap-assed Anti-aliasing
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)
        glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glEnable(GL_POLYGON_SMOOTH)
        glEnable(GL_LINE_SMOOTH)

        # Setup the view of the cube.
        self._gl_reshape(glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT))

        glutMainLoop()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
