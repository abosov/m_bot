document.addEventListener("DOMContentLoaded", () => {
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
    };

    options.forEach((option) => {
      option.addEventListener("click", () => applyPeriod(option.dataset.period));
    });
  }

});
