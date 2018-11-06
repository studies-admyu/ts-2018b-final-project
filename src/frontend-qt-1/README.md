# Qt colorization frontend

## Colorization

Use VideoProcessingColorization.ipynb as a sample. To use it you need to download the pretrained model::

    cd pretrained_models
    sh download_siggraph_model.sh
    cd ..

## Frontend

Frontend is based on PyQt5. To run please use::

    python frontend-qt.py

### Video opening

In order to open a video you need to go to File -> New Project... and specify the video file in dialog

### Painting

Then use Painting tools to specify color points and their colors. Use Ctrl+wheel up / down for image scaling.

1. Color picker - changes color of all the selected color points & default color for new ones.
2. Hand - navigates through a frame;
3. Eyedropper - takes pixel color from original image
4. Add point - Use the instrument to add color points via clicking on a frame;
5. Edit point - Use to select & drag color points;
6. Remove point - Use to remove the point;

### Colorization

Use to switch between frame modes:
1. Original - shows original frame (as in video);
2. Grayscale - shows grayscale frame;
3. Colorized - shows colorization model prediction (not implemented).

### Playback

Tools for navigation through the opened video (not implemented).
