from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import os
import json
import docx2txt
import PyPDF2
import docx
import re
from datetime import timedelta, datetime
import secrets
import smtplib
import threading
from email.message import EmailMessage

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD

from dotenv import load_dotenv
load_dotenv()

# Optional heavy/semantic models (SBERT, spaCy) are OFF by default.
# They only add 0.20 weight to the ensemble score and, in some
# environments, their load can hang for a long time. Enable them with
# ENABLE_SEMANTIC_MODELS=true only where the models load reliably.
ENABLE_SEMANTIC_MODELS = os.getenv('ENABLE_SEMANTIC_MODELS', 'false').lower() in ('1', 'true', 'yes', 'on')

# Use only locally cached HuggingFace/Transformers models when enabled.
# Outbound network calls (revision metadata, model downloads) can hang.
os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

_sbert_model = None


import time


def _guarded_calls(tasks, timeout=12):
    """Run several optional/possibly-hanging calls (e.g. model loads that may
    attempt network access) in parallel daemon threads. Returns a dict keyed by
    each task's name, falling back to that task's default. Guarantees the caller
    never blocks longer than `timeout` seconds total."""
    results = {name: default for name, _, default in tasks}
    states = {}

    def make_target(name, func):
        def _target():
            try:
                states[name] = func()
            except Exception:
                states[name] = results[name]
        return _target

    threads = []
    for name, func, _ in tasks:
        worker = threading.Thread(target=make_target(name, func), daemon=True)
        worker.start()
        threads.append(worker)

    deadline = time.time() + timeout
    for worker in threads:
        remaining = max(0.0, deadline - time.time())
        worker.join(remaining)

    results.update(states)
    return results

# Lazily load and cache the SBERT sentence-embedding model (disabled unless enabled)
def _get_sbert_model():
    global _sbert_model
    if not ENABLE_SEMANTIC_MODELS:
        _sbert_model = False
        return None
    if _sbert_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sbert_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception:
            _sbert_model = False
    if _sbert_model is False:
        return None
    return _sbert_model

# Allowed resume file extensions
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-me-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///analyzer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.permanent_session_lifetime = timedelta(days=7)

db = SQLAlchemy(app)

# User database model - must be defined before db.create_all()
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(30), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    profile_type = db.Column(db.String(20), default='user')

# Stores a saved resume analysis result and its JSON breakdown
class AnalysisResult(db.Model):
    __tablename__ = 'analysis_results'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), default='analyzer')
    score = db.Column(db.Integer, nullable=False)
    results_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# A resume-to-job match run (groups multiple matched resumes)
class MatchSession(db.Model):
    __tablename__ = 'match_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# A single resume's score within a match session
class MatchResult(db.Model):
    __tablename__ = 'match_results'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('match_sessions.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    match_score = db.Column(db.Integer, nullable=False)
    similarity = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Helper to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Resume parsing functions for different file types
def parse_pdf(file_path):
    text = ""
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        text = pdfminer_extract(file_path)
        if text and len(text.strip()) > 50:
            return text
    except Exception:
        pass
    
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(file_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        if text.strip():
            return text.strip()
    except Exception:
        pass
    
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception:
        pass
    
    return text

# Extract text from a DOCX file (python-docx first, docx2txt fallback)
def parse_docx(file_path):
    text = ""
    try:
        doc = docx.Document(file_path)
        full_text = [para.text for para in doc.paragraphs]
        text = '\n'.join(full_text)
    except Exception:
        pass
    
    if not text.strip():
        try:
            text = docx2txt.process(file_path)
        except Exception:
            pass
    
    return text

# Dispatch resume parsing based on file extension (pdf/docx/txt)
def parse_resume(file_path):
    if not os.path.exists(file_path):
        return ""
    
    ext = os.path.splitext(file_path)[1].lower().replace('.', '')
    
    if ext == 'pdf':
        return parse_pdf(file_path)
    elif ext == 'docx':
        return parse_docx(file_path)
    elif ext == 'txt':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""
    else:
        return ""

# Match resume text against known technical/soft skill keyword lists
def extract_skills_from_text(text):
    technical_skills = [
        'python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'go', 'golang', 'rust', 'swift',
        'html', 'css', 'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring',
        'sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'redis', 'elasticsearch',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git', 'github', 'gitlab',
        'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'keras', 'scikit-learn',
        'data analysis', 'data science', 'data engineering', 'big data', 'hadoop', 'spark',
        'tableau', 'power bi', 'excel', 'spss', 'statistics', 'r', 'matlab',
        'project management', 'agile', 'scrum', 'jira', 'confluence',
        'communication', 'teamwork', 'leadership', 'problem-solving', 'analytical',
        'cloud', 'devops', 'ci/cd', 'linux', 'unix', 'bash', 'shell scripting',
        'api', 'rest', 'graphql', 'microservices', 'docker', 'terraform',
        'nlp', 'natural language processing', 'computer vision', 'image processing',
        'iot', 'blockchain', 'cybersecurity', 'networking', 'security'
    ]
    
    soft_skills = [
        'communication', 'teamwork', 'leadership', 'problem-solving', 'analytical',
        'time management', 'adaptability', 'creativity', 'critical thinking',
        'interpersonal', 'collaboration', 'presentation', 'negotiation',
        'decision making', 'organization', 'attention to detail'
    ]
    
    text_lower = text.lower()
    found_technical = [skill for skill in technical_skills if skill in text_lower]
    found_soft = [skill for skill in soft_skills if skill in text_lower]
    
    return found_technical, found_soft

# Detect which standard resume sections are present using regex patterns
def detect_resume_sections(text):
    section_patterns = {
        'contact': r'(contact|contact info|personal info|personal information)\s*[:\-]?',
        'summary': r'(summary|profile|objective|career objective|about me|professional summary)\s*[:\-]?',
        'experience': r'(experience|work experience|employment|work history|professional experience|career)\s*[:\-]?',
        'education': r'(education|academic|qualification|degree|certifications?)\s*[:\-]?',
        'skills': r'(skills?|technical skills?|competencies|expertise|technologies)\s*[:\-]?',
        'projects': r'(projects?|project|portfolio)\s*[:\-]?',
        'languages': r'(languages?|language proficiency)\s*[:\-]?',
        'interests': r'(interests|hobbies|activities)\s*[:\-]?'
    }
    
    found_sections = {}
    for section, pattern in section_patterns.items():
        found_sections[section] = bool(re.search(pattern, text.lower()))
    
    return found_sections

# Score usage of strong vs weak action verbs in the resume
def analyze_action_verbs(text):
    strong_action_verbs = [
        'achieved', 'led', 'managed', 'developed', 'created', 'implemented', 'designed',
        'analyzed', 'optimized', 'improved', 'increased', 'decreased', 'reduced',
        'delivered', 'executed', 'coordinated', 'facilitated', 'negotiated',
        'collaborated', 'mentored', 'trained', 'presented', 'communicated',
        'built', 'launched', 'launched', 'established', 'transformed', 'spearheaded',
        'generated', 'produced', 'generated', 'drove', 'influenced', 'spearheaded'
    ]
    
    weak_action_verbs = ['was', 'were', 'had', 'did', 'made', 'worked', 'helped']
    
    text_lower = text.lower()
    found_strong = [verb for verb in strong_action_verbs if verb in text_lower]
    found_weak = [verb for verb in weak_action_verbs if verb in text_lower]
    
    action_score = min(len(found_strong) * 2, 15)
    if len(found_weak) > len(found_strong):
        action_score = max(action_score - 5, 0)
    
    return action_score, found_strong, found_weak

# Check ATS-friendliness (length, contact info, formatting) and list issues
def check_ats_compatibility(text):
    issues = []
    score = 10
    
    if len(text) < 500:
        issues.append("Resume is too short - may not have enough content for ATS parsing")
        score -= 3
    elif len(text) > 8000:
        issues.append("Resume is too long - may get truncated by ATS systems")
        score -= 2
    
    if not re.search(r'@', text):
        issues.append("No email detected - important for ATS and recruiters")
        score -= 2
    
    if not re.search(r'\d{3}.*\d{3}.*\d{4}', text):
        issues.append("No proper phone number format found")
        score -= 1
    
    if text.count('\n') < 5:
        issues.append("Limited line breaks may affect ATS parsing")
        score -= 1
    
    special_chars = sum(1 for c in text if c in '█▓▒░│┤╡╢╖╕╣║╗╝╜╛┐')
    if special_chars > 5:
        issues.append("Contains special characters that may not parse correctly")
        score -= 2
    
    return max(score, 0), issues

# Core rule-based resume scorer: returns overall score plus per-category breakdown
def score_resume_detailed(text):
    original_text = text
    text = text.lower()
    results = []

    tech_skills, soft_skills = extract_skills_from_text(original_text)
    action_score, strong_verbs, weak_verbs = analyze_action_verbs(original_text)
    quant_count = len(re.findall(r'\d+%|\$\d+|\d+\+?|\b\d{4}\b', original_text.lower()))
    word_count = len(original_text.split())
    sections = detect_resume_sections(original_text)
    has_proper_sections = sum(sections.values())

    # Contact Information
    email_pattern = r'\b[\w.-]+@[\w.-]+\.\w{2,4}\b'
    phone_pattern = r'\b(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b'
    linkedin_pattern = r'linkedin\.com/in/\w+'
    has_email = re.search(email_pattern, original_text) is not None
    has_phone = re.search(phone_pattern, original_text) is not None
    has_linkedin = re.search(linkedin_pattern, original_text) is not None

    contact_score = 10
    contact_flaws, contact_fixes = [], []
    if not has_email:
        contact_flaws.append("Missing email address")
        contact_fixes.append("Add a professional email like john.doe@email.com at the top")
    if not has_phone:
        contact_flaws.append("Missing phone number")
        contact_fixes.append("Include phone number in +1-XXX-XXX-XXXX format")
    if not has_linkedin:
        contact_flaws.append("LinkedIn URL not detected")
        contact_fixes.append("Add LinkedIn URL to boost recruiter visibility")
    if contact_flaws:
        contact_score = 5
    if has_email and has_phone and has_linkedin:
        contact_score = 10

    results.append({
        'category': 'Contact Information',
        'score': contact_score,
        'max_score': 10,
        'flaws': contact_flaws,
        'fix_tips': contact_fixes,
        'suggestions': ["Keep contact info in the header for easy scanning"] if has_email or has_phone else []
    })

    # Professional Summary
    has_summary = sections['summary']
    summary_score = 15
    summary_flaws, summary_fixes = [], []
    summary_text = ''
    if not has_summary:
        summary_flaws.append("No professional summary detected")
        summary_fixes.append("Add a 2-3 sentence summary stating your role, years of experience, and 2-3 core strengths")
        summary_score = 0
    else:
        try:
            summary_text = original_text.lower().split('summary')[1].split('\n')[0].strip()
            if len(summary_text) < 20:
                summary_flaws.append("Summary is too brief")
                summary_fixes.append("Expand to include: your target role, key achievements, and unique value proposition")
                summary_score = 10
            elif len(summary_text) > 300:
                summary_flaws.append("Summary is too long")
                summary_fixes.append("Trim to 2-3 sentences; save detail for Experience section")
                summary_score = 12
        except (IndexError, AttributeError):
            pass

    results.append({
        'category': 'Professional Summary',
        'score': summary_score,
        'max_score': 15,
        'flaws': summary_flaws,
        'fix_tips': summary_fixes,
        'suggestions': [
            "Tailor the summary to the target role",
            "Lead with your most relevant achievement or credential"
        ] if has_summary else ["Add a targeted summary to Frame your experience in the first 3 seconds"]
    })

    # Skills Analysis
    skills_score = 0
    skills_flaws, skills_fixes = [], []
    if tech_skills:
        skills_score += min(len(tech_skills) * 1.5, 15)
    else:
        skills_flaws.append("No technical skills detected")
        skills_fixes.append("Add technical skills relevant to your target role (e.g., Python, SQL, AWS)")
    if soft_skills:
        skills_score += min(len(soft_skills), 10)
    else:
        skills_flaws.append("No soft skills mentioned")
        skills_fixes.append("Include soft skills like communication, leadership, problem-solving")
    skills_score = min(skills_score, 25)
    if len(tech_skills) < 5:
        skills_flaws.append(f"Only {len(tech_skills)} technical skills found")
        skills_fixes.append("Add more role-specific tools and technologies from recent job descriptions")

    results.append({
        'category': 'Skills',
        'score': skills_score,
        'max_score': 25,
        'flaws': skills_flaws,
        'fix_tips': skills_fixes,
        'suggestions': [
            "Group skills by category: Technical, Tools, Soft Skills",
            "Mirror keywords from the job description you are targeting"
        ] if tech_skills else ["Add a dedicated Skills section with 8-12 relevant keywords"]
    })

    # Work Experience
    has_experience = sections['experience']
    exp_score = 0
    exp_flaws, exp_fixes = [], []
    if has_experience:
        exp_score += 15
    else:
        exp_flaws.append("No work experience section detected")
        exp_fixes.append("Add a detailed work experience section with roles, companies, dates, and responsibilities")
    exp_score += action_score
    if len(strong_verbs) < 3:
        exp_flaws.append("Limited use of strong action verbs")
        exp_fixes.append("Start bullets with verbs like: led, built, improved, automated, delivered")
    if quant_count < 2:
        exp_flaws.append(f"Only {quant_count} quantifiable achievements found")
        exp_fixes.append("Add metrics: increased revenue by X%, reduced latency by X%, managed X people")

    results.append({
        'category': 'Work Experience',
        'score': min(exp_score, 30),
        'max_score': 30,
        'flaws': exp_flaws,
        'fix_tips': exp_fixes,
        'suggestions': [
            "Use 4-6 bullet points per role",
            "Start each bullet with an action verb and end with a measurable result"
        ] if has_experience else ["Add work experience with company, role, dates, and impact-focused bullets"]
    })

    # Education
    has_education = sections['education']
    edu_score = 0
    edu_flaws, edu_fixes = [], []
    if has_education:
        edu_score += 10
        degree_keywords = ['bachelor', 'master', 'phd', 'doctorate', 'associate', 'mba', 'bs', 'ba', 'ms', 'ma']
        if any(deg in text for deg in degree_keywords):
            edu_score += 5
        else:
            edu_flaws.append("Degree type not clearly specified")
            edu_fixes.append("Clearly state your degree and field of study, e.g., B.S. in Computer Science")
    else:
        edu_flaws.append("No education section detected")
        edu_fixes.append("Add education with degree, institution, location, and graduation date")

    results.append({
        'category': 'Education',
        'score': min(edu_score, 15),
        'max_score': 15,
        'flaws': edu_flaws,
        'fix_tips': edu_fixes,
        'suggestions': [
            "List education in reverse chronological order",
            "Add GPA if above 3.5, plus honors or relevant coursework"
        ] if has_education else ["Add education section to satisfy baseline ATS requirements"]
    })

    # Certifications
    has_cert = sections['education'] and ('certification' in text or 'certified' in text or 'certificate' in text)
    cert_score = 0
    cert_flaws, cert_fixes = [], []
    if has_cert:
        cert_score += 10
        cert_keywords = ['aws', 'azure', 'google', 'cisco', 'pmp', 'scrum', 'agile', 'comptia', ' oracle']
        cert_count = sum(1 for cert in cert_keywords if cert in text)
        if cert_count >= 2:
            cert_score += 5
    else:
        cert_flaws.append("No certifications detected")
        cert_fixes.append("Add industry-recognized certifications relevant to your field")

    results.append({
        'category': 'Certifications',
        'score': min(cert_score, 15),
        'max_score': 15,
        'flaws': cert_flaws,
        'fix_tips': cert_fixes,
        'suggestions': [
            "Include certifying body, date earned, and expiration if applicable",
            "Prioritize certs that map directly to the target role"
        ] if has_cert else ["Add at least one relevant certification to strengthen credibility"]
    })

    # ATS Compatibility
    ats_score, ats_issues = check_ats_compatibility(original_text)
    ats_flaws, ats_fixes = [], []
    for issue in ats_issues:
        ats_flaws.append(issue)
        if "too short" in issue:
            ats_fixes.append("Expand with more experience, projects, or technical details to reach at least 400 words")
        elif "too long" in issue:
            ats_fixes.append("Trim to 1-2 pages; move older or less relevant roles to a separate 'Additional Experience' section")
        elif "email" in issue:
            ats_fixes.append("Use a standard email format like firstname.lastname@example.com")
        elif "phone" in issue:
            ats_fixes.append("Use format: +1-XXX-XXX-XXXX or (XXX) XXX-XXXX")
        elif "line breaks" in issue:
            ats_fixes.append("Add clear section headers and bullet points for better ATS parsing")
        elif "special characters" in issue:
            ats_fixes.append("Remove tables, text boxes, symbols, and non-standard characters")

    results.append({
        'category': 'ATS Compatibility',
        'score': ats_score,
        'max_score': 10,
        'flaws': ats_flaws,
        'fix_tips': ats_fixes,
        'suggestions': [
            "Use standard section names: Experience, Education, Skills",
            "Avoid headers/footers, columns, and graphics that break parsers"
        ] if ats_score >= 8 else ["Fix ATS issues first, then optimize content"]
    })

    # Formatting & Length
    length_score = 10
    length_flaws, length_fixes = [], []
    if word_count < 200:
        length_flaws.append(f"Resume is very short ({word_count} words)")
        length_fixes.append("Add 1-2 more experience bullets with context and outcomes")
        length_score = 3
    elif word_count < 400:
        length_flaws.append(f"Resume could be more detailed ({word_count} words)")
        length_fixes.append("Expand experience descriptions and add a Projects or Certifications section")
        length_score = 6
    elif word_count > 1500:
        length_flaws.append(f"Resume is long ({word_count} words)")
        length_fixes.append("Trim to 1-2 pages; focus on the last 10 years and most relevant roles")
        length_score = 7
    if has_proper_sections < 4:
        length_flaws.append("Missing standard resume sections")
        length_fixes.append("Ensure you have: Contact, Summary, Experience, Education, Skills")
        length_score = max(length_score - 2, 0)

    results.append({
        'category': 'Formatting & Length',
        'score': length_score,
        'max_score': 10,
        'flaws': length_flaws,
        'fix_tips': length_fixes,
        'suggestions': [
            "Keep to 1-2 pages with consistent date formatting",
            "Use standard fonts and avoid colors/graphics that distract from content"
        ] if length_score >= 8 else ["Simplify structure and ensure all core sections are present"]
    })

    return {
        'rule_score': min(sum(item['score'] for item in results), 100),
        'results': results,
        'extracted': {
            'tech_skills': tech_skills,
            'soft_skills': soft_skills,
            'strong_verbs': strong_verbs,
            'weak_verbs': weak_verbs,
            'quant_count': quant_count,
            'word_count': word_count,
            'sections': sections,
            'has_email': has_email,
            'has_phone': has_phone,
            'has_linkedin': has_linkedin
        }
    }

# Estimate readability from average sentence length (0-1 proxy score)
def _readability_proxy_score(text):
    words = re.findall(r'\b\w+\b', text)
    sentences = re.split(r'[.!?]+', text)
    sentence_count = max(1, len([s for s in sentences if s.strip()]))
    word_count = len(words)
    avg_sentence_len = word_count / sentence_count if sentence_count else word_count

    # Simple readability proxy for resume-like content.
    if avg_sentence_len <= 12:
        return 0.95
    if avg_sentence_len <= 18:
        return 0.85
    if avg_sentence_len <= 24:
        return 0.70
    if avg_sentence_len <= 32:
        return 0.55
    return 0.40

# Measure achievement impact from action verbs and quantified metrics
def _impact_density_score(text):
    action_score, strong_verbs, _ = analyze_action_verbs(text)
    number_hits = len(re.findall(r'\d+%|\$\d+|\d+\+?|\b\d{4}\b', text))
    impact = min((action_score / 15.0) * 0.65 + min(number_hits / 20.0, 1.0) * 0.35, 1.0)
    return max(0.0, impact), strong_verbs, number_hits

# Score breadth/depth of technical and soft skills found
def _skill_depth_score(text):
    tech_skills, soft_skills = extract_skills_from_text(text)
    tech_depth = min(len(set(tech_skills)) / 18.0, 1.0)
    soft_depth = min(len(set(soft_skills)) / 10.0, 1.0)
    depth = (0.75 * tech_depth) + (0.25 * soft_depth)
    return max(0.0, min(depth, 1.0)), tech_skills, soft_skills

# Return normalized ensemble scoring weights tuned to the target role
def _analyzer_weights_by_role(target_role):
    role = (target_role or 'general').lower().strip()
    base = {
        'rule_based': 0.38,
        'readability': 0.08,
        'impact_density': 0.14,
        'skill_depth': 0.12,
        'section_quality': 0.08,
        'sbert_semantic': 0.12,
        'spacy_features': 0.08
    }

    if any(k in role for k in ['data', 'ml', 'ai', 'science']):
        base['skill_depth'] += 0.05
        base['impact_density'] += 0.03
        base['readability'] -= 0.03
        base['section_quality'] -= 0.05
    elif any(k in role for k in ['manager', 'lead', 'management', 'product']):
        base['readability'] += 0.06
        base['section_quality'] += 0.05
        base['skill_depth'] -= 0.06
        base['impact_density'] -= 0.05
    elif any(k in role for k in ['frontend', 'backend', 'fullstack', 'developer', 'engineer']):
        base['skill_depth'] += 0.04
        base['impact_density'] += 0.02
        base['section_quality'] -= 0.03
        base['readability'] -= 0.03

    total = sum(max(0.01, v) for v in base.values())
    return {k: round(max(0.01, v) / total, 4) for k, v in base.items()}

# Semantic similarity between resume and an ideal role profile via SBERT
def _sbert_semantic_quality(resume_text, target_role='general'):
    model = _get_sbert_model()
    if not model or not resume_text.strip():
        return 0.0, ['SBERT model unavailable or empty resume text']
    try:
        role_prompts = {
            'data scientist': 'Data science resume with machine learning, Python, statistics, SQL, data analysis, and measurable achievements',
            'backend': 'Backend engineering resume with APIs, microservices, databases, cloud infrastructure, and server-side development',
            'frontend': 'Frontend engineering resume with JavaScript, React, CSS, user interfaces, and web performance optimization',
            'fullstack': 'Full-stack engineering resume with frontend, backend, database design, and end-to-end product development',
            'developer': 'Software developer resume with coding, debugging, feature delivery, and collaborative development practices',
            'manager': 'Management resume with leadership, stakeholder communication, project delivery, team mentoring, and strategic planning',
            'product': 'Product management resume with roadmap execution, user research, cross-functional leadership, and measurable product outcomes',
            'devops': 'DevOps resume with CI/CD, cloud platforms, containerization, infrastructure automation, and monitoring',
            'general': 'Professional resume with clear experience, quantified achievements, relevant skills, and strong professional summary'
        }
        role_key = (target_role or 'general').lower().strip()
        prompt = 'Ideal resume example: ' + next((v for k, v in role_prompts.items() if k in role_key), role_prompts['general'])

        embeddings = model.encode([resume_text, prompt], normalize_embeddings=True)
        from sklearn.metrics.pairwise import cosine_similarity
        score = float(cosine_similarity(embeddings[0:1], embeddings[1:2])[0][0])
        reasons = []
        if score < 0.35:
            reasons.append('Low semantic alignment with ideal ' + target_role + ' resume profiles')
        elif score >= 0.65:
            reasons.append('Strong semantic alignment with expected ' + target_role + ' resume content')
        return score, reasons
    except Exception as e:
        return 0.0, ['SBERT scoring failed: ' + str(e)]

_spacy_nlp = None

# Lazily load and cache the spaCy English NLP model (disabled unless enabled)
def _get_spacy_model():
    global _spacy_nlp
    if not ENABLE_SEMANTIC_MODELS:
        _spacy_nlp = False
        return None
    if _spacy_nlp is None:
        try:
            import spacy
            _spacy_nlp = spacy.load('en_core_web_sm')
        except Exception:
            _spacy_nlp = False
    if _spacy_nlp is False:
        return None
    return _spacy_nlp

# Extract named entities and skills from resume text using spaCy
def _spacy_extract_features(text):
    nlp = _get_spacy_model()
    if not nlp or not text.strip():
        return 0.0, [], []
    try:
        doc = nlp(text[:5000])
        entities = []
        skills = []

        ent_labels = ['PERSON', 'ORG', 'GPE', 'DATE', 'PRODUCT', 'EVENT']
        for ent in doc.ents:
            if ent.label_ in ent_labels and len(ent.text.strip()) > 2:
                entities.append({'text': ent.text.strip(), 'label': ent.label_})

        skill_patterns = [
            'python', 'java', 'javascript', 'c++', 'c#', 'sql', 'mysql', 'postgresql', 'mongodb',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'git', 'machine learning', 'deep learning',
            'tensorflow', 'pytorch', 'data analysis', 'data science', 'project management', 'agile',
            'scrum', 'leadership', 'communication', 'teamwork', 'problem solving', 'react', 'angular',
            'vue', 'node.js', 'django', 'flask', 'spring', 'rest', 'graphql', 'microservices'
        ]
        text_lower = text.lower()
        found_skills = [s for s in skill_patterns if s in text_lower]

        for chunk in doc.noun_chunks:
            chunk_text = chunk.text.lower().strip()
            if 3 < len(chunk_text) < 50 and any(s in chunk_text for s in ['skill', 'experience', 'knowledge', 'proficient', 'familiar']):
                skills.append(chunk.text.strip())

        score = min((min(len(entities), 15) / 15.0) * 0.4 + min(len(found_skills) / 12.0, 1.0) * 0.6, 1.0)
        return score, entities[:20], list(set(found_skills))[:20]
    except Exception as e:
        return 0.0, [], []

# Build grouped, role-aware improvement suggestions from all sub-scores
def _build_personalized_suggestions(
    resume_text,
    target_role,
    rule_score,
    readability,
    impact_density,
    skill_depth,
    section_quality,
    sbert_semantic,
    spacy_score,
    detailed_results,
    extracted,
    strong_verbs,
    weak_verbs,
    quant_count,
    word_count,
    tech_skills,
    soft_skills,
    spacy_entities,
    spacy_skills
):
    role = (target_role or 'general').lower().strip()
    suggestions = {
        'readability': [],
        'impact': [],
        'skills': [],
        'sbert': [],
        'spacy': [],
        'overall': []
    }

    # Overall score-based suggestions
    if rule_score < 40:
        suggestions['overall'].append('Your resume needs major work. Focus on adding missing sections and measurable achievements first.')
    elif rule_score < 70:
        suggestions['overall'].append('Your resume is decent. Improve by adding more quantifiable results and role-specific keywords.')
    else:
        suggestions['overall'].append('Strong foundation. Fine-tune keywords and formatting to match your target role more closely.')

    # Readability suggestions
    if readability < 0.55:
        suggestions['readability'].append('Your sentences are long and dense. Use shorter bullets with action-outcome structure.')
        suggestions['readability'].append('Aim for 1-line bullets where possible; recruiters scan, they do not read paragraphs.')
    elif readability < 0.75:
        suggestions['readability'].append('Readability is moderate. Tighten sentence length and increase white space around bullets.')

    # Impact suggestions (content-aware)
    if quant_count < 2:
        suggestions['impact'].append('Add at least 2-3 metrics: revenue impact, cost savings, efficiency gains, team size, or project scale.')
        suggestions['impact'].append('Example: "Reduced onboarding time by 35% across 200+ new hires" instead of "Helped with onboarding".')
    elif quant_count < 5:
        suggestions['impact'].append(f'You have {quant_count} metrics. Try adding scale indicators (%, $, time saved, users impacted) to 40% of your bullets.')

    if weak_verbs and len(weak_verbs) > len(strong_verbs):
        suggestions['impact'].append(f'Replace weak phrases like "worked on", "helped with" with strong verbs: {", ".join(strong_verbs[:5]) if strong_verbs else "led, built, improved, automated, delivered"}.')
    if len(strong_verbs) < 4:
        suggestions['impact'].append('Use stronger action verbs at the start of bullet points to show ownership and results.')

    # Skill suggestions (content-aware)
    missing_core = []
    if 'data' in role or 'science' in role or 'ml' in role or 'ai' in role:
        desired = ['python', 'sql', 'machine learning', 'data analysis', 'tableau', 'aws', 'statistics', 'pandas', 'numpy']
        missing_core = [s for s in desired if s not in tech_skills]
    elif 'backend' in role or 'developer' in role or 'engineer' in role:
        desired = ['python', 'java', 'sql', 'api', 'microservices', 'docker', 'aws', 'git', 'testing']
        missing_core = [s for s in desired if s not in tech_skills]
    elif 'frontend' in role or 'fullstack' in role:
        desired = ['javascript', 'react', 'css', 'html', 'node.js', 'typescript', 'redux', 'testing']
        missing_core = [s for s in desired if s not in tech_skills]
    elif 'manager' in role or 'lead' in role or 'product' in role:
        desired = ['leadership', 'project management', 'agile', 'communication', 'roadmap', 'stakeholder', 'budget', 'strategy']
        missing_core = [s for s in desired if s not in (tech_skills + soft_skills)]
    elif 'devops' in role or 'cloud' in role:
        desired = ['docker', 'kubernetes', 'aws', 'azure', 'ci/cd', 'terraform', 'linux', 'monitoring', 'python']
        missing_core = [s for s in desired if s not in tech_skills]

    if missing_core:
        suggestions['skills'].append(f'For {target_role} roles, add these in-demand skills: {", ".join(missing_core[:6])}.')
        suggestions['skills'].append('Place these in a dedicated Skills section and weave them into experience bullets.')

    if len(tech_skills) < 6:
        suggestions['skills'].append(f'You listed {len(tech_skills)} technical skills. Target 10-14 skills relevant to the job description.')
        suggestions['skills'].append('Mix tools, languages, frameworks, and platforms to show breadth and depth.')

    if not soft_skills:
        suggestions['skills'].append('Add soft skills such as communication, stakeholder management, or cross-functional leadership to show collaboration strength.')

    # SBERT suggestions
    if sbert_semantic < 0.35:
        suggestions['sbert'].append(f'Your resume content is semantically weak for "{target_role}". Increase mentions of role-specific responsibilities and outcomes.')
        suggestions['sbert'].append('Include keywords like: ' + _role_keywords(target_role) + '.')
    elif sbert_semantic < 0.55:
        suggestions['sbert'].append('Semantic alignment is moderate. Add more role-specific outcomes to strengthen fit signals for ATS and recruiters.')

    # Section quality suggestions
    missing_sections = [s for s, present in extracted['sections'].items() if not present]
    core_sections = ['experience', 'education', 'skills', 'summary']
    missing_core_sections = [s for s in missing_sections if s in core_sections]
    if missing_core_sections:
        suggestions['overall'].append(f'Add missing core sections: {", ".join(missing_core_sections)}. Recruiters expect these in every resume.')

    # Word count suggestions
    if word_count < 300:
        suggestions['overall'].append(f'Resume is only {word_count} words. Expand each role with 3-5 achievement bullets to reach 400-600 words.')
    elif word_count > 1200:
        suggestions['overall'].append(f'Resume is {word_count} words. Trim older roles and focus on the last 8-10 years to stay under 2 pages.')

    # ATS suggestions
    if not extracted['has_email']:
        suggestions['overall'].append('Add a clickable, professional email address in the header for ATS and recruiter contact.')
    if not extracted['has_phone']:
        suggestions['overall'].append('Add a clearly formatted phone number so recruiters can reach you quickly.')

    # Certification suggestions
    if 'certification' not in resume_text.lower() and 'certified' not in resume_text.lower():
        suggestions['overall'].append(f'For {target_role} roles, add at least one relevant certification to strengthen credibility.')

    return suggestions


# Return a comma-separated list of expected keywords for a given role
def _role_keywords(role):
    mapping = {
        'data scientist': 'machine learning, python, sql, statistics, data pipeline, model deployment, experimentation',
        'backend': 'api, microservices, database design, caching, authentication, scalability, testing',
        'frontend': 'javascript, react, css, accessibility, performance, component architecture, testing',
        'fullstack': 'frontend, backend, database, deployment, user experience, api design, testing',
        'developer': 'coding, debugging, feature delivery, code review, testing, documentation, collaboration',
        'manager': 'leadership, stakeholder communication, hiring, roadmaps, delivery, mentoring, strategy',
        'product': 'roadmap, user research, metrics, cross-functional, launch, backlog, OKRs, customer experience',
        'devops': 'ci/cd, cloud, containers, infrastructure, monitoring, automation, security, linux',
        'general': 'achievements, leadership, process improvement, collaboration, delivery, measurable results'
    }
    role_key = (role or 'general').lower().strip()
    for key, value in mapping.items():
        if key in role_key:
            return value
    return mapping['general']

# Full ensemble resume analysis: combines rule-based, readability, impact, skill, SBERT & spaCy signals
def analyze_resume_dynamic_v2(resume_text, target_role='general'):
    rule_based = score_resume_detailed(resume_text)
    rule_score = rule_based['rule_score']
    detailed_results = rule_based['results']
    extracted = rule_based['extracted']

    tech_skills = extracted['tech_skills']
    soft_skills = extracted['soft_skills']
    strong_verbs = extracted['strong_verbs']
    weak_verbs = extracted['weak_verbs']
    quant_count = extracted['quant_count']
    word_count = extracted['word_count']
    sections = extracted['sections']

    readability = _readability_proxy_score(resume_text)
    impact_density = _impact_density_score(resume_text)[0]
    skill_depth = _skill_depth_score(resume_text)[0]
    section_quality = _section_quality_score(resume_text)
    guarded = _guarded_calls([
        ("sbert", lambda: _sbert_semantic_quality(resume_text, target_role),
         (0.0, ["SBERT scoring skipped (model unavailable or timed out)"])),
        ("spacy", lambda: _spacy_extract_features(resume_text),
         (0.0, [], [])),
    ], timeout=12)
    sbert_semantic, sbert_reasons = guarded["sbert"]
    spacy_score, spacy_entities, spacy_skills = guarded["spacy"]
    weights = _analyzer_weights_by_role(target_role)

    # Optional models may be disabled or unavailable (e.g. SBERT/spaCy
    # in this environment). Renormalize the active weights so they sum
    # to 1.0, otherwise the maximum achievable score is capped
    # below 100 (a perfect resume would never reach 100).
    sbert_available = _get_sbert_model() is not None
    spacy_available = _get_spacy_model() is not None
    active = {
        'rule_based': True,
        'readability': True,
        'impact_density': True,
        'skill_depth': True,
        'section_quality': True,
        'sbert_semantic': sbert_available,
        'spacy_features': spacy_available,
    }
    active_total = sum(v for k, v in weights.items() if active.get(k, False)) or 1.0
    weights = {k: (v / active_total if active.get(k, False) else 0.0) for k, v in weights.items()}

    aggregate = (
        (weights['rule_based'] * (rule_score / 100.0)) +
        (weights['readability'] * readability) +
        (weights['impact_density'] * impact_density) +
        (weights['skill_depth'] * skill_depth) +
        (weights['section_quality'] * section_quality) +
        (weights['sbert_semantic'] * sbert_semantic) +
        (weights['spacy_features'] * spacy_score)
    )
    final_score = int(round(max(0.0, min(1.0, aggregate)) * 100))
    confidence = int(round(((rule_score / 100.0) + impact_density + sbert_semantic + section_quality) / 4.0 * 100))

    suggestions = _build_personalized_suggestions(
        resume_text=resume_text,
        target_role=target_role,
        rule_score=rule_score,
        readability=readability,
        impact_density=impact_density,
        skill_depth=skill_depth,
        section_quality=section_quality,
        sbert_semantic=sbert_semantic,
        spacy_score=spacy_score,
        detailed_results=detailed_results,
        extracted=extracted,
        strong_verbs=strong_verbs,
        weak_verbs=weak_verbs,
        quant_count=quant_count,
        word_count=word_count,
        tech_skills=tech_skills,
        soft_skills=soft_skills,
        spacy_entities=spacy_entities,
        spacy_skills=spacy_skills
    )

    advanced_items = [
        {
            'category': 'Semantic Readability',
            'score': round(readability * 10, 1),
            'max_score': 10,
            'model': 'Sentence-BERT (all-MiniLM-L6-v2)',
            'flaws': [] if readability >= 0.75 else ['Sentence density is high; resume is harder to scan quickly'],
            'fix_tips': [] if readability >= 0.75 else ['Use shorter bullet points and clearer action-outcome structure'],
            'suggestions': suggestions.get('readability', [])
        },
        {
            'category': 'Impact Density',
            'score': round(impact_density * 15, 1),
            'max_score': 15,
            'model': 'TF-IDF + Bag-of-Words',
            'flaws': [] if impact_density >= 0.65 else ['Low concentration of quantified impact statements'],
            'fix_tips': [] if impact_density >= 0.65 else ['Add measurable outcomes like % growth, savings, delivery speed'],
            'suggestions': suggestions.get('impact', [])
        },
        {
            'category': 'Skill Depth Intelligence',
            'score': round(skill_depth * 15, 1),
            'max_score': 15,
            'model': 'Rule-Based Skill Coverage',
            'flaws': [] if skill_depth >= 0.60 else ['Skill coverage is shallow for competitive ATS filtering'],
            'fix_tips': [] if skill_depth >= 0.60 else ['Add missing domain, tooling, and platform skills for target role'],
            'suggestions': suggestions.get('skills', [])
        },
        {
            'category': 'SBERT Semantic Quality',
            'score': round(sbert_semantic * 10, 1),
            'max_score': 10,
            'model': 'Sentence-BERT (all-MiniLM-L6-v2)',
            'flaws': sbert_reasons if sbert_reasons else [],
            'fix_tips': ['Align resume content with typical ' + (target_role or 'general') + ' responsibilities and skills'],
            'suggestions': suggestions.get('sbert', [])
        },
        {
            'category': 'spaCy Entity & Skill Extraction',
            'score': round(spacy_score * 10, 1),
            'max_score': 10,
            'model': 'spaCy en_core_web_sm (optional)',
            'flaws': [] if spacy_score >= 0.5 else ['Limited named entities or skill terms detected by spaCy'],
            'fix_tips': [] if spacy_score >= 0.5 else ['Ensure organizations, dates, and skill keywords are explicitly mentioned'],
            'suggestions': suggestions.get('spacy', [])
        }
    ]

    all_results = list(detailed_results) + advanced_items

    return {
        'score': final_score,
        'confidence': max(0, min(confidence, 100)),
        'model_version': 'analyzer_ensemble_v1',
        'target_role': target_role or 'general',
        'weights': weights,
        'signals': {
            'rule_based': round(rule_score, 2),
            'readability': round(readability * 100, 2),
            'impact_density': round(impact_density * 100, 2),
            'skill_depth': round(skill_depth * 100, 2),
            'section_quality': round(section_quality * 100, 2),
            'sbert_semantic': round(sbert_semantic * 100, 2),
            'spacy_features': round(spacy_score * 100, 2)
        },
        'suggestions': suggestions.get('overall', [])[:8],
        'results': all_results
    }

# Compare resume vs job keywords: returns matched, missing, and coverage stats
def analyze_keyword_gap(resume_text, job_description):
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
        'shall', 'can', 'need', 'dare', 'ought', 'used', 'it', 'its', 'this', 'that',
        'these', 'those', 'i', 'you', 'he', 'she', 'we', 'they', 'what', 'which', 'who',
        'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more',
        'most', 'other', 'some', 'such', 'no', 'not', 'only', 'same', 'so', 'than',
        'too', 'very', 'just', 'also', 'now', 'here', 'there', 'then', 'once', 'if',
        'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
        'between', 'under', 'again', 'further', 'because', 'until', 'while'
    }
    
    def extract_keywords(text):
        text_lower = text.lower()
        text_clean = re.sub(r'[^\w\s]', ' ', text_lower)
        words = text_clean.split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        skill_patterns = [
            r'\b(python|java|javascript|c\+\+|c#|ruby|go|golang|rust|swift)\b',
            r'\b(html|css|react|angular|vue|node\.js|django|flask|spring)\b',
            r'\b(sql|mysql|postgresql|mongodb|oracle|redis|elasticsearch)\b',
            r'\b(aws|azure|gcp|docker|kubernetes|jenkins|git)\b',
            r'\b(machine learning|deep learning|tensorflow|pytorch|keras)\b',
            r'\b(data analysis|data science|data engineering|big data|hadoop|spark)\b',
            r'\b(agile|scrum|project management|jira)\b',
            r'\b(api|rest|graphql|microservices)\b',
            r'\b(communication|teamwork|leadership|problem[- ]?solving|analytical)\b'
        ]
        
        found_skills = []
        for pattern in skill_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            found_skills.extend(matches)
        
        all_keywords = list(set(keywords + found_skills))
        return [k.lower() for k in all_keywords]
    
    resume_keywords = set(extract_keywords(resume_text))
    job_keywords = set(extract_keywords(job_description))
    
    matched = list(resume_keywords & job_keywords)
    missing = list(job_keywords - resume_keywords)
    
    job_keyword_count = len(job_keywords)
    matched_count = len(resume_keywords & job_keywords)
    missing_count = len(job_keywords - resume_keywords)
    coverage_pct = round((matched_count / job_keyword_count) * 100, 2) if job_keyword_count else 0.0

    return {
        'matched': matched[:20],
        'missing': missing[:20],
        'stats': {
            'job_keywords_total': job_keyword_count,
            'matched_count': matched_count,
            'missing_count': missing_count,
            'coverage_pct': coverage_pct
        }
    }

# Cosine similarity of two texts using SBERT embeddings
def _sbert_similarity(text_a, text_b):
    model = _get_sbert_model()
    if not model or not text_a.strip() or not text_b.strip():
        return 0.0
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        embeddings = model.encode([text_a, text_b], normalize_embeddings=True)
        return float(cosine_similarity(embeddings[0:1], embeddings[1:2])[0][0])
    except Exception:
        return 0.0


# Cosine similarity of two texts using the given vectorizer (TF-IDF/BoW)
def _safe_cosine_similarity(text_a, text_b, vectorizer):
    if not text_a.strip() or not text_b.strip():
        return 0.0
    try:
        matrix = vectorizer.fit_transform([text_a, text_b])
        return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    except Exception:
        return 0.0

# Latent Semantic Analysis similarity via TF-IDF + Truncated SVD
def _safe_lsa_similarity(text_a, text_b, n_components=2):
    if not text_a.strip() or not text_b.strip():
        return 0.0
    try:
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        matrix = vectorizer.fit_transform([text_a, text_b])
        if matrix.shape[1] < 2:
            return _safe_cosine_similarity(text_a, text_b, vectorizer)
        components = min(n_components, matrix.shape[1] - 1)
        if components < 1:
            return 0.0
        svd = TruncatedSVD(n_components=components, random_state=42)
        reduced = svd.fit_transform(matrix)
        return float(cosine_similarity([reduced[0]], [reduced[1]])[0][0])
    except Exception:
        return 0.0

# Jaccard overlap ratio between two token sets
def _jaccard_similarity(tokens_a, tokens_b):
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)

# Infer the job domain (data science, backend, frontend, etc.) from the description
def _extract_domain(job_description):
    text = (job_description or "").lower()
    domain_keywords = {
        'data_science': ['machine learning', 'data science', 'nlp', 'pytorch', 'tensorflow', 'statistics', 'sql'],
        'backend': ['api', 'microservices', 'flask', 'django', 'fastapi', 'spring', 'postgresql', 'redis'],
        'frontend': ['react', 'angular', 'vue', 'javascript', 'typescript', 'css', 'html'],
        'devops': ['docker', 'kubernetes', 'aws', 'azure', 'gcp', 'terraform', 'ci/cd', 'jenkins'],
        'management': ['project management', 'stakeholder', 'leadership', 'agile', 'scrum', 'roadmap']
    }
    best_domain = 'general'
    best_hits = 0
    for domain, keys in domain_keywords.items():
        hits = sum(1 for k in keys if k in text)
        if hits > best_hits:
            best_hits = hits
            best_domain = domain
    return best_domain

# Return normalized match-scoring weights tuned to the detected job domain
def _dynamic_weights_by_domain(domain):
    base = {
        'tfidf_word': 0.25,
        'tfidf_char': 0.15,
        'bow_word': 0.10,
        'sbert_semantic': 0.20,
        'keyword_coverage': 0.15,
        'skill_overlap': 0.10,
        'section_quality': 0.05
    }

    domain_boosts = {
        'data_science': {'sbert_semantic': 0.05, 'keyword_coverage': 0.05, 'tfidf_char': -0.03, 'bow_word': -0.02, 'section_quality': -0.05},
        'backend': {'keyword_coverage': 0.05, 'tfidf_word': 0.03, 'tfidf_char': -0.03, 'section_quality': -0.05},
        'frontend': {'tfidf_char': 0.05, 'tfidf_word': 0.03, 'sbert_semantic': -0.03, 'section_quality': -0.05},
        'devops': {'keyword_coverage': 0.05, 'bow_word': 0.03, 'tfidf_char': -0.03, 'section_quality': -0.05},
        'management': {'section_quality': 0.10, 'sbert_semantic': 0.03, 'tfidf_char': -0.03, 'bow_word': -0.02, 'tfidf_word': -0.03}
    }

    boosts = domain_boosts.get(domain, {})
    for key, value in boosts.items():
        base[key] = max(0.01, base.get(key, 0.0) + value)

    total = sum(base.values())
    if total <= 0:
        return base
    return {k: v / total for k, v in base.items()}

# Fraction of standard resume sections present (0-1)
def _section_quality_score(resume_text):
    sections = detect_resume_sections(resume_text)
    found = sum(1 for is_found in sections.values() if is_found)
    return min(found / 8.0, 1.0)

# Produce up to 3 human-readable reasons explaining a match score
def _build_match_explanation(components, keyword_gap):
    coverage = components.get('keyword_coverage', 0)
    semantic = components.get('sbert_semantic_similarity', 0)
    word_sim = components.get('tfidf_word_similarity', 0)
    missing = len(keyword_gap.get('missing', []))

    reasons = []
    if semantic >= 65:
        reasons.append("Strong semantic alignment with job responsibilities")
    elif semantic < 40:
        reasons.append("Low semantic alignment; experience narrative may not match role scope")

    if coverage >= 60:
        reasons.append("Good keyword coverage against job requirements")
    elif coverage < 35:
        reasons.append("Critical job keywords are missing from the resume")

    if word_sim >= 60:
        reasons.append("High phrase-level match with job description")
    elif word_sim < 35:
        reasons.append("Low phrase-level matching; wording should be aligned with target job")

    if missing > 8:
        reasons.append("Many required skills/terms are absent; consider role-specific tailoring")

    if not reasons:
        reasons.append("Balanced profile with moderate match signals across models")

    return reasons[:3]

# Ensemble resume-to-job match score combining TF-IDF, BoW, SBERT, keyword & skill signals
def calculate_advanced_match_metrics(resume_text, job_description):
    domain = _extract_domain(job_description)
    weights = _dynamic_weights_by_domain(domain)

    tfidf_word = _safe_cosine_similarity(
        resume_text,
        job_description,
        TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
    )
    tfidf_char = _safe_cosine_similarity(
        resume_text,
        job_description,
        TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5))
    )
    bow_word = _safe_cosine_similarity(
        resume_text,
        job_description,
        CountVectorizer(stop_words='english', ngram_range=(1, 2))
    )
    sbert_semantic = _sbert_similarity(resume_text, job_description)

    keyword_gap = analyze_keyword_gap(resume_text, job_description)
    coverage_pct = keyword_gap.get('stats', {}).get('coverage_pct', 0.0)
    keyword_score = coverage_pct / 100.0

    resume_tech, _ = extract_skills_from_text(resume_text)
    job_tech, _ = extract_skills_from_text(job_description)
    skill_overlap = _jaccard_similarity(resume_tech, job_tech)
    section_quality = _section_quality_score(resume_text)

    weighted_score = (
        (weights['tfidf_word'] * tfidf_word) +
        (weights['tfidf_char'] * tfidf_char) +
        (weights['bow_word'] * bow_word) +
        (weights['sbert_semantic'] * sbert_semantic) +
        (weights['keyword_coverage'] * keyword_score) +
        (weights['skill_overlap'] * skill_overlap) +
        (weights['section_quality'] * section_quality)
    )

    final_score_pct = int(round(max(0.0, min(1.0, weighted_score)) * 100))
    confidence = int(round(max(0.0, min(1.0, (tfidf_word + sbert_semantic + keyword_score) / 3.0)) * 100))

    components = {
        'tfidf_word_similarity': round(tfidf_word * 100, 2),
        'tfidf_char_similarity': round(tfidf_char * 100, 2),
        'bow_similarity': round(bow_word * 100, 2),
        'sbert_semantic_similarity': round(sbert_semantic * 100, 2),
        'keyword_coverage': round(coverage_pct, 2),
        'skill_overlap': round(skill_overlap * 100, 2),
        'section_quality': round(section_quality * 100, 2)
    }

    return {
        'score': final_score_pct,
        'confidence': confidence,
        'model_version': 'sbert_v1',
        'domain_detected': domain,
        'weights': {k: round(v, 4) for k, v in weights.items()},
        'components': components,
        'keyword_gap': keyword_gap,
        'explanations': _build_match_explanation(components, keyword_gap),
        'models': {
            'sbert': 'Sentence-BERT (all-MiniLM-L6-v2)',
            'cosine': 'Cosine Similarity',
            'tfidf': 'TF-IDF + Bag-of-Words + LSA',
            'keywords': 'Keyword Coverage + Jaccard Skill Overlap'
        }
    }

# Initialize database tables
with app.app_context():
    db.create_all()
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    try:
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'profile_type' not in columns:
            from sqlalchemy import text
            db.session.execute(text("ALTER TABLE users ADD COLUMN profile_type VARCHAR(20) DEFAULT 'user'"))
            db.session.commit()
    except Exception:
        pass

# Flask routes and handlers follow

# Landing page (redirects logged-in users to the dashboard)
@app.route('/', endpoint='public.home')
def home():
    if 'user_id' in session:
        return redirect(url_for('app.dashboard'))
    return render_template('public-home.html')

# Legacy /home URL -> permanent redirect to home
@app.route('/home')
def legacy_home():
    return redirect(url_for('public.home'), code=301)

# Employers landing page
@app.route('/employers', endpoint='employers')
def organizations():
    return render_template('public-home.html')

# Legacy /account URL -> redirect to profile
@app.route('/account', endpoint='account.overview')
def user():
    return redirect(url_for('account.profile'), code=301)

# Legacy /user URL -> redirect to profile
@app.route('/user')
def legacy_user():
    return redirect(url_for('account.profile'), code=301)

# Pricing page
@app.route('/billing/pricing', endpoint='billing.pricing')
def pricing():
    return render_template('billing-pricing.html')

# Public resume analyzer marketing/tool page
@app.route('/tools/resume-analysis', endpoint='tools.resume.analysis')
def resume_analyzer():
    return render_template('resume-analysis.html')

# Public job-matching tool page
@app.route('/tools/job-match', endpoint='tools.job.match')
def job_matching():
    return render_template('job-match.html')

# Public resume builder landing page
@app.route('/tools/resume-builder', endpoint='tools.resume.builder')
def resume_builder_page():
    return render_template('resume-builder-landing.html')

# Account profile page (supports embedded iframe view)
@app.route('/account/profile', endpoint='account.profile')
def profile():
    if 'user_id' not in session:
        flash('Please log in to view your profile.', 'danger')
        return redirect(url_for('auth.login'))
    user = User.query.get(session['user_id'])
    embedded = request.args.get('embedded') == '1'
    return render_template('account-profile.html', user=user, embedded=embedded)

# Update the logged-in user's username/email
@app.route('/api/account/profile/update', methods=['POST'], endpoint='api.account.profile.update')
def update_profile():
    if 'user_id' not in session:
        flash('Please log in to update your profile.', 'danger')
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.login'))
    
    username = request.form.get('username')
    email = request.form.get('email')
    
    if username:
        user.username = username
    if email:
        existing_user = User.query.filter(User.email == email, User.id != user.id).first()
        if existing_user:
            flash('Email already exists.', 'danger')
            return redirect(url_for('account.profile'))
        user.email = email
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('account.profile'))

# User registration (validates and creates a new account)
@app.route('/auth/register', methods=['GET', 'POST'], endpoint='auth.register')
def signup():
    if 'user_id' in session:
        return redirect(url_for('app.dashboard'))
        
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        profile_type = request.form.get('profile_type', 'user')

        # Email already exists check
        if User.query.filter_by(email=email).first():
            flash('Email already exists. Please use a different email.', 'danger')
            return render_template('auth-register.html', saved_username=username, saved_email=email, saved_profile_type=profile_type)
        
        # Password minimum 8 characters
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('auth-register.html', saved_username=username, saved_email=email, saved_profile_type=profile_type)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth-register.html', saved_username=username, saved_email=email, saved_profile_type=profile_type)

        # Save new user with hashed password
        new_user = User(
            username=username,
            email=email,
            phone='',
            password=generate_password_hash(password, method='pbkdf2:sha256'),
            profile_type=profile_type
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Signup successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth-register.html')

# User login (verifies credentials and starts a session)
@app.route('/auth/login', methods=['GET', 'POST'], endpoint='auth.login')
def login():
    if 'user_id' in session:
        return redirect(url_for('app.dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session.permanent = True
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            redirect_url = request.form.get('redirect') or url_for('app.dashboard')
            if redirect_url:
                return redirect(redirect_url)
            return redirect(url_for('app.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    redirect_url = request.args.get('redirect', '')
    return render_template('auth-login.html', redirect_url=redirect_url)

# Main dashboard (loads latest or requested analysis result)
@app.route('/app/dashboard', endpoint='app.dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    score = request.args.get('score', type=int)
    results = request.args.get('results')
    fresh = request.args.get('fresh')
    
    if fresh == '1' or session.pop('show_fresh_upload', False):
        score = None
        results = None
    elif (score is None or results is None) or (score == 0 and not results):
        latest_result = AnalysisResult.query.filter_by(user_id=session['user_id'], category='analyzer').order_by(AnalysisResult.created_at.desc()).first()
        if latest_result:
            score = latest_result.score
            try:
                results = json.loads(latest_result.results_json)
                if isinstance(results, dict) and 'items' in results:
                    results = results.get('items', [])
            except Exception:
                results = None
    else:
        if score is not None and results:
            try:
                results = json.loads(results)
            except Exception:
                try:
                    import ast
                    results = ast.literal_eval(results)
                except Exception:
                    results = None

    if isinstance(results, list):
        cleaned = []
        for item in results:
            if isinstance(item, str):
                try:
                    item = json.loads(item)
                except Exception:
                    continue
            if isinstance(item, dict):
                cleaned.append(item)
        results = cleaned if cleaned else None
    else:
        results = None
    return render_template('app-dashboard.html', user=user, score=score, results=results)

# Flag the dashboard to show a fresh upload form instead of past results
@app.route('/api/resume/fresh-upload', methods=['POST'], endpoint='api.resume.fresh-upload')
def set_fresh_upload():
    session['show_fresh_upload'] = True
    return jsonify({'success': True})

# Resume-match upload page (requires login)
@app.route('/tools/resume-match', methods=['GET'], endpoint='tools.resume.match.start')
def matchresume():
    if 'user_id' not in session:
        flash('Please log in to use the Resume Analyzer.', 'danger')
        return redirect(url_for('auth.login'))
    return render_template('resume-job-match.html')

# Analyze multiple resumes against a job description and rank them
@app.route('/api/resume/match/analyze', methods=['POST'], endpoint='api.resume.match.analyze')
def matcher():
    if 'user_id' not in session:
        flash('Please log in to use the Resume Analyzer.', 'danger')
        return redirect(url_for('auth.login'))

    job_description = request.form['job_description']
    resume_files = request.files.getlist('resumes')

    if not resume_files or not job_description:
        return render_template('resume-match-result.html', message="Please upload resumes and enter a job description.")

    resumes = []
    for resume_file in resume_files:
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id']), 'match')
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)
        filename = os.path.join(user_folder, secure_filename(resume_file.filename))
        resume_file.save(filename)
        resumes.append(parse_resume(filename))

    try:
        scored_resumes = []
        for i, resume_text in enumerate(resumes):
            metrics = calculate_advanced_match_metrics(resume_text, job_description)
            scored_resumes.append({
                'filename': resume_files[i].filename,
                'score': metrics['score'],
                'similarity': round(metrics['score'] / 100.0, 2),
                'components': metrics['components'],
                'confidence': metrics['confidence'],
                'domain_detected': metrics['domain_detected'],
                'model_version': metrics['model_version'],
                'weights': metrics['weights'],
                'explanations': metrics['explanations']
            })

        scored_resumes.sort(key=lambda item: item['score'], reverse=True)
        top_scored = scored_resumes[:5]
        top_resumes = [item['filename'] for item in top_scored]
        similarity_scores = [item['similarity'] for item in top_scored]
        
        # Save match session
        match_session = MatchSession(
            user_id=session['user_id'],
            job_description=job_description
        )
        db.session.add(match_session)
        db.session.flush()
        
        # Save match results to database
        for i, item in enumerate(top_scored):
            resume_name = item['filename']
            match_score = item['score']
            result = MatchResult(
                session_id=match_session.id,
                filename=resume_name,
                match_score=match_score,
                similarity=item['similarity']
            )
            db.session.add(result)
            
            # Also keep legacy record
            legacy_result = AnalysisResult(
                user_id=session['user_id'],
                filename=resume_name,
                category='match',
                score=match_score,
                results_json=json.dumps({
                    'job_description': job_description[:500],
                    'match_score': match_score,
                    'rank': i + 1,
                    'session_id': match_session.id,
                    'model_components': item['components'],
                    'confidence': item['confidence'],
                    'domain_detected': item['domain_detected'],
                    'model_version': item['model_version'],
                    'weights': item['weights'],
                    'explanations': item['explanations']
                })
            )
            db.session.add(legacy_result)
        db.session.commit()
        
        return render_template('resume-match-result.html',
                               message="",
                               top_resumes=top_resumes,
                               similarity_scores=similarity_scores,
                               advanced_components=[item['components'] for item in top_scored],
                               advanced_meta=[{
                                   'confidence': item['confidence'],
                                   'domain_detected': item['domain_detected'],
                                   'model_version': item['model_version'],
                                   'explanations': item['explanations']
                               } for item in top_scored],
                               session_id=match_session.id,
                               job_description=job_description)
    except Exception as e:
        return render_template('resume-match-result.html', message="Error processing resumes: " + str(e))

# Upload and analyze a single resume, persist the result, then show it
@app.route('/tools/resume-analysis/upload', methods=['GET', 'POST'], endpoint='tools.resume.analysis.upload')
def upload_resume():
    if request.method == 'POST':
        if 'user_id' not in session:
            flash('Please log in to upload resumes.', 'danger')
            return redirect(url_for('auth.login'))
        
        if 'resume' not in request.files:
            flash('No file selected', 'danger')
            return redirect(url_for('app.dashboard'))

        file = request.files['resume']

        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('app.dashboard'))

        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id']), 'analyzer')
                if not os.path.exists(user_folder):
                    os.makedirs(user_folder)
                filepath = os.path.join(user_folder, filename)
                file.save(filepath)

                resume_text = parse_resume(filepath)
                
                if not resume_text.strip():
                    # Try alternative parsing methods
                    resume_text = parse_resume(filepath)
                
                if not resume_text.strip():
                    # Last resort - try reading as text
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            resume_text = f.read()
                    except:
                        pass
                
                if not resume_text.strip():
                    flash('Failed to parse resume. Please upload a valid PDF or DOCX file.', 'danger')
                    return redirect(url_for('app.dashboard'))

                target_role = request.form.get('target_role', 'general')
                advanced_analysis = analyze_resume_dynamic_v2(resume_text, target_role=target_role)
                score = advanced_analysis['score']
                detailed_results = advanced_analysis['results']
                
                result = AnalysisResult(
                    user_id=session['user_id'],
                    filename=filename,
                    category='analyzer',
                    score=score,
                    results_json=json.dumps({
                        'model_version': advanced_analysis['model_version'],
                        'confidence': advanced_analysis['confidence'],
                        'target_role': advanced_analysis['target_role'],
                        'weights': advanced_analysis['weights'],
                        'signals': advanced_analysis['signals'],
                        'items': detailed_results
                    })
                )
                db.session.add(result)
                db.session.commit()
                
                return redirect(url_for('analyzer_result', result=resume_text, score=score, results_json=json.dumps(detailed_results), suggestions_json=json.dumps(advanced_analysis.get('suggestions', [])), signals_json=json.dumps(advanced_analysis.get('signals', {})), models_json=json.dumps({
        'rules': 'Rule-Based ATS Analysis',
        'sbert': 'Sentence-BERT (all-MiniLM-L6-v2)',
        'spacy': 'spaCy en_core_web_sm (optional)',
        'match': 'Cosine Similarity + TF-IDF + BOW + LSA'
    })))
            except Exception as e:
                flash(f'Error processing resume: {str(e)}', 'danger')
                return redirect(url_for('app.dashboard'))
        else:
            flash('Allowed file types are PDF and DOCX only.', 'danger')
            return redirect(url_for('app.dashboard'))

    return render_template('app-dashboard.html')

# Render the standalone resume analysis results page
@app.route('/tools/resume-analysis/results', endpoint='tools.resume.analysis.results')
def analyzer_result():
    result = request.args.get('result', '')
    score = request.args.get('score', 0, type=int)
    results_json = request.args.get('results_json', '[]')
    suggestions = []
    signals = {}
    models = {}
    
    try:
        suggestions = json.loads(request.args.get('suggestions_json', '[]'))
    except Exception:
        suggestions = []
    
    try:
        signals = json.loads(request.args.get('signals_json', '{}'))
    except Exception:
        signals = {}
    
    try:
        models = json.loads(request.args.get('models_json', '{}'))
    except Exception:
        models = {}
    
    if not result or score == 0 or not results_json or results_json == '[]':
        return redirect(url_for('app.dashboard'))
    
    try:
        results = json.loads(results_json)
    except Exception:
        results = []

    if isinstance(results, dict) and 'items' in results:
        results = results.get('items', [])
    
    return render_template('resume-analysis-result.html', result=result, score=score, results=results, resume_text=result, signals=signals, models=models, suggestions=suggestions)

# JSON API: analyze an uploaded resume and return score + results
@app.route('/api/resume/analyze', methods=['POST'], endpoint='api.resume.analyze')
def api_analyze():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    if 'resume' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['resume']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id']), 'analyzer')
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)
        filepath = os.path.join(user_folder, filename)
        file.save(filepath)

        resume_text = parse_resume(filepath)
        if not resume_text.strip():
            return jsonify({'error': 'Failed to parse resume'}), 400

        data_role = request.form.get('target_role') or request.args.get('target_role') or 'general'
        advanced_analysis = analyze_resume_dynamic_v2(resume_text, target_role=data_role)
        score = advanced_analysis['score']
        detailed_results = advanced_analysis['results']
        
        result = AnalysisResult(
            user_id=session['user_id'],
            filename=filename,
            category='analyzer',
            score=score,
            results_json=json.dumps({
                'model_version': advanced_analysis['model_version'],
                'confidence': advanced_analysis['confidence'],
                'target_role': advanced_analysis['target_role'],
                'weights': advanced_analysis['weights'],
                'signals': advanced_analysis['signals'],
                'items': detailed_results
            })
        )
        db.session.add(result)
        db.session.commit()
        
        return jsonify({
            'score': score,
            'results': detailed_results,
            'suggestions': advanced_analysis.get('suggestions', []),
            'advanced': {
                'model_version': advanced_analysis['model_version'],
                'confidence': advanced_analysis['confidence'],
                'target_role': advanced_analysis['target_role'],
                'weights': advanced_analysis['weights'],
                'signals': advanced_analysis['signals'],
                'models': {
                    'rules': 'Rule-Based ATS Analysis',
                    'sbert': 'Sentence-BERT (all-MiniLM-L6-v2)',
                    'spacy': 'spaCy en_core_web_sm (optional)',
                    'match': 'Cosine Similarity + TF-IDF + BOW + LSA'
                }
            }
        })
    else:
        return jsonify({'error': 'Invalid file type'}), 400

# JSON API: keyword gap + advanced match metrics for resume vs job description
@app.route('/api/resume/keyword-gap', methods=['POST'], endpoint='api.resume.keyword-gap')
def api_keyword_gap():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    data = request.get_json()
    if not data or 'resume_text' not in data or 'job_description' not in data:
        return jsonify({'error': 'Resume text and job description are required'}), 400
    
    resume_text = data.get('resume_text', '')
    job_description = data.get('job_description', '')
    
    if not resume_text.strip() or not job_description.strip():
        return jsonify({'error': 'Both resume text and job description are required'}), 400
    
    result = analyze_keyword_gap(resume_text, job_description)
    advanced = calculate_advanced_match_metrics(resume_text, job_description)
    return jsonify({'success': True, 'result': result, 'advanced': advanced})

# JSON API: score and rank multiple resumes against one job description
@app.route('/api/resume/batch-match', methods=['POST'], endpoint='api.resume.batch-match')
def api_dynamic_batch_match():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400

    job_description = data.get('job_description', '')
    resumes = data.get('resumes', [])

    if not job_description.strip() or not isinstance(resumes, list) or not resumes:
        return jsonify({'error': 'job_description and resumes[] are required'}), 400

    scored = []
    for item in resumes:
        filename = item.get('filename', 'resume')
        resume_text = item.get('resume_text', '')
        metrics = calculate_advanced_match_metrics(resume_text, job_description)
        scored.append({
            'filename': filename,
            'score': metrics['score'],
            'confidence': metrics['confidence'],
            'domain_detected': metrics['domain_detected'],
            'model_version': metrics['model_version'],
            'components': metrics['components'],
            'weights': metrics['weights'],
            'keyword_gap': metrics['keyword_gap'],
            'explanations': metrics['explanations']
        })

    scored.sort(key=lambda x: x['score'], reverse=True)
    return jsonify({
        'success': True,
        'model_version': 'sbert_v1',
        'total_resumes': len(scored),
        'results': scored
    })

# Resume builder editor page (requires login)
@app.route('/app/resume-builder/editor', methods=['GET'], endpoint='app.resume.builder.editor')
def resumebuilder():
    if 'user_id' not in session:
        flash('Please log in to use the Resume Analyzer.', 'danger')
        return redirect(url_for('auth.login'))
    return render_template('resume-builder.html')

# Log the user out and clear the session
@app.route('/auth/logout', endpoint='auth.logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out.', 'success')
    return redirect(url_for('public.home'))

# Plan order/checkout page (requires login)
@app.route('/billing/order', endpoint='billing.order')
def order():
    if 'user_id' not in session:
        return redirect(url_for('login', redirect=url_for('billing.order')))
    plan = request.args.get('plan', 'professional')
    return render_template('order.html', plan=plan)

# Partially mask an email address for display (e.g. jo***@x.com)
def mask_email(email):
    if not email or '@' not in email:
        return email or ''
    name, domain = email.split('@', 1)
    visible = name[:2] if len(name) > 2 else name[:1]
    return f'{visible}***@{domain}'


# Send a password-reset code via SMTP (returns False if email is not configured)
def send_password_reset_email(email, code):
    email_host = os.getenv('EMAIL_HOST')
    email_port = os.getenv('EMAIL_PORT', '587')
    email_username = os.getenv('EMAIL_USERNAME')
    email_password = os.getenv('EMAIL_PASSWORD')
    email_from = os.getenv('EMAIL_FROM') or email_username

    if not email_host or not email_username or not email_password or not email_from:
        return False

    message = EmailMessage()
    message['Subject'] = 'Resume AI Password Reset Code'
    message['From'] = email_from
    message['To'] = email
    message.set_content(
        f'Your Resume AI password reset code is: {code}\n\n'
        'This code is valid for 10 minutes. If you did not request this code, you can safely ignore this email.'
    )

    try:
        use_tls = os.getenv('EMAIL_USE_TLS', 'true').lower() != 'false'
        with smtplib.SMTP(email_host, int(email_port)) as server:
            if use_tls:
                server.starttls()
            server.login(email_username, email_password)
            server.send_message(message)
        return True
    except Exception:
        return False


# Multi-step password reset flow: request email -> verify code -> set new password
@app.route('/auth/forgot-password', methods=['GET', 'POST'], endpoint='auth.forgot-password')
def forgot_password():
    if 'user_id' in session:
        return redirect(url_for('app.dashboard'))

    step = request.form.get('step') if request.method == 'POST' else request.args.get('step', 'email')

    if request.method == 'POST' and step == 'email':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('No account found with this email address.', 'danger')
            return render_template('auth-forgot-password.html', step='email', masked_email=mask_email(session.get('reset_email')))

        code = f'{secrets.randbelow(1000000):06d}'
        session['reset_email'] = email
        session['reset_code'] = code
        session['reset_expires_at'] = (datetime.utcnow() + timedelta(minutes=10)).timestamp()
        session['reset_verified'] = False

        if not send_password_reset_email(email, code):
            flash('Email service is not configured. Please configure SMTP settings to send reset codes.', 'danger')
            return render_template('auth-forgot-password.html', step='email', masked_email=mask_email(session.get('reset_email')))

        flash('Verification code sent to your email.', 'success')
        return render_template('auth-forgot-password.html', step='code', masked_email=mask_email(session.get('reset_email')))

    if request.method == 'POST' and step == 'code':
        entered_code = request.form.get('code', '').strip()
        expires_at = session.get('reset_expires_at')

        if not entered_code or not session.get('reset_code') or entered_code != session.get('reset_code'):
            flash('Invalid verification code. Please try again.', 'danger')
            return render_template('auth-forgot-password.html', step='code', masked_email=mask_email(session.get('reset_email')))

        if expires_at and float(expires_at) < datetime.utcnow().timestamp():
            session.pop('reset_code', None)
            session.pop('reset_expires_at', None)
            flash('Verification code expired. Please request a new code.', 'danger')
            return render_template('auth-forgot-password.html', step='email', masked_email=mask_email(session.get('reset_email')))

        session['reset_verified'] = True
        flash('Code verified. Create your new password.', 'success')
        return render_template('auth-forgot-password.html', step='password', masked_email=mask_email(session.get('reset_email')))

    if request.method == 'POST' and step == 'password':
        if not session.get('reset_verified'):
            flash('Please verify your email code before resetting your password.', 'danger')
            return render_template('auth-forgot-password.html', step='code', masked_email=mask_email(session.get('reset_email')))

        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not new_password or not confirm_password:
            flash('All fields are required.', 'danger')
            return render_template('auth-forgot-password.html', step='password', masked_email=mask_email(session.get('reset_email')))

        if len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('auth-forgot-password.html', step='password', masked_email=mask_email(session.get('reset_email')))

        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth-forgot-password.html', step='password', masked_email=mask_email(session.get('reset_email')))

        email = session.get('reset_email')
        user = User.query.filter_by(email=email).first()

        if not user:
            for key in ['reset_email', 'reset_code', 'reset_expires_at', 'reset_verified']:
                session.pop(key, None)
            flash('No account found with this email address.', 'danger')
            return render_template('auth-forgot-password.html', step='email', masked_email=mask_email(session.get('reset_email')))

        user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
        db.session.commit()

        for key in ['reset_email', 'reset_code', 'reset_expires_at', 'reset_verified']:
            session.pop(key, None)

        flash('Password updated successfully! Please login with your new password.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth-forgot-password.html', step='email', masked_email=mask_email(session.get('reset_email')))

# Upload a resume from the documents view, analyze it, and show the result
@app.route('/api/documents/upload', methods=['POST'], endpoint='api.documents.upload')
def upload():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('auth.login'))

    result = None
    score = None
    if 'resume' in request.files:
        resume = request.files['resume']
        if resume:
            filename = secure_filename(resume.filename)
            user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id']), 'analyzer')
            if not os.path.exists(user_folder):
                os.makedirs(user_folder)
            path = os.path.join(user_folder, filename)
            resume.save(path)
            result = parse_resume(path)
            
            advanced_analysis = analyze_resume_dynamic_v2(result, target_role='general')
            score = advanced_analysis['score']
            detailed_results = advanced_analysis['results']
            
            analysis_result = AnalysisResult(
                user_id=session['user_id'],
                filename=filename,
                category='analyzer',
                score=score,
                results_json=json.dumps({
                    'model_version': advanced_analysis['model_version'],
                    'confidence': advanced_analysis['confidence'],
                    'target_role': advanced_analysis['target_role'],
                    'weights': advanced_analysis['weights'],
                    'signals': advanced_analysis['signals'],
                    'items': detailed_results
                })
            )
            db.session.add(analysis_result)
            db.session.commit()

    return render_template('resume-analysis-result.html', result=result, score=score, results=detailed_results, resume_text=result)

# List the user's uploaded documents grouped by category
@app.route('/app/documents', methods=['GET'], endpoint='app.documents')
def documents():
    if 'user_id' not in session:
        flash('Please log in to access your documents.', 'danger')
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    upload_folder = app.config['UPLOAD_FOLDER']
    user_folder = os.path.join(upload_folder, str(user_id))
    
    # Category folders
    categories = {
        'analyzer': 'Resume Analyzer',
        'builder': 'Resume Builder',
        'match': 'Resume Match'
    }
    
    files = []
    
    # Check each category folder
    for cat_id, cat_name in categories.items():
        cat_folder = os.path.join(user_folder, cat_id)
        if os.path.exists(cat_folder):
            for filename in os.listdir(cat_folder):
                filepath = os.path.join(cat_folder, filename)
                if os.path.isfile(filepath):
                    file_stat = os.stat(filepath)
                    files.append({
                        'name': filename,
                        'size': round(file_stat.st_size / 1024, 2),
                        'date': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                        'category': cat_name,
                        'category_id': cat_id
                    })
    
    # Also check main uploads folder for old files
    if os.path.exists(upload_folder):
        for filename in os.listdir(upload_folder):
            filepath = os.path.join(upload_folder, filename)
            if os.path.isfile(filepath) and filename not in [f['name'] for f in files]:
                file_stat = os.stat(filepath)
                files.append({
                    'name': filename,
                    'size': round(file_stat.st_size / 1024, 2),
                    'date': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                    'category': 'Resume Analyzer',
                    'category_id': 'analyzer'
                })
    
    files.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('app-documents.html', user=user, files=files)

# History page: analysis results and match sessions with tab filtering
@app.route('/app/resume-results', methods=['GET'], endpoint='app.resume.results')
def results():
    if 'user_id' not in session:
        flash('Please log in to view results.', 'danger')
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    active_tab = request.args.get('tab', 'analyzer')
    
    analysis_results = AnalysisResult.query.filter_by(user_id=user_id).order_by(AnalysisResult.created_at.desc()).all()
    
    results_list = []
    for result in analysis_results:
        category_name = {
            'analyzer': 'Resume Analyzer',
            'builder': 'Resume Builder',
            'match': 'Resume Match'
        }.get(result.category, 'Resume Analyzer')
        
        results_list.append({
            'id': result.id,
            'filename': result.filename,
            'category': category_name,
            'category_id': result.category,
            'score': result.score,
            'results': (lambda parsed: parsed.get('items', []) if isinstance(parsed, dict) and 'items' in parsed else parsed)(json.loads(result.results_json)),
            'date': result.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    sessions = MatchSession.query.filter_by(user_id=user_id).order_by(MatchSession.created_at.desc()).all()
    
    sessions_list = []
    for s in sessions:
        results = MatchResult.query.filter_by(session_id=s.id).order_by(MatchResult.match_score.desc()).all()
        sessions_list.append({
            'id': s.id,
            'job_description': s.job_description,
            'created_at': s.created_at.strftime('%Y-%m-%d %H:%M'),
            'results': [{
                'filename': r.filename,
                'match_score': r.match_score,
                'similarity': r.similarity
            } for r in results],
            'total_resumes': len(results)
        })
    
    return render_template('app-resume-results.html', user=user, results=results_list, sessions_list=sessions_list, active_tab=active_tab)

# Delete a saved analysis result owned by the user
@app.route('/api/results/delete/<int:result_id>', endpoint='api.results.delete')
def delete_result(result_id):
    if 'user_id' not in session:
        flash('Please log in.', 'danger')
        return redirect(url_for('auth.login'))
    
    result = AnalysisResult.query.filter_by(id=result_id, user_id=session['user_id']).first()
    if result:
        db.session.delete(result)
        db.session.commit()
        flash('Result deleted', 'success')
    else:
        flash('Result not found', 'danger')
    
    return redirect(url_for('app.resume.results'))

# Delete an uploaded document file from the user's category folder
@app.route('/api/documents/delete/<path:filename>', endpoint='api.documents.delete')
def delete_document(filename):
    if 'user_id' not in session:
        flash('Please log in to delete documents.', 'danger')
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    category = request.args.get('category', 'analyzer')
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id), category, secure_filename(filename))
    
    if os.path.exists(filepath):
        os.remove(filepath)
        flash(f'Deleted {filename}', 'success')
    else:
        flash('File not found', 'danger')
    
    return redirect(url_for('app.documents'))

# Download an uploaded document file as an attachment
@app.route('/api/documents/download/<path:filename>', endpoint='api.documents.download')
def download_document(filename):
    if 'user_id' not in session:
        flash('Please log in to download documents.', 'danger')
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    category = request.args.get('category', 'analyzer')
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id), category)
    filepath = os.path.join(folder_path, secure_filename(filename))
    
    if os.path.exists(filepath):
        return send_from_directory(folder_path, filename, as_attachment=True)
    else:
        flash('File not found', 'danger')
        return redirect(url_for('app.documents'))

# Full match-history page listing all of the user's match sessions
@app.route('/app/match-history', endpoint='app.match.history')
def match_history():
    if 'user_id' not in session:
        flash('Please log in to view match history.', 'danger')
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    sessions = MatchSession.query.filter_by(user_id=user_id).order_by(MatchSession.created_at.desc()).all()
    
    sessions_list = []
    for s in sessions:
        results = MatchResult.query.filter_by(session_id=s.id).order_by(MatchResult.match_score.desc()).all()
        sessions_list.append({
            'id': s.id,
            'job_description': s.job_description,
            'created_at': s.created_at.strftime('%Y-%m-%d %H:%M'),
            'results': [{
                'filename': r.filename,
                'match_score': r.match_score,
                'similarity': r.similarity
            } for r in results],
            'total_resumes': len(results)
        })
    
    return render_template('app-match-history.html', user=user, sessions=sessions_list)

# Detail page for a single match session
@app.route('/app/matches/<int:session_id>', endpoint='app.match.detail')
def view_match(session_id):
    if 'user_id' not in session:
        flash('Please log in to view match details.', 'danger')
        return redirect(url_for('auth.login'))
    
    session_obj = MatchSession.query.filter_by(id=session_id, user_id=session['user_id']).first()
    if not session_obj:
        flash('Match session not found', 'danger')
        return redirect(url_for('app.match.history'))
    
    results = MatchResult.query.filter_by(session_id=session_id).order_by(MatchResult.match_score.desc()).all()
    
    results_list = []
    for r in results:
        results_list.append({
            'filename': r.filename,
            'match_score': r.match_score,
            'similarity': r.similarity
        })
    
    return render_template('app-match-detail.html', 
                           session=session_obj, 
                           results=results_list,
                           job_description=session_obj.job_description)

# JSON API: match session details (used by the results modal)
@app.route('/api/matches/<int:session_id>', endpoint='api.match.detail')
def view_match_json(session_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    session_obj = MatchSession.query.filter_by(id=session_id, user_id=session['user_id']).first()
    if not session_obj:
        return jsonify({'error': 'Session not found'}), 404
    
    results = MatchResult.query.filter_by(session_id=session_id).order_by(MatchResult.match_score.desc()).all()
    
    results_list = []
    for r in results:
        results_list.append({
            'filename': r.filename,
            'match_score': r.match_score,
            'similarity': r.similarity
        })
    
    return jsonify({
        'session': {
            'id': session_obj.id,
            'created_at': session_obj.created_at.strftime('%Y-%m-%d %H:%M')
        },
        'job_description': session_obj.job_description,
        'results': results_list
    })

# Delete a match session and all its associated results
@app.route('/api/matches/delete/<int:session_id>', endpoint='api.match.delete')
def delete_match_session(session_id):
    if 'user_id' not in session:
        flash('Please log in.', 'danger')
        return redirect(url_for('auth.login'))
    
    session_obj = MatchSession.query.filter_by(id=session_id, user_id=session['user_id']).first()
    if session_obj:
        MatchResult.query.filter_by(session_id=session_id).delete()
        db.session.delete(session_obj)
        db.session.commit()
        flash('Match session deleted', 'success')
    else:
        flash('Session not found', 'danger')
    
    return redirect(url_for('app.match.history'))

# Entrypoint: run lightweight schema migrations then start the dev server
if __name__ == '__main__':
    with app.app_context():
        from sqlalchemy import text
        try:
            db.session.execute(text('SELECT category FROM analysis_results LIMIT 1'))
        except:
            db.session.execute(text("ALTER TABLE analysis_results ADD COLUMN category VARCHAR(50) DEFAULT 'analyzer'"))
            db.session.commit()
        
        try:
            db.session.execute(text('SELECT 1 FROM match_sessions LIMIT 1'))
        except:
            pass
        
        try:
            db.session.execute(text('SELECT 1 FROM match_results LIMIT 1'))
        except:
            pass
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)