<div align="center">

# AI-Powered Resume Analyzer & Resume Matching System

### Intelligent ATS Resume Analysis and Semantic Resume Matching Using AI, NLP & Machine Learning

<p align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web_Framework-000000?style=for-the-badge&logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite)
![Machine Learning](https://img.shields.io/badge/Machine-Learning-orange?style=for-the-badge)
![NLP](https://img.shields.io/badge/NLP-spaCy-success?style=for-the-badge)
![Sentence-BERT](https://img.shields.io/badge/Sentence--BERT-Embedding-red?style=for-the-badge)
![License](https://img.shields.io/badge/License-Educational-blue?style=for-the-badge)

</p>

*A Final Year Project developed at the Department of Computer Science and Engineering, Varendra University.*

</div>

---

# About

The **AI-Powered Resume Analyzer & Resume Matching System** is a modern web-based recruitment platform designed to improve the hiring process using **Artificial Intelligence (AI)**, **Machine Learning (ML)**, and **Natural Language Processing (NLP)**.

The system helps **job seekers** create ATS-friendly resumes by analyzing resume quality and providing personalized improvement suggestions. It also assists **recruiters** by automatically matching resumes with job descriptions through semantic similarity analysis instead of simple keyword matching.

Unlike conventional Applicant Tracking Systems (ATS), this project combines **Rule-Based ATS Analysis**, **Sentence-BERT**, **spaCy**, **TF-IDF**, **CountVectorizer**, and **Latent Semantic Analysis (LSA)** to produce more accurate and meaningful results.

---

# Key Features

### User Management
- Secure User Registration
- Login & Authentication
- Password Encryption using Werkzeug
- User Profile Management

### Resume Processing
- Upload Resume (PDF & DOCX)
- Automatic Resume Parsing
- Resume Text Extraction
- Resume Preprocessing

### ATS Resume Analysis
- ATS Compatibility Check
- Resume Formatting Analysis
- Keyword Analysis
- Contact Information Validation
- Skills Detection
- Experience Analysis
- Education Analysis
- Project & Certification Analysis
- ATS Score Generation
- Resume Quality Evaluation
- Personalized Improvement Suggestions

### Resume Matching
- Upload Job Description
- Semantic Resume Matching
- Similarity Score Calculation
- Candidate Ranking
- Missing Skill Detection

### Reports
- ATS Analysis Report
- Resume Matching Report
- Recommendation Report

---

# Data Processing Workflow

```text
                    User Registration
                           │
                           ▼
                     Secure Login
                           │
                           ▼
                 Upload Resume (PDF/DOCX)
                           │
                           ▼
                  Resume Text Extraction
                           │
                           ▼
                  Resume Preprocessing
      ┌──────────────────────────────────────┐
      │ • Text Cleaning                      │
      │ • Normalization                      │
      │ • Remove Special Characters          │
      │ • Tokenization                       │
      │ • Stop-word Processing               │
      └──────────────────────────────────────┘
                           │
                           ▼
                     Resume Parsing
                           │
                           ▼
        Extract Important Resume Sections
      ┌──────────────────────────────────────┐
      │ Personal Information                 │
      │ Professional Summary                 │
      │ Education                            │
      │ Skills                               │
      │ Work Experience                      │
      │ Projects                             │
      │ Certifications                       │
      │ Achievements                         │
      └──────────────────────────────────────┘
                           │
                           ▼
                Rule-Based ATS Evaluation
                           │
                           ▼
                 ATS Score Generation
                           │
                           ▼
          Personalized Resume Suggestions
                           │
                           ▼
              Upload Job Description
                           │
                           ▼
              Job Description Processing
                           │
                           ▼
             Machine Learning Pipeline
                           │
                           ▼
           Sentence-BERT Semantic Embedding
                           │
                           ▼
          TF-IDF Feature Representation
                           │
                           ▼
      CountVectorizer Feature Extraction
                           │
                           ▼
      Truncated SVD (Latent Semantic Analysis)
                           │
                           ▼
           Cosine Similarity Calculation
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

# System Architecture

```text
                  ┌─────────────────────────────┐
                  │        Web Browser          │
                  └─────────────┬───────────────┘
                                │
                                ▼
                  ┌─────────────────────────────┐
                  │      Flask Application      │
                  └─────────────┬───────────────┘
                                │
      ┌──────────────┬──────────┴───────────┬──────────────┐
      ▼              ▼                      ▼              ▼
 Authentication   Resume Parser       ATS Analyzer   Resume Matcher
      │              │                      │              │
      └──────────────┴──────────┬───────────┴──────────────┘
                                ▼
                    Machine Learning Engine
                                │
      ┌──────────────┬──────────┼──────────────┬─────────────┐
      ▼              ▼          ▼              ▼
   spaCy       Sentence-BERT  TF-IDF   CountVectorizer
                                │
                                ▼
                        Truncated SVD
                                │
                                ▼
                      Cosine Similarity
                                │
                                ▼
                           SQLite Database
```

---

# Technology Stack

| Category | Technology |
|:---------|:-----------|
| Programming Language | Python |
| Backend Framework | Flask |
| Frontend | HTML5, CSS3, JavaScript |
| Styling | Bootstrap, CSS |
| Database | SQLite |
| Authentication | Werkzeug Password Hashing |
| Version Control | Git & GitHub |
| Operating System | Windows / Linux |

---

# Artificial Intelligence & Machine Learning

| Model / Library | Purpose |
|:----------------|:--------|
| Rule-Based ATS Engine | Resume Evaluation |
| Sentence-BERT (all-MiniLM-L6-v2) | Semantic Resume Matching |
| spaCy | NLP Processing |
| TF-IDF Vectorizer | Keyword Feature Extraction |
| CountVectorizer | Text Vectorization |
| Truncated SVD (LSA) | Dimensionality Reduction |
| Cosine Similarity | Similarity Score Calculation |
| Scikit-learn | Machine Learning Algorithms |
| NLTK | Text Processing |

---

# Project Modules

| Module | Description |
|:-------|:------------|
| User Authentication | User Registration & Login |
| Resume Upload | Upload PDF/DOCX Resume |
| Resume Parser | Extract Resume Information |
| ATS Analyzer | Evaluate Resume According to ATS |
| Resume Matcher | Match Resume with Job Description |
| Recommendation Engine | Generate Resume Suggestions |
| Report Generator | Generate ATS & Matching Reports |
| Database Manager | Store Users & Analysis Results |

---

# Project Structure

```text
AI-Resume-Analyzer/
│
├── app.py
├── requirements.txt
├── README.md
├── database.db
│
├── static/
│   ├── css/
│   ├── js/
│   ├── images/
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│
├── uploads/
│
├── models/
│
├── utils/
│
├── reports/
│
└── assets/
```

---

# Project Highlights

- Intelligent ATS Resume Analysis
- AI-Based Resume Matching
- Secure Authentication
- Modern Web Interface
- Semantic Search
- Automated Candidate Ranking
- Resume Improvement Suggestions
- Machine Learning Integration
- NLP-Based Resume Understanding
- Recruiter-Friendly Dashboard

---

---

# Installation

## Prerequisites

Before running the project, ensure the following software is installed:

- Python 3.10 or later
- Git
- pip
- Virtual Environment (Recommended)

---

## Clone the Repository

```bash
git clone https://github.com/your-username/AI-Resume-Analyzer.git
```

Move into the project directory.

```bash
cd AI-Resume-Analyzer
```

---

## Create a Virtual Environment

Windows

```bash
python -m venv venv
venv\Scripts\activate
```

Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Run the Application

```bash
python app.py
```

Open your browser and visit:

```
http://127.0.0.1:5000
```

---

# Usage

### Step 1

Register a new account or log in.

### Step 2

Upload a Resume (PDF or DOCX).

### Step 3

The system automatically:

- Extracts resume text
- Parses resume sections
- Performs ATS analysis
- Generates ATS Score
- Detects missing keywords
- Provides improvement suggestions

### Step 4

Upload a Job Description.

### Step 5

The AI Matching Engine:

- Converts resume and job description into semantic embeddings
- Calculates similarity
- Displays Matching Score
- Ranks candidate suitability

---

# Database Overview

The application uses **SQLite** to securely store user and analysis data.

| Table | Description |
|:------|:------------|
| Users | User account information |
| Resumes | Uploaded resume files |
| ATS Reports | Resume analysis reports |
| Job Descriptions | Uploaded job descriptions |
| Matching Results | Resume similarity scores |

---

# Screenshots

> Add screenshots after uploading the project to GitHub.

```
assets/

├── home.png
├── login.png
├── dashboard.png
├── upload.png
├── ats-report.png
├── matching-result.png
```

Example:

```md
## Home Page

<p align="center">
<img src="assets/home.png" width="90%">
</p>

## ATS Report

<p align="center">
<img src="assets/ats-report.png" width="90%">
</p>

## Resume Matching

<p align="center">
<img src="assets/matching-result.png" width="90%">
</p>
```

---

# Team

| Name | Student ID | Department | Profile |
|:-----|:----------:|:-----------|:---------|
| **Farhana Tasnin** | 222311053 | Department of Computer Science & Engineering, Varendra University | *Add GitHub / LinkedIn* |
| **Katamun Jannat** | 222311058 | Department of Computer Science & Engineering, Varendra University | *Add GitHub / LinkedIn* |
| **Md. Ratan Ali** | **222311069** | Department of Computer Science & Engineering, Varendra University | **[GitHub](https://github.com/yourusername)** • **[LinkedIn](https://linkedin.com/in/yourusername)** |

---

# Project Supervisor

| Name | Designation | Profile |
|:-----|:------------|:--------|
| **Md. Fatin Ilham** | Lecturer, Department of Computer Science & Engineering, Varendra University | *Faculty Profile / University Website* |

---

# Future Improvements

The current system provides a strong foundation for intelligent recruitment. Future enhancements include:

- Multi-language Resume Analysis
- Cloud Deployment
- Recruiter Dashboard
- Resume Benchmarking
- Skill Gap Analysis
- AI Interview Recommendation
- Deep Learning Models
- Resume Ranking Dashboard
- Email Notifications
- Online Job Portal Integration
- REST API
- Docker Support
- CI/CD Pipeline

---

# Contributing

Contributions are welcome.

If you would like to improve this project:

1. Fork the repository
2. Create a new branch

```bash
git checkout -b feature-name
```

3. Commit your changes

```bash
git commit -m "Add new feature"
```

4. Push to GitHub

```bash
git push origin feature-name
```

5. Create a Pull Request

---

# License

This project was developed for academic and educational purposes.

Feel free to use it for learning and research with proper attribution.

---

# Acknowledgements

We would like to express our sincere gratitude to our respected supervisor **Md. Fatin Ilham**, Lecturer, Department of Computer Science and Engineering, Varendra University, for his continuous guidance, valuable suggestions, and encouragement throughout the development of this project.

We also thank the Department of Computer Science and Engineering, Varendra University, for providing the academic environment and support necessary to successfully complete this project.

Special thanks to everyone who contributed directly or indirectly to the successful completion of this project.

---

# Authors

| Name | Role |
|:-----|:-----|
| **Farhana Tasnin** | Developer |
| **Katamun Jannat** | Developer |
| **Md. Ratan Ali** | Developer, UI/UX Designer & Project Maintainer |

---

# Citation

If you use this project in your research or academic work, please cite it appropriately.

```text
AI-Powered Resume Analyzer and Resume Matching System
Department of Computer Science & Engineering
Varendra University
2026
```

---

# Support

If you found this project helpful, please consider giving it a ⭐ on GitHub.

---

<div align="center">

### ⭐ Thank You for Visiting ⭐

**AI-Powered Resume Analyzer & Resume Matching System**

Developed with ❤️ using **Python**, **Flask**, **Machine Learning**, and **Natural Language Processing**

© 2026 Department of Computer Science & Engineering, Varendra University

</div>
