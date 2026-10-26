/**
 * SRI SRINIVASA CANVASING - Mandapeta, Andhra Pradesh
 * Frontend Interactive Enhancements & Utilities
 */

document.addEventListener("DOMContentLoaded", function () {
    // 1. Mobile Navigation Menu Toggle
    const navToggle = document.querySelector(".nav-toggle");
    const navLinks = document.querySelector(".nav-links");

    if (navToggle && navLinks) {
        navToggle.addEventListener("click", function () {
            navLinks.classList.toggle("show");
        });
    }

    // 2. Alert Dismissal Handlers
    const alertCloses = document.querySelectorAll(".alert-close");
    alertCloses.forEach(function (btn) {
        btn.addEventListener("click", function () {
            const alert = btn.closest(".alert");
            if (alert) {
                alert.style.opacity = "0";
                setTimeout(() => alert.remove(), 250);
            }
        });
    });

    // Auto-fade flash alerts after 6 seconds
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.transition = "opacity 0.4s ease";
            alert.style.opacity = "0";
            setTimeout(() => alert.remove(), 400);
        }, 6000);
    });

    // 3. Print Trigger Helper
    const printButtons = document.querySelectorAll(".btn-print");
    printButtons.forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            window.print();
        });
    });

    // 4. Dynamic Paddy Weight Estimator on Transaction Form
    const bagsInput = document.getElementById("number_of_bags");
    const weightInput = document.getElementById("vehicle_weight_kg");
    const weightHint = document.getElementById("weight_estimate_hint");

    if (bagsInput && weightHint) {
        bagsInput.addEventListener("input", function () {
            const bags = parseInt(bagsInput.value, 10);
            if (!isNaN(bags) && bags > 0) {
                const estNet = bags * 75; // Standard Andhra Pradesh paddy bag is ~75 kg gross/net
                weightHint.innerHTML = `<em>Estimated net paddy weight: ~${estNet.toLocaleString()} kg (approx. 75 kg/bag)</em>`;
            } else {
                weightHint.innerHTML = "";
            }
        });
    }

    // 5. Admin Decision Confirmation Helpers
    const rejectForms = document.querySelectorAll(".form-reject-tx");
    rejectForms.forEach(function (form) {
        form.addEventListener("submit", function (e) {
            const reasonInput = form.querySelector("[name='rejection_reason']");
            if (reasonInput && !reasonInput.value.trim()) {
                const reason = prompt("Please provide a reason for rejecting this transaction (optional, click OK or Cancel):", "Quality inspection mismatch / Moisture high");
                if (reason !== null) {
                    reasonInput.value = reason;
                }
            }
        });
    });
});
