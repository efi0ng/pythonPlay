#!/usr/bin/env python3
# DeoVr doc: https://deovr.com/doc

from os import walk
from pathlib import Path  # https://docs.python.org/3/library/pathlib.html
from typing import Optional, Any
import json

# Path parts!

_ROOT_DIR_WIN = Path("N:/vr")
_ROOT_DIR_LINUX = Path("~/mnt/oook/vr").expanduser()
_ROOT_DIR = _ROOT_DIR_WIN

_DESCRIPTOR_SUFFIX = ".desc"
_VR_VIDEOS = []
_BASE_URL = "http://192.168.0.35/vr/"


class TimeStamp:
    def __init__(self, seconds: int, name: str):
        self.seconds = seconds
        self.name = name


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


class VrVideoDesc:
    """VR Video for the index"""
    THUMB_EXT = ".jpg"
    SEEK_SUFFIX = "_seek.mp4"
    PREVIEW_SUFFIX = "_preview.mp4"
    DEOVR_EXT = ".deovr"

    def __init__(self, descriptor: Path, title: str, group: str, video_url: str, thumb_url: str, deovr_url: str, duration: int=0):
        self.descriptor: Path = descriptor
        self.title: str = title
        self.video_url: str = video_url
        self.thumb_url: str = thumb_url
        self.deovr_url: str = deovr_url
        self.preview_url: Optional[str] = None
        self.seek_url: Optional[str] = None
        self.time_stamps: Any = None
        self.duration: int = duration
        self.group: str = group

    def get_deovr_json(self) -> object:
        """Produce json object that represents video description file"""
        deovr = DeoVrVideo(self.title, self.video_url, self.thumb_url, self.deovr_url)
        if self.preview_url:
            deovr.set_preview(self.preview_url)

        if self.seek_url:
            deovr.set_seek(self.seek_url)

        if self.duration > 0:
            deovr.set_duration(self.duration)

        if self.time_stamps:
            # todo: parse timestamps for timecodes.
            deovr.set_time_stamps_raw(self.time_stamps)

        return deovr.get_video_json()

    @staticmethod
    def load(desc_path: Path) -> object:
        file = None
        vid_desc = None
        try:
            file = desc_path.open(mode="r", encoding="utf-8")
            relative_path = desc_path.relative_to(_ROOT_DIR)
            desc_stem = relative_path.stem
            thumb_file = relative_path.with_suffix(VrVideoDesc.THUMB_EXT)
            thumb_url = _BASE_URL + str(thumb_file.as_posix())
            deovr_file = relative_path.with_suffix(VrVideoDesc.DEOVR_EXT)
            deovr_url = _BASE_URL + str(deovr_file.as_posix())

            desc_json = json.load(file)
            title = desc_json[VrDescLabels.TITLE]
            video = desc_json[VrDescLabels.VIDEO]
            group = desc_json[VrDescLabels.GROUP]

            video_url = _BASE_URL + relative_path.with_name(video).as_posix()

            vid_desc = VrVideoDesc(desc_path, title, group, video_url, thumb_url, deovr_url)

            preview_file = desc_stem + VrVideoDesc.PREVIEW_SUFFIX
            if desc_path.with_name(preview_file).exists():
                preview_url = _BASE_URL + str(relative_path.with_name(preview_file).as_posix())
                vid_desc.preview_url = preview_url

            seek_file = desc_stem + VrVideoDesc.SEEK_SUFFIX
            if desc_path.with_name(seek_file).exists():
                seek_url = _BASE_URL + str(relative_path.with_name(seek_file).as_posix())
                vid_desc.seek_url = seek_url

            if VrDescLabels.TIME_STAMPS in desc_json:
                vid_desc.time_stamps = desc_json[VrDescLabels.TIME_STAMPS]

            if VrDescLabels.DURATION in desc_json:
                duration_str = desc_json[VrDescLabels.DURATION]

            print(json.dumps(vid_desc.get_deovr_json(), indent=3))


        finally:
            if file:
                file.close()

        return vid_desc


def is_descriptor_file(filename: str):
    return filename.endswith(_DESCRIPTOR_SUFFIX)


def add_video(desc_path: Path):
    print("Processing {}".format(desc_path.relative_to(_ROOT_DIR).as_posix()))
    VrVideoDesc.load(desc_path)


def scan_for_videos():
    print("Scanning directories starting at {}".format(_ROOT_DIR))
    # vrCatalog = DeoVrCatalog()

    for root, dirs, files in walk(_ROOT_DIR):
        descriptors = filter(is_descriptor_file, files)
        for desc in descriptors:
            add_video(Path(root, desc))


def main():
    if not _ROOT_DIR.exists():
        print("Folder '{}' does not exist.".format(_ROOT_DIR))
        return

    scan_for_videos()


if __name__ == "__main__":
    main()
