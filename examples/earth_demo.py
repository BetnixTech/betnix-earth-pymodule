from betnix import earth
from OpenGL.GLUT import glutInit

glutInit()

# Run interactive Earth
renderer = earth.EarthRenderer()
renderer.run()

# Example: show tile and find coordinate
earth.show_tile(37.7749, -122.4194)
x, y, z = earth.find_coordinate(37.7749, -122.4194)
print(x, y, z)
