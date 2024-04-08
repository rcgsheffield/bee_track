#!/usr/bin/env python

from retrodetect.image_processing import getshift, shiftimg
import json
import hashlib
from datetime import datetime
import pickle
import retrodetect
import re
import os
import webbrowser
import argparse
from retrodetect.image_processing import getblockmaxedimage
from glob import glob
from flask import Flask, make_response, jsonify, render_template
import numpy as np
from flask_cors import CORS
# from flask_compress import Compress
app = Flask(__name__)
# Compress(app) SC: a mechanism for integrating applications. CORS defines a way for client web applications that are loaded in one domain to interact with resources in a different domain.
CORS(app)


parser = argparse.ArgumentParser(
    prog='btviewer', description='Provide simple interface to label bee images')
parser.add_argument('imgpath', type=str, help='Path to images')
parser.add_argument(
    '--refreshcache', help='Whether to refresh the cache', action="store_true")
parser.add_argument('--port', required=False, type=int, help='Port')
parser.add_argument('--config', required=False, type=str,
                    help='Config Filename, e.g. config000000.json')


args = parser.parse_args()
print(args)

# '/home/mike/Documents/Research/bee/photos2020/photos_June20'
pathtoimgsdir = args.imgpath
print("Absolute path to images:")
print(os.path.abspath(pathtoimgsdir))
pathtoimgsdir = os.path.abspath(pathtoimgsdir)
pathtoimgs = sorted(glob(pathtoimgsdir+'/*/'))
# SC: it seems there must be subdirectories in the data folder although the below code seems to work too

if (len(pathtoimgs) == 0):
    print("Failed to find any folders in the path, using base path given as camera folder.")
    pathtoimgs = [pathtoimgsdir]
print("Found the following camera folders:")
print(pathtoimgs)

# SC: scriptpath is not used elsewhere
scriptpath = os.path.dirname(os.path.realpath(__file__))
os.chdir(scriptpath)
print('scriptpath')
print(scriptpath)
# indexhtml = os.path.join(scriptpath, 'index.html')
# webbrowser.open("file://index.html",new=2)
# SC https://docs.python.org/3.11/library/webbrowser.html#webbrowser.new
webbrowser.open("file://" + os.path.realpath('index.html'), new=2)
# webbrowser.open("http://localhost:5000") SC: if we use this one with the index route, the page is shown in white background but no response
# SC: it loads 2 times when debug = True

if args.port is not None:
    port = args.port
else:
    port = 5000

# SC: Do we want to get configfile or the one created is fine? is it for @app.route('/configure/<string:path>')

if args.config is not None:
    configfilename = os.path.join(pathtoimgsdir, args.config)
else:
    configfilename = os.path.join(pathtoimgsdir, 'config_unnamed.json')
print(configfilename)


# SC: works well

##### Function Chunks#####

def getimgfilelist(path, camid=None):
    if camid is not None:
        return sorted(glob('%s/*%s*.np' % (path, camid)))
    else:
        # return sorted(glob('Data\\folder1\\*.np'))
        return sorted(glob('%s/*.np' % (path)))


def getcamfromfilename(fn):
    res = re.findall('photo_object_([0-9A-Z]*)_[0-9]{8}_', fn)
    if len(res) == 0:
        return None
    else:
        return res[0]


def getfnfordatetimeandcamid(path, camid, datetime):
    # fns = glob(f'Data\\folder1\\*{camid}_{datetime}*.np')
    fns = glob('%s/*%s_%s*.np' % (path, camid, datetime))
    if len(fns) == 0:
        return None
    else:
        return fns[0]


def getdatetimefromfilename(fn):
    res = re.findall(
        'photo_object_[0-9A-Z]*_([0-9]{8}_[0-9]{2}[:|_][0-9]{2}[:|_][0-9]{2})', fn)
    # SC I changed to the above to match Mike's file format
    # res = re.findall('photo_object_[0-9A-Z]*_([0-9]{8}_[0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]{6})_',fn)
    # res = re.findall('photo_object_([0-9]{8}_[0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]{6})_',fn)
    # res = re.findall('(_[0-9]{2}_[0-9]{2}_[0-9]{2})', fn)
    if len(res) == 0:
        return None  # SC: is it not good to just return None?
    else:
        # return res[0][1:]
        return res[0]  # SC: I changed to this


def getdatetimelist(path):
    """
    Returns a list of all unique datetimes in path
    """
    fns = getimgfilelist(path)
    return sorted(list(set([getdatetimefromfilename(fn) for fn in fns if getdatetimefromfilename(fn) is not None])))


def guesscamtypegetscore(fn):
    try:
        photo = pickle.load(open(fn, 'rb'))
    except EOFError:
        return np.NaN

    img = photo['img']
    if img is None:
        score = np.NaN
        # return np.NaN
    else:
        # e.g. 0.0001 = greyscale, 0.7 = colour
        score = np.abs(np.mean(
            img[0:-2:2, 0:-2:2]/2+img[2::2, 2::2]/2-img[1:-2:2, 1:-2:2])/np.mean(img))
    return score


def guesscamtype(path, camid):
    score = np.nanmean([guesscamtypegetscore(fn)
                       for fn in getimgfilelist(path, camid)[:50:5]])
    if score < 0.02:
        return 'greyscale'
    else:
        return 'colour'


def getorderedcamids(path):
    """
    Returns camera ids with greyscale ones first
    """
    fns = getimgfilelist(path)
    cam_ids = list(set([getcamfromfilename(fn)
                   for fn in fns if getcamfromfilename(fn) is not None]))
    return [cam_id for cam_id in cam_ids if guesscamtype(path, cam_id) == 'greyscale']+[cam_id for cam_id in cam_ids if guesscamtype(path, cam_id) == 'colour']


def getimgfilename(cam, internalcam, number):
    path = pathtoimgs[cam]  # SC: pathtoimgs is global? is it good this way
    dts = getdatetimelist(path)
    if number >= len(dts):
        return None

    try:  # SC camera_ids is global variable
        fn = getfnfordatetimeandcamid(
            pathtoimgs[cam], camera_ids[cam][internalcam], dts[number])
    except IndexError:
        return None
    return fn


def gethash(obj):
    """
    Returns a 160 bit integer hash
    """
    return int(hashlib.sha1(obj).hexdigest(), 16)


def converttodt(st):
    return datetime.strptime(st.replace('_', ':'), '%H:%M:%S') #SC: I add the regex replacement to tackle the filename time issues

######


camera_ids = []
for pti in pathtoimgs:
    camera_ids.append(getorderedcamids(pti))  # camera_ids is list of list
print('camera_ids')
print(camera_ids)
print('end')


# SC: The button 'GO TO'
@app.route('/getindexoftime/<int:cam>/<string:dtstring>')
def getindexoftime(cam: int, dtstring):
    fns = getimgfilelist(pathtoimgs[cam])
    # '20210720_13:58:00.000000') #SC: But the converttodt function only takes times!!!, so I used the below one
    #targ = converttodt(dtstring)
    #gotoNum = np.argmin(np.abs([(converttodt(re.findall('.*_([0-9]{8}_[0-9]{2}[:|_][0-9]{2}[:|_][0-9]{2}.[0-9]{6})__', fn)[0])-targ).total_seconds() for fn in fns]))

    targ = converttodt(dtstring) #'13:58:00.000000')
    gotoNum = np.argmin(np.abs([(converttodt(re.findall('.*_([0-9]{2}[:|_][0-9]{2}[:|_][0-9]{2})',fn)[0])-targ).total_seconds() for fn in fns]))
    return json.dumps(int(gotoNum))


@app.route('/detectfromto/<int:cam>/<int:from_idx>/<int:to_idx>')
def detectall(cam, from_idx, to_idx):
    print("STARTING DETECTION RUN: %d to %d" % (from_idx, to_idx))
    for i in range(from_idx, to_idx):
        detect(cam, i)
    return "done"


@app.route('/detect/<int:cam>/<int:number>')
def detect(cam, number):
    path = pathtoimgs[cam]
    cachefile = 'cache/detect_cache_%s_%d.pkl' % (
        gethash(path.encode("utf-8")), number)

    if not args.refreshcache:
        try:
            result = pickle.load(open(cachefile, 'rb'))
            print("Cache hit %s" % cachefile)
            return result

        except FileNotFoundError:
            pass
    photo_list = []
    for n in range(number-10, number+2):
        if n < 0:
            continue
        fn = getimgfilename(cam, 0, n)
        try:
            photoitem = np.load(fn, allow_pickle=True)
        except OSError:
            continue  # skip this one if we can't access it
        if photoitem is not None:
            if photoitem['img'] is not None:
                photoitem['img'] = photoitem['img'].astype(np.float16)
        photo_list.append(photoitem)
    contact, found, _ = retrodetect.detectcontact(photo_list, len(
        photo_list)-1, Npatches=50, delsize=5, blocksize=3, flashthreshold=0.01)
    newcontact = []
    if contact is not None:
        for c in contact:
            c['patch'] = c['patch'].tolist()  # makes it jsonable
            c['searchpatch'] = c['searchpatch'].tolist()  # makes it jsonable
            c['mean'] = float(c['mean'])
            c['searchmax'] = float(c['searchmax'])
            c['centremax'] = float(c['centremax'])
            c['x'] = int(c['x'])
            c['y'] = int(c['y'])
            newcontact.append(c)
    result = jsonify({'contact': newcontact, 'found': found})
    pickle.dump(result, open(cachefile, 'wb'))
    return result


@app.route('/')  # SC: this seems to be a placeholder and not shown
def hello_world():
    return 'root node of bee label API.'

# @app.route('/') #SC: I have tried to use this along with the webrowser.open with local host, but does not work
# def home_page():
#    return render_template('index.html')


# SC: This route seems to be first called when app starts running with all input as zero
@app.route('/filename/<int:cam>/<int:internalcam>/<int:number>')
def filename(cam, internalcam, number):
    # SC: there are quite a few times that there will be None
    fn = getimgfilename(cam, internalcam, number)
    print(fn)
    photoitem = np.load(fn, allow_pickle=True)
    returnst = fn
    # SC:what if record is none? the first photo is like that, photo_object_02G14695547_20230629_10_06_07.051416
    print(photoitem['record'])
    # SC: what if no such 'estimated_true_triggertimestring'
    if 'estimated_true_triggertimestring' in photoitem['record']:
        returnst = returnst + \
            ' (' + photoitem['record']['estimated_true_triggertimestring'] + ')'
    return jsonify(returnst)


@app.route('/configure/<string:path>')
def configure(path):
    global pathtoimgs
    pathtoimgs = path
    return "set new path %s" % path


@app.route('/savelm/<int:cam>/<int:internalcam>/<int:x>/<int:y>/<string:lmname>/<string:coords>')
def savelm(cam, internalcam, x, y, lmname, coords):

    print(coords, len(coords))
    if len(coords.split(",")) == 3:
        coords = [float(s) for s in coords.split(",")]

    try:
        data = json.load(open(configfilename, 'r'))
    except FileNotFoundError:
        data = {}
    camst = 'cam%d' % (cam+1)  # TODO The camera id stuff is a complete mess.
    # not using which internal camera for now...
    internalcamst = 'internalcam%d' % internalcam
    if 'items' not in data:
        data['items'] = {}
    if lmname not in data['items']:
        data['items'][lmname] = {}
    if 'imgcoords' not in data['items'][lmname]:
        data['items'][lmname]['imgcoords'] = {}
    if coords != "skip":
        data['items'][lmname]['coords'] = coords
    data['items'][lmname]['imgcoords'][camst] = [x, y]

    json.dump(data, open(configfilename, 'w'), indent=4)
    return "done"


def save_pos(cam, internalcam, number, x, y, confidence, label=None):
    fn = getimgfilename(cam, internalcam, number)
    beetrackfn = pathtoimgsdir+"/bee_track.json"
    try:
        data = json.load(open(beetrackfn, 'r'))
    except FileNotFoundError:
        data = {}
    camst = str(cam)
    numberst = str(number)
    if camst not in data:
        data[camst] = {}
    if numberst not in data[camst]:
        data[camst][numberst] = []
    newrecord = {'x': x, 'y': y, 'confidence': confidence, 'fn': fn}
    if label is not None:
        newrecord['label'] = label
    shift = getcachedshift(cam, internalcam, number)
    if shift is not None:
        newrecord['shift'] = [int(shift[0]), int(shift[1])]
    data[camst][numberst].append(newrecord)
    json.dump(data, open(beetrackfn, 'w'), indent=4)


@app.route('/savepos/<int:cam>/<int:internalcam>/<int:number>/<int:x>/<int:y>/<int:confidence>/<string:label>')
def savepos(cam, internalcam, number, x, y, confidence, label):
    save_pos(cam, internalcam, number, x, y, confidence, label)
    return "done"


@app.route('/deleteallpos/<int:cam>/<int:internalcam>/<int:number>')
def deleteallpos(cam, internalcam, number):
    beetrackfn = pathtoimgsdir + "/bee_track.json"
    try:
        data = json.load(open(beetrackfn, 'r'))
    except FileNotFoundError:
        data = {}
    cam = str(cam)
    number = str(number)
    if cam not in data:
        data[cam] = {}
    if number not in data[cam]:
        data[cam][number] = []
    data[cam][number] = []

    json.dump(data, open(beetrackfn, 'w'), indent=4)
    return "done"


def load_data(cam, internalcam, number):
    beetrackfn = pathtoimgsdir + "/bee_track.json"  # SC: we have no json file
    try:
        data = json.load(open(beetrackfn, 'r'))
    except FileNotFoundError:
        data = {}
    # print(data)
    camst = str(cam)
    # internalcamst = str(internalcam) #not used.
    numberst = str(number)

    if camst not in data:
        return []
    if numberst not in data[camst]:
        return []
    return data[camst][numberst]


@app.route('/loadpos/<int:cam>/<int:internalcam>/<int:number>')
def loadpos(cam, internalcam, number):
    d = load_data(cam, internalcam, number)
    return json.dumps(d)


@app.route('/stick/<int:cam>/<int:internalcam>/<int:number>/<int:numtags>')
def stick(cam, internalcam, number, numtags):
    """
    Experiments using a stick to image multiple tags require lots to be labelled simultaneously.
    This does that.
    """
    d = load_data(cam, internalcam, number)
    fn = getimgfilename(cam, internalcam, number)
    n, img, data = load_img(fn)
    if len(d) != 2:
        return "failed"
    xs = np.linspace(d[0]['x'], d[1]['x'], numtags)
    ys = np.linspace(d[0]['y'], d[1]['y'], numtags)

    # delete the old ones
    deleteallpos(cam, number)

    box = 5  # search box size for bright spots
    for i, (x, y) in enumerate(zip(xs, ys)):
        imgbox = img[int(y-box):int(y+box), int(x-box):int(x+box)]
        brightloc = np.unravel_index(imgbox.argmax(), imgbox.shape)[
            ::-1] + np.array([x, y]) - box
        print(x, y, brightloc)
        print(img[int(y-box):int(y+box), int(x-box):int(x+box)])
        save_pos(cam, number, brightloc[0], brightloc[1], 10, 'sticktag%d' % i)
    return "done"


def load_img(fn):
    try:
        rawdata = np.load(fn, allow_pickle=True)
    except OSError:
        return None, None, None
    if type(rawdata) == list:
        n, img, data = rawdata
    if type(rawdata) == dict:
        n = rawdata['index']
        img = rawdata['img']
        data = rawdata['record']
    return n, img, data


def getcachedshift(cam, internalcam, number):

    path = pathtoimgs[cam]
    cachefile = 'cache/shift_cache_%s.pkl' % (gethash(path.encode("utf-8")))
    if internalcam == 0:
        return None
    try:
        cache = pickle.load(open(cachefile, 'rb'))
    except FileNotFoundError:
        cache = {}
    if cam in cache:
        if number//20 in cache[cam]:
            return cache[cam][number//20]
    else:
        cache[cam] = {}

    fn = getimgfilename(cam, internalcam, number)
    n, img, data = load_img(fn)
    # get 0th internal cam -> should be greyscale...
    fn = getimgfilename(cam, 0, number)
    grey_n, grey_img, grey_data = load_img(fn)
    shift = getshift(grey_img, img, step=1)
    shift[0] -= 2  # trying to correct for difference in camera locations!
    cache[cam][number//20] = shift
    pickle.dump(cache, open(cachefile, 'wb'))
    return shift


@app.route('/getimage/<int:cam>/<int:internalcam>/<int:number>/<int:x1>/<int:y1>/<int:x2>/<int:y2>')
def getimage(cam, internalcam, number, x1, y1, x2, y2):
    fn = getimgfilename(cam, internalcam, number)

    print(fn)
    n, img, data = load_img(fn)

    if img is None:
        return jsonify({'index': -1, 'photo': 'failed', 'record': 'failed'})

    if internalcam > 0:
        shift = getcachedshift(cam, internalcam, number)
        img = shiftimg(img, shift, 0)

    # fns = sorted(glob('%s/*.np'%(pathtoimgs)))
    # if len(fns)==0:
    #    return "Image not found"

    steps = int((x2-x1)/500)
    if steps < 1:
        steps = 1
    # img = (img.T[x1:x2:steps,y1:y2:steps]).T

    img = (img.T[x1:x2, y1:y2]).T
    k = int(img.shape[0] / steps)
    l = int(img.shape[1] / steps)
    img = img[:k*steps, :l *
              steps].reshape(k, steps, l, steps).max(axis=(-1, -3))

    # img[int(img.shape[0]/2),:] = 255
    # img[:,int(img.shape[1]/2)] = 255
    return jsonify({'index': n, 'photo': img.tolist(), 'record': data})


# SC: If you have the debugger disabled or trust the users on your network, you can make the server publicly available simply by adding --host=0.0.0.0 to the command line:This tells your operating system to listen on all public IPs.
if __name__ == "__main__":
    #app.run(host="0.0.0.0", port=port, debug=True)
    app.run(host="0.0.0.0", port=port)

    # print(app.url_map)
