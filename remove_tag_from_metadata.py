import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from ui import Ui_Widget
from PyQt6.QtCore import QThreadPool, QRunnable, pyqtSlot, pyqtSignal, QObject
from jsonManager import JSONManager, get_list_of_json_files, JsonReplaceWorker


class MainWindow(QMainWindow, Ui_Widget):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.json_manager = JSONManager()

        self.loadFolder.clicked.connect(self.select_folder)
        self.processJSON.clicked.connect(self.process_folders)
        self.processJSONButton.clicked.connect(self.process_json_files)

    def handle_finished_json_processing(self, num_changes, num_errors):
        self.total_changes += num_changes
        self.total_errors += num_errors

    def select_folder(self):
        self.json_manager.select_folder()
        if self.json_manager.folder_path:
            self.processJSONProgressLabel.setText(self.json_manager.folder_path)

    def process_folders(self):
        exiftool_command = self.exiftoolCommand.toPlainText()
        if not exiftool_command:
            QMessageBox.warning(self, "Error", "Please provide a valid exiftool command.")
            return

        if not self.json_manager.folder_path:
            QMessageBox.warning(self, "Error", "Please select a folder first.")
            return

        self.processJSON.setEnabled(False)
        self.processJSONProgress.setValue(0)
        self.processJSONProgressLabel.setText("")

        self.json_manager.process_folders(
            exiftool_command,
            self.update_progress,
            self.update_progress_label,
            self.handle_error,
            self.handle_finish
        )

    def update_progress(self, value):
        if self.json_manager.num_folders == 0:
            return
        current_value = self.processJSONProgress.value()
        self.processJSONProgress.setValue(current_value + value * (100 / self.json_manager.num_folders))

    def update_progress_label(self, text):
        self.processJSONProgressLabel.setText(text)

    def handle_error(self, error_msg):
        self.json_manager.on_error(error_msg)

    def handle_finish(self):
        self.json_manager.on_finish()
        self.processJSON.setEnabled(True)

    def process_json_files(self):
        self.total_changes = 0  # Add this line
        self.total_errors = 0  # Add this line

        # Get the list of output.json files to process
        json_files = get_list_of_json_files(self.json_manager.folder_path)

        # Parse the input from the ReplaceText and notReplace text fields
        replace_text = self.ReplaceText.toPlainText()
        not_replace = self.notReplace.toPlainText()

        replace_list = [item.strip() for item in replace_text.split(',')]
        not_replace_list = [item.strip() for item in not_replace.split(',')]

        # Create a QThreadPool to handle multithreading
        thread_pool = QThreadPool()

        # Create progress and error signals
        signals = JsonReplaceSignals()
        signals.progress_signal.connect(self.update_progress)
        signals.error_signal.connect(self.handle_error)
        signals.finished_signal.connect(self.handle_finished_json_processing)  # Add this line

        # Iterate through the JSON files and process them using multiple threads
        for file_path in json_files:
            worker = JsonReplaceWorker(file_path, replace_list, not_replace_list, signals.progress_signal,
                                       signals.error_signal, signals.finished_signal,)
            thread_pool.start(worker)

        # Wait for all the threads to finish
        thread_pool.waitForDone()

        # Reset the progress bar and display a message when the processing is complete
        self.jsonProgress.setValue(0)
        QMessageBox.information(
            self,
            "Processing Complete",
            f"The JSON files have been processed. {self.total_changes} records changed, {self.total_errors} errors encountered."
        )


class JsonReplaceSignals(QObject):
    progress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int, int)  # Add this line



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
