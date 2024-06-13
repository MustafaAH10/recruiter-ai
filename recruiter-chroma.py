import chromadb
from sentence_transformers import SentenceTransformer, util
import json
import os
import sys
import fitz
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QTextEdit, QFileDialog,
    QLabel, QLineEdit, QStackedWidget, QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QDialogButtonBox, QHeaderView, QAbstractItemView, QHBoxLayout, QGridLayout, QInputDialog, QMessageBox
)

CONFIG_FILE = "config.json"
JOBS_FILE = "jobs.json"

# Load and save config functions
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file)

def load_jobs():
    if os.path.exists(JOBS_FILE):
        with open(JOBS_FILE, 'r') as file:
            return json.load(file)
    return []

def save_jobs(jobs):
    with open(JOBS_FILE, 'w') as file:
        json.dump(jobs, file)

# Initialize Chroma and embedding model
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="resumes")
model = SentenceTransformer('all-MiniLM-L6-v2')

class RecruiterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.jobs = load_jobs()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Tech Recruiter Assistant')
        self.setGeometry(300, 300, 1000, 800)

        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)

        self.home_page = HomePage(self)
        self.job_page = JobPage(self)
        self.upload_page = UploadPage(self)

        self.central_widget.addWidget(self.home_page)
        self.central_widget.addWidget(self.job_page)
        self.central_widget.addWidget(self.upload_page)

        self.setStyleSheet(self.light_mode_stylesheet())

    def light_mode_stylesheet(self):
        return """
        QWidget {
            background-color: #f5f5f5;
            color: #000000;
            font-family: Arial, sans-serif;
            font-size: 20px;
        }
        QLineEdit, QTextEdit {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #cccccc;
            padding: 12px;
            border-radius: 5px;
        }
        QPushButton {
            background-color: #4caf50;
            color: #ffffff;
            border: 1px solid #4caf50;
            padding: 12px;
            border-radius: 5px;
            font-size: 20px;
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
            border: 1px solid #cccccc.
        }
        """

class HomePage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        manage_jobs_btn = QPushButton('Manage Jobs')
        manage_jobs_btn.clicked.connect(self.show_job_page)
        layout.addWidget(manage_jobs_btn)

        self.setLayout(layout)

    def show_job_page(self):
        self.parent.central_widget.setCurrentWidget(self.parent.job_page)

class JobPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(10)

        self.load_jobs()

        create_job_btn = QPushButton('Create Job')
        create_job_btn.setStyleSheet('color: green')
        create_job_btn.clicked.connect(self.create_job)
        layout.addWidget(create_job_btn)

        layout.addLayout(self.grid_layout)

        back_btn = QPushButton('Back to Home')
        back_btn.clicked.connect(self.show_home_page)
        layout.addWidget(back_btn)

        self.setLayout(layout)

    def load_jobs(self):
        for i in reversed(range(self.grid_layout.count())): 
            widgetToRemove = self.grid_layout.itemAt(i).widget()
            self.grid_layout.removeWidget(widgetToRemove)
            widgetToRemove.setParent(None)

        for index, job in enumerate(self.parent.jobs):
            self.add_job_card(index, job)

    def add_job_card(self, index, job):
        job_card = QWidget()
        card_layout = QVBoxLayout()
        
        job_title = QLabel(f"{job['title']} at {job['company']}")
        card_layout.addWidget(job_title)

        open_btn = QPushButton("Open")
        open_btn.clicked.connect(lambda checked, index=index: self.open_job(index))
        card_layout.addWidget(open_btn)

        delete_btn = QPushButton('Delete Job')
        delete_btn.setStyleSheet('color: red')
        delete_btn.clicked.connect(lambda checked, index=index: self.delete_job(index))
        card_layout.addWidget(delete_btn)
        
        job_card.setLayout(card_layout)
        job_card.setMinimumHeight(100)
        self.grid_layout.addWidget(job_card, index // 2, index % 2)

    def create_job(self):
        title, ok = QInputDialog.getText(self, 'Job Title', 'Enter job title:')
        if ok and title:
            company, ok = QInputDialog.getText(self, 'Company Name', 'Enter company name:')
            if ok and company:
                description, ok = QInputDialog.getMultiLineText(self, 'Job Description', 'Enter job description:')
                if ok:
                    new_job = {
                        "title": title,
                        "company": company,
                        "description": description,
                        "rankings": []
                    }
                    self.parent.jobs.append(new_job)
                    save_jobs(self.parent.jobs)
                    self.load_jobs()

    def open_job(self, index):
        job = self.parent.jobs[index]
        self.parent.upload_page.set_job_index(index)
        self.parent.upload_page.set_job_description(job['description'])
        self.parent.upload_page.load_rankings(job.get('rankings', []))
        self.parent.central_widget.setCurrentWidget(self.parent.upload_page)

    def delete_job(self, index):
        del self.parent.jobs[index]
        save_jobs(self.parent.jobs)
        self.load_jobs()

    def show_home_page(self):
        self.parent.central_widget.setCurrentWidget(self.parent.home_page)

class UploadPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.job_index = None
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

        back_btn = QPushButton('Back to Jobs')
        back_btn.clicked.connect(self.show_job_page)
        layout.addWidget(back_btn)

        self.setLayout(layout)

    def set_job_index(self, index):
        self.job_index = index

    def set_job_description(self, description):
        self.job_desc.setText(description)

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

        # Embed job description
        job_desc_embedding = model.encode(job_description).tolist()

        # Store resume embeddings in Chroma
        resume_embeddings = []
        for i, resume in enumerate(resumes):
            embedding = model.encode(resume).tolist()  # Convert to list
            resume_embeddings.append(embedding)
            collection.upsert(documents=[resume], embeddings=[embedding], ids=[str(i)])  # Add unique IDs

        # Compute similarity scores
        similarities = []
        for embedding in resume_embeddings:
            similarity = util.pytorch_cos_sim(job_desc_embedding, embedding).item()
            similarities.append(similarity)

        # Rank candidates based on similarity scores
        ranked_candidates = sorted(
            [(resumes[i], similarities[i]) for i in range(len(resumes))],
            key=lambda x: x[1],
            reverse=True
        )

        self.processing_label.setText("Processing complete.")
        self.format_results(ranked_candidates)


    def format_results(self, ranked_candidates):
        candidates = [
            {"ranking": str(i + 1), "overview": ranked_candidates[i][0], "pros": "", "cons": ""}
            for i in range(len(ranked_candidates))
        ]
        self.populate_table(candidates)
        self.save_rankings(candidates)

    def populate_table(self, candidates):
        self.results_table.setRowCount(len(candidates))
        for row, candidate in enumerate(candidates):
            self.results_table.setItem(row, 0, QTableWidgetItem(candidate["ranking"]))
            self.results_table.setItem(row, 1, QTableWidgetItem(candidate["overview"]))
            self.results_table.setItem(row, 2, QTableWidgetItem(candidate["pros"]))
            self.results_table.setItem(row, 3, QTableWidgetItem(candidate["cons"]))
        self.results_table.resizeRowsToContents()  # Adjust row heights

    def save_rankings(self, candidates):
        if self.job_index is not None:
            self.parent.jobs[self.job_index]['rankings'] = candidates
            save_jobs(self.parent.jobs)

    def load_rankings(self, rankings):
        self.populate_table(rankings)

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

    def show_job_page(self):
        self.parent.central_widget.setCurrentWidget(self.parent.job_page)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    ex = RecruiterApp()
    ex.show()
    sys.exit(app.exec_())
