import os
import json
import subprocess
from PyQt6.QtCore import QRunnable, pyqtSlot, QObject, pyqtSignal

class WorkerSignals(QObject):
    finished = pyqtSignal()


class MetadataWriterWorker(QRunnable):
    def __init__(self, directory):
        super().__init__()
        self.directory = directory
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        for root, _, files in os.walk(self.directory):
            modified_json_path = os.path.join(root, "modified.json")
            if not os.path.exists(modified_json_path):
                continue

            with open(modified_json_path, "r") as f:
                json_data = json.load(f)

            # Process all files in json_data at once
            self.write_metadata_to_image(root)  # Remove the json_data argument
            self.signals.finished.emit()

    def write_metadata_to_image(self, directory):
        metadata_json = os.path.join(directory, "modified.json")
        errors_file = os.path.join(directory, "errors.txt")
        exiftool_output_file = os.path.join(self.directory, "exiftool_output.txt")

        try:
            # Run ExifTool with the provided command to update the metadata.
            # command = f"exiftool -progress -r -stay_open True -execute -json='{metadata_json}' -preserve -overwrite_original -stay_open False '{directory}'"
            command = f"exiftool -progress -v -preserve_original -m -stay_open True -execute -json='{metadata_json}' -overwrite_original_in_place -r '{directory}' -stay_open False"
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            print(f"{command}")
            # Print the current directory and ExifTool's output
            print(f"Processing directory: {directory}")
            print(f"ExifTool stdout: {stdout.decode('utf-8')}")
            print(f"ExifTool stderr: {stderr.decode('utf-8')}")

            # Print the names of the updated files
            # for item in json_data:
            #     print(f"Updated file: {os.path.join(directory, item['SourceFile'])}")

            # If there are errors, write them to the "errors.txt" file.
            if stderr:
                with open(errors_file, "a") as error_log:
                    error_log.write(stderr.decode('utf-8'))

            # Save ExifTool's output to 'exiftool_output.txt' in the master photo folder
            with open(exiftool_output_file, "a") as output_log:
                output_log.write(f"Processing directory: {directory}\n")
                output_log.write(f"ExifTool stdout: {stdout.decode('utf-8')}\n")
                output_log.write(f"ExifTool stderr: {stderr.decode('utf-8')}\n")
                output_log.write("\n")

        except Exception as e:
            print(f"Error writing metadata: {e}")
