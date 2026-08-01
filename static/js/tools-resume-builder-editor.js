
let selectedTemplate = '';
let userPhoto = null;

function selectTemplate(card) {
    document.querySelectorAll('.template-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    selectedTemplate = card.dataset.template;
    document.getElementById('btn-go').disabled = false;
}

function goToForm() {
    if (!selectedTemplate) return;
    document.getElementById('template-section').classList.add('hidden');
    document.getElementById('form-section').classList.remove('hidden');
    document.getElementById('step1').classList.remove('active');
    document.getElementById('step1').classList.add('completed');
    document.getElementById('step2').classList.add('active');
}

function editDetails() {
    document.getElementById('preview-section').classList.add('hidden');
    document.getElementById('form-section').classList.remove('hidden');
}

function removeItem(btn) {
    const parent = btn.closest('.dynamic-item');
    if (parent) {
        parent.remove();
    }
}

function addEducation() {
    const list = document.getElementById('education-list');
    const item = document.createElement('div');
    item.className = 'dynamic-item';
    item.innerHTML = `
    <button class="remove-btn" onclick="removeItem(this)">×</button>
    <div class="form-row">
      <div class="form-group">
        <label>Institution</label>
        <input type="text" class="edu-institution" placeholder="University name">
      </div>
      <div class="form-group">
        <label>Degree</label>
        <input type="text" class="edu-degree" placeholder="Degree/Certification">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Year</label>
        <input type="text" class="edu-year" placeholder="2024">
      </div>
      <div class="form-group">
        <label>GPA (Optional)</label>
        <input type="text" class="edu-gpa" placeholder="3.5">
      </div>
    </div>
  `;
    list.appendChild(item);
}

function addExperience() {
    const list = document.getElementById('experience-list');
    const item = document.createElement('div');
    item.className = 'dynamic-item';
    item.innerHTML = `
    <button class="remove-btn" onclick="removeItem(this)">×</button>
    <div class="form-row">
      <div class="form-group">
        <label>Company</label>
        <input type="text" class="exp-company" placeholder="Company name">
      </div>
      <div class="form-group">
        <label>Job Title</label>
        <input type="text" class="exp-title" placeholder="Job title">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Start Date</label>
        <input type="text" class="exp-start" placeholder="Jan 2022">
      </div>
      <div class="form-group">
        <label>End Date</label>
        <input type="text" class="exp-end" placeholder="Present">
      </div>
    </div>
    <div class="form-group">
      <label>Description / Achievements</label>
      <textarea class="exp-description" placeholder="• Describe your responsibilities and achievements..."></textarea>
    </div>
  `;
    list.appendChild(item);
}

function addProject() {
    const list = document.getElementById('project-list');
    const item = document.createElement('div');
    item.className = 'dynamic-item';
    item.innerHTML = `
    <button class="remove-btn" onclick="removeItem(this)">×</button>
    <div class="form-group">
      <label>Project Name</label>
      <input type="text" class="proj-name" placeholder="Project name">
    </div>
    <div class="form-group">
      <label>Description</label>
      <textarea class="proj-description" placeholder="Describe the project..."></textarea>
    </div>
  `;
    list.appendChild(item);
}

document.getElementById('photo-upload').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            userPhoto = e.target.result;
        };
        reader.readAsDataURL(file);
    }
});

function getResumeHTML(data, template) {
    const photo = userPhoto ? `<img src="${userPhoto}" class="header-photo" alt="Photo">` : '';

    const educationHTML = data.education.map(edu => `
    <div class="entry">
      <div class="entry-header">
        <span class="entry-title">${edu.institution}</span>
        <span class="entry-date">${edu.year}</span>
      </div>
      <div class="entry-subtitle">${edu.degree}${edu.gpa ? ', GPA: ' + edu.gpa : ''}</div>
    </div>
  `).join('');

    const experienceHTML = data.experience.map(exp => `
    <div class="entry">
      <div class="entry-header">
        <span class="entry-title">${exp.company}</span>
        <span class="entry-date">${exp.start} - ${exp.end}</span>
      </div>
      <div class="entry-subtitle">${exp.title}</div>
      <div class="entry-description">${exp.description.replace(/\n/g, '<br>')}</div>
    </div>
  `).join('');

    const skillsArray = data.skills.split(/[\n,]+/).map(s => s.trim()).filter(s => s);

    let skillsHTML;
    if (template === 'modern') {
        skillsHTML = `<div class="skills-grid">${skillsArray.map(s => `<span class="skill-item">${s}</span>`).join('')}</div>`;
    } else if (template === 'classic') {
        skillsHTML = `<div class="skills-list">${skillsArray.map(s => `<span class="skill-item">${s}</span>`).join('')}</div>`;
    } else if (template === 'executive' || template === 'minimal') {
        skillsHTML = `<div class="skills-container">${skillsArray.map(s => `<span class="skill-item">${s}</span>`).join('')}</div>`;
    }

    const projectsHTML = data.projects.map(proj => `
    <div class="entry">
      <div class="entry-title">${proj.name}</div>
      <div class="entry-description">${proj.description}</div>
    </div>
  `).join('');

    const certsHTML = data.certifications ? data.certifications.split('\n').filter(c => c.trim()).map(c => `
    <div class="entry">
      <div class="entry-title">${c}</div>
    </div>
  `).join('') : '';

    if (template === 'modern') {
        return `
      <div class="resume-doc template-modern">
        <div class="resume-header">
          <div class="header-info">
            <h1>${data.name}</h1>
            <div class="title">${data.title}</div>
            <div class="contact-details">
              <span><i class="fas fa-envelope"></i> ${data.email}</span>
              <span><i class="fas fa-phone"></i> ${data.phone}</span>
              <span><i class="fas fa-map-marker-alt"></i> ${data.location}</span>
              <span><i class="fab fa-linkedin"></i> ${data.linkedin}</span>
            </div>
          </div>
          ${photo}
        </div>
        
        <div class="resume-section">
          <h2>Professional Summary</h2>
          <p>${data.summary}</p>
        </div>
        
        <div class="resume-section">
          <h2>Experience</h2>
          ${experienceHTML}
        </div>
        
        <div class="resume-section">
          <h2>Education</h2>
          ${educationHTML}
        </div>
        
        <div class="resume-section">
          <h2>Skills</h2>
          ${skillsHTML}
        </div>
        
        ${projectsHTML ? `
        <div class="resume-section">
          <h2>Projects</h2>
          ${projectsHTML}
        </div>
        ` : ''}
        
        ${certsHTML ? `
        <div class="resume-section">
          <h2>Certifications</h2>
          ${certsHTML}
        </div>
        ` : ''}
      </div>
    `;
    }

    if (template === 'classic') {
        return `
      <div class="resume-doc template-classic">
        <div class="resume-header">
          <h1>${data.name}</h1>
          <div class="title">${data.title}</div>
          <div class="contact-details">
            <span>${data.email}</span>
            <span>${data.phone}</span>
            <span>${data.location}</span>
            <span>${data.linkedin}</span>
          </div>
        </div>
        
        <div class="resume-section">
          <h2>Summary</h2>
          <p>${data.summary}</p>
        </div>
        
        <div class="resume-section">
          <h2>Experience</h2>
          ${experienceHTML}
        </div>
        
        <div class="resume-section">
          <h2>Education</h2>
          ${educationHTML}
        </div>
        
        <div class="resume-section">
          <h2>Skills</h2>
          ${skillsHTML}
        </div>
        
        ${projectsHTML ? `
        <div class="resume-section">
          <h2>Projects</h2>
          ${projectsHTML}
        </div>
        ` : ''}
      </div>
    `;
    }

    if (template === 'executive') {
        return `
      <div class="resume-doc template-executive">
        <div class="resume-header">
          <h1>${data.name}</h1>
          <div class="title">${data.title}</div>
          <div class="contact-details">
            <span><i class="fas fa-envelope"></i> ${data.email}</span>
            <span><i class="fas fa-phone"></i> ${data.phone}</span>
            <span><i class="fas fa-map-marker-alt"></i> ${data.location}</span>
            <span><i class="fab fa-linkedin"></i> ${data.linkedin}</span>
          </div>
        </div>
        
        <div class="resume-section">
          <h2>Professional Summary</h2>
          <p>${data.summary}</p>
        </div>
        
        <div class="resume-section">
          <h2>Professional Experience</h2>
          ${experienceHTML}
        </div>
        
        <div class="resume-section">
          <h2>Education</h2>
          ${educationHTML}
        </div>
        
        <div class="resume-section">
          <h2>Technical Skills</h2>
          ${skillsHTML}
        </div>
        
        ${projectsHTML ? `
        <div class="resume-section">
          <h2>Key Projects</h2>
          ${projectsHTML}
        </div>
        ` : ''}
      </div>
    `;
    }

    if (template === 'minimal') {
        return `
      <div class="resume-doc template-minimal">
        <div class="resume-header">
          <div class="header-info">
            <h1>${data.name}</h1>
            <div class="title">${data.title}</div>
          </div>
          <div class="contact-details">
            <div>${data.email}</div>
            <div>${data.phone}</div>
            <div>${data.location}</div>
            <div>${data.linkedin}</div>
          </div>
        </div>
        
        <div class="resume-section">
          <h2>Summary</h2>
          <p>${data.summary}</p>
        </div>
        
        <div class="resume-section">
          <h2>Experience</h2>
          ${experienceHTML}
        </div>
        
        <div class="resume-section">
          <h2>Education</h2>
          ${educationHTML}
        </div>
        
        <div class="resume-section">
          <h2>Skills</h2>
          ${skillsHTML}
        </div>
        
        ${projectsHTML ? `
        <div class="resume-section">
          <h2>Projects</h2>
          ${projectsHTML}
        </div>
        ` : ''}
      </div>
    `;
    }

    return '';
}

function collectResumeData() {
    const data = {
        name: document.getElementById('name').value || 'Your Name',
        title: document.getElementById('title').value || 'Job Title',
        email: document.getElementById('email').value || 'email@example.com',
        phone: document.getElementById('phone').value || 'Phone',
        location: document.getElementById('location').value || 'Location',
        linkedin: document.getElementById('linkedin').value || 'linkedin.com/in/yourprofile',
        summary: document.getElementById('summary').value || 'Professional summary...',
        education: [],
        experience: [],
        skills: document.getElementById('skills').value || '',
        projects: [],
        certifications: document.getElementById('certifications').value || ''
    };

    document.querySelectorAll('#education-list .dynamic-item').forEach(item => {
        const inst = item.querySelector('.edu-institution').value;
        const deg = item.querySelector('.edu-degree').value;
        const yr = item.querySelector('.edu-year').value;
        const gpa = item.querySelector('.edu-gpa').value;
        if (inst || deg) {
            data.education.push({
                institution: inst,
                degree: deg,
                year: yr,
                gpa: gpa
            });
        }
    });

    document.querySelectorAll('#experience-list .dynamic-item').forEach(item => {
        const comp = item.querySelector('.exp-company').value;
        const tit = item.querySelector('.exp-title').value;
        const start = item.querySelector('.exp-start').value;
        const end = item.querySelector('.exp-end').value;
        const desc = item.querySelector('.exp-description').value;
        if (comp || tit) {
            data.experience.push({
                company: comp,
                title: tit,
                start: start,
                end: end,
                description: desc
            });
        }
    });

    document.querySelectorAll('#project-list .dynamic-item').forEach(item => {
        const name = item.querySelector('.proj-name').value;
        const desc = item.querySelector('.proj-description').value;
        if (name || desc) {
            data.projects.push({
                name: name,
                description: desc
            });
        }
    });

    return data;
}

function generateResume() {
    const data = collectResumeData();
    const html = getResumeHTML(data, selectedTemplate);
    document.getElementById('resume-output').innerHTML = html;

    document.getElementById('form-section').classList.add('hidden');
    document.getElementById('preview-section').classList.remove('hidden');
    document.getElementById('step2').classList.remove('active');
    document.getElementById('step2').classList.add('completed');
    document.getElementById('step3').classList.add('active');

    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

async function downloadPDF() {
    const element = document.getElementById('resume-output');
    if (!element.innerHTML.trim()) {
        generateResume();
        await new Promise((resolve) => setTimeout(resolve, 300));
        if (!element.innerHTML.trim()) {
            alert('Unable to generate resume preview. Please check your form data.');
            return;
        }
    }

    const downloadBtn = document.querySelector('#preview-section .btn-download') || document.querySelector('.btn-download');
    if (!downloadBtn) {
        return;
    }

    const originalText = downloadBtn.innerHTML;
    downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
    downloadBtn.disabled = true;

    try {
        await document.fonts.ready;
        const opt = {
            margin: [0.2, 0.2, 0.2, 0.2],
            filename: `${document.getElementById('name').value.replace(/[^a-zA-Z0-9]/g, '_') || 'Resume'}.pdf`,
            image: {
                type: 'png',
                quality: 1.0
            },
            html2canvas: {
                scale: 2.5,
                useCORS: true,
                letterRendering: true,
                logging: false,
                allowTaint: true
            },
            jsPDF: {
                unit: 'in',
                format: 'letter',
                orientation: 'portrait'
            }
        };
        await html2pdf().set(opt).from(element).save();
    } catch (err) {
        console.error('PDF generation error:', err);
        alert('PDF generation failed. Please try again.');
    } finally {
        downloadBtn.innerHTML = originalText;
        downloadBtn.disabled = false;
    }
}