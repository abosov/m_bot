document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#contact-form") || document.querySelector(".contact-form");
  if (!form) {
    return;
  }

  const nameInput = form.querySelector("#contact-name, [name='name']");
  const emailInput = form.querySelector("#contact-email, [name='email']");
  const messageInput = form.querySelector("#contact-message, [name='message']");
  const hpInput = form.querySelector("#contact-hp, [name='hp']");
  const statusNode = form.querySelector("#contact-status");
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
      hp: hpInput ? hpInput.value : null,
    };

    submitButton.disabled = true;
    if (statusNode) {
      statusNode.textContent = "";
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
        if (statusNode) {
          statusNode.textContent = "Сообщение отправлено";
        }
        messageInput.value = "";
      } else if (statusNode) {
        statusNode.textContent = "Не удалось отправить. Попробуйте позже.";
      }
    } catch (_) {
      if (statusNode) {
        statusNode.textContent = "Не удалось отправить. Попробуйте позже.";
      }
    } finally {
      submitButton.disabled = false;
    }
  });
});
