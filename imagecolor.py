# Copyright (c) 2022 Johan Kanflo (github.com/kanflo)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import io
import sys
import json
import re
import json
import tempfile
import logging
try:
    from PIL import Image
    from PIL.PngImagePlugin import PngImageFile
except ImportError:
    print("sudo -H python -m pip install Pillow'")
    sys.exit(1)
try:
    import requests
except ImportError:
    print("sudo -H python -m pip install requests")
    sys.exit(1)


def download_image(url: str) -> PngImageFile:
    """Fetch image and load into PIL

    Args:
        url (str): Image URL

    Returns:
        PngImageFile: PIL image
    """
    headers = {}
    headers['Accept'] = 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
    headers['Accept-Language'] = 'en-US,en;q=0.9,sv;q=0.8'
    headers['Connection'] = 'keep-alive'
    headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'
    headers['sec-ch-ua'] = '" Not A;Brand";v="99", "Chromium";v="102", "Google Chrome";v="102"'
    headers['sec-ch-ua-mobile'] = '?0'
    headers['sec-ch-ua-platform'] = '"Linux"'

    im = None
    r = requests.get(url, headers=headers, stream=True)
    if r.status_code == 200:
        buffer = tempfile.SpooledTemporaryFile(max_size=1e9)
        downloaded = 0
        for chunk in r.iter_content(chunk_size=1024):
            downloaded += len(chunk)
            buffer.write(chunk)
        buffer.seek(0)
        im = Image.open(io.BytesIO(buffer.read()))
        buffer.close()
    else:
        logging.error("Error: API access failed with %d" % r.status_code)
    return im


# Search for 'keywords' and return image URLs in a list or None if, well, none
# are found or an error occurred
def search_image(keywords: str):
    """Lookup image for given registration (or whatever)

    Args:
        registration (str): _description_

    Returns:
        str: Image URL or None
    """
    for image in ddg_search("\"%s\"" % keywords):
#        print("---")
#        print(image["image"])
#            if image["width"] > 1000 and image["height"] > 700:
        return image["image"]
    return None


"""
Based on https://github.com/deepanprabhu/duckduckgo-images-api/blob/master/duckduckgo_images_api/api.py
"""
class DuckException(Exception):
       pass

def ddg_search(keywords: str, max_results: int = 10) -> list:
    """Search DuckDuckGo for keywords

    Args:
        keywords (str): Keywords to search for
        max_results (int, optional): Requested number of search results. Defaults to 10.

    Returns:
        list: A list of dictionaries containing the following fields:
                "image"     : image URL
                "url"       : URL of page where image was found
                "height"    : height of image
                "width"     : width of image
                "title"     : title of page
                "source"    : No idea, often "Bing"
                "thumbnail" : URL of thumbnail
        None: in case of errors
    """
    url = 'https://duckduckgo.com/'
    params = {'q': keywords}
    headers = {
        'authority': 'duckduckgo.com',
        'accept': 'application/json, text/javascript, */* q=0.01',
        'sec-fetch-dest': 'empty',
        'x-requested-with': 'XMLHttpRequest',
        'user-agent': 'Mozilla/5.0 (Macintosh Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'referer': 'https://duckduckgo.com/',
        'accept-language': 'en-US,enq=0.9',
    }

    # First make a request to above URL, and parse out the 'vqd'
    # This is a special token, which should be used in the subsequent request
    res = requests.post(url, headers = headers, data = params)
    if res.status_code != 200:
        logging.error("DuckDuckGo responded with %d" % (res.status_code))
        if res.status_code == 403:
            raise DuckException("403: They are on to us")
        return None
    search_obj = re.search(r'vqd=([\d-]+)\&', res.text, re.M|re.I)

    if not search_obj:
        logging.error("Token parsing failed")
        return None

    params = (
        ('l', 'us-en'),
        ('o', 'json'),
        ('q', keywords),
        ('vqd', search_obj.group(1)),
        ('f', ',,,'),
        ('p', '1'),
        ('v7exp', 'a'),
    )

    request_url = url + "i.js"
    search_results = []
    counter = 0
    while True:
        try:
            res = requests.get(request_url, headers = headers, params = params)
            if res.status_code != 200:
                logging.error("DuckDuckGo responded with %d" % (res.status_code))
                if res.status_code == 403:
                    raise DuckException("403: They are on to us")
                return search_results
            data = json.loads(res.text)
        except ValueError as e:
            logging.error("Caught exception", exc_info = True)
            continue

        for foo in data["results"]:
            search_results.append(foo)
            counter += 1
            if counter == max_results:
                return search_results

        if "next" not in data:
            return search_results

        request_url = url + data["next"]


def get_prominent_color(im: PngImageFile) -> tuple:
    """Get the prominent color from image

    Args:
        im (PngImageFile): PIL image

    Returns:
        tuple: (r, g, b) of most prominent color or (0, 0, 0) in case of errors
    """
    histogram = {}
    limit = 10  # Ignore "dark" pixels

    try:
        for i in range(im.size[0]):
            for j in range(im.size[1]):
                px = im.getpixel((i,j))
                if px != (0, 0, 0) and px != (0, 0, 0, 0) and px != (255, 255, 255):
                    if px[0] > limit or px[1] > limit or px[2] > limit:
                        if not px in histogram:
                            histogram[px] = 1
                        else:
                            histogram[px] += 1
    except AttributeError as e:
        logging.error("Image analysis caused exception", exc_info = True)
        return (0, 0, 0)

    px_max = (0, 0, 0)
    max_count = 0
    for px in histogram:
        if histogram[px] > max_count:
            px_max = px
            max_count = histogram[px]

    return (((px_max[0], px_max[1], px_max[2])))


def load_color_data() -> dict:
    """Load color data from logocolors.json

    Returns:
        dict: A dictionary used internally
    """
    global colors
    try:
        colors = json.load(open("logocolors.json"))
    except:
        colors = {}
    return colors


def get_color(airline: str) -> tuple:
    """Get color for named airline. If the airline is not found in the cache,
       make an image search, analyze and store result.

    Args:
        airline (str): Name of airline

    Returns:
        tuple: And (r, g, b) tuple or (0, 0, 0) if the airline is not known or in case of errors
    """
    global colors
    color = (0, 0, 0)
    key = airline
    if key in colors:
        color = colors[key]["color"]
    else:
        url = search_image(airline + " logo")
        if url:
            logging.info("Downloading " + url)
            image = download_image(url)
            color = get_prominent_color(image)
            if color:
                colors[key] = {}
                colors[key]["color"] = color
                colors[key]["url"] = url
                logging.info("Added #%02x%02x%02x for %s" % (color[0], color[1], color[2], airline))
                with open("logocolors.json", "w+") as f:
                    f.write(json.dumps(colors))
    return color
