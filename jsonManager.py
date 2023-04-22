import sys
import os
import subprocess
import json
import re
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, QRunnable


def get_list_of_json_files(folder_path):
    json_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith("output.json"):
                json_files.append(os.path.join(root, file))
    return json_files

class ThreadWorker(QThread):
    progress_signal = pyqtSignal(int)
    progress_text_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, folder, command):
        QThread.__init__(self)
        self.folder = folder
        self.command = command

    @pyqtSlot()
    def run(self):
        # pydevd.settrace(suspend=False)
        print()
        json_output_path = os.path.join(self.folder, "output.json")
        command_with_folder = f"{self.command} \"{self.folder}\" > \"{json_output_path}\""

        print("ExifTool command:", command_with_folder)  # Add this print statement

        try:
            process = subprocess.Popen(command_with_folder, cwd=self.folder, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                self.error_signal.emit(f"Error processing folder: {self.folder}\n{stderr.decode('utf-8')}")
            self.progress_text_signal.emit(stdout.decode('utf-8'))
        except Exception as e:
            self.error_signal.emit(f"Error processing folder: {self.folder}\n{str(e)}")
        finally:
            self.progress_signal.emit(1)


class JSONManager:
    def __init__(self):
        self.folder_path = ''
        self.num_folders = 0
        self.threads = []
        self.errors = []
        self.finished_threads = 0

    def select_folder(self):
        self.folder_path = QFileDialog.getExistingDirectory(None, "Select folder", "",)

    def process_folders(self, command, progress_callback, progress_text_callback, error_callback, finish_callback):
        self.num_folders = 0
        self.threads = []
        self.errors = []

        for year_folder in os.listdir(self.folder_path):
            year_path = os.path.join(self.folder_path, year_folder)
            if os.path.isdir(year_path):
                self.num_folders += 1
                worker = ThreadWorker(year_path, command)
                worker.progress_signal.connect(progress_callback)
                worker.progress_text_signal.connect(progress_text_callback)
                worker.error_signal.connect(error_callback)
                self.threads.append(worker)

        for thread in self.threads:
            thread.start()

        for thread in self.threads:
            thread.finished.connect(self.check_finish(finish_callback))

    def check_finish(self, finish_callback):
        def wrapped_finish_callback():
            self.finished_threads += 1
            if self.finished_threads == self.num_folders:
                finish_callback()

        return wrapped_finish_callback

    def on_error(self, error_msg):
        self.errors.append(error_msg)

    def on_finish(self, parent=None):
        if self.errors:
            with open(os.path.join(self.folder_path, 'errors.txt'), 'w') as f:
                f.writelines(self.errors)
            QMessageBox.warning(parent, "Processing Completed with Errors", f"{len(self.errors)} error(s) occurred. Check errors.txt for details.")
        else:
            QMessageBox.information(parent, "Processing Completed", "Processing completed successfully.")

class JsonReplaceWorker(QRunnable):
    def __init__(self, file_path, replace_list, not_replace_list, progress_signal, error_signal, finished_signal,):
        super().__init__()
        self.file_path = file_path
        self.replace_list = replace_list
        self.not_replace_list = not_replace_list
        self.progress_signal = progress_signal
        self.error_signal = error_signal
        self.finished_signal = finished_signal

    @pyqtSlot()
    def run(self):
        num_changes, num_errors = 0, 0
        try:
            with open(self.file_path, 'r') as json_file:
                data = json.load(json_file)

            num_changes = self.process_json_data(data)

            # Save the modified data to a new file called 'modified.json'
            modified_file_path = os.path.join(os.path.dirname(self.file_path), 'modified.json')
            with open(modified_file_path, 'w') as modified_json_file:
                json.dump(data, modified_json_file)

            self.progress_signal.emit(1)
        except Exception as e:
            num_errors = 1
            self.error_signal.emit(f"Error processing file: {self.file_path}\n{str(e)}")
        finally:
            self.finished_signal.emit(num_changes, num_errors)

    def process_json_data(self, data):
        removed_count = 0
        for image_data in data:
            for tag, value in image_data.items():
                if isinstance(value, list):
                    new_values = []
                    for item in value:
                        # Check if the item contains any of the not_replace characters
                        contains_not_replace_chars = any(char in item for char in self.not_replace_list)

                        # Check if the item contains any of the words in the replace_list
                        contains_replace_word = any(word in item for word in self.replace_list)

                        # Only remove the item if it contains a word from the replace_list and doesn't contain any not_replace characters
                        if not contains_not_replace_chars and contains_replace_word:
                            removed_count += 1
                        else:
                            new_values.append(item)
                    image_data[tag] = new_values
        return removed_count


if __name__ == "__main__":
    app = QApplication(sys.argv)
    manager = JSONManager()
    manager.select_folder()
    sys.exit(app.exec())
