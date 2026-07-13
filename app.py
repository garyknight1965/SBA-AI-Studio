import sys

from PySide6.QtWidgets import QApplication

from ui.windows.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.setWindowTitle("SBA AI Studio v0.4.0-alpha")
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()