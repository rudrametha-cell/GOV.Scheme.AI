// =========================================================
// SchemeMatch AI — script.js
// Handles: mobile nav, form validation, demo profile,
// loading overlay sequence, animated progress bars, modal.
// =========================================================

document.addEventListener("DOMContentLoaded", function () {
  initMobileNav();
  initHeroProgress();
  initFundingField();
  initDemoButton();
  initFormValidation();
  initScoreBars();
  initSchemeModal();
});

/* ---------- Funding: preset dropdown + custom amount ---------- */
function initFundingField() {
  const select = document.getElementById("fundingSelect");
  const custom = document.getElementById("fundingCustom");
  const hidden = document.getElementById("fundingRequiredHidden");
  if (!select || !custom || !hidden) return;

  function syncHidden() {
    if (select.value === "custom") {
      custom.style.display = "block";
      hidden.value = custom.value || "";
    } else {
      custom.style.display = "none";
      hidden.value = select.value || "";
    }
  }

  select.addEventListener("change", syncHidden);
  custom.addEventListener("input", syncHidden);

  // Restore state if the form is re-rendered after a validation error.
  if (hidden.value) {
    const preset = Array.from(select.options).find(function (opt) { return opt.value === hidden.value; });
    if (preset) {
      select.value = hidden.value;
    } else {
      select.value = "custom";
      custom.value = hidden.value;
      custom.style.display = "block";
    }
  }
}

/* ---------- Mobile navigation ---------- */
function initMobileNav() {
  const toggle = document.getElementById("navToggle");
  const links = document.getElementById("navLinks");
  if (!toggle || !links) return;

  toggle.addEventListener("click", function () {
    const isOpen = links.classList.toggle("open");
    toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });

  links.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", function () {
      links.classList.remove("open");
      toggle.setAttribute("aria-expanded", "false");
    });
  });
}

/* ---------- Hero AI preview card progress bar ---------- */
function initHeroProgress() {
  const bar = document.getElementById("heroProgress");
  if (!bar) return;
  requestAnimationFrame(function () {
    setTimeout(function () { bar.style.width = "92%"; }, 300);
  });
}

/* ---------- Demo profile autofill ---------- */
function initDemoButton() {
  const demoBtn = document.getElementById("demoBtn");
  if (!demoBtn) return;

  demoBtn.addEventListener("click", function () {
    const values = {
      age: 28,
      gender: "Female",
      category: "SC",
      state: "Gujarat",
      income: 300000,
      business_type: "Tailoring",
      business_stage: "New Business",
    };

    Object.keys(values).forEach(function (name) {
      const el = document.querySelector('[name="' + name + '"]');
      if (el) {
        el.value = values[name];
        clearFieldError(el);
      }
    });

    // Funding uses the preset dropdown + hidden field, not a plain [name] input.
    const fundingSelect = document.getElementById("fundingSelect");
    const fundingCustom = document.getElementById("fundingCustom");
    const fundingHidden = document.getElementById("fundingRequiredHidden");
    if (fundingSelect && fundingHidden) {
      fundingSelect.value = "200000";
      fundingCustom.style.display = "none";
      fundingHidden.value = "200000";
      clearFieldError(fundingSelect);
    }
  });
}

/* ---------- Form validation + loading sequence ---------- */
function initFormValidation() {
  const form = document.getElementById("profileForm");
  if (!form) return;

  form.addEventListener("submit", function (event) {
    // Make sure the hidden funding_required field reflects the latest
    // dropdown/custom-amount state before we validate and submit.
    const fundingSelect = document.getElementById("fundingSelect");
    const fundingCustom = document.getElementById("fundingCustom");
    const fundingHidden = document.getElementById("fundingRequiredHidden");
    if (fundingSelect && fundingHidden) {
      fundingHidden.value = fundingSelect.value === "custom"
        ? (fundingCustom.value || "")
        : (fundingSelect.value || "");
    }

    const isValid = validateForm(form);
    if (!isValid) {
      event.preventDefault();
      return;
    }

    // Show polished loading state, then submit for real.
    event.preventDefault();
    runLoadingSequence(function () {
      form.submit();
    });
  });
}

function validateForm(form) {
  let valid = true;
  const requiredEls = form.querySelectorAll("[required]");

  requiredEls.forEach(function (el) {
    // The funding preset <select> is handled separately below.
    if (el.id === "fundingSelect") return;

    const fieldWrapper = el.closest(".field");
    const value = (el.value || "").trim();
    let fieldValid = value !== "";

    if (el.type === "number" && value !== "") {
      const num = Number(value);
      if (el.id === "age") {
        fieldValid = num >= 18 && num <= 100;
      } else {
        fieldValid = num >= 0;
      }
    }

    if (fieldWrapper) {
      if (fieldValid) {
        fieldWrapper.classList.remove("invalid");
      } else {
        fieldWrapper.classList.add("invalid");
        valid = false;
      }
    }
  });

  // Funding: either a preset was chosen, or a valid custom amount was entered.
  const fundingSelect = document.getElementById("fundingSelect");
  const fundingCustom = document.getElementById("fundingCustom");
  const fundingWrapper = fundingSelect ? fundingSelect.closest(".field") : null;
  if (fundingSelect && fundingWrapper) {
    let fundingValid = false;
    if (fundingSelect.value === "custom") {
      fundingValid = fundingCustom.value !== "" && Number(fundingCustom.value) >= 0;
    } else {
      fundingValid = fundingSelect.value !== "";
    }
    if (fundingValid) {
      fundingWrapper.classList.remove("invalid");
    } else {
      fundingWrapper.classList.add("invalid");
      valid = false;
    }
  }

  return valid;
}

function clearFieldError(el) {
  const fieldWrapper = el.closest(".field");
  if (fieldWrapper) fieldWrapper.classList.remove("invalid");
}

function runLoadingSequence(onDone) {
  const overlay = document.getElementById("loadingOverlay");
  const text = document.getElementById("loadingText");
  if (!overlay || !text) { onDone(); return; }

  const messages = [
    "Analyzing your entrepreneur profile…",
    "Matching available schemes…",
    "Preparing your recommendations…",
  ];

  overlay.classList.add("active");
  let step = 0;
  text.textContent = messages[step];

  const interval = setInterval(function () {
    step += 1;
    if (step < messages.length) {
      text.textContent = messages[step];
    } else {
      clearInterval(interval);
      onDone();
    }
  }, 420);
}

/* ---------- Results page: animate score bars ---------- */
function initScoreBars() {
  const bars = document.querySelectorAll(".score-bar");
  if (!bars.length) return;

  bars.forEach(function (bar, index) {
    const score = bar.getAttribute("data-score") || 0;
    setTimeout(function () {
      bar.style.width = score + "%";
    }, 150 + index * 120);
  });
}

/* ---------- Results page: scheme details modal ---------- */
function initSchemeModal() {
  const overlay = document.getElementById("modalOverlay");
  if (!overlay) return;

  const closeBtn = document.getElementById("modalClose");
  const titleEl = document.getElementById("modalTitle");
  const scoreEl = document.getElementById("modalScore");
  const descEl = document.getElementById("modalDescription");
  const reasonsEl = document.getElementById("modalReasons");
  const docsEl = document.getElementById("modalDocuments");
  const sourceEl = document.getElementById("modalSource");
  const applyLink = document.getElementById("modalApplyLink");

  document.querySelectorAll('[data-action="view-details"]').forEach(function (btn) {
    btn.addEventListener("click", function () {
      const card = btn.closest(".scheme-card");
      if (!card) return;
      const data = JSON.parse(card.getAttribute("data-scheme"));

      titleEl.textContent = data.scheme_name;
      scoreEl.textContent = data.match_score + "% Match · " + data.match_label;
      descEl.textContent = data.description;

      reasonsEl.innerHTML = "";
      (data.reasons || []).forEach(function (reason) {
        const li = document.createElement("li");
        li.className = "reason";
        li.textContent = reason;
        reasonsEl.appendChild(li);
      });

      docsEl.innerHTML = "";
      (data.documents || []).forEach(function (doc) {
        const li = document.createElement("li");
        li.className = "doc";
        li.textContent = doc;
        docsEl.appendChild(li);
      });

      const hasOfficialLink = data.official_source && data.official_source.indexOf("http") === 0;
      sourceEl.textContent = data.official_source || "Official source to be verified.";

      if (hasOfficialLink) {
        applyLink.href = data.official_source;
        applyLink.style.display = "inline-flex";
      } else {
        applyLink.removeAttribute("href");
        applyLink.style.display = "none";
      }

      overlay.classList.add("active");
      closeBtn.focus();
    });
  });

  function closeModal() {
    overlay.classList.remove("active");
  }

  closeBtn.addEventListener("click", closeModal);
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) closeModal();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeModal();
  });
}