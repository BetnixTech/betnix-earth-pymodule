# earth.py - Betnix Earth Full Module
import pygame, math, json, requests, os
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from PIL import Image
from io import BytesIO
from earth import EarthRenderer
from OpenGL.GLUT import glutInit

# ---------------- DATA STORE ----------------
DATA_FILE = "betnix_data.json"
class DataStore:
    def load(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE,"r") as f:
                d = json.load(f)
                return {
                    "markers": d.get("markers", []),
                    "routes": d.get("routes", []),
                    "trees": d.get("trees", []),
                    "grass": d.get("grass", []),
                    "buildings": d.get("buildings", [])
                }
        return {"markers":[],"routes":[],"trees":[],"grass":[],"buildings":[]}

    def save(self, data):
        with open(DATA_FILE,"w") as f:
            json.dump(data,f)

# ---------------- GEO ----------------
def latlon_to_xyz(lat, lon, radius=2.0):
    x = radius * math.cos(math.radians(lat)) * math.cos(math.radians(lon))
    y = radius * math.sin(math.radians(lat))
    z = radius * math.cos(math.radians(lat)) * math.sin(math.radians(lon))
    return x, y, z

# ---------------- ENTITIES ----------------
class Marker:
    def __init__(self, lat, lon, color=(1,0,0)):
        self.lat, self.lon = lat, lon
        self.color = color
    def draw(self, radius=2.02):
        glColor3f(*self.color)
        x, y, z = latlon_to_xyz(self.lat, self.lon, radius)
        glPushMatrix()
        glTranslatef(x, y, z)
        quad = gluNewQuadric()
        gluSphere(quad, 0.03, 10, 10)
        glPopMatrix()

class Route:
    def __init__(self, markers, color=(0,1,0)):
        self.markers = markers
        self.color = color
    def draw(self, radius=2.01):
        glColor3f(*self.color)
        glBegin(GL_LINE_STRIP)
        for m in self.markers:
            x, y, z = latlon_to_xyz(m.lat, m.lon, radius)
            glVertex3f(x, y, z)
        glEnd()

# ---------------- TREES, GRASS, BUILDINGS ----------------
def draw_tree(lat, lon, height=0.2, radius=2.0):
    x, y, z = latlon_to_xyz(lat, lon, radius)
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(0, 0.5, 0)
    quad = gluNewQuadric()
    glRotatef(-90,1,0,0)
    gluCylinder(quad, 0.0, 0.05, height, 8, 8)
    glPopMatrix()

def draw_grass(lat, lon, radius=2.0):
    x, y, z = latlon_to_xyz(lat, lon, radius)
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(0.2, 0.8, 0.2)
    glBegin(GL_QUADS)
    glVertex3f(-0.02,0,-0.02)
    glVertex3f(0.02,0,-0.02)
    glVertex3f(0.02,0,0.02)
    glVertex3f(-0.02,0,0.02)
    glEnd()
    glPopMatrix()

def draw_building(lat, lon, height=0.3, radius=2.0):
    x, y, z = latlon_to_xyz(lat, lon, radius)
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(0.6, 0.6, 0.6)
    glutSolidCube(height)
    glPopMatrix()

# ---------------- TILE FETCHING ----------------
def latlon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    xtile = int((lon+180)/360*n)
    ytile = int((1 - math.log(math.tan(math.radians(lat)) + 1/math.cos(math.radians(lat)))/math.pi)/2*n)
    return xtile, ytile

def get_tile_image(x, y, z):
    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    r = requests.get(url)
    if r.status_code == 200:
        return Image.open(BytesIO(r.content))
    return None

# ---------------- EARTH RENDERER ----------------
class EarthRenderer:
    def __init__(self, width=1200, height=800, tile_zoom=2):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("Betnix Earth")
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_TEXTURE_2D)
        glClearColor(0.02,0.02,0.05,1)
        gluPerspective(45, width/float(height),0.1,200.0)
        glTranslatef(0,0,-6)
        self.rot_x=self.rot_y=0
        self.zoom=-6
        self.dragging=False
        self.last_mouse=(0,0)
        self.data_store = DataStore()
        ds = self.data_store.load()
        self.markers = [Marker(**m) for m in ds["markers"]]
        self.routes = [Route([Marker(**pt) for pt in r]) for r in ds["routes"]]
        self.trees = [(t["lat"], t["lon"]) for t in ds["trees"]]
        self.grass = [(g["lat"], g["lon"]) for g in ds["grass"]]
        self.buildings = [(b["lat"], b["lon"], b.get("height",0.3)) for b in ds["buildings"]]
        self.tile_zoom = tile_zoom
        self.clock = pygame.time.Clock()
        self.input_active=False
        self.input_text=""
        self.current_route=[]

    def draw_earth_surface(self, radius=2.0, slices=40, stacks=40):
        for i in range(stacks):
            lat0 = -90 + 180 * i / stacks
            lat1 = -90 + 180 * (i+1) / stacks
            glBegin(GL_QUAD_STRIP)
            for j in range(slices+1):
                lon = -180 + 360 * j / slices
                glColor3f(0.2,0.7,0.2) if -60<=lat0<=75 else glColor3f(0.1,0.3,0.8)
                x,y,z = latlon_to_xyz(lat0,lon,radius)
                glVertex3f(x,y,z)
                glColor3f(0.2,0.7,0.2) if -60<=lat1<=75 else glColor3f(0.1,0.3,0.8)
                x,y,z = latlon_to_xyz(lat1,lon,radius)
                glVertex3f(x,y,z)
            glEnd()

    def draw_grid(self,radius=2.03, step=30):
        glColor3f(0.5,0.5,0.5)
        for lat in range(-90,91,step):
            glBegin(GL_LINE_STRIP)
            for lon in range(-180,181,2):
                x,y,z=latlon_to_xyz(lat,lon,radius)
                glVertex3f(x,y,z)
            glEnd()
        for lon in range(-180,181,step):
            glBegin(GL_LINE_STRIP)
            for lat in range(-90,91,2):
                x,y,z=latlon_to_xyz(lat,lon,radius)
                glVertex3f(x,y,z)
            glEnd()

    def draw_entities(self):
        for m in self.markers: m.draw()
        for r in self.routes: r.draw()
        if len(self.current_route)>1: Route(self.current_route,(1,1,0)).draw()
        for lat,lon in self.trees: draw_tree(lat,lon)
        for lat,lon in self.grass: draw_grass(lat,lon)
        for lat,lon,h in self.buildings: draw_building(lat,lon,h)

    def handle_input(self,event):
        if event.type==pygame.QUIT: return False
        elif event.type==pygame.MOUSEBUTTONDOWN:
            if event.button==4:self.zoom+=0.3
            elif event.button==5:self.zoom-=0.3
        elif event.type==pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
            dx,dy=event.rel
            self.rot_y+=dx
            self.rot_x+=dy
        elif event.type==pygame.KEYDOWN:
            if self.input_active:
                if event.key==pygame.K_RETURN:
                    try:
                        lat, lon = map(float,self.input_text.split(","))
                        m=Marker(lat,lon)
                        self.markers.append(m)
                        self.current_route.append(m)
                    except: pass
                    self.input_text=""
                    self.input_active=False
                elif event.key==pygame.K_BACKSPACE: self.input_text=self.input_text[:-1]
                else: self.input_text+=event.unicode
            else:
                if event.key==pygame.K_f: self.input_active=True
                elif event.key==pygame.K_s:
                    self.data_store.save({
                        "markers":[{"lat":m.lat,"lon":m.lon} for m in self.markers],
                        "routes":[[{"lat":pt.lat,"lon":pt.lon} for pt in r.markers] for r in self.routes],
                        "trees":[{"lat":t[0],"lon":t[1]} for t in self.trees],
                        "grass":[{"lat":g[0],"lon":g[1]} for g in self.grass],
                        "buildings":[{"lat":b[0],"lon":b[1],"height":b[2]} for b in self.buildings]
                    })
                elif event.key==pygame.K_r:
                    if len(self.current_route)>1:
                        self.routes.append(Route(self.current_route.copy()))
                        self.current_route=[]
                elif event.key==pygame.K_t:
                    if self.current_route: self.trees.append((self.current_route[-1].lat,self.current_route[-1].lon))
                elif event.key==pygame.K_g:
                    if self.current_route: self.grass.append((self.current_route[-1].lat,self.current_route[-1].lon))
                elif event.key==pygame.K_b:
                    if self.current_route: self.buildings.append((self.current_route[-1].lat,self.current_route[-1].lon,0.3))
        return True

    def run(self):
        running=True
        font=pygame.font.SysFont("Arial",20)
        while running:
            for event in pygame.event.get():
                running=self.handle_input(event)
            glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()
            glTranslatef(0,0,self.zoom)
            glRotatef(self.rot_x,1,0,0)
            glRotatef(self.rot_y,0,1,0)
            self.draw_earth_surface()
            self.draw_grid()
            self.draw_entities()
            if self.input_active:
                txt_surf=font.render("Enter lat,lon: "+self.input_text,True,(255,255,255))
                self.screen.blit(txt_surf,(10,10))
            pygame.display.flip()
            self.clock.tick(60)
        # Save on exit
        self.data_store.save({
            "markers":[{"lat":m.lat,"lon":m.lon} for m in self.markers],
            "routes":[[{"lat":pt.lat,"lon":pt.lon} for pt in r.markers] for r in self.routes],
            "trees":[{"lat":t[0],"lon":t[1]} for t in self.trees],
            "grass":[{"lat":g[0],"lon":g[1]} for g in self.grass],
            "buildings":[{"lat":b[0],"lon":b[1],"height":b[2]} for b in self.buildings]
        })

# ---------------- UTILITY FUNCTIONS ----------------
def find_coordinate(lat, lon, radius=2.0):
    return latlon_to_xyz(lat, lon, radius)

def show_tile(lat, lon, zoom=2):
    x,y = latlon_to_tile(lat, lon, zoom)
    img=get_tile_image(x, y, zoom)
    if img: img.show()

# ---------------- EXAMPLE ----------------
if __name__=="__main__":
    glutInit()
    renderer = EarthRenderer()
    renderer.run()
