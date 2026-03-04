document.addEventListener("DOMContentLoaded", () => {

  const BOT_BASE_URL = "https://t.me/zumhelper_bot";

  function getBillingPeriodCode() {
    const active = document.querySelector(".billing-toggle .toggle-option.active");
    const billing = active?.getAttribute("data-billing") || "monthly";
    return billing === "yearly" ? "y" : "m";
  }

  function buildPlanDeepLink(plan, periodCode) {
    if (plan === "team") {
      return `${BOT_BASE_URL}?start=plan_team_contact`;
    }

    const payload = `plan_${plan}_${periodCode}`;
    return `${BOT_BASE_URL}?start=${encodeURIComponent(payload)}`;
  }

  function updatePlanCtas() {
    const periodCode = getBillingPeriodCode();
    const ctas = document.querySelectorAll("a.plan-cta");

    ctas.forEach((cta) => {
      const explicitPlan = (cta.getAttribute("data-plan") || "").trim().toLowerCase();
      const plan = explicitPlan || (cta.classList.contains("plan-team-contact") ? "team" : "");
      if (!plan) {
        return;
      }

      cta.setAttribute("href", buildPlanDeepLink(plan, periodCode));
      cta.setAttribute("data-period", periodCode);
      cta.setAttribute("target", "_blank");
      cta.setAttribute("rel", "noopener noreferrer");
    });
  }

  const form = document.querySelector(".contact-form");
  const statusEl = document.getElementById("contact-status");
  const nameInput = document.getElementById("contact-name");
  const emailInput = document.getElementById("contact-email");
  const messageInput = document.getElementById("contact-message");
  const hpInput = document.getElementById("contact-hp");
  const submitButton = form ? form.querySelector("button[type='submit']") : null;

  if (form && nameInput && emailInput && messageInput && submitButton) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const payload = {
        name: nameInput.value,
        email: emailInput.value,
        message: messageInput.value,
        hp: hpInput ? hpInput.value : "",
      };

      submitButton.disabled = true;
      if (statusEl) {
        statusEl.textContent = "Отправляем...";
      }

      try {
        const response = await fetch("/public/contact", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        const data = await response.json();
        if (data && data.ok === true) {
          if (statusEl) {
            statusEl.textContent = "Сообщение отправлено.";
          }
          messageInput.value = "";
        } else if (statusEl) {
          statusEl.textContent = "Не удалось отправить. Попробуйте позже.";
        }
      } catch (_) {
        if (statusEl) {
          statusEl.textContent = "Не удалось отправить. Попробуйте позже.";
        }
      } finally {
        submitButton.disabled = false;
      }
    });
  }

  const pricingToggle = document.querySelector(".billing-toggle, .pricing-toggle");
  updatePlanCtas();

  if (pricingToggle) {
    const options = pricingToggle.querySelectorAll(".toggle-option");
    const monthYearFields = document.querySelectorAll("[data-month][data-year]");

    const applyPeriod = (period) => {
      options.forEach((option) => {
        option.classList.toggle("active", option.dataset.period === period);
      });

      monthYearFields.forEach((field) => {
        field.textContent = period === "year" ? field.dataset.year : field.dataset.month;
      });

      updatePlanCtas();
    };

    options.forEach((option) => {
      option.addEventListener("click", () => applyPeriod(option.dataset.period));
    });

    const activeOption = pricingToggle.querySelector(".toggle-option.active");
    applyPeriod(activeOption ? activeOption.dataset.period : "month");
  }

});
