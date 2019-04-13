#!/usr/bin/env python3

from os import walk
from pathlib import Path  # https://docs.python.org/3/library/pathlib.html
from typing import Union
# Path parts!
# import json

_ROOT_DIR = Path("N:/vr")
_DESCRIPTOR_SUFFIX = ".vid.json"
_VR_VIDEOS = []
_BASE_URL = "http://192.168.0.35/vr"


class TimeStamp:
    def __init__(self, seconds: int, name: str):
        self.seconds = seconds
        self.name = name


class DeoVrCatalog:
    def __init__(self):
        self.scenes:[DeoVrScene] = []

    def add_video(self, scene:str, video):
        # TODO Implement this.
        print("not implemented")

    def to_json(self):
        scene_json = []
        for scene in self.scenes:
            scene_json.append(scene.as_json)

        result = {
            "scenes": scene_json
        }
        return result


class DeoVrScene:
    def __init__(self, name: str):
        self.name = name
        self.videos = []

    def to_json(self):
        """Return scenes json object given the tab contents"""
        # TODO Convert video list to json

        return {
                "name": self.name,
                "list": []
        }


class DeoVrVideo:
    def __init__(self, title: str, video_url: str, thumb_url: str):
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

    def video_index_json(self, video_json_url:str):
        """Return the deovr index entry json object"""
        result = {
            "title": self.json["title"],
            "thumbnailUrl": self.json["thumbnailUrl"],
            "video_url": video_json_url
        }

        return result

    def add_preview(self, preview_url):
        self.json["videoPreview"] = preview_url

    def add_seek(self, seek_url):
        self.json["videoThumbnail"] = seek_url

    def add_time_stamps(self, stamps):
        timestamps = []

        for stamp in stamps:
            timestamps.append({
                "ts": stamp.seconds,
                "name": stamp.name
            })

        self.json["timeStamps"] = timestamps


class VrVideo:
    """VR Video for the index"""
    def __init__(self, descriptor: Path, title: str, tab: str, video_url: str, thumb_url: str, duration: int):
        self.descriptor = descriptor
        self.title = title
        self.video_url = video_url
        self.thumb_url = thumb_url
        self.preview_url: Union[str, None] = None
        self.bookmarks = []
        self.duration = duration
        self.tab = tab

    def get_deovr_json(self):
        """Produce json object that represents video description file"""
        deovr = DeoVrVideo(self.title, self.video_url, self.thumb_url)
        if self.preview_url:
            deovr.add_preview(self.preview_url);

        return deovr.json


def is_descriptor_file(filename: str):
    return filename.endswith(_DESCRIPTOR_SUFFIX)


def add_video(desc_path: Path):
    print(desc_path.with_suffix("").with_suffix(".jpg").relative_to(_ROOT_DIR).as_posix())


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
