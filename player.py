import logging
import os
from pathlib import Path
from threading import Thread
import time
import subprocess as sp

from ffpyplayer.player import MediaPlayer
from tinytag import TinyTag


class Player:
    def __init__(self):
        super(Player, self).__init__()
        self.playing_state = "init"
        self.time, self.source_duration = (float, float)
        self.player: MediaPlayer
        self.playlist = list()
        self.loaded = False

    def play(self):
        self.playing_state = "played"
        self.player = MediaPlayer(self.path)


    def load(self, path):
        self.path = path
        self.tag = self.get_tag(self.path)


    def replay(self):
        self.playing_state = "played"
        self.player.set_pause(False)

    def pause_music(self):
        self.playing_state = "paused"
        self.player.set_pause(True)

    def stop_music(self):
        self.playing_state = "stopped"
        self.player.seek(0)
        self.player.set_pause(True)

    def get_duration(self):
        metadata = self.get_tag(self.path)
        duration = metadata.duration
        current_duration = int(self.player.get_pts() / duration * 500)
        return current_duration

    def seek_song(self,  value, max):
        value = int(value)
        current_duration = self.get_duration()
        metadata = self.get_tag(self.path)
        duration = metadata.duration
        if value != 0 and (value - current_duration > 3 or value < current_duration):
            pts = value / max * duration
            pts = round(pts, 2)
            print(pts)
            time.sleep(0.3)
            self.player.seek(pts)

    def get_tag(self, file):
        self.tag = TinyTag.get(file, image=True)
        return self.tag

    def close_player(self):
        self.player.close_player()