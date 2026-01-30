(function () {
  function getToastRoot() {
    return document.getElementById("toast-root");
  }

  function normalizeLevel(level) {
    const l = (level || "").toLowerCase();
    if (l.includes("success")) return "success";
    if (l.includes("warning")) return "warning";
    if (l.includes("info")) return "info";
    return "error";
  }

  function removeToast(el) {
    if (!el) return;
    el.classList.add("toast--hide");
    setTimeout(() => el.remove(), 180);
  }

  function showToast({ text, level = "info", actionText = null, actionHref = null, timeout = 4200 }) {
    const root = getToastRoot();
    if (!root) return;

    const toast = document.createElement("div");
    toast.className = `toast toast--${level}`;

    const body = document.createElement("div");
    body.className = "toast-body";
    body.textContent = text;

    const actions = document.createElement("div");
    actions.className = "toast-actions";

    if (actionText && actionHref) {
      const a = document.createElement("a");
      a.className = "toast-action";
      a.href = actionHref;
      a.textContent = actionText;
      actions.appendChild(a);
    }

    const close = document.createElement("button");
    close.className = "toast-close";
    close.type = "button";
    close.setAttribute("aria-label", "Close");
    close.textContent = "×";
    close.addEventListener("click", () => removeToast(toast));

    toast.appendChild(body);
    toast.appendChild(actions);
    toast.appendChild(close);

    root.appendChild(toast);

    if (timeout && timeout > 0) {
      setTimeout(() => removeToast(toast), timeout);
    }
  }

  function bootDjangoMessagesToToasts() {
    const nodes = document.querySelectorAll(".js-message");
    if (!nodes.length) return;

    nodes.forEach((n) => {
      const level = normalizeLevel(n.dataset.level);
      const text = n.dataset.text || "";
      if (text.trim()) showToast({ text, level });
    });
  }

  function bootSidebarAuthGuard() {
    const isAuthenticated = document.body.dataset.authenticated === "1";
    if (isAuthenticated) return;

    const loginUrl = document.body.dataset.loginUrl || "/login/";
    const message = "You are not logged in. Please sign in to use this feature.";

    document.querySelectorAll("[data-auth-required='1']").forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();

        link.classList.remove("shake-x");
        void link.offsetWidth;
        link.classList.add("shake-x");

        showToast({
          text: message,
          level: "warning",
          actionText: "Sign in",
          actionHref: loginUrl,
        });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    bootDjangoMessagesToToasts();
    bootSidebarAuthGuard();
  });

  // Public API
  window.FT = window.FT || {};
  window.FT.toast = showToast;
})();
