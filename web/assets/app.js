document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".contact-form");
  if (!form) {
    return;
  }

  const statusEl = document.getElementById("contact-status");
  const nameInput = document.getElementById("contact-name");
  const emailInput = document.getElementById("contact-email");
  const messageInput = document.getElementById("contact-message");
  const hpInput = document.getElementById("contact-hp");
  const submitButton = form.querySelector("button[type='submit']");

  if (!nameInput || !emailInput || !messageInput || !submitButton) {
    return;
  }

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
});
