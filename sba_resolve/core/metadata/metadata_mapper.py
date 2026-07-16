"""
SBA AI Studio
Metadata Mapper
Version 4.1.0
Robust numeric parsing
"""

from __future__ import annotations

import re
from pathlib import Path

from sba_resolve.core.models.media_file import MediaFile
from sba_resolve.core.metadata.confidence_engine import ConfidenceEngine
from sba_resolve.core.metadata.timestamp_resolver import TimestampResolver
from sba_resolve.core.services.camera_recognition_engine import CameraRecognitionEngine


class MetadataMapper:

    @staticmethod
    def _to_int(value):
        if value is None:
            return 0
        if isinstance(value,(int,float)):
            return int(value)
        s=str(value).strip()
        m=re.search(r"[-+]?[0-9]+",s.replace(",",""))
        return int(m.group()) if m else 0

    @staticmethod
    def _to_float(value):
        if value is None:
            return 0.0
        if isinstance(value,(int,float)):
            return float(value)
        s=str(value).strip()
        if " " in s:
            p=s.split()
            if len(p)==2:
                try:
                    return float(p[0])/float(p[1])
                except Exception:
                    pass
        try:
            return float(s)
        except Exception:
            m=re.search(r"[-+]?[0-9]*\.?[0-9]+",s)
            return float(m.group()) if m else 0.0

    @staticmethod
    def map(item:dict, project_root:Path)->MediaFile:
        full_path=Path(item.get("SourceFile",""))
        try:
            rel=full_path.relative_to(project_root)
        except Exception:
            rel=Path(full_path.name)

        camera_profile = CameraRecognitionEngine.detect(item, str(full_path))

        model = camera_profile.model if camera_profile.is_known() else (item.get("Model") or "Unknown")
        make = camera_profile.manufacturer.value if camera_profile.is_known() else (item.get("Make") or MetadataMapper._infer_make(model))

        created, timestamp_source = TimestampResolver.resolve_with_source(item)

        timestamp_confidence = (
            ConfidenceEngine.score(timestamp_source)
            if timestamp_source
            else 0
        )

        return MediaFile(
            filename=full_path.name,
            full_path=full_path,
            relative_path=rel,
            extension=full_path.suffix.lower(),
            size=MetadataMapper._to_int(item.get("FileSize")),
            camera_make=make,
            camera_model=model,
            camera_profile=camera_profile,
            lens=item.get("LensModel",""),
            width=MetadataMapper._to_int(item.get("ImageWidth")),
            height=MetadataMapper._to_int(item.get("ImageHeight")),
            fps=MetadataMapper._to_float(item.get("VideoFrameRate")),
            duration=str(item.get("Duration","")),
            codec=item.get("CompressorName",""),
            bitrate=MetadataMapper._to_int(item.get("AvgBitrate")),
            rotation=MetadataMapper._to_int(item.get("Rotation")),
            audio_channels=MetadataMapper._to_int(item.get("AudioChannels")),
            sample_rate=MetadataMapper._to_int(item.get("AudioSampleRate")),
            gps_latitude=item.get("GPSLatitude"),
            gps_longitude=item.get("GPSLongitude"),
            created=created,
            category=camera_profile.display_name if camera_profile.is_known() else MetadataMapper._category(make,model),
            timestamp_source=timestamp_source or "",
            timestamp_confidence=timestamp_confidence,
        )

    @staticmethod
    def map_many(metadata, project_root):
        return [MetadataMapper.map(x,project_root) for x in metadata]

    @staticmethod
    def _infer_make(model:str)->str:
        u=model.upper()
        if "HERO" in u: return "GoPro"
        if "DJI" in u: return "DJI"
        if "INSTA360" in u: return "Insta360"
        if "CANON" in u: return "Canon"
        if "SONY" in u: return "Sony"
        return "Unknown"

    @staticmethod
    def _category(make:str,model:str)->str:
        m=make.upper(); mo=model.upper()
        if "GOPRO" in m or "HERO" in mo: return "GoPro"
        if "DJI" in m: return "DJI Flip" if "FLIP" in mo else "Drone"
        if "INSTA360" in m: return "Insta360"
        return "Unknown"
