import logging
import os
from pathlib import Path
from threading import Thread
import traceback
import time
import subprocess as sp

import flet as ft
from tinytag import TinyTag


class Player:
    def __init__(self):
        super(Player, self).__init__()
        self.playing_state = "init"
        self.time, self.source_duration = (float, float)
        self.player = ft.Audio()
        self.playlist = list()
        self.loaded = False

    def play(self):
        self.playing_state = "played"
        my_thread = Thread(target=self.player.play)
        my_thread.start()
        self.player.autoplay = True


    def load(self, path: str, page: ft.Page = None):
        self.path = path
        if self.playing_state == "init":
            page.overlay.append(self.player)
        self.player.src = path
        self.tag = self.get_tag(self.path)


    def replay(self):
        self.playing_state = "played"
        pos = self.player.get_current_position()
        self.player.seek(pos)
        my_thread = Thread(target=self.player.play)
        my_thread.start()

    def pause_music(self):
        self.playing_state = "paused"
        self.player.pause()

    def stop_music(self):
        self.playing_state = "stopped"
        self.player.seek(0)
        self.player.pause()

    def get_duration(self):
        try:
            duration = self.player.get_duration()
            current_duration = int(self.player.get_current_position() / duration * 500)
        except:
            traceback.format_exc()
            current_duration = 0
        return current_duration

    def seek_song(self,  value, max):
        value = int(value)
        current_duration = self.get_duration()
        metadata = self.get_tag(self.path)
        duration = self.player.get_duration()
        if value != 0 and (value - current_duration > 3 or value < current_duration):
            pts = value / max * duration
            pts = round(pts)
            print(pts)
            self.player.seek(pts)

    def get_tag(self, file):
        self.tag = TinyTag.get(file, image=True)
        return self.tag

    def close_player(self):
        self.player.clean()
