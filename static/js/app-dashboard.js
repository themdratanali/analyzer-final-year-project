
const username = document.body.dataset.username || "User";
const apiAnalyzeUrl = document.body.dataset.apiAnalyzeUrl || "";
const setFreshUploadUrl = document.body.dataset.setFreshUploadUrl || "";
const dashboardUrl = document.body.dataset.dashboardUrl || "/dashboard";
const logoutUrl = document.body.dataset.logoutUrl || "/auth/logout";

function applyDynamicPresentation(root = document) {
    root.querySelectorAll('.progress-fill[data-width]').forEach(el => {
        el.style.width = `${el.dataset.width}%`;
    });

    root.querySelectorAll('.dynamic-icon[data-color]').forEach(icon => {
        icon.style.color = icon.dataset.color;
    });
}

function showContent(sectionId, link, saveState = true) {
    document.querySelectorAll('.sidebar-menu a').forEach(item => item.classList.remove('active'));
    if (link && link.classList) {
        link.classList.add('active');
    }

    document.querySelectorAll('.content-section').forEach(section => section.classList.remove('active'));
    const target = document.getElementById(sectionId);
    if (target) {
        target.classList.add('active');

        // Refresh history panels so newly stored results always show up.
        const refreshablePanels = ['results-panel', 'documents-panel', 'match-history-panel'];
        if (refreshablePanels.includes(sectionId)) {
            const iframe = target.querySelector('iframe');
            if (iframe) {
                const baseSrc = iframe.getAttribute('data-src') || iframe.getAttribute('src');
                if (baseSrc) {
                    iframe.setAttribute('data-src', baseSrc);
                    const separator = baseSrc.includes('?') ? '&' : '?';
                    iframe.setAttribute('src', baseSrc + separator + '_ts=' + Date.now());
                }
            }
        }
    }

    if (saveState && sectionId !== 'home-panel') {
        localStorage.setItem('activeSection', sectionId);
        const sectionName = sectionId.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase());
        document.title = username + ' - ' + sectionName;
    } else if (sectionId === 'home-panel') {
        document.title = username + ' - Resume Analyzer';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const savedSection = localStorage.getItem('activeSection');
    if (savedSection) {
        const link = document.querySelector('a[onclick*="' + savedSection + '"]');
        if (link) {
            showContent(savedSection, link, false);
        }
    }

    const form = document.getElementById('resume-analyzer-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            e.stopPropagation();
            submitResume();
        });
    }

    applyDynamicPresentation();
});

function updateMatchFileName(input) {
    const label = document.getElementById('match-file-label');
    if (input.files && input.files[0]) {
        label.innerHTML = '<i class="fas fa-check-circle icon-primary"></i> ' + input.files[0].name;
    } else {
        label.innerHTML = 'Select PDF or DOCX File';
    }
}

function updateBuilderPreview() {
    document.getElementById('p-name').textContent = document.getElementById('rb-name').value || 'Your Name';
    document.getElementById('p-title').textContent = document.getElementById('rb-title').value || 'Job Title';
    document.getElementById('p-phone').textContent = document.getElementById('rb-phone').value || 'Phone';
    document.getElementById('p-email').textContent = document.getElementById('rb-email').value || 'email@example.com';
    document.getElementById('p-location').textContent = document.getElementById('rb-location').value || 'Location';
    document.getElementById('p-objective').textContent = document.getElementById('rb-objective').value || '';
    document.getElementById('p-skills').innerHTML = document.getElementById('rb-skills').value.replace(/\n/g, '<br>') || '';
}

function toggleProfileMenu() {
    const menu = document.getElementById('profile-menu');
    menu.classList.toggle('active');
}

document.addEventListener('click', function(event) {
    const profileSection = document.querySelector('.sidebar-profile');
    if (profileSection && !profileSection.contains(event.target)) {
        const menu = document.getElementById('profile-menu');
        if (menu) {
            menu.classList.remove('active');
        }
    }
});

function confirmLogout() {
    const modal = document.getElementById('logout-modal');
    if (modal) {
        modal.classList.add('active');
    }
}

function closeLogoutModal() {
    const modal = document.getElementById('logout-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function logoutNow() {
    window.location.href = logoutUrl;
}

function downloadBuilderPDF() {
    const element = document.getElementById('resume-preview');
    html2pdf()
        .set({
            margin: 0.5,
            filename: 'Resume.pdf',
            image: {
                type: 'jpeg',
                quality: 0.98
            },
            html2canvas: {
                scale: 2
            },
            jsPDF: {
                unit: 'in',
                format: 'letter',
                orientation: 'portrait'
            }
        })
        .from(element)
        .save();
}

let isSubmitting = false;

function submitResume() {
    if (isSubmitting) {
        return;
    }
    isSubmitting = true;

    const fileInput = document.getElementById('resume');
    if (!fileInput || !fileInput.files || !fileInput.files[0]) {
        alert('Please select a file first');
        isSubmitting = false;
        return;
    }

    const formData = new FormData();
    formData.append('resume', fileInput.files[0]);

    const uploadCard = document.querySelector('.upload-card');
    const btn = uploadCard ? uploadCard.querySelector('.action-btn') : null;
    const modal = document.getElementById('analyzer-modal');

    if (modal) {
        modal.classList.add('is-visible');
        modal.setAttribute('aria-hidden', 'false');
    }
    if (btn) {
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
        btn.disabled = true;
    }

    if (!apiAnalyzeUrl) {
        alert('Upload URL not configured. Please refresh the page.');
        if (modal) {
            modal.classList.remove('is-visible');
            modal.setAttribute('aria-hidden', 'true');
        }
        if (btn) {
            btn.innerHTML = 'Analyze Resume';
            btn.disabled = false;
        }
        isSubmitting = false;
        return;
    }

    fetch(apiAnalyzeUrl + (apiAnalyzeUrl.includes('?') ? '&' : '?') + '_ts=' + Date.now(), {
            method: 'POST',
            body: formData,
            cache: 'no-store'
        })
        .then(response => {
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                return response.text().then(text => {
                    throw new Error('Server returned non-JSON response: ' + text.substring(0, 100));
                });
            }
            return response.json();
        })
        .then(data => {
            if (modal) {
                modal.classList.remove('is-visible');
                modal.setAttribute('aria-hidden', 'true');
            }
            if (data.error) {
                alert('Error: ' + data.error);
                if (btn) {
                    btn.innerHTML = 'Analyze Resume';
                    btn.disabled = false;
                }
            } else {
                try {
                    showResults(data.score, data.results, data.suggestions);
                    if (btn) {
                        btn.innerHTML = '<i class="fas fa-check"></i> Analysis Complete';
                        setTimeout(() => {
                            btn.innerHTML = 'Analyze Resume';
                            btn.disabled = false;
                        }, 2000);
                    }
                } catch (displayError) {
                    console.error('Error displaying results:', displayError);
                    alert('Error displaying results. Please refresh and try again.');
                    if (btn) {
                        btn.innerHTML = 'Analyze Resume';
                        btn.disabled = false;
                    }
                }
            }
            isSubmitting = false;
        })
        .catch(error => {
            console.error('Upload error:', error);
            if (modal) {
                modal.classList.remove('is-visible');
                modal.setAttribute('aria-hidden', 'true');
            }
            alert('Error uploading file: ' + error.message);
            if (btn) {
                btn.innerHTML = 'Analyze Resume';
                btn.disabled = false;
            }
            isSubmitting = false;
        });
}

function showResults(score, results, suggestions) {
    if (typeof score !== 'number' || isNaN(score)) {
            console.error('Invalid score value:', score);
            alert('Invalid analysis score received. Please try again.');
            return;
        }

        if (!Array.isArray(results)) {
            console.error('Results is not an array:', results);
            results = [];
        }

        const container = document.getElementById('resume-analyzer');
        if (!container) {
            console.error('Resume analyzer container not found');
            return;
        }

        container.innerHTML = '';

        const hiddenCategories = new Set([
            'SBERT Semantic Quality',
            'spaCy Entity & Skill Extraction',
            'Skill Depth Intelligence'
        ]);

        let tagText = 'Needs Improvement', tagClass = 'is-low';
        let verdict = 'Needs focused improvement across key resume sections.';
        if (score >= 80) {
            verdict = 'Your resume is well-optimized and application-ready.';
            tagText = 'Excellent';
            tagClass = 'is-high';
        } else if (score >= 60) {
            verdict = 'Solid foundation \u2014 a few targeted improvements will strengthen it.';
            tagText = 'Good';
            tagClass = 'is-mid';
        }

        const ringRadius = 74;
        const ringCirc = 2 * Math.PI * ringRadius;
        const clamped = Math.max(0, Math.min(100, score));
        const ringOffset = ringCirc * (1 - clamped / 100);

        let html = '<div class="results-section">';
        html += '<div class="score-hero">';
        html += '<div class="score-ring">';
        html += '<svg viewBox="0 0 168 168" role="img" aria-label="Overall score ' + Math.round(score) + ' out of 100">';
        html += '<defs><linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="100%">';
        html += '<stop offset="0%" stop-color="#6366f1" /><stop offset="100%" stop-color="#8b5cf6" /></linearGradient></defs>';
        html += '<circle class="score-ring-track" cx="84" cy="84" r="' + ringRadius + '" />';
        html += '<circle class="score-ring-value" cx="84" cy="84" r="' + ringRadius + '" '
            + 'stroke-dasharray="' + ringCirc.toFixed(2) + '" stroke-dashoffset="' + ringCirc.toFixed(2) + '" '
            + 'data-offset="' + ringOffset.toFixed(2) + '" />';
        html += '</svg>';
        html += '<div class="score-ring-center"><span class="score-value">' + Math.round(score) + '</span><span class="score-outof">/ 100</span></div>';
        html += '</div>';
        html += '<div class="score-meta"><span class="score-label">Overall Score</span>';
        html += '<span class="score-tag ' + tagClass + '">' + tagText + '</span></div>';
        html += '<p class="score-verdict">' + verdict + '</p>';
        html += '</div>';

        if (Array.isArray(suggestions) && suggestions.length > 0) {
            html += '<div class="overall-suggestions">';
            html += '<h2>Top Improvement Suggestions</h2>';
            html += '<ul>';
            for (const sug of suggestions) {
                if (sug && sug.trim()) {
                    html += '<li>' + sug + '</li>';
                }
            }
            html += '</ul></div>';
        }

        html += '<div class="results-grid">';

        for (const item of results) {
            if (item && item.category && !hiddenCategories.has(item.category)) {
                let hasFlaws = item.flaws && item.flaws.length > 0;
                let icon = hasFlaws ? 'exclamation-circle' : 'check-circle';
                let iconColor = hasFlaws ? '#f59e0b' : '#10b981';

                const maxScore = (typeof item.max_score === 'number' && item.max_score > 0) ? item.max_score : 1;
                const itemScore = (typeof item.score === 'number') ? item.score : 0;
                const pct = Math.max(0, Math.min(100, ((itemScore / maxScore) * 100)));

                html += '<div class="result-card">';
                html += '<h3><i class="fas fa-' + icon + ' dynamic-icon" data-color="' + iconColor + '"></i> ' + item.category + '<span class="score-chip">' + itemScore + '/' + maxScore + '</span></h3>';

                html += '<div class="score-bar"><div class="progress-fill" data-width="' + pct + '"></div></div>';

                if (item.flaws && item.flaws.length > 0) {
                    html += '<ul>';
                    for (const flaw of item.flaws) {
                        html += '<li>' + flaw + '</li>';
                    }
                    html += '</ul>';
                }

                if (item.fix_tips && item.fix_tips.length > 0) {
                    html += '<div class="suggestions">';
                    html += '<span class="suggestions-title">💡 Fix Tips:</span>';
                    html += '<ul class="suggestions-list">';
                    for (const tip of item.fix_tips) {
                        html += '<li class="suggestion-item">' + tip + '</li>';
                    }
                    html += '</ul></div>';
                }

                if (item.suggestions && item.suggestions.length > 0) {
                    html += '<div class="suggestions">';
                    html += '<span class="suggestions-title">💡 Suggestions:</span>';
                    html += '<ul class="suggestions-list">';
                    for (const sug of item.suggestions) {
                        html += '<li class="suggestion-item">' + sug + '</li>';
                    }
                    html += '</ul></div>';
                }

                html += '</div>';
            }
        }

        html += '</div>';
        html += '<button class="action-btn" onclick="resetAnalysis()">Analyze Another Resume</button>';
        html += '</div>';

        container.innerHTML = html;
        applyDynamicPresentation(container);

        const ringValue = container.querySelector('.score-ring-value');
        if (ringValue) {
            const target = ringValue.getAttribute('data-offset');
            requestAnimationFrame(() => {
                setTimeout(() => { ringValue.style.strokeDashoffset = target; }, 80);
            });
        }
}

function closeAnalyzerModal() {
    const modal = document.getElementById('analyzer-modal');
    if (modal) {
        modal.classList.remove('is-visible');
        modal.setAttribute('aria-hidden', 'true');
    }
}

function resetAnalysis() {
    closeAnalyzerModal();
    fetch(setFreshUploadUrl, {
            method: 'POST'
        })
        .then(() => {
            window.location.href = dashboardUrl;
        });
}

document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeAnalyzerModal();
    }
});

document.addEventListener('click', function(event) {
    const modal = document.getElementById('analyzer-modal');
    if (!modal) return;
    if (event.target === modal || event.target.classList.contains('analyzer-modal-backdrop')) {
        closeAnalyzerModal();
    }
});