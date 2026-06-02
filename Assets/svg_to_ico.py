from PyQt6.QtGui import QImage, QPainter, QIcon
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication
from PIL import Image
import sys
import os

app = QApplication(sys.argv)

folder = os.path.dirname(os.path.abspath(__file__)) # Assuming the SVG is in the same folder as this script
svg_path = os.path.join(folder, "ffx_builder_icon.svg")
png_path = os.path.join(folder, "ffx_builder_icon.png")
ico_path = os.path.join(folder, "icon.ico")

# Render SVG to PNG via Qt
renderer = QSvgRenderer(svg_path)
image = QImage(256, 256, QImage.Format.Format_ARGB32)
image.fill(0)
painter = QPainter(image)
renderer.render(painter)
painter.end()
image.save(png_path)

# Convert PNG to ICO via Pillow
img = Image.open(png_path)
img.save(ico_path, sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])

print("Done:", ico_path)