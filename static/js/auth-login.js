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
});
