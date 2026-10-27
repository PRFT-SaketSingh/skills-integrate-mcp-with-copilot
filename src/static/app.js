document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const signupContainer = document.getElementById("signup-container");
  const accountMenuToggle = document.getElementById("account-menu-toggle");
  const accountMenu = document.getElementById("account-menu");
  const loginMenuButton = document.getElementById("login-menu-button");
  const teacherName = document.getElementById("teacher-name");
  const logoutButton = document.getElementById("logout-button");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("teacher-login-form");
  const loginError = document.getElementById("login-error");
  let currentTeacher = null;

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, (character) => {
      const entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      };
      return entities[character];
    });
  }

  function updateTeacherUI(username) {
    currentTeacher = username;
    signupContainer.classList.toggle("hidden", !username);
    loginMenuButton.classList.toggle("hidden", Boolean(username));
    teacherName.textContent = username ? `Logged in: ${username}` : "";
    teacherName.classList.toggle("hidden", !username);
    logoutButton.classList.toggle("hidden", !username);
    fetchActivities();
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                .map((email) => `<li>
                    <span class="participant-email">${escapeHTML(email)}</span>
                    ${
                      currentTeacher
                        ? `<button class="delete-btn" data-activity="${escapeHTML(
                            name
                          )}" data-email="${escapeHTML(email)}" aria-label="Unregister ${escapeHTML(
                            email
                          )}">Remove</button>`
                        : ""
                    }
                  </li>`)
                .join("")}
            </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${escapeHTML(name)}</h4>
          <p>${escapeHTML(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHTML(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      activitiesList.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.currentTarget;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");
    if (!activity || !email) {
      return;
    }

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  accountMenuToggle.addEventListener("click", () => {
    const expanded = accountMenuToggle.getAttribute("aria-expanded") === "true";
    accountMenuToggle.setAttribute("aria-expanded", String(!expanded));
    accountMenu.classList.toggle("hidden", expanded);
  });

  loginMenuButton.addEventListener("click", () => {
    accountMenu.classList.add("hidden");
    accountMenuToggle.setAttribute("aria-expanded", "false");
    loginError.classList.add("hidden");
    loginDialog.showModal();
  });

  document.getElementById("cancel-login-button").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.classList.add("hidden");
    const formData = new FormData(loginForm);

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        loginError.textContent = result.detail || "Unable to log in";
        loginError.classList.remove("hidden");
        return;
      }

      loginForm.reset();
      loginDialog.close();
      updateTeacherUI(result.username);
    } catch (error) {
      loginError.textContent = "Failed to log in. Please try again.";
      loginError.classList.remove("hidden");
      console.error("Error logging in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      if (!response.ok) {
        throw new Error("Unable to log out");
      }
      accountMenu.classList.add("hidden");
      accountMenuToggle.setAttribute("aria-expanded", "false");
      updateTeacherUI(null);
    } catch (error) {
      messageDiv.textContent = "Failed to log out. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error logging out:", error);
    }
  });

  async function restoreTeacherSession() {
    try {
      const response = await fetch("/auth/me");
      if (response.ok) {
        const result = await response.json();
        updateTeacherUI(result.username);
        return;
      }
      if (response.status !== 401) {
        throw new Error("Unable to check teacher login");
      }
    } catch (error) {
      console.error("Error checking teacher login:", error);
    }
    updateTeacherUI(null);
  }

  restoreTeacherSession();
});
