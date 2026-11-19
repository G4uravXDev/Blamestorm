/**
 * zit — AI-powered Git & GitHub Manager (Django Edition)
 * Global JavaScript helper & keyboard shortcuts
 */

document.addEventListener("DOMContentLoaded", function () {
  // ── Keyboard Shortcuts ──────────────────────────────────────────
  document.addEventListener("keydown", function (e) {
    // Ignore keystrokes when focused on input, textarea, or contentEditable
    const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : "";
    if (activeTag === "input" || activeTag === "textarea" || activeTag === "select") {
      if (e.key === "Escape") {
        document.activeElement.blur();
      }
      return;
    }

    if (e.ctrlKey || e.altKey || e.metaKey) return;

    switch (e.key) {
      case "s":
        window.location.href = "/staging/";
        break;
      case "c":
        window.location.href = "/commit/";
        break;
      case "b":
        window.location.href = "/branches/";
        break;
      case "l":
        window.location.href = "/timeline/";
        break;
      case "t":
        window.location.href = "/time-travel/";
        break;
      case "r":
        window.location.href = "/reflog/";
        break;
      case "x":
        window.location.href = "/stash/";
        break;
      case "m":
        window.location.href = "/merge/";
        break;
      case "B":
        window.location.href = "/bisect/";
        break;
      case "p":
        window.location.href = "/cherry-pick/";
        break;
      case "w":
        window.location.href = "/workflow/";
        break;
      case "g":
        window.location.href = "/github/";
        break;
      case "a":
        window.location.href = "/mentor/";
        break;
      case "A":
        window.location.href = "/agent/";
        break;
      case "?":
        openModal("shortcutsModal");
        break;
      case "Escape":
        closeAllModals();
        break;
    }
  });
});

// ── Modal Helpers ────────────────────────────────────────────────
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add("active");
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("active");
}

function closeAllModals() {
  document.querySelectorAll(".modal-overlay").forEach(function (m) {
    m.classList.remove("active");
  });
}

// ── Generic Git Command AJAX Caller ─────────────────────────────
async function runGitAction(action, payload = {}, reloadOnSuccess = true) {
  try {
    const res = await fetch("/api/git-command/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: action, ...payload })
    });
    const data = await res.json();
    if (data.success) {
      if (reloadOnSuccess) {
        window.location.reload();
      } else {
        showToast("Git action completed successfully", "success");
        return data;
      }
    } else {
      showToast(data.stderr || data.error || "Git command failed", "danger");
      return data;
    }
  } catch (err) {
    showToast("Network / server error: " + err, "danger");
  }
}

// ── Toast Notification System ────────────────────────────────────
function showToast(message, type = "info") {
  let toastContainer = document.getElementById("zit-toast-container");
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.id = "zit-toast-container";
    toastContainer.style.position = "fixed";
    toastContainer.style.bottom = "20px";
    toastContainer.style.right = "20px";
    toastContainer.style.zIndex = "9999";
    toastContainer.style.display = "flex";
    toastContainer.style.flexDirection = "column";
    toastContainer.style.gap = "8px";
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement("div");
  toast.className = `alert alert-${type}`;
  toast.style.minWidth = "260px";
  toast.style.maxWidth = "420px";
  toast.style.boxShadow = "0 8px 16px rgba(0,0,0,0.5)";
  toast.style.margin = "0";
  toast.innerHTML = `<span>${message}</span>`;

  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

// ── Repository Switcher ──────────────────────────────────────────
async function switchRepository(path) {
  try {
    const res = await fetch("/api/switch-repo/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: path })
    });
    const data = await res.json();
    if (data.success) {
      window.location.reload();
    } else {
      showToast(data.error || "Failed to switch repository", "danger");
    }
  } catch (err) {
    showToast("Error switching repo: " + err, "danger");
  }
}
