// Depends on site-common.js (mobile nav, FAQ accordion, animated counters)

const body = document.body;
const isLoggedIn = body.dataset.isLoggedIn === "true";
const orderUrlBase = body.dataset.orderUrl || "/billing/order";
const loginUrlBase = body.dataset.loginUrl || "/login";
let isAnnual = false;

function togglePricing() {
    isAnnual = !isAnnual;
    const toggle = document.querySelector(".toggle-switch");
    const monthlyLabel = document.getElementById("monthly-label");
    const annualLabel = document.getElementById("annual-label");
    const proPrice = document.getElementById("pro-price");
    const proPeriod = document.getElementById("pro-period");
    const enterprisePrice = document.getElementById("enterprise-price");
    const enterprisePeriod = document.getElementById("enterprise-period");

    if (isAnnual) {
        proPrice.textContent = "7.99";
        proPeriod.textContent = "/month";
        enterprisePrice.textContent = (15.99).toFixed(2);
        enterprisePeriod.textContent = "/month";
        toggle.classList.add("active");
        monthlyLabel.classList.remove("active-label");
        annualLabel.classList.add("active-label");
    } else {
        proPrice.textContent = "12.99";
        proPeriod.textContent = "/month";
        enterprisePrice.textContent = "29.00";
        enterprisePeriod.textContent = "/month";
        toggle.classList.remove("active");
        monthlyLabel.classList.add("active-label");
        annualLabel.classList.remove("active-label");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".select-btn").forEach((btn) => {
        btn.addEventListener("click", (event) => {
            event.preventDefault();
            const plan = btn.getAttribute("data-plan");
            const orderUrl = `${orderUrlBase}?plan=${encodeURIComponent(plan || "")}`;

            if (isLoggedIn) {
                window.location.href = orderUrl;
                return;
            }

            window.location.href = `${loginUrlBase}?redirect=${encodeURIComponent(orderUrl)}`;
        });
    });
});
