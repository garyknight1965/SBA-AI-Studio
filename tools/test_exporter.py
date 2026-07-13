from bridge.models import BridgeProject
from bridge.exporter import BridgeExporter

project = BridgeProject(
    project_name="ABR Festival",

    bins=[
        "GoPro",
        "DJI Flip",
        "Insta360",
        "Drone",
        "Audio",
    ],

    media=[
        {
            "file": r"D:\Media\GoPro\GX010060.MP4",
            "bin": "GoPro",
            "camera": "GoPro Hero13"
        }
    ]
)

exporter = BridgeExporter()

output = exporter.export(project)

print(output)