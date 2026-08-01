// Depends on site-common.js (mobile nav, FAQ accordion, animated counters)

document.addEventListener('DOMContentLoaded', () => {
    const howItWorksSection = document.querySelector('.how-it-works');
    const stepItems = document.querySelectorAll('.how-it-works .step-item');

    if (howItWorksSection && stepItems.length) {
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        stepItems.forEach(step => step.classList.add('is-visible'));
                        observer.unobserve(howItWorksSection);
                    }
                });
            },
            { threshold: 0.25 }
        );

        observer.observe(howItWorksSection);
    }
});
