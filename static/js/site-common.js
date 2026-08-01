// site-common.js
// Shared site functionality used across marketing and app pages.
// Provides the mobile navigation toggle, FAQ accordion, and stat counters.
// Load this script before any page-specific script that relies on it.

function initMobileNav() {
    const mobileToggle = document.querySelector('.mobile-toggle');
    const navMenu = document.querySelector('.nav-menu');

    if (mobileToggle && navMenu) {
        mobileToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
            const icon = mobileToggle.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-bars');
                icon.classList.toggle('fa-times');
            }
        });
    }

    document.querySelectorAll('.nav-item.dropdown').forEach((dropdown) => {
        const link = dropdown.querySelector('.nav-link');
        if (!link) {
            return;
        }
        link.addEventListener('click', (e) => {
            if (window.innerWidth <= 768) {
                e.preventDefault();
                dropdown.classList.toggle('active');
            }
        });
    });
}

function initFaqAccordion() {
    document.querySelectorAll('.faq-question').forEach((button) => {
        button.addEventListener('click', () => {
            const item = button.closest('.faq-item');
            if (!item) {
                return;
            }
            const isOpen = item.classList.contains('is-open');

            document.querySelectorAll('.faq-item').forEach((otherItem) => {
                otherItem.classList.remove('is-open');
                const otherButton = otherItem.querySelector('.faq-question');
                if (otherButton) {
                    otherButton.setAttribute('aria-expanded', 'false');
                }
            });

            if (!isOpen) {
                item.classList.add('is-open');
                button.setAttribute('aria-expanded', 'true');
            }
        });
    });
}

function animateCounters() {
    const statNumbers = document.querySelectorAll('.stat-number[data-count]');
    statNumbers.forEach((counter) => {
        const target = parseInt(counter.getAttribute('data-count'));
        const duration = 2000;
        const step = target / (duration / 16);
        let current = 0;

        const updateCounter = () => {
            current += step;
            if (current < target) {
                counter.textContent = Math.ceil(current).toLocaleString();
                requestAnimationFrame(updateCounter);
            } else {
                counter.textContent = target.toLocaleString() + '+';
            }
        };

        updateCounter();
    });
}

function initCounterObserver() {
    const statNumbers = document.querySelectorAll('.stat-number[data-count]');
    const statsSection = document.querySelector('.stats-section');

    if (statsSection && statNumbers.length) {
        const counterObserver = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        animateCounters();
                        counterObserver.unobserve(statsSection);
                    }
                });
            },
            { threshold: 0.3 }
        );

        counterObserver.observe(statsSection);
    }
}

function updateFileName(input) {
    const label = document.getElementById('file-label');
    if (!label) {
        return;
    }
    if (input.files && input.files.length > 0) {
        const fileNames = Array.from(input.files).map((f) => f.name).join(', ');
        label.innerHTML = '<i class="fas fa-check-circle"></i> ' + fileNames;
    } else {
        label.innerHTML = 'Click to upload or drag and drop';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initMobileNav();
    initFaqAccordion();
    initCounterObserver();
});
