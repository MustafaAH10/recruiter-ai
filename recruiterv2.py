import sys
import json
import os
import threading
from openai import OpenAI, AssistantEventHandler
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QTextEdit, QFileDialog,
    QLabel, QLineEdit, QStackedWidget, QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QDialogButtonBox, QHeaderView, QAbstractItemView
)
import fitz  # PyMuPDF

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file)

class APIKeyDialog(QDialog):
    def __init__(self, parent=None):
        super(APIKeyDialog, self).__init__(parent)
        self.setWindowTitle('Enter OpenAI API Key')
        self.api_key_input = QLineEdit(self)
        self.api_key_input.setPlaceholderText("Enter your OpenAI API Key")
        
        layout = QFormLayout(self)
        layout.addRow("API Key:", self.api_key_input)
        
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def get_api_key(self):
        return self.api_key_input.text()

class RecruiterApp(QMainWindow):
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key)
        self.config = load_config()
        self.initUI()
        self.create_assistant()

    def initUI(self):
        self.setWindowTitle('Tech Recruiter Assistant')
        self.setGeometry(300, 300, 800, 600)

        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)

        self.home_page = HomePage(self)
        self.upload_page = UploadPage(self)

        self.central_widget.addWidget(self.home_page)
        self.central_widget.addWidget(self.upload_page)

        self.setStyleSheet(self.light_mode_stylesheet())

    def create_assistant(self):
        self.assistant = self.client.beta.assistants.create(
            name="Recruiter Assistant",
            instructions="You are a recruiter assistant. Evaluate job candidates based on their resumes and a job description. Provide a ranking, overview, pros, and cons for each candidate.",
            tools=[],
            model="gpt-4o",
        )

    def light_mode_stylesheet(self):
        return """
        QWidget {
            background-color: #f5f5f5;
            color: #000000;
            font-family: Arial, sans-serif;
            font-size: 18px;
        }
        QLineEdit, QTextEdit {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #cccccc;
            padding: 10px;
            border-radius: 5px;
        }
        QPushButton {
            background-color: #4caf50;
            color: #ffffff;
            border: 1px solid #4caf50;
            padding: 10px;
            border-radius: 5px;
            font-size: 18px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QLabel {
            color: #000000;
            font-weight: bold;
        }
        QTableWidget {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #cccccc;
            padding: 10px;
            border-radius: 5px;
        }
        QHeaderView::section {
            background-color: #4caf50;
            color: #ffffff;
            padding: 5px;
            border: 1px solid #cccccc;
        }
        """

class HomePage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        upload_btn = QPushButton('Upload Resumes')
        upload_btn.clicked.connect(self.show_upload_page)
        layout.addWidget(upload_btn)

        self.setLayout(layout)

    def show_upload_page(self):
        self.parent.central_widget.setCurrentWidget(self.parent.upload_page)

class UploadPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.upload_status = QLabel("No files uploaded.")
        layout.addWidget(self.upload_status)

        self.upload_btn = QPushButton('Upload Resumes', self)
        self.upload_btn.clicked.connect(self.upload_files)
        layout.addWidget(self.upload_btn)

        self.job_desc = QTextEdit(self)
        self.job_desc.setPlaceholderText("Enter Job Description")
        if 'job_description' in self.parent.config:
            self.job_desc.setText(self.parent.config['job_description'])
        layout.addWidget(QLabel("Job Description:"))
        layout.addWidget(self.job_desc)

        self.process_btn = QPushButton('Process Candidates', self)
        self.process_btn.clicked.connect(self.process_candidates)
        layout.addWidget(self.process_btn)

        self.processing_label = QLabel("")
        layout.addWidget(self.processing_label)

        self.results_table = QTableWidget(self)
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Ranking", "Overview", "Pros", "Cons"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setSelectionMode(QAbstractItemView.NoSelection)
        layout.addWidget(self.results_table)

        back_btn = QPushButton('Back to Home')
        back_btn.clicked.connect(self.show_home_page)
        layout.addWidget(back_btn)

        self.setLayout(layout)

    def upload_files(self):
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(self, "Select Resume Files", "", "All Files (*);;Text Files (*.txt);;PDF Files (*.pdf)", options=options)
        if files:
            self.files = files
            self.upload_status.setText("Files uploaded: " + ", ".join([os.path.basename(file) for file in self.files]))
            self.parent.config['files'] = self.files
            save_config(self.parent.config)

    def process_candidates(self):
        job_description = self.job_desc.toPlainText()
        self.parent.config['job_description'] = job_description
        save_config(self.parent.config)

        resumes = [self.read_file(file) for file in self.files]

        self.processing_label.setText("Processing...")

        # Create a new thread for the conversation
        thread = self.parent.client.beta.threads.create()

        # Add the job description as the first message
        self.parent.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"""
                Job Description: {job_description}

                Evaluate each candidate based on their resume and the job description. Provide a ranking, overview, pros, and cons for each candidate in the following JSON format:

                [
                    {{
                        "ranking": "1",
                        "overview": "Candidate's overview",
                        "pros": "List of pros",
                        "cons": "List of cons"
                    }},
                    {{
                        "ranking": "2",
                        "overview": "Candidate's overview",
                        "pros": "List of pros",
                        "cons": "List of cons"
                    }},
                    ...
                ]

                Ensure the response is a valid JSON array.
            """
        )

        # Add each resume as a separate message
        for resume in resumes:
            self.parent.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"Resume: {resume}"
            )

        # Run the assistant on a separate thread to avoid blocking the UI
        threading.Thread(target=self.run_thread, args=(thread.id,)).start()

    def run_thread(self, thread_id):
        parent = self

        class EventHandler(AssistantEventHandler):    
            def on_text_created(self, text) -> None:
                pass
              
            def on_text_delta(self, delta, snapshot):
                parent.results_text += delta.value
              
            def on_tool_call_created(self, tool_call):
                pass
          
            def on_tool_call_delta(self, delta, snapshot):
                if delta.type == 'code_interpreter':
                    if delta.code_interpreter.input:
                        pass
                    if delta.code_interpreter.outputs:
                        for output in delta.code_interpreter.outputs:
                            if output.type == "logs":
                                parent.results_text += output.logs

        self.results_text = ""
        with self.parent.client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=self.parent.assistant.id,
            instructions="Evaluate each candidate based on their resume and job description. Provide a ranking, overview, pros, and cons for each candidate in a structured format.",
            event_handler=EventHandler(),
        ) as stream:
            stream.until_done()

        print("Raw API response:", self.results_text)  # Debug print to see the raw API response
        self.processing_label.setText("Processing complete.")
        self.format_results()

    def format_results(self):
        candidates = self.parse_results(self.results_text)
        self.populate_table(candidates)

    def parse_results(self, text):
        # Remove code fences if present
        if text.startswith("```json") and text.endswith("```"):
            text = text[7:-3].strip()
        elif text.startswith("```") and text.endswith("```"):
            text = text[3:-3].strip()
        
        try:
            candidates = json.loads(text)
        except json.JSONDecodeError:
            print("Error parsing JSON")
            print("Raw JSON text:", text)  # Debug print to see what was attempted to be parsed
            return []

        return candidates

    def populate_table(self, candidates):
        self.results_table.setRowCount(len(candidates))
        for row, candidate in enumerate(candidates):
            self.results_table.setItem(row, 0, QTableWidgetItem(candidate["ranking"]))
            self.results_table.setItem(row, 1, QTableWidgetItem(candidate["overview"]))
            self.results_table.setItem(row, 2, QTableWidgetItem(", ".join(candidate["pros"])))
            self.results_table.setItem(row, 3, QTableWidgetItem(", ".join(candidate["cons"])))

    def read_file(self, file_path):
        if file_path.lower().endswith('.pdf'):
            return self.read_pdf(file_path)
        else:
            return self.read_text_file(file_path)

    def read_text_file(self, file_path):
        encodings = ['utf-8', 'latin1', 'utf-16', 'iso-8859-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read().replace('\n', ' ')
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        raise UnicodeDecodeError(f"Unable to decode the file: {file_path}")

    def read_pdf(self, file_path):
        doc = fitz.open(file_path)
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text().replace('\n', ' ')
        return text

    def show_home_page(self):
        self.parent.central_widget.setCurrentWidget(self.parent.home_page)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    config = load_config()
    api_key = config.get('api_key')
    if not api_key:
        api_key_dialog = APIKeyDialog()
        if api_key_dialog.exec_() == QDialog.Accepted:
            api_key = api_key_dialog.get_api_key()
            config['api_key'] = api_key
            save_config(config)

    ex = RecruiterApp(api_key)
    ex.show()
    sys.exit(app.exec_())
