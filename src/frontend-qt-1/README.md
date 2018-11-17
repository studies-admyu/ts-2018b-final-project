# Qt colorization frontend

## Colorization

Use VideoProcessingColorization.ipynb as a sample. To use it you need to download the pretrained model::

    cd pretrained_models
    sh download_siggraph_model.sh
    cd ..

## Frontend

Frontend is based on PyQt5. To run please use::

    python frontend-qt.py

This frontend uses icons from Free FatCow Farm-Fresh Icons collection (see [FatCow website](http://www.fatcow.com/free-icons/) for further information).

### Video opening

In order to open a video you need to go to File -> New Project... and specify the video file in dialog

### Painting

Then use Painting tools to specify color points and their colors. Use Ctrl+wheel up / down for image scaling.

1. Color selection - changes color of all the selected color points & default color for new ones;
2. Hand - navigates through a frame;
3. Color picker - obtains pixel color from original frame;
4. Add color point - Use to add color hint point via clicking on a frame;
5. Edit color point - Use to select & move color points;
6. Delete color point - Use to remove color points.

### Colorization

Use to switch between frame modes:
1. Original - shows original frame (as in video);
2. Grayscale - shows grayscale frame;
3. Colorized - shows colorization model prediction.

Calculate colorization - use to colorize the grayscale verion of image according to provided color hit points.

### Playback

Tools for navigation through the opened video (not implemented).
