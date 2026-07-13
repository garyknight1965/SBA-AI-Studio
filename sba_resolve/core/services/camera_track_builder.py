"""
============================================================
SBA AI Studio
Camera Track Builder Service

Version : RES-006F.1

Purpose:
    Build camera-aware clip groups for DaVinci Resolve timelines.

Responsibilities:
    - Group MediaFile objects by camera
    - Preserve Resolve clip references
    - Prepare track assignment data
    - Provide timeline statistics

Next stage:
    RES-006F.2
    Create Resolve timeline tracks and append clips.
============================================================
"""


from collections import OrderedDict



class CameraTrackBuilder:
    """
    Builds camera-based timeline groups.

    Input:
        assignments:
            [
                {
                    "media": MediaFile,
                    "clip": Resolve MediaPoolItem
                }
            ]

    Output:
        {
            "GoPro HERO13 Black": [
                assignments
            ]
        }
    """


    DEFAULT_ORDER = [
        "GoPro HERO13 Black",
        "GoPro HERO8 Black",
        "Insta360 X3",
        "DJI Flip",
        "Unknown Camera",
    ]


    def __init__(self):

        self.camera_groups = OrderedDict()



    def get_camera_name(self, media_file):
        """
        Resolve camera display name from MediaFile.
        """

        if media_file is None:
            return "Unknown Camera"


        try:

            name = media_file.camera_display_name

            if name:
                return name

        except Exception:
            pass



        model = getattr(
            media_file,
            "camera_model",
            None
        )


        if model and model != "Unknown":

            return model



        make = getattr(
            media_file,
            "camera_make",
            None
        )


        if make and make != "Unknown":

            return make



        return "Unknown Camera"



    def build_groups(self, assignments):
        """
        Group clip assignments by camera.

        assignments:

            {
                media:
                    MediaFile,

                clip:
                    Resolve MediaPoolItem
            }

        Returns:

            {
                camera_name:
                    [
                        assignments
                    ]
            }
        """


        self.camera_groups = OrderedDict()


        for assignment in assignments:


            media_file = assignment.get(
                "media"
            )


            camera = self.get_camera_name(
                media_file
            )


            if camera not in self.camera_groups:

                self.camera_groups[camera] = []


            self.camera_groups[camera].append(
                assignment
            )


        return self.camera_groups



    def get_statistics(self):
        """
        Return camera statistics.
        """


        statistics = OrderedDict()


        for camera, clips in self.camera_groups.items():

            statistics[camera] = len(clips)


        return statistics



    def print_statistics(self):
        """
        Print camera summary.
        """


        print()

        print("=" * 60)
        print("Camera Track Summary")
        print("=" * 60)


        total = 0


        for camera, clips in self.camera_groups.items():

            count = len(clips)

            total += count


            print(
                f"{camera:<35}{count:>5} clips"
            )


        print("-" * 60)

        print(
            f"{'Total Clips':<35}{total:>5}"
        )

        print()



    def get_track_order(self):
        """
        Return preferred Resolve track order.

        Highest camera priority first.
        """

        available = list(
            self.camera_groups.keys()
        )


        ordered = []


        for camera in self.DEFAULT_ORDER:

            if camera in available:

                ordered.append(camera)



        for camera in available:

            if camera not in ordered:

                ordered.append(camera)



        return ordered



    def get_track_name(self, camera):
        """
        Generate Resolve track name.
        """

        return camera



    def get_clips_for_camera(self, camera):
        """
        Return Resolve assignments for a camera.
        """

        return self.camera_groups.get(
            camera,
            []
        )