const previewShell = document.getElementById("start");
const modal = document.getElementById("onboarding-modal");
const publicPreviewStorageKey = "getonlinefast_public_preview_v1";

const formatPreviewTemplate = (template, values) => {
  let formatted = template || "";

  Object.entries(values).forEach(([key, value]) => {
    formatted = formatted.replaceAll(`%(${key})s`, value ?? "");
  });

  return formatted;
};

const slugifyBusinessName = (value, fallbackValue = "") => {
  const normalized = (value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/[\s_-]+/g, "-")
    .replace(/^-+|-+$/g, "");

  return normalized || fallbackValue;
};

const readStoredPreview = (storageKey = publicPreviewStorageKey) => {
  try {
    return JSON.parse(localStorage.getItem(storageKey)) || {};
  } catch (error) {
    return {};
  }
};

const saveStoredPreview = (values, storageKey = publicPreviewStorageKey) => {
  try {
    localStorage.setItem(storageKey, JSON.stringify(values));
  } catch (error) {
    // Storage is optional for the public preview.
  }
};

if (modal) {
  const openTriggers = document.querySelectorAll('[data-modal-open="onboarding-modal"]');
  const closeTriggers = modal.querySelectorAll("[data-modal-close]");
  const onboardingForm = modal.querySelector(".onboarding-form");
  const modalPreviewLayout = modal.querySelector(".modal-preview-layout");
  const modalStatus = modal.querySelector("[data-modal-preview-status]");
  const modalDefaultSlug = modalPreviewLayout?.dataset.defaultSlug || "";

  const modalFields = {
    name: document.getElementById("id_business_name"),
    type: document.getElementById("id_service_type"),
    city: document.getElementById("id_city"),
    text: document.getElementById("id_short_description"),
  };

  const modalPreviewTargets = {
    url: modal.querySelector("[data-modal-preview-url]"),
    name: modal.querySelector("[data-modal-preview-business-name]"),
    city: modal.querySelector("[data-modal-preview-location]"),
    title: modal.querySelector("[data-modal-preview-title]"),
    text: modal.querySelector("[data-modal-preview-description]"),
    type: modal.querySelector("[data-modal-preview-business-type]"),
    serviceLine: modal.querySelector("[data-modal-preview-service-line]"),
  };

  const getModalPreviewValues = () => ({
    name: modalFields.name?.value.trim() || modalPreviewLayout?.dataset.defaultName || "",
    type: modalFields.type?.value.trim() || modalPreviewLayout?.dataset.defaultType || "",
    city: modalFields.city?.value.trim() || modalPreviewLayout?.dataset.defaultCity || "",
    text:
      modalFields.text?.value.trim() ||
      modalPreviewLayout?.dataset.previewText ||
      modalPreviewLayout?.dataset.defaultText ||
      "",
    template: "jcw_professional",
  });

  const updateModalPreview = () => {
    const values = getModalPreviewValues();
    const slug = slugifyBusinessName(values.name, modalDefaultSlug);

    if (modalPreviewTargets.url) {
      modalPreviewTargets.url.textContent = `${slug}.getonlinefast.eu`;
    }
    if (modalPreviewTargets.name) modalPreviewTargets.name.textContent = values.name;
    if (modalPreviewTargets.city) modalPreviewTargets.city.textContent = values.city;
    if (modalPreviewTargets.title) {
      const titleTemplate = modalPreviewLayout?.dataset.titleTemplate || "";
      modalPreviewTargets.title.textContent = formatPreviewTemplate(titleTemplate, {
        type: values.type.toLowerCase(),
        city: values.city,
      });
    }
    if (modalPreviewTargets.text) modalPreviewTargets.text.textContent = values.text;
    if (modalPreviewTargets.type) modalPreviewTargets.type.textContent = values.type;
    if (modalPreviewTargets.serviceLine) {
      const serviceLineTemplate = modalPreviewLayout?.dataset.serviceLineTemplate || "";
      modalPreviewTargets.serviceLine.textContent = formatPreviewTemplate(serviceLineTemplate, {
        type: values.type,
        city: values.city,
      });
    }

    saveStoredPreview(values);

    if (modalStatus) {
      modalStatus.classList.remove("is-saved");
    }
  };

  const applyStoredPreviewToModal = () => {
    const storedPreview = readStoredPreview();

    if (storedPreview.name && modalFields.name) modalFields.name.value = storedPreview.name;
    if (storedPreview.type && modalFields.type) modalFields.type.value = storedPreview.type;
    if (storedPreview.city && modalFields.city) modalFields.city.value = storedPreview.city;
  };

  const openModal = () => {
    updateModalPreview();
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  };

  const syncPreviewToOnboarding = () => {
    const mappings = [
      ["bizName", "id_business_name"],
      ["bizType", "id_service_type"],
      ["bizCity", "id_city"],
      ["bizText", "id_short_description"],
    ];

    mappings.forEach(([previewId, formId]) => {
      const previewField = document.getElementById(previewId);
      const formField = document.getElementById(formId);

      if (previewField && formField) {
        formField.value = previewField.value;
      }
    });

    const previewTextField = document.getElementById("bizText");
    if (modalPreviewLayout && previewTextField) {
      modalPreviewLayout.dataset.previewText = previewTextField.value.trim();
    }

    updateModalPreview();
  };

  const closeModal = () => {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  };

  openTriggers.forEach((trigger) => {
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      syncPreviewToOnboarding();
      openModal();
    });
  });

  closeTriggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      closeModal();
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal.classList.contains("is-open")) {
      closeModal();
    }
  });

  if (onboardingForm) {
    Object.values(modalFields)
      .filter(Boolean)
      .forEach((field) => {
        field.addEventListener("input", updateModalPreview);
        field.addEventListener("change", updateModalPreview);
      });

    onboardingForm.addEventListener("submit", () => {
      saveStoredPreview(getModalPreviewValues());

      if (modalStatus) {
        modalStatus.textContent = modalStatus.dataset.savedMessage || modalStatus.textContent;
        modalStatus.classList.add("is-saved");
      }
    });

    applyStoredPreviewToModal();
    updateModalPreview();
  }
}

if (previewShell) {
  const bizName = document.getElementById("bizName");
  const bizType = document.getElementById("bizType");
  const bizCity = document.getElementById("bizCity");
  const bizText = document.getElementById("bizText");
  const templateChoice = document.getElementById("templateChoice");

  const previewUrl = document.getElementById("previewUrl");
  const previewBrand = document.getElementById("previewBrand");
  const previewCity = document.getElementById("previewCity");
  const previewTitle = document.getElementById("previewTitle");
  const previewText = document.getElementById("previewText");
  const previewTemplateLabel = document.getElementById("previewTemplateLabel");

  const defaultName = previewShell.dataset.defaultName || "";
  const defaultType = previewShell.dataset.defaultType || "";
  const defaultCity = previewShell.dataset.defaultCity || "";
  const defaultText = previewShell.dataset.defaultText || "";
  const defaultSlug = previewShell.dataset.defaultSlug || "";
  const titleTemplate = previewShell.dataset.titleTemplate || previewTitle.textContent || "";
  const storageKey = previewShell.dataset.storageKey || publicPreviewStorageKey;
  const defaultTemplateLabel = previewShell.dataset.defaultTemplateLabel || "";

  const templatePresets = {
    jcw_professional: {
      label: templateChoice?.options[0]?.textContent || defaultTemplateLabel,
    },
  };

  const previewFields = [bizName, bizType, bizCity, bizText, templateChoice].filter(Boolean);

  const applyStoredPreview = () => {
    const storedPreview = readStoredPreview(storageKey);

    if (storedPreview.name && bizName) bizName.value = storedPreview.name;
    if (storedPreview.type && bizType) bizType.value = storedPreview.type;
    if (storedPreview.city && bizCity) bizCity.value = storedPreview.city;
    if (storedPreview.text && bizText) bizText.value = storedPreview.text;
    if (storedPreview.template && templateChoice) templateChoice.value = storedPreview.template;
  };

  const updatePreview = () => {
    const name = bizName.value.trim() || defaultName;
    const type = bizType.value.trim() || defaultType;
    const city = bizCity.value.trim() || defaultCity;
    const text = bizText?.value.trim() || defaultText;
    const template = templateChoice?.value || previewShell.dataset.template || "jcw_professional";
    const templatePreset = templatePresets[template] || templatePresets.jcw_professional;
    const slug = slugifyBusinessName(name, defaultSlug);

    if (previewUrl) {
      previewUrl.textContent = `${slug}.getonlinefast.eu`;
    }

    previewShell.dataset.template = template;
    previewBrand.textContent = name;
    previewCity.textContent = city;
    previewTitle.textContent = formatPreviewTemplate(titleTemplate, {
      type: type.toLowerCase(),
      city,
    });
    previewText.textContent = text;

    if (previewTemplateLabel && templatePreset) {
      previewTemplateLabel.textContent = templatePreset.label;
    }

    // TODO: Add simple preview suggestions using 2-3 fields:
    // - Business name
    // - Business type/service
    // - City
    // Suggested output:
    // - suggested headline
    // - suggested short description
    // - suggested CTA text

    saveStoredPreview({
      name: bizName.value,
      type: bizType.value,
      city: bizCity.value,
      text,
      template,
    }, storageKey);
  };

  previewFields.forEach((element) => {
    element.addEventListener("input", updatePreview);
    element.addEventListener("change", updatePreview);
  });

  applyStoredPreview();
  updatePreview();
}

const heroSlider = document.querySelector("[data-hero-slider]");

if (heroSlider) {
  const slides = Array.from(heroSlider.querySelectorAll("[data-hero-slide]"));
  const dots = Array.from(heroSlider.querySelectorAll("[data-hero-dot]"));
  const prevButton = heroSlider.querySelector("[data-hero-prev]");
  const nextButton = heroSlider.querySelector("[data-hero-next]");
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const intervalMs = Number(heroSlider.dataset.sliderInterval || 5500);
  let activeIndex = slides.findIndex((slide) => slide.classList.contains("is-active"));
  let timerId = null;
  let isPaused = false;

  if (activeIndex < 0) {
    activeIndex = 0;
  }

  const renderSlide = (index) => {
    slides.forEach((slide, slideIndex) => {
      const isActive = slideIndex === index;
      slide.classList.toggle("is-active", isActive);
      slide.setAttribute("aria-hidden", String(!isActive));
    });

    dots.forEach((dot, dotIndex) => {
      const isActive = dotIndex === index;
      dot.classList.toggle("is-active", isActive);
      dot.setAttribute("aria-selected", String(isActive));
      dot.tabIndex = isActive ? 0 : -1;
    });

    activeIndex = index;
  };

  const stopAutoSlide = () => {
    if (timerId) {
      window.clearInterval(timerId);
      timerId = null;
    }
  };

  const startAutoSlide = () => {
    stopAutoSlide();

    if (prefersReducedMotion.matches || isPaused || slides.length < 2) {
      return;
    }

    timerId = window.setInterval(() => {
      renderSlide((activeIndex + 1) % slides.length);
    }, intervalMs);
  };

  const setPausedState = (paused) => {
    isPaused = paused;

    if (paused) {
      stopAutoSlide();
    } else {
      startAutoSlide();
    }
  };

  const showRelativeSlide = (step) => {
    renderSlide((activeIndex + step + slides.length) % slides.length);
    startAutoSlide();
  };

  dots.forEach((dot, index) => {
    dot.addEventListener("click", () => {
      renderSlide(index);
      startAutoSlide();
    });
  });

  prevButton?.addEventListener("click", () => {
    showRelativeSlide(-1);
  });

  nextButton?.addEventListener("click", () => {
    showRelativeSlide(1);
  });

  heroSlider.addEventListener("mouseenter", () => setPausedState(true));
  heroSlider.addEventListener("mouseleave", () => setPausedState(false));
  heroSlider.addEventListener("focusin", () => setPausedState(true));
  heroSlider.addEventListener("focusout", (event) => {
    if (!heroSlider.contains(event.relatedTarget)) {
      setPausedState(false);
    }
  });

  if (typeof prefersReducedMotion.addEventListener === "function") {
    prefersReducedMotion.addEventListener("change", startAutoSlide);
  } else if (typeof prefersReducedMotion.addListener === "function") {
    prefersReducedMotion.addListener(startAutoSlide);
  }

  renderSlide(activeIndex);
  startAutoSlide();
}
