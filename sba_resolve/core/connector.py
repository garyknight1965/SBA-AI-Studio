"""
============================================================
SBA AI Studio
Resolve Connector
Version : 3.0.0
============================================================
"""

import DaVinciResolveScript as bmd

from sba_resolve.context import ResolveContext
from sba_resolve.commands.create_project import create_project
from sba_resolve.manager.media_pool_manager import MediaPoolManager


class ResolveConnector:
    """
    Coordinates execution of all application managers.
    """

    def __init__(self, project_data):

        self.context = ResolveContext()
        self.context.project_data = project_data

        print("=" * 60)
        print("SBA Resolve Connector")
        print("=" * 60)
        print()

        print("Connecting to Resolve...")

        self.context.resolve = bmd.scriptapp("Resolve")

        if self.context.resolve is None:
            raise RuntimeError(
                "Unable to connect to DaVinci Resolve."
            )

        print("Connected.")
        print()

    # ---------------------------------------------------------

    def create_project(self):

        print("STEP 1 : Create / Open Project")
        print()

        create_project(self.context)

    # ---------------------------------------------------------

    def media_pool(self):

        print("STEP 2 : Media Pool Manager")
        print()

        manager = MediaPoolManager(self.context)
        manager.run()

    # ---------------------------------------------------------

    def print_summary(self):

        report = self.context.report

        print()
        print("=" * 60)
        print("SBA Resolve Report")
        print("=" * 60)

        print(f"Project : {self.context.project_data['project_name']}")
        print()

        print("Bins")
        print("----")
        print(f"Created : {report.bins_created}")
        print(f"Existing: {report.bins_existing}")

        print()

        if report.errors:
            print("Errors")
            print("------")
            for error in report.errors:
                print(f"- {error}")
            print()

        if report.warnings:
            print("Warnings")
            print("--------")
            for warning in report.warnings:
                print(f"- {warning}")
            print()

        print("Status : SUCCESS")
        print("=" * 60)

    # ---------------------------------------------------------

    def run(self):

        print("=" * 60)
        print("Starting Resolve Pipeline")
        print("=" * 60)
        print()

        self.create_project()

        self.media_pool()

        self.print_summary()