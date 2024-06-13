import sys
import json
import os
from openai import OpenAI, AssistantEventHandler
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QTextEdit, QFileDialog, QLabel, QLineEdit, QStackedWidget, QListWidget, QListWidgetItem, QDialog, QFormLayout, QDialogButtonBox, QHBoxLayout
from PyQt5.QtGui import QMovie
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
        self.summary_page = SummaryPage(self)

        self.central_widget.addWidget(self.home_page)
        self.central_widget.addWidget(self.upload_page)
        self.central_widget.addWidget(self.summary_page)

        self.setStyleSheet(self.dark_mode_stylesheet())

    def create_assistant(self):
        self.assistant = self.client.beta.assistants.create(
            name="Recruiter Assistant",
            instructions="You are a recruiter assistant. Evaluate job candidates based on their resumes and a job description. Provide a concise overview, pros, and cons for each candidate.",
            tools=[],
            model="gpt-4o",
        )

    def dark_mode_stylesheet(self):
        return """
        QWidget {
            background-color: #1e1e1e;
            color: #ffffff;
            font-family: Arial, sans-serif;
            font-size: 16px;
        }
        QLineEdit, QTextEdit {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #4a4a4a;
            padding: 10px;
            border-radius: 5px;
        }
        QPushButton {
            background-color: #3c3f41;
            color: #ffffff;
            border: 1px solid #4a4a4a;
            padding: 10px;
            border-radius: 5px;
            font-size: 16px;
        }
        QPushButton:hover {
            background-color: #4a4a4a;
        }
        QLabel {
            color: #ffffff;
            font-weight: bold;
        }
        QListWidget {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #4a4a4a;
            padding: 10px;
            border-radius: 5px;
        }
        QHeaderView::section {
            background-color: #3c3f41;
            color: #ffffff;
            padding: 5px;
            border: 1px solid #4a4a4a;
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

        summary_btn = QPushButton('View Candidate Summary')
        summary_btn.clicked.connect(self.show_summary_page)
        layout.addWidget(summary_btn)

        self.setLayout(layout)

    def show_upload_page(self):
        self.parent.central_widget.setCurrentWidget(self.parent.upload_page)

    def show_summary_page(self):
        self.parent.central_widget.setCurrentWidget(self.parent.summary_page)

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

        self.results = QTextEdit(self)
        self.results.setReadOnly(True)
        layout.addWidget(QLabel("Results:"))
        layout.addWidget(self.results)

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
            content=f"Job Description: {job_description}"
        )

        # Add each resume as a separate message
        for resume in resumes:
            self.parent.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"Resume: {resume}"
            )

        # Run the assistant on the thread
        self.run_thread(thread.id)

    def run_thread(self, thread_id):
        parent = self

        class EventHandler(AssistantEventHandler):    
            def on_text_created(self, text) -> None:
                print(f"\nassistant > ", end="", flush=True)
              
            def on_text_delta(self, delta, snapshot):
                print(delta.value, end="", flush=True)
                parent.results.append(delta.value)
              
            def on_tool_call_created(self, tool_call):
                print(f"\nassistant > {tool_call.type}\n", flush=True)
          
            def on_tool_call_delta(self, delta, snapshot):
                if delta.type == 'code_interpreter':
                    if delta.code_interpreter.input:
                        print(delta.code_interpreter.input, end="", flush=True)
                    if delta.code_interpreter.outputs:
                        print(f"\n\noutput >", flush=True)
                        for output in delta.code_interpreter.outputs:
                            if output.type == "logs":
                                print(f"\n{output.logs}", flush=True)
                                parent.results.append(output.logs)
        
        with self.parent.client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=self.parent.assistant.id,
            instructions="Evaluate each candidate based on their resume and job description. Provide a concise overview, pros, and cons for each candidate in a structured format.",
            event_handler=EventHandler(),
        ) as stream:
            stream.until_done()
        
        self.processing_label.setText("Processing complete.")
        self.format_results()

    def format_results(self):
        text = self.results.toPlainText()
        # Replace newlines and double asterisks with HTML tags
        formatted_text = text.replace('\n', '<br>').replace('**', '<b>').replace('**', '</b>')
        self.results.setHtml(f"<div style='padding: 10px;'>{formatted_text}</div>")

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

class SummaryPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.candidate_list = QListWidget(self)
        layout.addWidget(QLabel("Candidate Summary:"))
        layout.addWidget(self.candidate_list)

        back_btn = QPushButton('Back to Home')
        back_btn.clicked.connect(self.show_home_page)
        layout.addWidget(back_btn)

        self.setLayout(layout)

    def show_home_page(self):
        self.parent.central_widget.setCurrentWidget(self.parent.home_page)

    def load_candidates(self, candidates):
        self.candidate_list.clear()
        for candidate in candidates:
            item = QListWidgetItem(f"{candidate['name']}\nSkills: {candidate['skills']}\nResume: {candidate['resume_link']}")
            self.candidate_list.addItem(item)

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
