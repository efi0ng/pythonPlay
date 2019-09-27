#!/usr/bin/env python3
# DeoVr doc: https://deovr.com/doc

import os
from pathlib import Path  # https://docs.python.org/3/library/pathlib.html
from typing import Optional, Any
import json
import re


_DESCRIPTOR_SUFFIX = ".desc"
_ROOT_DIR_WIN = Path("N:/vr")
_ROOT_DIR_LINUX = Path("~/mnt/oook/vr").expanduser()
_BASE_URL: str = "http://192.168.0.4/vr/"


def urljoin(*args):
    """
    Joins given arguments into an url. Trailing but not leading slashes are
    stripped for each argument.
    Credit: https://stackoverflow.com/questions/1793261/how-to-join-components-of-a-path-when-you-are-constructing-a-url-in-python
    Credit: Rune Kaagaard
    """
    return "/".join(map(lambda x: str(x).rstrip('/'), args))


class TimeStamp:
    def __init__(self, name: str, seconds: int):
        self.seconds = seconds
        self.name = name


class TimeCode:
    _REGEX = []

    @staticmethod
    def ints_to_duration(h: int, m: int, s: int):
        return h*3600 + m*60 + s

    @staticmethod
    def text_to_duration(h: str, m: str, s: str):
        return TimeCode.ints_to_duration(int(h), int(m), int(s))

    @staticmethod
    def parse_hhmmss(time_string):
        """Must pass in a valid 00:00:00 value"""
        (h, m, s) = time_string.split(":")
        return TimeCode.text_to_duration(h, m, s)

    @staticmethod
    def parse_mmss(time_string):
        """Must pass in a valid 00:00 value"""
        (m, s) = time_string.split(":")
        return TimeCode.text_to_duration("0", m, s)

    @staticmethod
    def parse_0h0m0s(time_string):
        """Must pass in a valid 0h0m0s value"""
        time_str = time_string.strip("s")
        (h, x) = time_str.split("h")
        (m, s) = x.split("m")
        return TimeCode.text_to_duration(h, m, s)

    @staticmethod
    def parse_seconds(time_string):
        """Must pass valid ##### value."""
        return int(time_string)

    @staticmethod
    def is_valid(time: str):
        """Allow either 00:00:00 or 00:00 or 0h0m0s or 0 (seconds)"""
        if type(time) is int:
            return True

        for regex in TimeCode._REGEX:
            if re.fullmatch(regex[0], time):
                return True

        return False

    @staticmethod
    def duration(time: Any):
        # if duration was specified as seconds it may already be an int
        if type(time) is int:
            return time

        for regex in TimeCode._REGEX:
            if re.fullmatch(regex[0], time):
                return regex[1](time)

        raise Exception('Invalid timecode format: "{}"'.format(time))


TimeCode._REGEX = [
    (r"\d\d:\d\d:\d\d", TimeCode.parse_hhmmss),
    (r"\d\d:\d\d", TimeCode.parse_mmss),
    (r"\d\d?h\d\d?m\d\d?s", TimeCode.parse_0h0m0s),
    (r"\d+", TimeCode.parse_seconds)]


class DeoVrVideo:
    DURATION = "videoLength"
    RESOLUTION = "resolution"
    ENCODINGS = "encodings"
    VIDEO_SOURCES = "videoSources"
    SCREEN_TYPE = "screenType"
    STEREO_MODE = "stereoMode"
    IS_3D = "is3d"

    def __init__(self, title: str, video_url: str, thumb_url: str, json_url: str, json_path: Path, desc_path: Path):
        self.json_url: str = json_url
        self.json_path: str = json_path
        self.video_url: str = video_url
        self.desc_path: Path = desc_path

        self.json = {
            "encodings": [{
                "name": "h264",
                "videoSources": [{
                    "url": video_url
                }]
            }],
            "title": title,
            "id": 0,
            "is3d": True,
            "screenType": "dome",
            "stereoMode": "sbs",
            "skipIntro": 0,
            "thumbnailUrl": thumb_url,
            "corrections": {
                "x": 0,
                "y": 0,
                "br": 0,
                "cont": 0,
                "sat": 0
            }
        }

    def to_json(self) -> object: return self.json

    def to_index_json(self) -> object:
        """Return the deovr index entry json object"""
        result = {
            "title": self.json["title"],
            "thumbnailUrl": self.json["thumbnailUrl"],
            "video_url": self.json_url
        }

        if DeoVrVideo.DURATION in self.json:
            result[DeoVrVideo.DURATION] = self.json[DeoVrVideo.DURATION]

        return result

    def get_video_json(self) -> object:
        return self.json

    def get_video_url(self) -> str:
        return self.video_url

    def get_desc_path(self) -> str:
        return self.desc_path

    def set_preview(self, preview_url):
        self.json["videoPreview"] = preview_url

    def set_seek(self, seek_url):
        self.json["videoThumbnail"] = seek_url

    def set_duration(self, duration):
        if duration > 0:
            self.json[DeoVrVideo.DURATION] = duration

    def set_screen_type(self, screen_type):
        self.json[DeoVrVideo.SCREEN_TYPE] = screen_type

    def set_stereo_mode(self, stereo_mode):
        self.json[DeoVrVideo.STEREO_MODE] = stereo_mode
        if stereo_mode == "off":
            self.json[DeoVrVideo.IS_3D] = False

    def set_2d(self):
        '''Short hand to set up video as flat 2d'''
        self.json[DeoVrVideo.STEREO_MODE] = "off"
        self.json[DeoVrVideo.IS_3D] = False
        self.json.pop(DeoVrVideo.SCREEN_TYPE, None)

    def set_3d(self, is_3d: bool):
       self.json[DeoVrVideo.IS_3D] = is_3d

    def set_resolution(self, resolution):
        if resolution > 0:
            h264_encoding = self.json[DeoVrVideo.ENCODINGS][0]
            h264_encoding[DeoVrVideo.VIDEO_SOURCES][0][DeoVrVideo.RESOLUTION] = resolution

    def set_time_stamps(self, stamps):
        timestamps = []

        for stamp in stamps:
            timestamps.append({
                "ts": stamp.seconds,
                "name": stamp.name
            })

        self.json["timeStamps"] = timestamps

    def set_time_stamps_raw(self, json_stamps):
        self.json["timeStamps"] = json_stamps


class DeoVrScene:
    def __init__(self, name: str):
        self.name = name
        self._videos: [DeoVrVideo] = []

    @property
    def videos(self): return self._videos

    def add_video(self, video: DeoVrVideo):
        self._videos.append(video)

    def to_json(self) -> object:
        """Return scenes json object given the tab contents"""

        video_json = []
        for video in self._videos:
            video_json.append(video.to_index_json())

        return {
                "name": self.name,
                "list": video_json
        }


class DeoVrCatalog:
    def __init__(self):
        self.scenes: [DeoVrScene] = []

    def add_scene(self, scene: DeoVrScene):
        self.scenes.append(scene)

    def to_json(self):
        scene_json = []
        for scene in self.scenes:
            scene_json.append(scene.to_json())

        return {
            "scenes": scene_json
        }


class VrDescLabels:
    TITLE = "title"
    SITE = "site"
    VIDEO = "video"
    PREVIEW = "preview"
    SEEK = "seek"
    DURATION = "duration"
    GROUP = "group"
    ACTORS = "actors"
    RESOLUTION = "resolution"
    TIME_STAMPS = "timeStamps"
    TS_TIMECODE = "ts"
    TS_NAME = "name"
    SCREEN_TYPE = "type"
    STEREO_MODE = "stereo"


class VrVideoDesc:
    """VR Video for the index"""
    THUMB_EXT = ".jpg"
    SEEK_SUFFIX = "_seek.mp4"
    PREVIEW_SUFFIX = "_preview.mp4"
    DEOVR_EXT = ".deovr"
    VIDEO_SUFFIX = ".mp4"
    SCREEN_TYPE_2D = "2D"

    def __init__(self, desc_path: Path,
                 parent_path: Path, parent_url: str,
                 title: str, group: str,
                 video_url: str, thumb_url: str,
                 duration: int = 0, resolution: int = 0):
        self.desc_path: Path = desc_path
        self._parent_path: Path = parent_path
        self._parent_url: str = parent_url
        self.title: str = title
        self.video_url: str = video_url
        self.thumb_url: str = thumb_url
        self.preview_url: Optional[str] = None
        self.seek_url: Optional[str] = None
        self.time_stamps: Any = None
        self.duration: int = duration
        self.resolution: int = resolution
        self.screen_type: Optional[str] = None
        self.stereo_mode: Optional[str] = None
        self.is_3d: bool = True
        self._group: str = group

    @property
    def group(self): return self._group

    @property
    def name_stem(self): return self.desc_path.stem

    @property
    def parent_path(self): return self._parent_path

    @property
    def parent_url(self): return self._parent_url

    def get_deovr_vid(self) -> DeoVrVideo:
        """Produce json object that represents video description file"""
        deovr_url = urljoin(self.parent_url, self.name_stem + VrVideoDesc.DEOVR_EXT)
        deovr_path = self.parent_path / (self.name_stem + VrVideoDesc.DEOVR_EXT)

        deovr = DeoVrVideo(self.title, self.video_url, self.thumb_url, deovr_url, deovr_path, self.desc_path)

        if self.preview_url:
            deovr.set_preview(self.preview_url)

        if self.seek_url:
            deovr.set_seek(self.seek_url)

        if self.duration > 0:
            deovr.set_duration(self.duration)

        if self.resolution > 0:
            deovr.set_resolution(self.resolution)

        if self.time_stamps:
            deovr.set_time_stamps(self.time_stamps)

        if not self.is_3d:
            deovr.set_3d(false);
        
        if self.screen_type:
            if self.screen_type == VrVideoDesc.SCREEN_TYPE_2D:
                deovr.set_2d()
            else:
                deovr.set_screen_type(self.screen_type)

        if self.stereo_mode:
            deovr.set_stereo_mode(self.stereo_mode)

        return deovr


def calc_group_from_relative_path(rel_path: Path):
    """Decide group from first dir in the relative path"""
    group_name = rel_path.parts[0];
    return group_name.lower().capitalize()


def load_video(desc_path: Path, root_dir: Path, base_url: str) -> Optional[VrVideoDesc]:
    def parse_time_stamps(ts_json):
        time_stamps = []
        for stamp in ts_json:
            time_code = stamp[VrDescLabels.TS_TIMECODE]
            if not TimeCode.is_valid(time_code):
                print("Invalid timecode ignored: {}".format(time_code))
                continue

            name = stamp[VrDescLabels.TS_NAME]
            duration = TimeCode.duration(time_code)
            time_stamps.append(TimeStamp(name, duration))

        return time_stamps

    file = None
    try:
        file = desc_path.open(mode="r", encoding="utf-8")
        parent_path = desc_path.parent
        relative_path = desc_path.relative_to(root_dir)
        parent_url = urljoin(base_url, relative_path.parent.as_posix())

        thumb_file = relative_path.with_suffix(VrVideoDesc.THUMB_EXT)
        thumb_url = urljoin(base_url, thumb_file.as_posix())

        desc_json = json.load(file)

        # title
        title = desc_json[VrDescLabels.TITLE]

        # group
        group = ""
        if VrDescLabels.GROUP in desc_json:
            group = desc_json[VrDescLabels.GROUP]

        if group == "":
                group = calc_group_from_relative_path(relative_path)

        # video name and path
        if VrDescLabels.VIDEO not in desc_json:
            video = desc_path.stem + VrVideoDesc.VIDEO_SUFFIX
        else:
            video = desc_json[VrDescLabels.VIDEO]

        video_path = desc_path.with_name(video)
        if not video_path.exists():
            print("Video file not found: {}".format(video_path))
            return None

        video_url = urljoin(base_url, relative_path.with_name(video).as_posix())

        # create description object
        vid_desc = VrVideoDesc(desc_path, parent_path, parent_url, title, group, video_url, thumb_url)

        # preview file
        preview_file = desc_path.stem + VrVideoDesc.PREVIEW_SUFFIX
        if desc_path.with_name(preview_file).exists():
            preview_url = urljoin(base_url, relative_path.with_name(preview_file).as_posix())
            vid_desc.preview_url = str(preview_url)

        # seek file
        seek_file = desc_path.stem + VrVideoDesc.SEEK_SUFFIX
        if desc_path.with_name(seek_file).exists():
            seek_url = urljoin(base_url, relative_path.with_name(seek_file).as_posix())
            vid_desc.seek_url = str(seek_url)

        # other attributes
        if VrDescLabels.TIME_STAMPS in desc_json:
            vid_desc.time_stamps = parse_time_stamps(desc_json[VrDescLabels.TIME_STAMPS])

        if VrDescLabels.DURATION in desc_json:
            duration_str = desc_json[VrDescLabels.DURATION]
            if TimeCode.is_valid(duration_str):
                vid_desc.duration = TimeCode.duration(duration_str)
            else:
                print("{} has invalid time code:{}".format(desc_path, duration_str))

        if VrDescLabels.RESOLUTION in desc_json:
            vid_desc.resolution = desc_json[VrDescLabels.RESOLUTION]

        if VrDescLabels.SCREEN_TYPE in desc_json:
            vid_desc.screen_type = desc_json[VrDescLabels.SCREEN_TYPE]

        if VrDescLabels.STEREO_MODE in desc_json:
            vid_desc.stereo_mode = desc_json[VrDescLabels.STEREO_MODE]

    finally:
        if file:
            file.close()

    return vid_desc


class VideoLibrary:
    """Encapsulates the video library on my machine.
    Provides services to output static references for deovr."""

    def __init__(self, root_dir: Path, base_url: str):
        self.video_dict = {}
        self.root_dir: Path = root_dir
        self.base_url: str = base_url

    def add_video(self, desc_path: Path, verbose: bool = False):
        if verbose:
            print("-> {}".format(desc_path.relative_to(self.root_dir).as_posix()))

        video_desc = load_video(desc_path, self.root_dir, self.base_url)
        if video_desc:
            group = video_desc.group
            if group not in self.video_dict:
                self.video_dict[group] = [video_desc]
            else:
                self.video_dict[group].append(video_desc)

    @staticmethod
    def is_descriptor_file(filename: str):
        return filename.endswith(_DESCRIPTOR_SUFFIX)

    def scan_for_videos(self, verbose: bool = False):
        for root, dirs, files in os.walk(str(self.root_dir)):
            descriptors = filter(VideoLibrary.is_descriptor_file, files)
            for desc in descriptors:
                self.add_video(Path(root, desc), verbose)

    def deovr_construct_catalog(self) -> DeoVrCatalog:
        deovr_cat = DeoVrCatalog()

        for group in self.video_dict:
            group_videos = self.video_dict[group]
            if len(group_videos) > 0:
                scene = DeoVrScene(group)
                deovr_cat.add_scene(scene)

                for video in group_videos:
                    deovr_vid = video.get_deovr_vid()
                    scene.add_video(deovr_vid)

        return deovr_cat

    @staticmethod
    def deovr_write_vid_file(video: DeoVrVideo):
        fp = video.json_path.open(mode="w")
        try:
            json.dump(video.to_json(), fp, indent=2)
        finally:
            fp.close()

    @staticmethod
    def deovr_existing_file_valid(video: DeoVrVideo) -> bool:
        deovr_path = Path(video.json_path)
        if not deovr_path.exists():
            return False
        
        # check date of deovr file vs date of desc file

        # check URL in existing file matches the new one
        return True

    def deovr_write_files(self, verbose: bool = False):
        _DEO_CATALOG_FILENAME = "deovr"
        # convert library to DeoVrScene hierarchy
        deovr_cat = self.deovr_construct_catalog()

        deovr_file = self.root_dir / _DEO_CATALOG_FILENAME
        if verbose:
            print("Writing deovr index file at {}".format(deovr_file))

        fp = deovr_file.open(mode="w")
        try:
            json.dump(deovr_cat.to_json(), fp, indent=2)
        finally:
            fp.close()

        if verbose:
            print("Writing deovr video files")

        for scene in deovr_cat.scenes:
            for video in scene.videos:
                if not self.deovr_existing_file_valid(video):
                    self.deovr_write_vid_file(video)


def index_lib_for_deovr(root: str = None, base_url: str = _BASE_URL, verbose: bool = False):
    if not root:
        root_dir = _ROOT_DIR_LINUX if os.name == "posix" else _ROOT_DIR_WIN
    else:
        root_dir = Path(root)

    if not root_dir.exists():
        print("Folder '{}' does not exist.".format(root_dir))
        return

    video_lib = VideoLibrary(root_dir, base_url)

    print("Scanning directories starting at {}".format(root_dir))
    video_lib.scan_for_videos(verbose)

    print("Writing DEOVR files")
    video_lib.deovr_write_files(verbose)


def write_template_desc(video_file: str):
    video_path = Path(video_file)
    if not video_path.exists():
        print("File not found: {}".format(video_path))
        return

    desc_path = video_path.with_suffix(_DESCRIPTOR_SUFFIX)
    if desc_path.exists():
        print("Error. Desc file already exists: {}".format(desc_path))
        return

    json_str = r'''{
    "title": "{%TITLE%}",
    "site": "Unknown",
    "duration": "00:00:00",
    "resolution": 1920,
    "group": "",
    "actors": ["Unknown"],
    "timeStamps": [
        {"ts":"00:", "name":""},
        {"ts":"00:", "name":""}
    ]
}'''

    title = video_path.name.replace("_"," ").title()

    json_str = json_str.replace("{%TITLE%}",title)

    fp = desc_path.open(mode="w")
    try:
        fp.write(json_str)
    finally:
        fp.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        index_lib_for_deovr(verbose=True)
    elif sys.argv[1].endswith("mp4") or sys.argv[1].endswith("jpg"):
        write_template_desc(sys.argv[1])

