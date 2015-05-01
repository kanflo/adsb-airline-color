import sys, os
import urllib2
import cStringIO
import json
import socket
try:
    from PIL import Image
except ImportError:
    print "PIL module not found, install using 'sudo pip install PIL'"
    print "If that fails, try 'sudo pip install PIL --allow-external PIL --allow-unverified PIL'"
    sys.exit(1)


def getProminentColor(searchTerm):
    if 0:
        imageUrl = "http://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/Wizz_Air_logo.svg/2000px-Wizz_Air_logo.svg.png"
    #   imageUrl = "http://upload.wikimedia.org/wikipedia/en/thumb/9/9f/United_Parcel_Service_logo.svg/857px-United_Parcel_Service_logo.svg.png"
    #   imageUrl = "http://upload.wikimedia.org/wikipedia/de/thumb/d/d6/Thomas_Cook_Airlines_Logo.png/150px-Thomas_Cook_Airlines_Logo.png"
    #   imageUrl = "http://upload.wikimedia.org/wikipedia/commons/d/d4/Logo_Air_Berlin_mit_Claim.jpg"
    #   imageUrl = "http://commons.wikimedia.org/wiki/File:Tuifly_logo.svg"
    #   imageUrl = "http://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Scandinavian_Airlines_logo.svg/2000px-Scandinavian_Airlines_logo.svg.png"

    else:
        searchTerm = searchTerm.replace(" ", "+")

        fetcher = urllib2.build_opener()
        searchTerm = "%s+logo" % (searchTerm)
        startIndex = 0
        searchUrl = "http://ajax.googleapis.com/ajax/services/search/images?v=1.0&q=" + searchTerm + "&start=%d" % (startIndex)
        f = fetcher.open(searchUrl)
        data = f.read()
        j = json.loads(data)
        for i in range(0, len(j['responseData']['results'])):
            imageUrl = j['responseData']['results'][i]['unescapedUrl']
            fileName, fileExtension = os.path.splitext(imageUrl)
            if fileExtension != ".svg" and fileExtension != ".gif":
                break

    print imageUrl
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    counter = 3
    while counter > 0:
        try:
            file = cStringIO.StringIO(opener.open(imageUrl).read())
        except socket.timeout, e:
            # For Python 2.7
            print "Timeout, retrying"
            pass
        counter -= 1

#    file = cStringIO.StringIO(urllib2.urlopen(imageUrl).read())
    im = Image.open(file)

    histogram = {}
    limit = 10

    px = im.getpixel((0, 0))
    if isinstance(px, (int, long)):
        im = im.convert() # Conver to multi-layer image

    try:
        for i in range(im.size[0]):
            for j in range(im.size[1]):
                px = im.getpixel((i,j))
    #            print px
                if px != (0, 0, 0) and px != (0, 0, 0, 0) and px != (255, 255, 255):
                    if abs(px[0]-px[1]) > limit or abs(px[0]-px[2]) > limit or abs(px[1]-px[2]) > limit:
                        if not px in histogram:
                            histogram[px] = 1
                        else:
                            histogram[px] = histogram[px] + 1
    except AttributeError, e:
        pass # Grayscale image?

    px_max = (0, 0, 0)
    max_count = 0
    for px in histogram:
        if histogram[px] > max_count:
            px_max = px
            max_count = histogram[px]

    return (((px_max[0], px_max[1], px_max[2])), imageUrl)

def loadColorData():
    global colors
    try:
        colors = json.load(open("imagecolors.json"))
    except:
        colors = {}
    return colors

def getColor(key):
    global colors
    if key in colors:
        color = colors[key]["color"]
    else:
        (color, url) = getProminentColor(key)
        colors[key] = {}
        colors[key]["color"] = color
        colors[key]["url"] = url
        with open("imagecolors.json", "w+") as f:
            f.write(json.dumps(colors))
    return color

