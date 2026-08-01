# AI-Powered Resume Analyzer and Resume Matching System

<p align="center">
  <img src="assets/logo.png" width="120" alt="Project Logo">
</p>

## 📌 Project Overview

The AI-Powered Resume Analyzer and Resume Matching System is an intelligent web application that helps job seekers optimize their resumes and enables recruiters to identify suitable candidates efficiently.

The system analyzes resumes according to Applicant Tracking System (ATS) standards and matches resumes with job descriptions using Artificial Intelligence (AI), Machine Learning (ML), and Natural Language Processing (NLP).

Unlike traditional keyword-based systems, this project uses semantic similarity techniques to understand the actual meaning of resume content and provide accurate matching results.

---

# ✨ Features

- User Registration & Login
- Secure Authentication
- Resume Upload (PDF/DOCX)
- Resume Parsing
- ATS Resume Analysis
- ATS Score Generation
- Resume Improvement Suggestions
- Resume Matching with Job Description
- Semantic Similarity using Sentence-BERT
- Skill Extraction
- Keyword Analysis
- Report Generation
- SQLite Database Storage
- Responsive Web Interface

---

# 🧠 Data Processing Workflow

The complete workflow of the system is shown below.

```
User Registration/Login
          │
          ▼
Upload Resume (PDF/DOCX)
          │
          ▼
Resume Text Extraction
          │
          ▼
Text Preprocessing
 • Cleaning
 • Normalization
 • Tokenization
          │
          ▼
Resume Parsing
 • Personal Information
 • Education
 • Skills
 • Experience
 • Projects
 • Certifications
 • Achievements
          │
          ▼
ATS Resume Analysis
 • Formatting Check
 • Keyword Analysis
 • Section Analysis
 • Readability
 • Action Verbs
 • Quantified Achievements
          │
          ▼
ATS Score Generation
          │
          ▼
Resume Recommendations
          │
          ▼
(Optional)
Upload Job Description
          │
          ▼
Job Description Preprocessing
          │
          ▼
Feature Extraction
 • Sentence-BERT
 • spaCy
 • TF-IDF
 • CountVectorizer
 • Truncated SVD (LSA)
          │
          ▼
Semantic Similarity Calculation
          │
          ▼
Resume Matching Score
          │
          ▼
Candidate Ranking
          │
          ▼
Store Results in SQLite Database
          │
          ▼
Generate Final Report
```

---

# ⚙️ Technologies Used

| Category | Technology |
|-----------|------------|
| Programming Language | Python |
| Backend Framework | Flask |
| Frontend | HTML5, CSS3, JavaScript |
| Database | SQLite |
| Authentication | Werkzeug Password Hashing |
| NLP Library | spaCy |
| Sentence Embedding | Sentence-BERT (all-MiniLM-L6-v2) |
| Machine Learning | Scikit-learn |
| Feature Extraction | TF-IDF |
| Vectorization | CountVectorizer |
| Dimensionality Reduction | Truncated SVD (LSA) |
| Similarity Measurement | Cosine Similarity |
| Document Processing | PyPDF2, pdfplumber, python-docx |
| Version Control | Git & GitHub |

---

# 📂 Project Modules

- User Authentication
- Resume Upload
- Resume Parser
- ATS Analyzer
- Resume Matcher
- Recommendation Engine
- Report Generator
- Database Management

---

# 📁 Project Structure

```
Resume-Analyzer/
│
├── app.py
├── requirements.txt
├── database.db
├── static/
├── templates/
├── uploads/
├── models/
├── utils/
├── assets/
└── README.md
```

---

# 🚀 Installation

Clone the repository

```bash
git clone https://github.com/yourusername/resume-analyzer.git
```

Go to project directory

```bash
cd resume-analyzer
```

Create virtual environment

```bash
python -m venv venv
```

Activate virtual environment

Windows

```bash
venv\Scripts\activate
```

Linux/Mac

```bash
source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run the application

```bash
python app.py
```

Open your browser

```
http://127.0.0.1:5000
```

---

# 📊 Machine Learning Models Used

| Model | Purpose |
|-------|---------|
| Sentence-BERT | Semantic Resume Matching |
| spaCy | NLP Processing |
| TF-IDF | Keyword Feature Extraction |
| CountVectorizer | Text Vectorization |
| Truncated SVD (LSA) | Feature Reduction |
| Cosine Similarity | Similarity Score Calculation |

---

# 📋 Team Members

| Name | Student ID | Department | University |
|------|------------|------------|------------|
| Farhana Tasnin | 222311053 | Department of Computer Science & Engineering | Varendra University |
| Katamun Jannat | 222311058 | Department of Computer Science & Engineering | Varendra University |
| **Md. Ratan Ali** | **222311069** | **Department of Computer Science & Engineering** | **Varendra University** |

---

# 👨‍🏫 Supervisor

| Name | Designation |
|------|-------------|
| **Md. Fatin Ilham** | Lecturer, Department of Computer Science & Engineering, Varendra University |

---

# 🎯 Future Improvements

- Cloud Deployment
- Recruiter Dashboard
- AI Interview Recommendation
- Resume Benchmarking
- Skill Gap Analysis
- Multi-language Resume Analysis
- Deep Learning Based Resume Ranking
- Integration with Online Job Portals

---

# 📄 License

This project is developed for academic and educational purposes.

---

# ⭐ Acknowledgement

We sincerely express our gratitude to our respected supervisor **Md. Fatin Ilham**, Lecturer, Department of Computer Science and Engineering, Varendra University, for his valuable guidance, continuous encouragement, and constructive suggestions throughout the development of this project.

We also thank the Department of Computer Science and Engineering, Varendra University, for providing the opportunity and support to successfully complete this project.
