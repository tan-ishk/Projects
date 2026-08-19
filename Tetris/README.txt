Tetris Qt
-------------------
Files:
- Tetris.pro            : qmake project file
- main.cpp              : entry point
- tetrisboard.h/.cpp   : main game widget (Qt Widgets)

Build (Qt 5 or Qt 6 with qmake):
1. cd into the project directory
2. Run: qmake Tetris.pro
3. Run: make  (or nmake on Windows / mingw make)
4. Run the produced executable

Controls:
- Left / Right arrows: move piece
- Down arrow: soft drop
- Up arrow or X: rotate clockwise
- Z: rotate counter-clockwise
- Space: hard drop
- P: pause
