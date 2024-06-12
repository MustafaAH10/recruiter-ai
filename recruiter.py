import sys
import fitz  # PyMuPDF
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QTextEdit, QFileDialog, QLabel, QLineEdit, QStackedWidget, QListWidget, QListWidgetItem, QDialog, QFormLayout, QDialogButtonBox
import openai

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
        self.initUI()

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

    def dark_mode_stylesheet(self):
        return """
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
            font-family: Arial, sans-serif;
            font-size: 16px;
        }
        QLineEdit, QTextEdit {
            background-color: #3c3f41;
            color: #ffffff;
            border: 1px solid #4a4a4a;
            padding: 10px;
            border-radius: 10px;
        }
        QPushButton {
            background-color: #3c3f41;
            color: #ffffff;
            border: 1px solid #4a4a4a;
            padding: 10px;
            border-radius: 10px;
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
            background-color: #3c3f41;
            color: #ffffff;
            border: 1px solid #4a4a4a;
            padding: 10px;
            border-radius: 10px;
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

        self.upload_btn = QPushButton('Upload Resumes', self)
        self.upload_btn.clicked.connect(self.upload_files)
        layout.addWidget(self.upload_btn)

        self.job_desc = QTextEdit(self)
        self.job_desc.setPlaceholderText("Enter Job Description")
        layout.addWidget(QLabel("Job Description:"))
        layout.addWidget(self.job_desc)

        self.process_btn = QPushButton('Process Candidates', self)
        self.process_btn.clicked.connect(self.process_candidates)
        layout.addWidget(self.process_btn)

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

    def process_candidates(self):
        job_description = self.job_desc.toPlainText()
        resumes = [self.read_file(file) for file in self.files]

        results = self.rank_candidates(self.parent.api_key, job_description, resumes)
        self.display_results(results)

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

    def rank_candidates(self, api_key, job_description, resumes):
        openai.api_key = api_key
        response = openai.Completion.create(
            engine="davinci",
            prompt=f"Job Description:\n{job_description}\n\nResumes:\n" + "\n\n".join(resumes) + "\n\nRank the candidates based on their suitability for the job and provide pros and cons for each.",
            max_tokens=500
        )
        return response.choices[0].text

    def display_results(self, results):
        self.results.setText(results)

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
    
    api_key_dialog = APIKeyDialog()
    if api_key_dialog.exec_() == QDialog.Accepted:
        api_key = api_key_dialog.get_api_key()
        ex = RecruiterApp(api_key)
        ex.show()
        sys.exit(app.exec_())
