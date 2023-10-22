#!/usr/bin/env python3

import os
import json
from threading import Thread, Timer
import multiprocessing

import moviepy.editor as mp

import tkinter as tk
from tkinter import filedialog
from tkSliderWidget import Slider
from PIL import Image, ImageTk
from tkinterdnd2 import DND_FILES, TkinterDnD

from playsound import playsound

windowObjects = {}
loadedVideo = None
loadedVideoFileName = ""
lastChangedValues = [0, 1]
videoPlaying = False


def handleFileSelect(event=None):
    file = selectFile()
    processSelectedFile(file)


def selectFile():
    filetypes = (("MP4 files", "*.mp4"), ("All files", "*.*"))

    filename = filedialog.askopenfilename(
        title="Open a video file", initialdir="/", filetypes=filetypes
    )

    return filename


def processSelectedFile(file):
    global windowObjects, loadedVideo, loadedVideoFileName

    loadedVideoFileName = file
    loadedVideo = loadVideo(file)
    if loadedVideo is not None:
        values = windowObjects["lengthSlider"].getValues()
        handleSliderChange(values)
        windowObjects["videoName"].config(text=file)
        changeVideoFrame(values[0] * loadedVideo.duration)


def changeVideoFrame(frameNumber):
    global loadedVideo

    canvas = windowObjects["canvas"]
    windowObjects["videoCurrentDesc"].config(
        text="Video Current: " + "{:.2f}".format(frameNumber) + " s"
    )

    if loadedVideo is None:
        return

    videoFrame = loadedVideo.get_frame(frameNumber)
    img = Image.fromarray(videoFrame).resize((1280, 720))
    ph = ImageTk.PhotoImage(img)

    canvas.create_image(0, 0, image=ph, anchor=tk.NW)
    canvas.image = ph


def saveVideo(config):
    global loadedVideo

    if loadedVideo is None:
        print("No video loaded.")
        return

    volume = float(windowObjects["volumeTextBox"].get()) / 100
    length = windowObjects["lengthSlider"].getValues()

    realLength = [loadedVideo.duration * length[0], loadedVideo.duration * length[1]]

    Thread(target=saveVideoThreaded, args=(config, volume, realLength)).start()


def saveVideoThreaded(config, volume, length):
    newVideo = loadedVideo.subclip(length[0], length[1])
    newVideo = newVideo.volumex(volume)

    fileNameWithoutExtension = os.path.splitext(loadedVideoFileName)[0]
    newVideo.write_videofile(fileNameWithoutExtension + config["newFileName"])


def loadVideo(filename):
    if filename == "":
        return None

    try:
        videoClip = mp.VideoFileClip(filename)
        return videoClip

    except Exception as e:
        print(e)
        return None


def debounce(func, delay=0.05):
    def debounced(*args, **kwargs):
        debounced.timer = None

        def call_it():
            func(*args, **kwargs)

        if debounced.timer is not None:
            debounced.timer.cancel()
        debounced.timer = Timer(delay, call_it)
        debounced.timer.start()

    return debounced


def handleSliderChange(values):
    global loadedVideo, lastChangedValues

    if loadedVideo is None:
        return

    changeToStart = values[0] != lastChangedValues[0] or (values[0] == 0)

    videoStart = loadedVideo.duration * values[0]
    videoEnd = loadedVideo.duration * values[1]

    windowObjects["videoStartDesc"].config(
        text="Video Start: " + "{:.2f}".format(videoStart) + " s"
    )
    windowObjects["videoEndDesc"].config(
        text="Video End: " + "{:.2f}".format(videoEnd) + " s"
    )

    lastChangedValues = values

    if changeToStart:
        debounce(changeVideoFrame(videoStart))
    else:
        debounce(changeVideoFrame(videoEnd - 1))


def playAudio(start, end):
    global loadedVideo

    audio = loadedVideo.audio
    audio = audio.subclip(start, end)
    # play audio
    audio.write_audiofile("temp.mp3")

    return multiprocessing.Process(target=playsound, args=("temp.mp3",))


def playVideo():
    global loadedVideo, videoPlaying, lastChangedValues, windowObjects

    if videoPlaying:
        return

    videoPlaying = True

    if loadedVideo is None:
        return

    videoStart = loadedVideo.duration * lastChangedValues[0]
    videoEnd = loadedVideo.duration * lastChangedValues[1]

    player = playAudio(videoStart, videoEnd)
    player.start()

    while videoStart < videoEnd:
        if not videoPlaying:
            player.terminate()
            break
        changeVideoFrame(videoStart)
        videoStart += 0.1

    os.remove("temp.mp3")


def stopVideo():
    global videoPlaying
    videoPlaying = False


def createWindow(config):
    global windowObjects

    if config is None:
        print("Config is not defined. Exiting...")
        return

    window = TkinterDnD.Tk()
    # window = tk.Tk()
    window.title("Video Editor")
    window.geometry("1280x850")
    window.resizable(False, False)

    canvas = tk.Canvas(window, width=1280, height=720)
    canvas.bind("<Button-1>", handleFileSelect)  # on click
    canvas.drop_target_register(DND_FILES)
    canvas.dnd_bind(
        "<<Drop>>", lambda e: processSelectedFile(e.data)
    )  # on drag and drop
    canvas.create_text(640, 360, text="Click to select a video file")
    canvas.pack()
    windowObjects["canvas"] = canvas

    lengthSlider = Slider(window, 1280, 80, 0, 1, [0, 1], False)
    lengthSlider.setValueChageCallback(lambda values: handleSliderChange(values))
    lengthSlider.pack()
    windowObjects["lengthSlider"] = lengthSlider

    canvas2 = tk.Canvas(window, width=1280, height=25)
    canvas2.pack()
    windowObjects["canvas2"] = canvas2

    volumeDesc = tk.Label(canvas2, text="Volume")
    volumeDesc.pack(side=tk.LEFT)
    windowObjects["volumeDesc"] = volumeDesc

    volumeTextBox = tk.Entry(canvas2)
    volumeTextBox.insert(0, config["volume"])
    volumeTextBox.pack(side=tk.LEFT)
    windowObjects["volumeTextBox"] = volumeTextBox

    videoName = tk.Label(canvas2, text="No video selected")
    videoName.pack(side=tk.LEFT)
    windowObjects["videoName"] = videoName

    playVideoThreaded = lambda: Thread(target=playVideo).start()
    videoPlayBtn = tk.Button(canvas2, text="Play Video", command=playVideoThreaded)
    videoPlayBtn.pack(side=tk.RIGHT)
    windowObjects["videoPlayBtn"] = videoPlayBtn

    stopVideoBtn = tk.Button(canvas2, text="Stop Video", command=stopVideo)
    stopVideoBtn.pack(side=tk.RIGHT)
    windowObjects["stopVideoBtn"] = stopVideoBtn

    saveVideoPartial = lambda: saveVideo(config)
    saveVideoButton = tk.Button(canvas2, text="Save Video", command=saveVideoPartial)
    saveVideoButton.pack(side=tk.RIGHT)
    windowObjects["saveVideoButton"] = saveVideoButton

    canvas3 = tk.Canvas(window, width=1280, height=25)
    canvas3.pack()
    windowObjects["canvas3"] = canvas3

    videoStartDesc = tk.Label(canvas3, text="Video Start: N/A")
    videoStartDesc.pack(side=tk.LEFT)
    windowObjects["videoStartDesc"] = videoStartDesc

    videoEndDesc = tk.Label(canvas3, text="Video End: N/A")
    videoEndDesc.pack(side=tk.LEFT)
    windowObjects["videoEndDesc"] = videoEndDesc

    videoCurrentDesc = tk.Label(canvas3, text="Video Current: N/A")
    videoCurrentDesc.pack(side=tk.LEFT)
    windowObjects["videoCurrentDesc"] = videoCurrentDesc

    return window


def main():
    script_dir = os.path.abspath(os.path.dirname(__file__))
    config = json.load(open(os.path.join(script_dir, "config.json"), "r"))

    window = createWindow(config)
    window.mainloop()


if __name__ == "__main__":
    main()
