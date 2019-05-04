#! /usr/bin/env python3

from flask import Flask
app = Flask(__name__)

DEFAULT_FONTS = ["Arial", "Bahnschrift", "Calibri", "Cambria", "Comic Sans MS", "Courier New", "Ebrima", "Franklin Gothic", "Gadugi", "Impact", "Leelawadee UI", "Lucida Console", "Malgun Gothic", "Microsoft Himalaya", "Microsoft Sans Serif", "Microsoft Yi Baiti", "MingLiU-ExtB", "Mongolian Baiti", "MV Boli", "Nirmala UI", "Palatino Linotype", "Segoe UI", "Segoe UI Symbol", "SimSun", "Sylfaen", "Symbol", "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana", "Yu Gothic", "Yu Gothic UI", "Book Antiqua", "Arial Rounded MT", "Baskerville Old Face", "Bernard MT", "Bodoni MT", "Bookman Old Style", "Britannic", "Berlin Sans FB", "Californian FB", "Calisto MT", "Century Schoolbook", "Centaur", "Century", "Copperplate Gothic", "Dubai", "Engravers MT", "Eras ITC", "Felix Titling", "Franklin Gothic Book", "Footlight MT", "Garamond", "Gill Sans MT", "Gloucester MT", "Century Gothic", "Goudy Old Style", "Goudy Stout", "Lucida Bright", "Lucida Handwriting", "Maiandra GD", "Monotype Corsiva", "Old English Text MT", "Perpetua", "Perpetua Titling MT", "Rockwell", "Tw Cen MT", "Tempus Sans ITC", "Lato", "Oswald", "Source Sans Pro", "Montserrat", "Global User Interface", "Global Monospace", "Global Sans Serif", "Global Serif"]

@app.route("/")
def root(fonts=None):
    if fonts:
        fonts = [f.strip('"') for f in fonts.split(',\s*')]
    fonts = sorted(fonts or DEFAULT_FONTS)
    font_list = ', '.join('&quot;%s&quot;' % f for f in fonts)
    font_samples = "\n".join(
        "<li style='font-family: %s; font-size: 48pt'>4702 ... %s</li>" % (font, font)
        for font in fonts
    )
        
    return f"""
<!DOCTYPE html>
<html>
<head>
<title>Fonts</title>
</head>
<body>
<div width="100%">Fonts: <textarea rows="8" cols="300" name="fonts">{font_list}</textarea></div>
<ul>
{font_samples}
</ul>
</body>
</html>
"""
