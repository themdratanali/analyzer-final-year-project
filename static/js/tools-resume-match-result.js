
document.addEventListener("DOMContentLoaded", () => {
    const scoreValue = Number(document.body.dataset.topScore || 0);
    const circles = document.querySelectorAll(".score-circle-large circle.progress");
    const circumference = 2 * Math.PI * 45;

    circles.forEach((circle) => {
        circle.style.strokeDasharray = String(circumference);
        circle.style.strokeDashoffset = String(circumference);
        setTimeout(() => {
            circle.style.transition = "stroke-dashoffset 1.5s ease";
            circle.style.strokeDashoffset = String(circumference - (circumference * scoreValue) / 100);
        }, 100);
    });

    document.querySelectorAll(".progress-fill").forEach((el) => {
        const width = `${el.dataset.width || 0}%`;
        el.style.width = "0";
        setTimeout(() => {
            el.style.width = width;
        }, 300);
    });
});