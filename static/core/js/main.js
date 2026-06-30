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

const bindOnboardingPreview = (previewLayout) => {
  if (!previewLayout) {
    return null;
  }

  const onboardingForm = previewLayout.querySelector(".onboarding-form");
  if (!onboardingForm) {
    return null;
  }

  const status = previewLayout.querySelector("[data-modal-preview-status]");
  const defaultSlug = previewLayout.dataset.defaultSlug || "";
  const pickField = (...selectors) =>
    selectors
      .map((selector) => onboardingForm.querySelector(selector))
      .find(Boolean) || null;
  const fields = {
    name: pickField("#id_business_name"),
    type: pickField("#id_service_type", "#id_business_type"),
    city: pickField("#id_city", "#id_service_area", "#id_business_address"),
    text: pickField("#id_short_description", "#id_main_services", "#id_business_description"),
  };
  const templateChoices = Array.from(
    onboardingForm.querySelectorAll('input[name="template_slug"][data-template-choice]')
  );

  const targets = {
    url: previewLayout.querySelector("[data-modal-preview-url]"),
    name: previewLayout.querySelector("[data-modal-preview-business-name]"),
    city: previewLayout.querySelector("[data-modal-preview-location]"),
    title: previewLayout.querySelector("[data-modal-preview-title]"),
    text: previewLayout.querySelector("[data-modal-preview-description]"),
    type: previewLayout.querySelector("[data-modal-preview-business-type]"),
    serviceLine: previewLayout.querySelector("[data-modal-preview-service-line]"),
    templateLabel: previewLayout.querySelector("[data-modal-preview-template-label]"),
    templatePreview: previewLayout.querySelector("[data-template-preview]"),
  };

  const previewTemplateClasses = [
    "template-classic-service",
    "template-visual-hero",
    "template-card-grid",
  ];

  const getValues = () => ({
    name: fields.name?.value.trim() || previewLayout.dataset.defaultName || "",
    type: fields.type?.value.trim() || previewLayout.dataset.defaultType || "",
    city: fields.city?.value.trim() || previewLayout.dataset.defaultCity || "",
    text:
      fields.text?.value.trim() ||
      previewLayout.dataset.previewText ||
      previewLayout.dataset.defaultText ||
      "",
    template:
      templateChoices.find((choice) => choice.checked)?.value ||
      previewLayout.dataset.template ||
      "classic_service",
    templateLabel:
      templateChoices.find((choice) => choice.checked)?.dataset.templateLabel ||
      previewLayout.dataset.defaultTemplateLabel ||
      "",
  });

  const updatePreview = () => {
    const values = getValues();
    const slug = slugifyBusinessName(values.name, defaultSlug);

    if (targets.url) {
      targets.url.textContent = `${slug}.getonlinefast.eu`;
    }
    if (targets.name) targets.name.textContent = values.name;
    if (targets.city) targets.city.textContent = values.city;
    if (targets.title) {
      const titleTemplate = previewLayout.dataset.titleTemplate || "";
      targets.title.textContent = formatPreviewTemplate(titleTemplate, {
        type: values.type.toLowerCase(),
        city: values.city,
      });
    }
    if (targets.text) targets.text.textContent = values.text;
    if (targets.type) targets.type.textContent = values.type;
    if (targets.serviceLine) {
      const serviceLineTemplate = previewLayout.dataset.serviceLineTemplate || "";
      targets.serviceLine.textContent = formatPreviewTemplate(serviceLineTemplate, {
        type: values.type,
        city: values.city,
      });
    }

    if (targets.templateLabel && values.templateLabel) {
      targets.templateLabel.textContent = values.templateLabel;
    }
    if (targets.templatePreview) {
      previewTemplateClasses.forEach((className) => {
        targets.templatePreview.classList.remove(className);
      });
      targets.templatePreview.dataset.templatePreview = values.template;
      targets.templatePreview.classList.add(`template-${values.template.replace(/_/g, "-")}`);
    }

    saveStoredPreview(values);

    if (status) {
      status.classList.remove("is-saved");
    }
  };

  const applyStoredPreview = () => {
    const storedPreview = readStoredPreview();

    if (storedPreview.name && fields.name) fields.name.value = storedPreview.name;
    if (storedPreview.type && fields.type) fields.type.value = storedPreview.type;
    if (storedPreview.city && fields.city) fields.city.value = storedPreview.city;
    if (storedPreview.text && fields.text) fields.text.value = storedPreview.text;
    if (storedPreview.template && templateChoices.length) {
      const matchingChoice = templateChoices.find((choice) => choice.value === storedPreview.template);
      if (matchingChoice) {
        matchingChoice.checked = true;
      }
    }
  };

  Object.values(fields)
    .filter(Boolean)
    .forEach((field) => {
      field.addEventListener("input", updatePreview);
      field.addEventListener("change", updatePreview);
    });

  templateChoices.forEach((choice) => {
    choice.addEventListener("change", updatePreview);
  });

  onboardingForm.addEventListener("submit", () => {
    saveStoredPreview(getValues());

    if (status) {
      status.textContent = status.dataset.savedMessage || status.textContent;
      status.classList.add("is-saved");
    }
  });

  applyStoredPreview();
  updatePreview();

  return {
    form: onboardingForm,
    fields,
    previewLayout,
    updatePreview,
  };
};

if (modal) {
  const openTriggers = document.querySelectorAll('[data-modal-open="onboarding-modal"]');
  const closeTriggers = modal.querySelectorAll("[data-modal-close]");
  const modalPreviewLayout = modal.querySelector(".modal-preview-layout");
  const modalPreview = bindOnboardingPreview(modalPreviewLayout);

  const openModal = () => {
    modalPreview?.updatePreview();
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  };

  const syncPreviewToOnboarding = () => {
    const mappings = [
      ["bizName", "name"],
      ["bizType", "type"],
      ["bizCity", "city"],
      ["bizText", "text"],
    ];

    mappings.forEach(([previewId, fieldKey]) => {
      const previewField = document.getElementById(previewId);
      const formField = modalPreview?.fields?.[fieldKey];

      if (previewField && formField) {
        formField.value = previewField.value;
      }
    });

    const previewTextField = document.getElementById("bizText");
    if (modalPreviewLayout && previewTextField) {
      modalPreviewLayout.dataset.previewText = previewTextField.value.trim();
    }

    const previewTemplateChoices = Array.from(
      document.querySelectorAll('#start input[name="template_slug_preview"][data-template-choice]')
    );
    const modalTemplateChoices = Array.from(
      modal.querySelectorAll('input[name="template_slug"][data-template-choice]')
    );
    const selectedPreviewTemplate = previewTemplateChoices.find((choice) => choice.checked)?.value;
    if (selectedPreviewTemplate && modalTemplateChoices.length) {
      const matchingModalChoice = modalTemplateChoices.find((choice) => choice.value === selectedPreviewTemplate);
      if (matchingModalChoice) {
        matchingModalChoice.checked = true;
      }
    }

    modalPreview?.updatePreview();
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

}

const startBuilderPreviewLayout = document.querySelector("[data-onboarding-preview-page]");

if (startBuilderPreviewLayout) {
  bindOnboardingPreview(startBuilderPreviewLayout);
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

const siteAssistant = document.querySelector("[data-site-assistant]");

if (siteAssistant) {
  const toggle = siteAssistant.querySelector("[data-assistant-toggle]");
  const closeButton = siteAssistant.querySelector("[data-assistant-close]");
  const panel = siteAssistant.querySelector("[data-assistant-panel]");
  const form = siteAssistant.querySelector("[data-assistant-form]");
  const input = siteAssistant.querySelector("[data-assistant-input]");
  const messages = siteAssistant.querySelector("[data-assistant-messages]");
  const suggestionButtons = Array.from(siteAssistant.querySelectorAll("[data-assistant-suggestion]"));
  const endpoint = siteAssistant.dataset.assistantEndpoint || "";
  const language = siteAssistant.dataset.assistantLanguage || "en";

  const labels = {
    en: {
      loading: "Checking that for you...",
      error: "I could not load an answer right now. Please use the contact or support page.",
    },
    nl: {
      loading: "Ik kijk het even voor je na...",
      error: "Ik kon nu geen antwoord laden. Gebruik dan de contact- of supportpagina.",
    },
  };

  const copy = labels[language] || labels.en;

  const appendMessage = (text, type, links = []) => {
    if (!messages) return null;

    const node = document.createElement("article");
    node.className = `site-assistant-message site-assistant-message--${type}`;

    const textNode = document.createElement("p");
    textNode.className = "site-assistant-message__text";
    textNode.textContent = text;
    node.appendChild(textNode);

    if (type === "assistant" && Array.isArray(links) && links.length) {
      const linksNode = document.createElement("div");
      linksNode.className = "site-assistant-message__links";

      links.forEach((link) => {
        if (!link?.url || !link?.label) {
          return;
        }

        const anchor = document.createElement("a");
        anchor.href = link.url;
        anchor.textContent = link.label;
        linksNode.appendChild(anchor);
      });

      if (linksNode.childElementCount) {
        node.appendChild(linksNode);
      }
    }

    messages.appendChild(node);
    messages.scrollTop = messages.scrollHeight;
    return node;
  };

  const requestAssistantAnswer = async (question) => {
    if (!endpoint) {
      throw new Error("Assistant endpoint missing");
    }

    const url = new URL(endpoint, window.location.origin);
    url.searchParams.set("q", question);
    url.searchParams.set("lang", language);

    const response = await fetch(url.toString(), {
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new Error(`Assistant request failed: ${response.status}`);
    }

    return response.json();
  };

  const submitAssistantQuestion = async (question) => {
    const trimmedQuestion = (question || "").trim();
    if (!trimmedQuestion) {
      return;
    }

    appendMessage(trimmedQuestion, "user");
    if (input) {
      input.value = "";
    }

    const loadingNode = appendMessage(copy.loading, "assistant");

    try {
      const payload = await requestAssistantAnswer(trimmedQuestion);
      const replacementNode = appendMessage(payload.answer || copy.error, "assistant", payload.suggested_links || []);
      loadingNode?.remove();
      messages?.scrollTo({ top: messages.scrollHeight, behavior: "smooth" });
      return replacementNode;
    } catch (error) {
      if (loadingNode) {
        const textNode = loadingNode.querySelector(".site-assistant-message__text");
        if (textNode) {
          textNode.textContent = copy.error;
        }
      }
      return null;
    }
  };

  const setOpen = (open) => {
    if (!panel) return;
    panel.hidden = !open;
    siteAssistant.classList.toggle("is-open", open);
    if (open) {
      input?.focus();
    }
  };

  toggle?.addEventListener("click", () => {
    setOpen(panel?.hidden);
  });

  closeButton?.addEventListener("click", () => {
    setOpen(false);
  });

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!endpoint || !input) return;

    await submitAssistantQuestion(input.value);
  });

  suggestionButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const question = button.dataset.assistantSuggestion || button.textContent || "";
      setOpen(true);
      if (input) {
        input.value = question;
      }
      await submitAssistantQuestion(question);
    });
  });
}
