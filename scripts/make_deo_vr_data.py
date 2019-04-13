#!/usr/bin/env python3
# DeoVr doc: https://deovr.com/doc

from os import walk
from pathlib import Path  # https://docs.python.org/3/library/pathlib.html
from typing import Optional
# Path parts!
# import json

_ROOT_DIR = Path("N:/vr")
_DESCRIPTOR_SUFFIX = ".desc"
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

    def get_index_json(self):
        """Return the deovr index entry json object"""
        result = {
            "title": self.json["title"],
            "thumbnailUrl": self.json["thumbnailUrl"],
            "video_url": self.json_url
        }

        return result

    def get_video_json(self):
        return self.json

    def set_preview(self, preview_url):
        self.json["videoPreview"] = preview_url

    def set_seek(self, seek_url):
        self.json["videoThumbnail"] = seek_url

    def set_duration(self, duration):
        if duration > 0:
            self.json["videoLength"] = duration

    def set_time_stamps(self, stamps):
        timestamps = []

        for stamp in stamps:
            timestamps.append({
                "ts": stamp.seconds,
                "name": stamp.name
            })

        self.json["timeStamps"] = timestamps


class DeoVrScene:
    def __init__(self, name: str):
        self.name = name
        self.videos = []

    def get_json(self):
        """Return scenes json object given the tab contents"""
        # TODO Convert video list to json

        return {
                "name": self.name,
                "list": []
        }

    def add_video(self, video: DeoVrVideo):
        self.videos.append(video)


class VrVideo:
    """VR Video for the index"""
    def __init__(self, descriptor: Path, title: str, group: str, video_url: str, thumb_url: str, duration: int=0):
        self.descriptor = descriptor
        self.title = title
        self.video_url = video_url
        self.thumb_url = thumb_url
        self.preview_url: Optional[str] = None
        self.seek_url: Optional[str] = None
        self.bookmarks = []
        self.duration = duration
        self.group = group

    def get_deovr_json(self):
        """Produce json object that represents video description file"""
        deovr = DeoVrVideo(self.title, self.video_url, self.thumb_url)
        if self.preview_url:
            deovr.set_preview(self.preview_url)

        if self.seek_url:
            deovr.set_seek(self.seek_url)

        if self.duration > 0:
            deovr.set_duration(self.duration)

        return deovr.get_video_json()


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
