#!/usr/bin/env python3
# DeoVr doc: https://deovr.com/doc

import os
from pathlib import Path  # https://docs.python.org/3/library/pathlib.html
from typing import Optional, Any
import json
import re

# Path parts!


class TimeStamp:
    def __init__(self, seconds: int, name: str):
        self.seconds = seconds
        self.name = name


class TimeCode:
    _REGEX = []

    @staticmethod
    def ints_to_duration(h: int, m: int, s: int):
        return h*3600 + m*60 + s

    @staticmethod
    def text_to_duration(h: str, m: str, s: str=None):
        seconds = int(s) if s is not None else 0
        return TimeCode.ints_to_duration(int(h),int(m),seconds)

    @staticmethod
    def parse_hhmmss(time_string):
        """Must pass in a valid 00:00:00 value"""
        (h, m, s) = time_string.split(":")
        return TimeCode.text_to_duration(h, m, s)

    @staticmethod
    def parse_hhmm(time_string):
        """Must pass in a valid 00:00 value"""
        (h, m) = time_string.split(":")
        return TimeCode.text_to_duration(h, m)

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

        return False


TimeCode._REGEX = [
    (r"\d\d:\d\d:\d\d", TimeCode.parse_hhmmss),
    (r"\d\d:\d\d", TimeCode.parse_hhmm),
    (r"\d\d?h\d\d?m\d\d?s", TimeCode.parse_0h0m0s),
    (r"\d+", TimeCode.parse_seconds)]


class DeoVrCatalog:
    def __init__(self):
        self.scenes: [DeoVrScene] = []

    def to_json(self):
        scene_json = []
        for scene in self.scenes:
            scene_json.append(scene.as_json)

        result = {
            "scenes": scene_json
        }
        return result


class DeoVrVideo:
    def __init__(self, title: str, video_url: str, thumb_url: str, json_url: str):
        self.json_url = json_url
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

    def get_index_json(self) -> object:
        """Return the deovr index entry json object"""
        result = {
            "title": self.json["title"],
            "thumbnailUrl": self.json["thumbnailUrl"],
            "video_url": self.json_url
        }

        return result

    def get_video_json(self) -> object:
        return self.json

    def set_preview(self, preview_url):
        self.json["videoPreview"] = preview_url

    def set_seek(self, seek_url):
        self.json["videoThumbnail"] = seek_url

    def set_duration(self, duration):
        if duration > 0:
            self.json["videoLength"] = duration

    def set_time_stamps(self, stamps):
        timestamps = stamps

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
        self.videos = []

    def get_json(self) -> object:
        """Return scenes json object given the tab contents"""
        # TODO Convert video list to json

        return {
                "name": self.name,
                "list": []
        }

    def add_video(self, video: DeoVrVideo):
        self.videos.append(video)


class VrDescLabels:
    TITLE = "title"
    SITE = "site"
    VIDEO = "video"
    PREVIEW = "preview"
    SEEK = "seek"
    DURATION = "duration"
    GROUP = "group"
    ACTORS = "actors"
    TIME_STAMPS = "timeStamps"
    TS_TIMECODE = "ts"
    TS_NAME = "name"


class VrVideoDesc:
    """VR Video for the index"""
    THUMB_EXT = ".jpg"
    SEEK_SUFFIX = "_seek.mp4"
    PREVIEW_SUFFIX = "_preview.mp4"
    DEOVR_EXT = ".deovr"

    def __init__(self, descriptor: Path,
                 parent_path: str, parent_url: str,
                 title: str, group: str,
                 video_url: str, thumb_url: str, duration: int = 0):
        self.descriptor: Path = descriptor
        self._parent_url: str = parent_url
        self._parent_path: str = parent_path
        self.title: str = title
        self.video_url: str = video_url
        self.thumb_url: str = thumb_url
        self.preview_url: Optional[str] = None
        self.seek_url: Optional[str] = None
        self.time_stamps: Any = None
        self.duration: int = duration
        self._group: str = group

    @property
    def group(self): return self._group

    @property
    def name_stem(self): return self.descriptor.stem

    @property
    def parent_path(self): return self._parent_path

    @property
    def parent_url(self): return self._parent_url

    def get_deovr_obj(self) -> object:
        """Produce json object that represents video description file"""
        deovr_url = self.parent_url + self.name_stem + VrVideoDesc.DEOVR_EXT

        deovr = DeoVrVideo(self.title, self.video_url, self.thumb_url, deovr_url)
        if self.preview_url:
            deovr.set_preview(self.preview_url)

        if self.seek_url:
            deovr.set_seek(self.seek_url)

        if self.duration > 0:
            deovr.set_duration(self.duration)

        if self.time_stamps:
            deovr.set_time_stamps(self.time_stamps)

        return deovr


def load_video(desc_path: Path, root_dir: Path, base_url: str) -> VrVideoDesc:
    def parse_time_stamps(ts_json):
        time_stamps = []
        for stamp in ts_json:
            name = stamp[VrDescLabels.TS_NAME]
            duration = TimeCode.duration(stamp[VrDescLabels.TS_TIMECODE])
            time_stamps.append(TimeStamp(name, duration))

        return time_stamps

    file = None
    try:
        file = desc_path.open(mode="r", encoding="utf-8")
        parent_path = desc_path.parent
        relative_path = desc_path.relative_to(root_dir)
        parent_url = base_url + str(relative_path.parent.as_posix())

        thumb_file = relative_path.with_suffix(VrVideoDesc.THUMB_EXT)
        thumb_url = base_url + str(thumb_file.as_posix())

        desc_json = json.load(file)
        title = desc_json[VrDescLabels.TITLE]
        video = desc_json[VrDescLabels.VIDEO]
        group = desc_json[VrDescLabels.GROUP]

        video_url = base_url + relative_path.with_name(video).as_posix()

        vid_desc = VrVideoDesc(desc_path, str(parent_path), parent_url, title, group, video_url, thumb_url)

        preview_file = vid_desc.name_stem + VrVideoDesc.PREVIEW_SUFFIX
        if desc_path.with_name(preview_file).exists():
            preview_url = base_url + str(relative_path.with_name(preview_file).as_posix())
            vid_desc.preview_url = preview_url

        seek_file = vid_desc.name_stem + VrVideoDesc.SEEK_SUFFIX
        if desc_path.with_name(seek_file).exists():
            seek_url = base_url + str(relative_path.with_name(seek_file).as_posix())
            vid_desc.seek_url = seek_url

        if VrDescLabels.TIME_STAMPS in desc_json:
            vid_desc.time_stamps = parse_time_stamps(desc_json[VrDescLabels.TIME_STAMPS])

        if VrDescLabels.DURATION in desc_json:
            duration_str = desc_json[VrDescLabels.DURATION]
            if TimeCode.is_valid(duration_str):
                vid_desc.duration = TimeCode.duration(duration_str)
            else:
                print("{} has invalid time code:{}".format(desc_path,duration_str))

        # DIAGNOSTIC print(json.dumps(vid_desc.get_deovr_json(), indent=3))

    finally:
        if file:
            file.close()

    return vid_desc


class VideoLibrary:
    """Encapsulates the video library on my machine.
    Provides services to output static references for deovr."""
    _DESCRIPTOR_SUFFIX = ".desc"

    def __init__(self, root_dir: Path, base_url):
        self.video_dict = {}
        self.root_dir: Path = root_dir
        self.base_url: str = base_url

    def add_video(self, desc_path: Path):
        print("Processing {}".format(desc_path.relative_to(self.root_dir).as_posix()))
        video_desc = load_video(desc_path, self.root_dir, self.base_url)

        group = video_desc.group
        if group not in self.video_dict:
            self.video_dict[group] = [video_desc]
        else:
            self.video_dict[group].append(video_desc)

    @staticmethod
    def is_descriptor_file(filename: str):
        return filename.endswith(VideoLibrary._DESCRIPTOR_SUFFIX)

    def scan_for_videos(self):
        print("Scanning directories starting at {}".format(self.root_dir))

        for root, dirs, files in os.walk(str(self.root_dir)):
            descriptors = filter(VideoLibrary.is_descriptor_file, files)
            for desc in descriptors:
                self.add_video(Path(root, desc))

    def deovr_write_files(self):
        # TODO
        print("Writing deovr index file at {}: Not implemented".format(self.root_dir))
        print("Writing deovr files: Not implemented")
        print(self.video_dict)


def main():
    _ROOT_DIR_WIN = Path("N:/vr")
    _ROOT_DIR_LINUX = Path("~/mnt/oook/vr").expanduser()

    _ROOT_DIR = _ROOT_DIR_LINUX if os.name == "posix" else _ROOT_DIR_WIN

    # base URL must include final backslash to work at the moment
    _BASE_URL = "http://192.168.0.35/vr/"

    if not _ROOT_DIR.exists():
        print("Folder '{}' does not exist.".format(_ROOT_DIR))
        return

    video_lib = VideoLibrary(_ROOT_DIR, _BASE_URL)
    video_lib.scan_for_videos()
    video_lib.deovr_write_files()


if __name__ == "__main__":
    main()
