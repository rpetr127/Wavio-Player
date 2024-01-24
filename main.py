#!/bin/sh

import asyncio
import copy
import itertools
import json
import logging
import os
import re
import time
from pathlib import Path
import platform
import random
from threading import Timer

import flet as ft
from tinytag import TinyTag

import m3u_parser
from player import Player


def get_dirpath():
    system = platform.system()
    if system == "Linux":
        fname = 'Музыка'
    else:
        fname = 'Music'
    dirpath = "%s/%s" % (Path.home().absolute(), fname)
    return dirpath


def get_items():
    items = [item for item in os.listdir(get_dirpath())
             if re.search(r"(\.(m3u|m3u8)$)", item)]
    return items


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


class PlaylistView(ft.ListView):
    def __init__(self):
        super().__init__(expand=True, spacing=10, padding=10, auto_scroll=False)
        self.__current_index = 0

    @property
    def current_index(self):
        return self.__current_index

    @property
    def current_item(self):
        return self.controls[self.current_index]

    @current_index.setter
    def current_index(self, index):
        self.__current_index = index

    def update_playlist(self, files: list):
        self.controls.clear()
        for file in files:
            print(file.fpath)
            item = PlaylistItem(file)
            self.controls.append(item)
            self.update()
        self.page.update()


class MetadataView(ft.UserControl):
    def __init__(self):
        super().__init__()

    def build(self):
        self.logo_image = ft.Image("icons/melody.png")
        self.title_label = ft.Text("")
        return ft.Container(content=ft.Row([self.title_label, self.logo_image, favorites_view]), padding=3.5)


class PlaylistItem(ft.UserControl):
    def __init__(self, file: File):
        super().__init__()
        self.file = file

    def build(self):
        def item_clicked(e):
            playlist_view.current_index = files.index(self.file)
            print(playlist_view.current_index, len(files))
            print(self.file.fpath)
            player.load(self.file.fpath, page=self.page)
            add_to_recently_played_list(self.file)
            get_song_metadata()
            favorites_view.current_file = self.file
            favorites_view.update()
            self.page.update()

        item = ft.ListTile(title=ft.Text(self.file.fname), on_click=item_clicked)
        return ft.Container(item)


class SidebarItem(ft.UserControl):
    text = str()

    def __init__(self, text, icon=None, rows=None):
        super().__init__()
        self.count = 0
        self.text = text
        self.icon = icon
        self.rows: ft.Column = rows

    def get_items(self):
        items = [SidebarItem(i) for i in get_items()]
        dropdown_rows = ft.Column(items)
        if self.count % 2 != 0:
            print(len(self.rows.controls))
            self.rows.controls.insert(1, dropdown_rows)
            self.rows.update()
        else:
            del self.rows.controls[1]

    @staticmethod
    def add_items():
        global favorites_copy
        playlist = list()
        print(SidebarItem.text)
        with open("config.json", "r") as file:
            data = json.load(file)
            if SidebarItem.text == "Favorites":
                playlist = data["favorites"]
                for file in playlist:
                    if file:
                        file = File(fname=file["name"], fpath=file["path"])
                        favorites.append(file)
                favorites_copy = copy.deepcopy(favorites) 
                       
            elif SidebarItem.text == "Recently played":
                playlist = data["recently_played"]
                for file in playlist:
                    if file:
                        file = File(fname=file["name"], fpath=file["path"])
                        recently_played_list.append(file)

    def build(self):

        def menu_dropdown_event(e):
            self.count += 1
            self.get_items()
            self.page.update()

        def show_playlist_event(e):
            SidebarItem.text = self.text
            playlists = [item for item in get_items() if self.text in get_items()]
            if len(playlists) > 0:
                filepath = "%s/%s" % (get_dirpath(), playlists[0])
                playlist = m3u_parser.load(filepath=filepath)
                print(len(playlist.files))
                for file in playlist.files:
                    if file and file.name != "":
                        print(file.name)
                        file = File(fname=file.name, fpath=file.path)
                        files.append(file)
                playlist_view.update_playlist(files)
            elif SidebarItem.text == "Favorites":
                self.add_items()
                playlist_view.update_playlist(favorites)
            else:
                self.add_items()
                playlist_view.update_playlist(recently_played_list)

        btn_1 = ft.TextButton(icon=self.icon, text=self.text, on_click=show_playlist_event)
        btn_2 = ft.IconButton(icon=ft.icons.ARROW_RIGHT, visible=False)
        if self.rows:
            btn_2 = ft.IconButton(icon=ft.icons.ARROW_DOWNWARD, icon_color=ft.colors.BLUE, on_click=menu_dropdown_event)
        return ft.Card(expand=True, content=ft.Row([btn_1, btn_2]))


class FavoritesView(ft.UserControl):
    def __init__(self):
        super().__init__()
        self._current_file = File()
        self.state = "initialized"

    def favorite_item(self):
        with open("config.json", "r") as file:
            self.data = json.load(file)
            playlist = self.data["favorites"]
            if len(playlist) == 0:
                return False
            items = set()
            for item in playlist:
                if item.get("path") != self.current_file.fpath:
                    items.add(None)
                else:
                    items.add(self.current_file)
            if self.current_file in items:
                return True
            else:
                return False

    @property
    def current_file(self):
        return self._current_file

    @current_file.setter
    def current_file(self, file):
        self._current_file = file

    def update(self):
        print(self.current_file.fname)
        if not self.favorite_item():
            self.button.icon = ft.icons.FAVORITE_BORDER
        else:
            self.button.icon = ft.icons.FAVORITE
        self.button.update()

    def build(self):

        def on_click(e):
            self.state = "changed"
            if not self.favorite_item():
                self.button.icon = ft.icons.FAVORITE
                fav_item = {"name": self.current_file.fname,
                            "path": self.current_file.fpath}
                self.data["favorites"].append(fav_item)
            else:
                self.button.icon = ft.icons.FAVORITE_BORDER
                item = self.favorite_item()
                print(item)
                self.data["favorites"].remove(item)
            self.button.update()
            with open("config.json", "w") as file:
                json.dump(self.data, file)
            if SidebarItem.text == "Favorites":
                SidebarItem.add_items()
                playlist_view.update_playlist(favorites)
            self.page.update()

        self.button = ft.IconButton(on_click=on_click)
        self.button.icon = ft.icons.FAVORITE
        return self.button


class ShuffleButton(ft.UserControl):
    def __init__(self):
        super().__init__()
        self.is_shuffled = False

    def build(self):
        
        def on_click(e):
            global files, favorites
            index = int()
            if not self.is_shuffled:
                self.is_shuffled = True
                if SidebarItem.text != "Recently played":
                    if playlist_view.current_index:
                        index = playlist_view.current_index
                    else:
                        index = 0
                    if SidebarItem.text != "Favorites":
                        random.shuffle(files)
                    else:
                        random.shuffle(favorites)
                self.button.icon = ft.icons.SHUFFLE_ON_SHARP                
            else:
                self.is_shuffled = False
                if SidebarItem.text != "Recently played":
                    playlist_view.current_index = index
                    if SidebarItem.text != "Favorites":
                        files = copy.deepcopy(files_copy)        
                    else:
                        favorites = copy.deepcopy(favorites)
                self.button.icon = ft.icons.SHUFFLE_OUTLINED
            self.button.update()
                
        self.button = ft.IconButton(icon=ft.icons.SHUFFLE_OUTLINED, on_click=on_click)
        return self.button
    

class RepeatButton(ft.UserControl):
    def __init__(self):
        super().__init__()
        self.is_repeated = False

    def build(self):

        def on_click(e):
            if not self.is_repeated:
                self.is_repeated = True
                self.button.icon = ft.icons.REPEAT_ON
            else:
                self.is_repeated = False
                self.button.icon = ft.icons.ARROW_RIGHT_ALT
            self.button.update()

        self.button = ft.IconButton(icon = ft.icons.ARROW_RIGHT_ALT, on_click=on_click)
        return self.button
    

logger = logging.getLogger()
player = Player()
# DEFAULT_FLET_PATH = ''  # or 'ui/path'
# DEFAULT_FLET_PORT = 8502
files, favorites, recently_played_list, files_copy, favorites_copy = itertools.repeat(Files(), 5)
playlist_view = PlaylistView()
metadata_view = MetadataView()
favorites_view = FavoritesView()
repeat_button = RepeatButton()
shuffle_button = ShuffleButton()


def get_song_metadata():
    tag = player.tag
    text = f'{tag.title}\n{tag.artist} - {tag.album}'
    metadata_view.title_label.value = text
    metadata_view.logo_image.src = tag.get_image()
    metadata_view.update()


def add_to_recently_played_list(file_item: File):
    data = dict()
    with open("config.json", "r") as file:
        data = json.load(file)
    with open("config.json", "w") as file:
        item = {
                "name": file_item.fname,
                "path": file_item.fpath
            }
        if item not in data["recently_played"]:
            data["recently_played"].append(item)
        json.dump(data, file)


def main(page: ft.Page):
    # w, h = (420, 720)
    # page.window_resizable = False
    # page.window_width = w
    # page.window_height = h
    # page.window_visible = True
    main_view = ft.Column(expand=True)
    playlist_row = ft.Row(expand=True)
    sidebar = ft.Column()

    def add_files_result(e: ft.FilePickerResultEvent):
        if len(e.files) > 0 or e.path.endswith(".mp3, .flac, .aac, .wav, .wma"):
            for file in e.files:
                file = File(fname=file.name, fpath=file.path)
                files.append(file)
            return playlist_view.update_playlist(files)

    open_files_dialog = ft.FilePicker(on_result=add_files_result)
    page.overlay.append(open_files_dialog)
    page.update()

    def add_directory_result(e: ft.FilePickerResultEvent):
        flist = os.listdir(e.path)
        for item in flist:
            if item and item != "" and re.search(r"\.(mp3|wav|wma|aac|flac)", item):
                file = File(fname=item, fpath="%s/%s" % (e.path, item))
                files.append(file)
        return playlist_view.update_playlist(files)

    add_folder_dialog = ft.FilePicker(on_result=add_directory_result)
    page.overlay.append(add_folder_dialog)
    page.update()

    def add_playlist_result(e: ft.FilePickerResultEvent):
        print(e.files[0].path)
        playlist = m3u_parser.load(filepath=e.files[0].path)
        print(playlist.files)
        for file in playlist.files:
            print(file)
            if file and file != "":
                file = File(fname=file.name, fpath=file.path)
                files.append(file)
        return playlist_view.update_playlist(files)

    open_playlist_dialog = ft.FilePicker(on_result=add_playlist_result)
    page.overlay.append(open_playlist_dialog)
    page.update()

    def open_dir_result(e: ft.FilePickerResultEvent):
        files.clear()
        add_directory_result(e)

    open_dir_dialog = ft.FilePicker(on_result=open_dir_result)
    page.overlay.append(open_dir_dialog)
    page.update()

    def open_playlist_result(e: ft.FilePickerResultEvent):
        files.clear()
        add_playlist_result(e)

    open_playlist_dialog = ft.FilePicker(on_result=open_playlist_result)
    page.overlay.append(open_playlist_dialog)
    page.update()

    def save_playlist(e: ft.FilePickerResultEvent):
        filepath = e.path
        if e.path:
            for file in files:
                command = "echo '%s' >> %s" % (
                    file.fpath, filepath)
                asyncio.run(asyncio.create_subprocess_shell(command))

    save_playlist_dialog = ft.FilePicker(on_result=save_playlist)
    page.overlay.append(save_playlist_dialog)
    page.update()

    def popup_menu_item(icon, text, on_click):
        return ft.PopupMenuItem(content=ft.Row([
            ft.Icon(icon),
            ft.Text(text)
        ]), on_click=on_click)

    dd = ft.PopupMenuButton(icon=ft.icons.ADD_CIRCLE, items=[
        popup_menu_item(icon=ft.icons.FILE_OPEN, text="Add file",
                        on_click=lambda _: open_files_dialog.pick_files(dialog_title="Add files to queue",
                                                                        initial_directory=init_dir,
                                                                        file_type=ft.FilePickerFileType.AUDIO,
                                                                        allow_multiple=True)),
        popup_menu_item(icon=ft.icons.FOLDER_OPEN, text="Add folder",
                        on_click=lambda _: add_folder_dialog.get_directory_path(dialog_title="Add folder to queue",
                                                                                initial_directory=init_dir)),
        popup_menu_item(icon=ft.icons.PLAYLIST_ADD, text="Add playlist",
                        on_click=lambda _: open_playlist_dialog.pick_files(dialog_title="Add playlist to queue",
                                                                           allowed_extensions=["m3u", "m3u8", "pls"],
                                                                           allow_multiple=False)),
        popup_menu_item(icon=ft.icons.FOLDER_OPEN, text="Open folder",
                        on_click=lambda _: open_dir_dialog.get_directory_path(dialog_title="Open folder",
                                                                              initial_directory=init_dir)),
        popup_menu_item(icon=ft.icons.PLAYLIST_ADD, text="Open playlist",
                        on_click=lambda _: open_playlist_dialog.pick_files(dialog_title="Open playlist",
                                                                           allowed_extensions=["m3u", "m3u8", "pls"],
                                                                           allow_multiple=False))
    ])

    dd_2 = ft.IconButton(ft.icons.SAVE_AS, on_click=lambda _: save_playlist_dialog.save_file(
        dialog_title="Save playlist", ))

    def skip_previous():
        index = playlist_view.current_index
        index -= 1
        playlist_view.current_index = index
        play_icon.icon = ft.icons.PLAY_ARROW
        page.update()
        time.sleep(0.3)
        file = files[index]
        path = file.fpath
        player.load(path)
        add_to_recently_played_list(file)
        SidebarItem.add_items()
        if SidebarItem.text == "Recently played":
            playlist_view.update_playlist(files_2)
        player.play()
        get_song_metadata()
        play_icon.icon = ft.icons.PAUSE
        page.update()

    def play():
        timer = Timer(0.1, start_timer)
        if player.playing_state == "init":
            play_icon.icon = ft.icons.PAUSE
            page.update()
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
        index = playlist_view.current_index
        print(index, len(files))
        if index == len(files) - 1: 
            if repeat_button.is_repeated:
                if shuffle_button.is_shuffled:
                    random.shuffle(files)
                index = -1
            else:
                return
        index += 1
        playlist_view.current_index = index
        play_icon.icon = ft.icons.PLAY_ARROW
        page.update()
        file = files[index]
        path = files[index].fpath
        player.load(path)
        add_to_recently_played_list(file)
        SidebarItem.add_items()
        if SidebarItem.text == "Recently played":
            playlist_view.update_playlist(recently_played_list)
        player.play()
        get_song_metadata()
        play_icon.icon = ft.icons.PAUSE
        page.update()

    def playback_event():
        pts = player.get_duration()
        print(pts, slider.max)
        if pts == slider.max - 1:
            skip_next()

    def set_slider_pos():
        slider.value = player.get_duration()
        slider.update()

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
        title=ft.Text("Wavio Player"),
        center_title=False,
        bgcolor=ft.colors.SURFACE_VARIANT,
        actions=[dd, dd_2])

    files_copy = copy.deepcopy(files)



    sidebar.controls.append(SidebarItem("Playlists", ft.icons.MUSIC_NOTE, sidebar))
    sidebar.controls.append(SidebarItem("Favorites", ft.icons.FAVORITE_SHARP))
    sidebar.controls.append(SidebarItem("Recently played", ft.icons.TIME_TO_LEAVE_SHARP))

    playlist_row.controls.append(sidebar)
    playlist_row.controls.append(ft.VerticalDivider(width=2))
    playlist_row.controls.append(playlist_view)
    main_view.controls.append(playlist_row)
    main_view.controls.append(ft.Divider(height=2))

    prev_icon = ft.IconButton(icon=ft.icons.SKIP_PREVIOUS, on_click=lambda _: skip_previous())
    play_icon = ft.IconButton(icon=ft.icons.PLAY_ARROW, on_click=lambda _: play())
    forward_icon = ft.IconButton(icon=ft.icons.SKIP_NEXT, on_click=lambda _: skip_next())
    main_view.controls.append(ft.Row(controls=[shuffle_button, prev_icon, play_icon, forward_icon,
                                               metadata_view, repeat_button],
                                     alignment=ft.MainAxisAlignment.CENTER))

    slider = ft.Slider(min=0, max=500, on_change=slider_changed)
    slider.autofocus = False
    main_view.controls.append(slider)

    index = int()
    page.title = "Wavio Player"
    init_dir = str(Path.home().absolute())
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.add(main_view)
    # page.update()


if __name__ == '__main__':
    ft.app(target=main, view=ft.FLET_APP_WEB)
