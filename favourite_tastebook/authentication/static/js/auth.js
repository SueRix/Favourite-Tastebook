(function () {
  function bootAuthFormHints() {
    // If there are field errors on the auth form, show a generic toast.
    const hasErrors = document.querySelector(".field-errors, .errorlist");
    if (!hasErrors) return;

    if (window.FT && typeof window.FT.toast === "function") {
      window.FT.toast({
        text: "Please review the form fields: validation errors were found.",
        level: "error",
        timeout: 5000,
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    bootAuthFormHints();
  });
})();
