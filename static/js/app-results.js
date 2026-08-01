
window.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.tab-content[data-initial-display]').forEach(content => {
        content.style.display = content.dataset.initialDisplay;
    });
    document.querySelectorAll('.progress-fill[data-width]').forEach(el => {
        el.style.width = `${el.dataset.width}%`;
    });

    document.querySelectorAll('a[data-session-id]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            viewMatchDetails(link.dataset.sessionId);
        });
    });
});

function showTab(tabName, event) {
    document.querySelectorAll('.filter-tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.style.display = 'none');

    event.target.classList.add('active');
    document.getElementById('tab-' + tabName).style.display = 'block';
}

function toggleDetails(id, btn) {
    var details = document.getElementById('details-' + id);
    if (details) {
        var nowShown = details.classList.toggle('show');
        details.classList.remove('is-hidden');
        if (btn) {
            btn.innerHTML = nowShown
                ? '<i class="fas fa-eye-slash"></i> Hide Details'
                : '<i class="fas fa-eye"></i> View Details';
        }
    }
}

function viewMatchDetails(sessionId) {
    var modal = document.getElementById('match-detail-modal');
    var content = document.getElementById('match-detail-content');

    fetch('/api/matches/' + encodeURIComponent(sessionId))
        .then(response => response.json())
        .then(data => {
            var html = '<div class="detail-header-card">' +
                '<h1><i class="fas fa-file-contract"></i> Match Session #' + data.session.id + '</h1>' +
                '<div class="detail-meta">' +
                '<div class="meta-item"><i class="fas fa-calendar"></i> ' + data.session.created_at + '</div>' +
                '<div class="meta-item"><i class="fas fa-file-pdf"></i> ' + data.results.length + ' Resume(s)</div>';

            if (data.results.length > 0) {
                html += '<div class="meta-item"><i class="fas fa-star"></i> Best Match: ' + data.results[0].match_score + '%</div>';
            }

            html += '</div></div>' +
                '<div class="job-description-box">' +
                '<h3><i class="fas fa-briefcase"></i> Job Description</h3>' +
                '<p>' + (data.job_description || '').substring(0, 500) + '...</p>' +
                '</div>' +
                '<h2 class="section-title"><i class="fas fa-list"></i> Matched Resumes</h2>' +
                '<div class="results-grid">';

            data.results.forEach(function(result) {
                var scorePct = result.match_score;
                var scoreClass = scorePct >= 70 ? 'score-high' : (scorePct >= 40 ? 'score-medium' : 'score-low');
                var progressClass = scorePct >= 70 ? 'progress-green' : (scorePct >= 40 ? 'progress-yellow' : 'progress-red');

                html += '<div class="result-card">' +
                    '<div class="result-card-header">' +
                    '<div class="result-filename"><i class="fas fa-file-pdf file-icon-pdf"></i> ' + result.filename + '</div>' +
                    '<div class="score-circle ' + scoreClass + '">' +
                    '<svg width="60" height="60"><circle class="bg" cx="30" cy="30" r="24"></circle>' +
                    '<circle class="progress" cx="30" cy="30" r="24" stroke-dasharray="150.79" stroke-dashoffset="' + (150.79 - (150.79 * scorePct / 100)) + '"></circle></svg>' +
                    '<span class="score-text">' + scorePct + '%</span></div></div>' +
                    '<div class="progress-bar"><div class="progress-fill ' + progressClass + '" data-width="' + scorePct + '"></div></div>' +
                    '<div class="match-label"><i class="fas fa-percentage"></i> Similarity: ' + (result.similarity * 100).toFixed(1) + '%</div></div>';
            });

            html += '</div>';
            content.innerHTML = html;
            modal.style.display = 'block';
        })
        .catch(function(error) {
            console.error('Error loading match details:', error);
        });
}

function closeMatchModal() {
    document.getElementById('match-detail-modal').style.display = 'none';
}

window.onclick = function(event) {
    var modal = document.getElementById('match-detail-modal');
    if (event.target == modal) {
        modal.style.display = 'none';
    }
}