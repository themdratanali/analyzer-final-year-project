// Depends on site-common.js (mobile nav toggle)

function filterDocuments(category, btn) {
    document.querySelectorAll('.filter-tab').forEach(function(tab) {
        tab.classList.remove('active');
    });
    btn.classList.add('active');
    document.querySelectorAll('.document-card').forEach(function(card) {
        if (category === 'all' || card.dataset.category === category) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}
