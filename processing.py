from PIL import Image

import numpy as np
import pandas as pd

import os
import io
import socket
import struct

import collections
import time

import base64
import requests

import matplotlib

import atexit

import subprocess as sp

binwidth = 5

def get_changed_pixels(image, background, pixeldiffcutoff=10):
    diff = image.astype(np.int16) - background.astype(np.int16)
    changedpixels = image[diff.max(2) >= pixeldiffcutoff]
    return changedpixels

def count(changed_pixels):
    return (changed_pixels / (2**binwidth) * np.array([2**0, 2**binwidth, 2**(binwidth * 2)])).sum(1).astype(np.int).tolist()

pixeldiffcutoff = 20

class Master:
    def __init__(self, folder, ssh=None, delete=False, save=False, gates=[], bins=[], pictures=[], decisionmaker_args = {}, processor_args = {}):
        self.server = Server()
        self.sorter = Sorter(self, ssh)
        self.decisionmaker = DecisionMaker(self, **decisionmaker_args)
        self.processor = ImageProcessor(self, folder, delete=delete, save=save, **processor_args)

        self.ssh = ssh

        # initialize server
        initialData = {}
        initialData["signal"] = "initialize"
        initialData["bins"] = [
            {"id":i, "color":matplotlib.colors.cnames[name]} for i, name in enumerate(bins)
        ]
        initialData["bincounts"] = [
            [] for i in bins
        ]

        initialData["directions"] = [{"colors":list(colors), "picture":pictures[i]} for i, colors in enumerate(gates)]
        initialData["frameids"] = [-1]

        self.server.send(initialData, "initialize")

        # register atexit
        atexit.register(self.finish)
        
    def run_camera(self, nseconds = 10):
        def listener(processor):
            # Start a socket listening for connections on 0.0.0.0:8002
            #sp.call("fuser 8002/tcp -k", shell=True) # kill everyone listening at 8002
            server_socket = socket.socket()
            server_socket.bind(('0.0.0.0', 8002))
            server_socket.listen(0)

            # Accept a single connection and make a file-like object out of it
            connection = server_socket.accept()[0].makefile('rb')

            frameid = 0

            try:
                while True:
                    # Read the length of the image as a 32-bit unsigned int. If the
                    # length is zero, quit the loop
                    image_len = struct.unpack('<L', connection.read(struct.calcsize('<L')))[0]
                    if not image_len:
                        break
                    # Construct a stream to hold the image data and read the image
                    # data from the connection
                    image_stream = io.BytesIO()
                    image_stream.write(connection.read(image_len))
                    # Rewind the stream, open it as an image with PIL and do some
                    # processing on it
                    image_stream.seek(0)
                    image = Image.open(image_stream)
                    #print('Image is %dx%d' % image.size)
                    #image.verify()
                    #print('Image is verified')
                    self.processor.process(image, frameid)

                    frameid += 1
            finally:
                connection.close()
                server_socket.shutdown(socket.SHUT_RDWR)
                server_socket.close()

            return image

        def start_stream(nseconds=10):
            stdin, stdout, stderr = self.ssh.exec_command("python3 flow2/stream.py " + str(nseconds) + " &")

        start_stream(nseconds)
        image = listener(self.processor)
        
        self.finish()
        
    def run_local(self):
        folder = self.processor.imagefolder
        frameids = sorted([int(file.split(".")[0]) for file in os.listdir(folder) if file.endswith(".jpg")])
        print(len(frameids))
        for i in frameids:
            image = Image.open(folder + str(i) + ".jpg")

            i = i + self.processor.warmup
            
            self.processor.process(image, i)
        self.finish()
        
    def finish(self):
        print("finish")
        self.processor.finish()
        self.sorter.finish()

class ImageProcessor:
    def __init__(self, master, imagefolder, delete=True, save=True, colorbin_models = [], warmup=10, ball_rolling_cutoff = 1000):
        self.master = master
        self.imagefolder = imagefolder
        if os.path.exists(imagefolder):
            if delete:
                for file in os.listdir(imagefolder):
                    os.unlink(imagefolder + "/" + file)
        else:
            os.makedirs(imagefolder)
            
        self.background = None
        self.diffs = []
        
        self.diffs_local = collections.deque(maxlen=4)
        self.diffs_global = collections.deque(maxlen=100)
        
        self.warmup = warmup
        self.ball_rolling_cutoff = ball_rolling_cutoff
        
        self.ball = False

        self.colorbin_models = colorbin_models
        
        self.log = []
        
        self.save = save

        self.start = 0
            
    def process(self, image, frameid):
        if(frameid == 0):
            print(">>  Receiving images ----------------------------------------")
            
        if self.save:
            image.save(self.imagefolder + "/" + str(frameid-self.warmup) + ".jpg")
        
        # Now check for passing balls
        # only check after warmup
        if frameid >= self.warmup:
            if frameid == self.warmup:
                print(">>  Warm up ended -------------------------------------------")
                self.start = time.time()
                
            frameid = frameid - self.warmup
            self.frameid = frameid

            rgb = np.array(image)

            if self.background is None:
                self.background = rgb

            changed_pixels = get_changed_pixels(rgb, self.background, pixeldiffcutoff)
            ndiff = changed_pixels.shape[0]

            self.diffs_local.append(ndiff)
            self.diffs_global.append(ndiff)
            self.diffs.append(ndiff)
            
            rolling_global = np.mean(self.diffs_global)
            rolling_local = np.mean(self.diffs_local)
            
            rolling_fold = rolling_local/rolling_global

            counts = count(changed_pixels)
            
            if not self.ball and rolling_local > self.ball_rolling_cutoff:
                # new ball
                print("Ball is passing by...")
                self.ball = True
                self.ballcounts = counts
                self.ballstart = frameid
            elif self.ball and rolling_local < self.ball_rolling_cutoff:
                # ball has passed
                print("Ball has passed...")
                self.ball = False
                self.ballend = frameid
                self.master.decisionmaker.decide(self.ballcounts, self.ballstart, self.ballend)
            elif self.ball:
                # add information
                self.ballcounts.extend(counts)
            
            self.log.append({
                "rolling_global":rolling_global,
                "rolling_local":rolling_local,
                "rolling_fold":rolling_fold,
                "ball":self.ball,
                "counts":counts,
                "frameid":frameid
            })
            
            # change background to last frame
            self.background = rgb

            if frameid % 1 == 0:
                bincounts = np.bincount(counts, minlength=2**(3*binwidth))

                newcounts = [model.predict_proba(bincounts.reshape(-1, 2**(3*binwidth)))[0, 1] for model in self.colorbin_models]
                #newcounts = [0, 0, 0, 0]

                # send to server
                packet = {
                   "signal":"newCounts",
                   "newcounts":[[float(np.max([i-0.5, 0])*2 * np.random.random())] for i in newcounts]
                }
                if frameid % 3 == 0:
                    stream = io.BytesIO()
                    image.save(stream, format="png")
                    encodedimage = base64.b64encode(stream.getvalue())
                    packet["image"] = "data:image/png;base64," + encodedimage.decode("utf-8")
                self.master.server.send(packet, "publish")
    
    def finish(self):
        self.log = pd.DataFrame(self.log)
        
        totaltime = time.time() - self.start
        print(" Total time: " + str(totaltime))
        print(" FPS:        " + str(self.frameid/totaltime))

class DecisionMaker:
    def __init__(self, master, gatenames=("blue","blue_orange","green_orange","yellow","yellow_blue"), knn_model=None):
        self.master = master
        self.gatenames = gatenames
        self.knn_model = knn_model
        self.balls = []

        print(gatenames)
    
    def decide(self, ballcounts, ballstart, ballend):
        bincounts = np.bincount(ballcounts, minlength=2**(3*binwidth))/(ballend-ballstart)
        
        self.balls.append({
                "bincounts":bincounts,
                "ids":range(ballstart, ballend)
            })
        
        print("deciding...")

        if self.knn_model is None:
            gateid = np.random.choice(range(len(self.gatenames)))
        else:
            gateid = self.knn_model.predict([bincounts])[0]
        
        # send to server
        if gateid in self.gatenames:
            packet = {
                "signal":"decision",
                "directionid":self.gatenames.index(gateid)
            }

            self.master.server.send(packet, "publish")

        # send to sorter
        self.master.sorter.send(gateid)

class Sorter:
    def __init__(self, master, ssh):
        self.master = master
        self.ssh = ssh
        if self.ssh is not None:
            # start up the sorter on raspberry
            self.s = None
            start = time.time()
            while self.s is None and (time.time() - start < 2):
                try:
                    # connect to socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    host ="172.24.1.1"
                    port = 8001
                    s.connect((host,port))
                    self.s = s
                except:
                    print("Trying to connect to sorter...")
                    time.sleep(0.05)

            if self.s is not None:
                print("Connected to sorter")
            else:
                raise ValueError("Sorter cannot connect to port 8001")
        else:
            print("Not connecting sorter")

    def send(self, r):
        print("Sending gate", r)
        if self.ssh is not None:
            self.s.send(r.encode())
    
    def finish(self):
        if self.ssh is not None:
            self.s.close()

def stop_framboos(ssh):
    if ssh is not None:
        stdin, stdout, stderr = ssh.exec_command("pkill python3")

class Server:
    def __init__(self):
        ""
    def send(self, packet, adress="publish"):
        requests.post(r"http://localhost:5000/" + adress, json=packet, timeout=5)
