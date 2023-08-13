#!/bin/sh

import asyncio
import logging
import os
import time
from pathlib import Path
import re
from threading import Thread, Timer

import flet as ft
from tinytag import TinyTag

from player import Player

logger = logging.getLogger()


class File:
    def __init__(self, fname=None, fpath=None):
        self.fname = fname
        self.fpath = fpath


class Files(list):
    def __init__(self, *args, **kwargs):
        super(Files, self).__init__(args)
        self.type = File

    def append(self, item):
        if not isinstance(item, self.type):
            raise TypeError('item is not of type %s' % self.type)
        super(Files, self).append(item)  # append the item to itself (the list)

    def __next__(self):
        yield self.type



def main(page: ft.Page):
    w, h = (420, 720)
    page.window_resizable = False
    page.window_width = w
    page.window_height = h
    page.window_visible = True
    logo_image = ft.Image("icons/melody.png")
    title_label = ft.Text("")
    view = ft.Column(expand=True)
    lv = ft.ListView(expand=1, spacing=10, padding=20, auto_scroll=True)

    def open_files_result(e: ft.FilePickerResultEvent):
        if len(e.files) > 0 or e.path.endswith((".mp3, .flac, .aac, .wav, .wma")):
            for file in e.files:
                files.append(File(fname=file.name, fpath=file.path))
            return update_playlist()

    open_files_dialog = ft.FilePicker(on_result=open_files_result)
    page.overlay.append(open_files_dialog)
    page.update()

    def open_directory_result(e: ft.FilePickerResultEvent):
        flist = os.listdir(e.path)
        for item in flist:
            if item and item != "":
                file = File(fname=item, fpath="%s/%s" % (e.path, item))
                files.append(file)
        return update_playlist()

    open_folder_dialog = ft.FilePicker(on_result=open_directory_result)
    page.overlay.append(open_folder_dialog)
    page.update()

    def open_playlist_result(e: ft.FilePickerResultEvent):
        if e.path.endswith(".m3u, .m3u8"):
            ...
        page.update()
        return update_playlist()

    open_playlist_dialog = ft.FilePicker(on_result=open_playlist_result)
    page.overlay.append(open_folder_dialog)
    page.update()

    dd = ft.PopupMenuButton(icon=ft.icons.ADD_CIRCLE, items=[
        ft.PopupMenuItem(content=ft.Row([
            ft.Icon(ft.icons.FILE_OPEN),
            ft.Text("Add file")
        ]), on_click=lambda _: open_files_dialog.pick_files(initial_directory=init_dir,
                                                            file_type=ft.FilePickerFileType.AUDIO,
                                                            allow_multiple=True)),
        ft.PopupMenuItem(content=ft.Row([
            ft.Icon(ft.icons.FOLDER_OPEN),
            ft.Text("Add folder")
        ]), on_click=lambda _: open_folder_dialog.get_directory_path(initial_directory=init_dir)),
        ft.PopupMenuItem(content=ft.Row([
            ft.Icon(ft.icons.PLAYLIST_ADD),
            ft.Text("Open playlist")
        ]), on_click=lambda _: open_playlist_dialog.pick_files(initial_directory=init_dir,
                                                               allowed_extensions=["m3u", "m3u8", "pls"]))])



    def skip_previous():
        nonlocal index
        print(index)
        index -= 1
        lv.controls[index].selected = True
        play_icon.icon = ft.icons.PLAY_ARROW
        page.update()
        time.sleep(0.3)
        path = files[index].fpath
        player.load(path)
        player.play()
        get_song_metadata()
        play_icon.icon = ft.icons.PAUSE
        page.update()


    def play():
        timer = Timer(0.1, start_timer)
        if player.playing_state == "init":
            play_icon.icon = ft.icons.PAUSE
            page.update()
            player.load(files[index].fpath)
            player.play()
            timer.start()
            time.sleep(0.5)
        elif player.playing_state == "played":
            play_icon.icon = ft.icons.PLAY_ARROW
            page.update()
            player.pause_music()
            timer.cancel()
        elif player.playing_state == "paused":
            play_icon.icon = ft.icons.PAUSE
            page.update()
            player.replay()
            timer = Timer(0.1, playback_event)
            timer.start()

    def skip_next():
        nonlocal index, player
        print(index)
        index += 1
        lv.controls[index].selected = True
        play_icon.icon = ft.icons.PLAY_ARROW
        page.update()
        path = files[index].fpath
        player.load(path)
        player.play()
        get_song_metadata()
        play_icon.icon = ft.icons.PAUSE
        page.update()

    def get_song_metadata():
        tag = player.tag
        text = f'{tag.title}\n{tag.artist} - {tag.album}'
        title_label.value = text
        logo_image.src = tag.get_image()
        page.update(title_label, logo_image)

    def playback_event():
        pts = player.get_duration()
        if pts == slider.max:
            skip_next()

    def set_slider_pos():
        time.sleep(0.3)
        slider.value = player.get_duration()
        page.update()

    def start_timer():
        while True:
            set_slider_pos()
            playback_event()

    def slider_changed(e):
        value = e.control.value
        max = slider.max
        player.seek_song(value, max)
        set_slider_pos()

    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.icons.PALETTE),
        leading_width=20,
        title=ft.Text("CWavePlayer"),
        center_title=False,
        bgcolor=ft.colors.SURFACE_VARIANT,
        actions=[dd])

    def item_clicked(ind):
        nonlocal index
        index = ind
        path = files[index].fpath
        player.load(path)
        get_song_metadata()

    def list_item(file):
        return ft.Container(
            ft.ListTile(title=ft.Text(file.fname), on_click=lambda e: item_clicked(files.index(file))))

    def update_playlist():
        for file in files:
            lv.controls.append(list_item(file))
        page.update()

    prev_icon = ft.IconButton(icon=ft.icons.SKIP_PREVIOUS, on_click=lambda _: skip_previous())
    play_icon = ft.IconButton(icon=ft.icons.PLAY_ARROW, on_click=lambda _: play())
    forward_icon = ft.IconButton(icon=ft.icons.SKIP_NEXT, on_click=lambda _: skip_next())

    view.controls.append(lv)
    view.controls.append(ft.Row(controls=[prev_icon, play_icon, forward_icon,
                                          logo_image, title_label],
                                alignment=ft.MainAxisAlignment.CENTER))

    slider = ft.Slider(min=0, max=499, on_change=slider_changed)
    slider.autofocus = False
    view.controls.append(slider)

    index = int()
    page.title = "Player"
    player = Player()
    init_dir = str(Path.home().absolute())
    files = Files()
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.add(view)
    page.update()


if __name__ == '__main__':
    ft.app(target=main, view=ft.FLET_APP_WEB)
