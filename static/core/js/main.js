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

const mobileNavShell = document.querySelector("[data-mobile-nav-shell]");

if (mobileNavShell) {
  const mobileNavToggle = mobileNavShell.querySelector("[data-mobile-nav-toggle]");
  const mobileNav = mobileNavShell.querySelector(".nav");
  const mobileNavLinks = Array.from(mobileNavShell.querySelectorAll(".nav a"));
  const mobileNavBreakpoint = window.matchMedia("(max-width: 720px)");
  const mobileNavOpenLabel = mobileNavToggle?.dataset.labelOpen || "Open navigation menu";
  const mobileNavCloseLabel = mobileNavToggle?.dataset.labelClose || "Close navigation menu";

  const setMobileNavState = (isOpen) => {
    const open = Boolean(isOpen);
    mobileNavShell.classList.toggle("is-mobile-open", open);
    document.body.classList.toggle("site-menu-open", open);
    if (mobileNavToggle) {
      mobileNavToggle.setAttribute("aria-expanded", String(open));
      mobileNavToggle.setAttribute("aria-label", open ? mobileNavCloseLabel : mobileNavOpenLabel);
    }
  };

  const closeMobileNav = () => {
    setMobileNavState(false);
  };

  const syncMobileNavForViewport = () => {
    if (!mobileNavBreakpoint.matches) {
      closeMobileNav();
    }
  };

  mobileNavToggle?.addEventListener("click", () => {
    setMobileNavState(!mobileNavShell.classList.contains("is-mobile-open"));
  });

  mobileNavLinks.forEach((link) => {
    link.addEventListener("click", () => {
      closeMobileNav();
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && mobileNavShell.classList.contains("is-mobile-open")) {
      closeMobileNav();
    }
  });

  if (typeof mobileNavBreakpoint.addEventListener === "function") {
    mobileNavBreakpoint.addEventListener("change", syncMobileNavForViewport);
  } else if (typeof mobileNavBreakpoint.addListener === "function") {
    mobileNavBreakpoint.addListener(syncMobileNavForViewport);
  }

  syncMobileNavForViewport();
}

const siteAssistant = document.querySelector("[data-site-assistant]");

if (siteAssistant) {
  const toggle = siteAssistant.querySelector("[data-assistant-toggle]");
  const closeButton = siteAssistant.querySelector("[data-assistant-close]");
  const resetButton = siteAssistant.querySelector("[data-assistant-reset]");
  const panel = siteAssistant.querySelector("[data-assistant-panel]");
  const form = siteAssistant.querySelector("[data-assistant-form]");
  const input = siteAssistant.querySelector("[data-assistant-input]");
  const messages = siteAssistant.querySelector("[data-assistant-messages]");
  const csrfInput = siteAssistant.querySelector('input[name="csrfmiddlewaretoken"]');
  const templateLanguage = siteAssistant.dataset.assistantLanguage || "en";
  const getLanguageFromPath = () => {
    const normalizedPath = (window.location.pathname || "/").trim();
    const firstSegment = normalizedPath.replace(/^\/+/, "").split("/", 1)[0].toLowerCase();
    return ["en", "nl", "fr", "pt"].includes(firstSegment) ? firstSegment : "";
  };
  const language = getLanguageFromPath() || templateLanguage || "en";
  const siteKey = siteAssistant.dataset.assistantSiteKey || "getonlinefast-public";
  const assistantVersion = siteAssistant.dataset.assistantVersion || "v2";
  const assistantEndpoint = siteAssistant.dataset.assistantEndpoint || "/assistant/help/";
  const storageKey = `gof_public_assistant_${assistantVersion}_${siteKey}_${language}`;
  const legacyStorageKey = `gof-site-assistant-v1-${language}`;
  const urls = {
    websites: siteAssistant.dataset.urlWebsites || "/websites/",
    onlineShop: siteAssistant.dataset.urlOnlineShop || "/online-shop/",
    ads: siteAssistant.dataset.urlAds || "/ads/",
    pricing: siteAssistant.dataset.urlPricing || "/pricing/",
    faq: siteAssistant.dataset.urlFaq || "/faq/",
    contact: siteAssistant.dataset.urlContact || "/contact/",
    support: siteAssistant.dataset.urlSupport || "/support/",
    metaAds: siteAssistant.dataset.urlMetaAds || "/facebook-instagram-ads/",
    googleAds: siteAssistant.dataset.urlGoogleAds || "/google-ads/",
    linkedinAds: siteAssistant.dataset.urlLinkedinAds || "/linkedin-ads/",
  };
  const pageContextPaths = [
    ["meta_ads", urls.metaAds],
    ["google_ads", urls.googleAds],
    ["linkedin_ads", urls.linkedinAds],
    ["online_shop", urls.onlineShop],
    ["websites", urls.websites],
    ["ads", urls.ads],
    ["pricing", urls.pricing],
    ["faq", urls.faq],
    ["contact", urls.contact],
    ["support", urls.support],
  ];
  const restrictedTerms = [
    "sexual service",
    "escort",
    "adult service",
    "porn",
    "casino",
    "gambling",
    "weapon",
    "gun",
    "drugs",
    "cocaine",
    "fraud",
    "scam",
    "hate",
    "extremist",
    "seks",
    "escortservice",
    "wapen",
    "gokken",
    "drugs",
    "fraude",
    "haat",
    "extremisme",
  ];
  const copy = {
    en: {
      greeting: "Hello, welcome to Get Online Fast. How can I help you today?",
      shortGreeting: "Hi. What would you like help with today?",
      emojiGreeting: "?? Hi. What can I help you with?",
      openedPage: "I opened the {page} page. You can ask me questions about it here.",
      networkFallback: "Sorry, I could not load the answer just now. Please try again or use the contact page if the problem continues.",
      restricted: "Sorry, that type of project is not allowed on our platform. I can still help with general questions about websites, pricing, or allowed business services.",
      reset: "Reset",
    },
    nl: {
      greeting: "Hallo, welkom bij Get Online Fast. Hoe kan ik je vandaag helpen?",
      shortGreeting: "Hoi. Waarmee kan ik je vandaag helpen?",
      emojiGreeting: "?? Hoi. Waarmee kan ik je helpen?",
      openedPage: "Ik heb de pagina {page} geopend. Je kunt hier vragen over die pagina stellen.",
      networkFallback: "Sorry, ik kon het antwoord net niet laden. Probeer het opnieuw of gebruik de contactpagina als het probleem blijft bestaan.",
      restricted: "Sorry, dit type project is niet toegestaan op ons platform. Ik kan nog wel helpen met algemene vragen over websites, prijzen of toegestane bedrijfsdiensten.",
      reset: "Reset",
    },
    fr: {
      greeting: "Bonjour, bienvenue chez Get Online Fast. Comment puis-je vous aider aujourd'hui ?",
      shortGreeting: "Bonjour. Que voulez-vous savoir aujourd'hui ?",
      emojiGreeting: "?? Bonjour. Comment puis-je vous aider ?",
      openedPage: "J'ai ouvert la page {page}. Vous pouvez poser des questions sur cette page ici.",
      networkFallback: "Désolé, je n'ai pas pu charger la réponse pour le moment. Réessayez ou utilisez la page de contact si le problème continue.",
      restricted: "Désolé, ce type de projet n'est pas autorisé sur notre plateforme. Je peux quand même aider avec des questions générales sur les sites web, les tarifs ou les services autorisés.",
      reset: "Réinitialiser",
    },
    pt: {
      greeting: "Olá, bem-vindo ao Get Online Fast. Como posso ajudar hoje?",
      shortGreeting: "Olá. Em que posso ajudar hoje?",
      emojiGreeting: "?? Olá. Como posso ajudar?",
      openedPage: "Abri a página {page}. Pode fazer perguntas sobre essa página aqui.",
      networkFallback: "Desculpe, não consegui carregar a resposta agora. Tente novamente ou use a página de contacto se o problema continuar.",
      restricted: "Desculpe, esse tipo de projeto não é permitido na nossa plataforma. Ainda posso ajudar com perguntas gerais sobre websites, preços ou serviços permitidos.",
      reset: "Limpar",
    },
  }[language] || {
    greeting: "Hello, welcome to Get Online Fast. How can I help you today?",
    shortGreeting: "Hi. What would you like help with today?",
    emojiGreeting: "?? Hi. What can I help you with?",
    openedPage: "I opened the {page} page. You can ask me questions about it here.",
    networkFallback: "Sorry, I could not load the answer just now. Please try again or use the contact page if the problem continues.",
    restricted: "Sorry, that type of project is not allowed on our platform. I can still help with general questions about websites, pricing, or allowed business services.",
    reset: "Reset",
  };
  const assistantOpenTriggers = Array.from(document.querySelectorAll("[data-open-site-assistant]"));

  const emptyState = () => ({
    isOpen: false,
    pageContext: "",
    messages: [],
    pendingNavigation: null,
  });

  const pathNameFor = (rawUrl) => {
    try {
      return new URL(rawUrl, window.location.origin).pathname;
    } catch (error) {
      return rawUrl || "/";
    }
  };

  const getCurrentPageContext = () => {
    const currentPath = window.location.pathname;
    for (const [key, url] of pageContextPaths) {
      if (currentPath === pathNameFor(url)) {
        return key;
      }
    }
    return "general";
  };

  if (window.localStorage.getItem(legacyStorageKey)) {
    window.localStorage.removeItem(legacyStorageKey);
  }

  const loadState = () => {
    try {
      const parsed = JSON.parse(window.localStorage.getItem(storageKey) || "{}");
      return { ...emptyState(), ...parsed };
    } catch (error) {
      return emptyState();
    }
  };

  const state = loadState();
  state.pageContext = getCurrentPageContext();

  const saveState = () => {
    state.pageContext = getCurrentPageContext();
    window.localStorage.setItem(
      storageKey,
      JSON.stringify({
        isOpen: Boolean(state.isOpen),
        pageContext: state.pageContext || "general",
        messages: Array.isArray(state.messages) ? state.messages.slice(-24) : [],
        pendingNavigation: state.pendingNavigation || null,
      }),
    );
  };

  const renderMessages = () => {
    if (!messages) {
      return;
    }
    messages.innerHTML = "";

    state.messages.forEach((message) => {
      const node = document.createElement("article");
      node.className = `site-assistant-message site-assistant-message--${message.role}`;

      const textNode = document.createElement("p");
      textNode.className = "site-assistant-message__text";
      textNode.textContent = message.text;
      node.appendChild(textNode);

      if (message.role === "assistant" && Array.isArray(message.actions) && message.actions.length) {
        const actionsNode = document.createElement("div");
        actionsNode.className = "site-assistant-message__actions";

        message.actions.forEach((action) => {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "site-assistant-action";
          button.textContent = action.label;
          button.dataset.actionKind = action.kind;
          if (action.url) {
            button.dataset.actionUrl = action.url;
          }
          if (action.pageName) {
            button.dataset.actionPageName = action.pageName;
          }
          actionsNode.appendChild(button);
        });

        node.appendChild(actionsNode);
      }

      messages.appendChild(node);
    });

    messages.scrollTop = messages.scrollHeight;
  };

  const addMessage = (role, text, actions = []) => {
    state.messages.push({ role, text, actions });
    saveState();
    renderMessages();
  };

  const setOpen = (open) => {
    if (!panel) {
      return;
    }
    state.isOpen = Boolean(open);
    panel.hidden = !state.isOpen;
    siteAssistant.classList.toggle("is-open", state.isOpen);
    saveState();
    if (state.isOpen) {
      input?.focus();
    }
  };

  const ensureGreeting = () => {
    if (!Array.isArray(state.messages) || !state.messages.length) {
      state.messages = [{ role: "assistant", text: copy.greeting, actions: [] }];
      saveState();
    }
  };

  const resetAssistantState = ({ keepOpen = true } = {}) => {
    state.isOpen = Boolean(keepOpen);
    state.pageContext = getCurrentPageContext();
    state.pendingNavigation = null;
    state.messages = [{ role: "assistant", text: copy.greeting, actions: [] }];
    saveState();
    renderMessages();
  };

  const isEmojiOnly = (message) => {
    const trimmed = (message || "").trim();
    if (!trimmed) {
      return false;
    }

    const withoutCommonEmoji = trimmed
      .replace(/[\u{1F300}-\u{1FAFF}]/gu, "")
      .replace(/[\u{2600}-\u{27BF}]/gu, "")
      .replace(/[\u{FE0F}\u{200D}]/gu, "")
      .replace(/[:;=8xX][\-~^]?[)(DPp]/g, "")
      .replace(/[)(DPp]/g, "")
      .trim();

    return withoutCommonEmoji === "";
  };

  const greetingReplyFor = (message) => {
    const normalized = (message || "")
      .toLowerCase()
      .replace(/[?!.,/\\]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    if (!normalized) {
      return "";
    }
    if (["bom dia", "boa tarde", "boa noite", "ola", "olá"].includes(normalized)) {
      return "Olá. Como posso ajudar hoje?";
    }
    if (["hoi", "hallo", "goedemorgen", "goedemiddag", "goedenavond"].includes(normalized)) {
      return "Hoi. Waarmee kan ik je vandaag helpen?";
    }
    if (["bonjour", "salut", "bonsoir"].includes(normalized)) {
      return "Bonjour. Comment puis-je vous aider aujourd’hui ?";
    }
    if (["hola", "buenos dias", "buenas tardes", "buenas noches"].includes(normalized)) {
      return "Hola. ¿Cómo puedo ayudarle hoy?";
    }
    if (["hallo", "guten morgen", "guten tag", "guten abend"].includes(normalized)) {
      return "Hallo. Wie kann ich Ihnen heute helfen?";
    }
    return ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"].includes(normalized)
      ? "Hi. What would you like help with today?"
      : "";
  };

  const mapSuggestedLinksToActions = (suggestedLinks) =>
    (Array.isArray(suggestedLinks) ? suggestedLinks : [])
      .filter((link) => link && link.url && link.label)
      .slice(0, 4)
      .map((link) => ({
        kind: "link",
        label: link.label,
        pageName: link.label,
        url: link.url,
      }));

  const readCookie = (name) => {
    const escapedName = name.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, "\\$&");
    const match = document.cookie.match(new RegExp(`(?:^|; )${escapedName}=([^;]*)`));
    return match ? decodeURIComponent(match[1]) : "";
  };

  const getCsrfToken = () => {
    const formToken = csrfInput?.value?.trim();
    if (formToken) {
      return formToken;
    }
    return readCookie("csrftoken");
  };

  const requestAssistantAnswer = async (question) => {
    const params = new URLSearchParams({
      message: question,
      q: question,
      lang: language,
      page_path: window.location.pathname,
    });
    const csrfToken = getCsrfToken();
    const response = await window.fetch(assistantEndpoint, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      },
      body: params.toString(),
    });
    if (!response.ok) {
      throw new Error(`assistant_http_${response.status}`);
    }
    return response.json();
  };

  const submitAssistantQuestion = async (question) => {
    const trimmedQuestion = (question || "").trim();
    if (!trimmedQuestion) {
      return;
    }
    addMessage("user", trimmedQuestion);
    if (input) {
      input.value = "";
    }

    if (isEmojiOnly(trimmedQuestion)) {
      addMessage("assistant", copy.emojiGreeting, []);
      return;
    }
    const greetingReply = greetingReplyFor(trimmedQuestion);
    if (greetingReply) {
      addMessage("assistant", greetingReply, []);
      return;
    }
    if (restrictedTerms.some((term) => trimmedQuestion.toLowerCase().includes(term))) {
      addMessage("assistant", copy.restricted, []);
      return;
    }

    try {
      const payload = await requestAssistantAnswer(trimmedQuestion);
      if (payload && typeof payload.answer === "string" && payload.answer.trim()) {
        addMessage("assistant", payload.answer.trim(), mapSuggestedLinksToActions(payload?.suggested_links));
        return;
      }
      throw new Error("assistant_missing_answer");
    } catch (error) {
      addMessage("assistant", copy.networkFallback, []);
    }
  };

  const navigateFromAssistant = (url, pageName) => {
    state.pendingNavigation = { url, pageName };
    state.isOpen = true;
    saveState();
    window.location.href = url;
  };

  ensureGreeting();
  if (state.pendingNavigation && pathNameFor(state.pendingNavigation.url) === window.location.pathname) {
    const expected = copy.openedPage.replace("{page}", state.pendingNavigation.pageName);
    const lastMessage = state.messages[state.messages.length - 1];
    if (!lastMessage || lastMessage.text !== expected) {
      state.messages.push({ role: "assistant", text: expected, actions: [] });
    }
    state.pendingNavigation = null;
    saveState();
  }
  renderMessages();
  setOpen(state.isOpen);

  toggle?.addEventListener("click", () => {
    setOpen(panel?.hidden);
  });

  assistantOpenTriggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      ensureGreeting();
      renderMessages();
      setOpen(true);
    });
  });

  closeButton?.addEventListener("click", () => {
    setOpen(false);
  });

  resetButton?.addEventListener("click", () => {
    resetAssistantState();
    setOpen(true);
  });

  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!input) {
      return;
    }
    setOpen(true);
    void submitAssistantQuestion(input.value);
  });

  messages?.addEventListener("click", (event) => {
    const button = event.target.closest(".site-assistant-action");
    if (!button) {
      return;
    }

    const actionKind = button.dataset.actionKind;
    const actionUrl = button.dataset.actionUrl || "";
    const actionPageName = button.dataset.actionPageName || "";

    if (actionKind === "link" && actionUrl) {
      navigateFromAssistant(actionUrl, actionPageName || button.textContent || "");
    }
  });
}

const backToTopButton = document.querySelector("[data-back-to-top]");

if (backToTopButton) {
  const toggleBackToTop = () => {
    const shouldShow = window.scrollY > 360;
    backToTopButton.hidden = !shouldShow;
    backToTopButton.classList.toggle("is-visible", shouldShow);
  };

  backToTopButton.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  window.addEventListener("scroll", toggleBackToTop, { passive: true });
  toggleBackToTop();
}
