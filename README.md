# AfterEffects-FFX-Builder
A PyQt6 desktop GUI for building Adobe After Effects pseudo effect preset files (.ffx). Define sliders, colors, checkboxes, layers, and other effect controls visually, then export a ready-to-use FFX binary without writing any code.

<img width="1878" height="1110" alt="image" src="https://github.com/user-attachments/assets/8d36a41d-deb7-41f4-a45d-778452cbdadc" />

 
---
 
## Features
 
- Visual drag-and-drop control tree for building effect hierarchies
- Supports all major AE pseudo effect control types: Slider, Angle, Color, Checkbox, Layer, Point, Point3D, Popup, Label, Group
- Group nesting with full deep-clone duplication
- Drag control type buttons directly onto the tree to insert controls
- Per-control property editor (ranges, defaults, keyframe options, visibility)
- Save and load projects as `.ffxbuild` JSON files
- Export directly to `.ffx` binary preset, auto-targeting your AE User Presets folder
- Drag and drop `.ffxbuild` or `.json` project files onto the window to load them
- Dark themed UI
---
 
## Requirements
 
- Python 3.10+
- PyQt6
Install dependencies:
```
pip install PyQt6
```
 
---
 
## Usage
 
```
python main.py
```
 
### Building a preset
 
1. Set your **Effect Name** and **Match Name** in the Effect Identity panel
2. Click control type buttons to add controls to the tree, or drag them directly onto a group
3. Select any control to edit its properties in the right panel
4. Use **Up / Down** to reorder, **Dupe** to duplicate, **Delete** to remove
5. Click **Export FFX** to save the `.ffx` preset -- it will auto-open to your After Effects User Presets folder
### Projects
 
- **Save Project** saves the current tree as a `.ffxbuild` file you can reload later
- **Load Project** or drag a `.ffxbuild` / `.json` file onto the window to restore a session
---
 
## Building a standalone executable
 
Requires PyInstaller:
```
pip install pyinstaller
```
 
Build:
```
pyinstaller --noconfirm --clean "FFX Builder.spec"
```
 
Output is in the `dist/` folder.
 
---
 
## File structure
 
```
AfterEffects-FFX-Builder/
├── main.py               # Main application
├── ae_ffx.py             # FFX binary generator
├── build.txt             # Simple build instructions
├── FFX Builder.spec      # PyInstaller spec
├── icon.ico              # App icon
├── Assets/
│   ├── ffx_builder_icon.ai
│   ├── ffx_builder_icon.png
│   ├── ffx_builder_icon.svg
│   ├── icon.ico
│   └── svg_to_ico.py
├── .github/
│   └── workflows/
│       └── build.yml
└── requirements.txt      # Python
```
 
---
 
## License

© 2026 Guy Micciche — MICCICHE Studios
This project is licensed under [GNU GPL v3.0](LICENSE).
Free to use, modify, and distribute with attribution. Any derivative works must remain open source under the same license.