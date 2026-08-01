function toggleProfileMenu() {
    const menu = document.getElementById("profile-menu");
    if (menu) {
        menu.classList.toggle("active");
    }
}

document.addEventListener("click", function(event) {
    const profileSection = document.querySelector(".sidebar-profile");
    if (profileSection && !profileSection.contains(event.target)) {
        const menu = document.getElementById("profile-menu");
        if (menu) {
            menu.classList.remove("active");
        }
    }
});
