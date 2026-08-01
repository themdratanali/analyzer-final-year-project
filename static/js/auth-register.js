document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".password-toggle").forEach((button) => {
        const input = button.closest(".auth-input-wrap").querySelector(".password-toggle-input");
        const icon = button.querySelector("i");
        if (!input || !icon) return;

        button.addEventListener("click", () => {
            const isVisible = input.type === "text";
            input.type = isVisible ? "password" : "text";
            icon.classList.toggle("fa-eye", isVisible);
            icon.classList.toggle("fa-eye-slash", !isVisible);
            button.setAttribute("aria-label", isVisible ? "Show password" : "Hide password");
        });
    });

    const strengthInput = document.querySelector(".password-strength-input");
    const strengthBar = document.querySelector(".password-meter span");
    if (!strengthInput || !strengthBar) return;

    const updateStrength = () => {
        const value = strengthInput.value;
        let score = 0;
        if (value.length >= 8) score += 1;
        if (/[A-Z]/.test(value)) score += 1;
        if (/[0-9]/.test(value)) score += 1;
        if (/[^A-Za-z0-9]/.test(value)) score += 1;
        const colors = ["#ef4444", "#f59e0b", "#3b82f6", "#22c55e"];
        const index = Math.min(score, colors.length - 1);
        strengthBar.style.width = value ? `${25 + index * 25}%` : "0%";
        strengthBar.style.background = value ? colors[index] : "#e2e8f0";
    };

    strengthInput.addEventListener("input", updateStrength);
});
