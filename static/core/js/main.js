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
  const language = siteAssistant.dataset.assistantLanguage || "en";
  const storageKey = `gof-site-assistant-v1-${language}`;
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
      emojiGreeting: "🙂 Hi. What can I help you with?",
      openedPage: "I opened the {page} page. You can ask me questions about it here.",
      fallback: "I’m not sure yet. Are you asking about a website, an online shop, ads, pricing, or support?",
      restricted: "Sorry, that type of project is not allowed on our platform. I can still help with general questions about websites, pricing, or allowed business services.",
      websiteQuestion: "Sure. What kind of business is the website for?",
      websiteRecommendation: "For that type of business, a clear business website with services, contact options, and local information is usually a good start.",
      websiteNextQuestion: "Do you already have a website, or are you starting from zero?",
      websiteStartingZeroAnswer: "Starting from zero is usually the easiest path. We can begin with the basics and improve later.",
      websiteReplaceOldAnswer: "Replacing an old website is often a good moment to simplify the content and improve contact options.",
      websiteNotSureAnswer: "That is fine. A simple business website is usually the best first step.",
      shopIntro: "An online shop can work well if you have products, prices, images, and payment/contact details ready.",
      shopQuestion: "Are you starting with a few products or a larger catalog?",
      shopFewProductsAnswer: "A smaller product setup is usually the easiest way to start. You can expand the catalog later.",
      shopLargerCatalogAnswer: "A larger catalog usually needs more structure for categories, product details, and navigation.",
      shopNotSureAnswer: "No problem. Starting smaller is usually safer if you are still deciding.",
      adsIntro: "Ads can help a new website get visitors faster. The cost usually has two parts: setup/service fee and advertising budget.",
      adsQuestion: "Which platform are you thinking about?",
      adsNotSureAnswer: "That is normal. Facebook & Instagram, Google Ads, and LinkedIn Ads each fit different business types.",
      pricingQuestion: "That depends on what you need. Are you asking about a website, an online shop, ads, or support?",
      pricingWebsiteAnswer: "Website pricing depends on the type of site and how much content you need.",
      pricingOnlineShopAnswer: "Online shop pricing depends on product count, structure, and how much setup is needed.",
      pricingAdsAnswer: "Ads pricing usually includes a setup/service fee plus the ad budget.",
      pricingSupportAnswer: "Support pricing depends on the type of help or changes you need.",
      supportQuestion: "Is this for an existing Get Online Fast project?",
      supportExistingAnswer: "For an existing project, support is the right next step.",
      supportNewAnswer: "No problem. Ask your new question and I will point you in the right direction.",
      contactAnswer: "You can contact Get Online Fast through the contact page. I can open it for you.",
      adviceAnswer: "No problem. Start simple. I can point you to websites, online shops, ads, or support.",
      pageOnlineShop: "Yes. For an online shop, starting small is usually best. You can begin with a small product catalog and expand later.",
      pageWebsites: "Yes. A simple business website is usually the best first step. Start with your services, location, and contact details.",
      pageAds: "A small local ads campaign can be enough to start. The best option depends on your business and service area.",
      pagePricing: "Pricing depends on whether you need a website, an online shop, ads, or support.",
      pageContact: "If it is urgent, the contact page is the fastest next step.",
      pageFaq: "The FAQ covers common setup, pricing, and support questions.",
      websiteBusinessPrompt: "What kind of business is it?",
      sendLabel: "Send",
      buttons: {
        website: "Website",
        onlineShop: "Online Shop",
        ads: "Ads",
        support: "Support",
        notSure: "Not sure",
        pricing: "Pricing",
        faq: "FAQ",
        contact: "Contact",
        metaAds: "Facebook & Instagram",
        googleAds: "Google Ads",
        linkedinAds: "LinkedIn Ads",
        fewProducts: "Few products",
        largerCatalog: "Larger catalog",
        notSureYet: "Not sure yet",
        openOnlineShopPage: "Open Online Shop page",
        openAdsPage: "Open Ads page",
        openPricingPage: "Open Pricing page",
        openContactPage: "Open Contact page",
        contactSupport: "Contact support",
        askAnotherQuestion: "Ask another question",
        startingFromZero: "Starting from zero",
        replaceOldWebsite: "Replace old website",
        existingProjectYes: "Yes, existing project",
        newQuestionNo: "No, new question",
      },
      pageNames: {
        websites: "Websites",
        onlineShop: "Online Shop",
        ads: "Ads",
        pricing: "Pricing",
        faq: "FAQ",
        contact: "Contact",
        support: "Support",
        metaAds: "Facebook & Instagram Ads",
        googleAds: "Google Ads",
        linkedinAds: "LinkedIn Ads",
      },
    },
    nl: {
      greeting: "Hallo, welkom bij Get Online Fast. Hoe kan ik je vandaag helpen?",
      shortGreeting: "Hoi. Waarmee kan ik je vandaag helpen?",
      emojiGreeting: "🙂 Hoi. Waarmee kan ik je helpen?",
      openedPage: "Ik heb de pagina {page} geopend. Je kunt hier vragen over die pagina stellen.",
      fallback: "Ik weet het nog niet zeker. Gaat het over een website, een webshop, advertenties, prijzen of support?",
      restricted: "Sorry, dit type project is niet toegestaan op ons platform. Ik kan nog wel helpen met algemene vragen over websites, prijzen of toegestane bedrijfsdiensten.",
      websiteQuestion: "Natuurlijk. Voor wat voor bedrijf is de website?",
      websiteRecommendation: "Voor dat type bedrijf is een duidelijke bedrijfswebsite met diensten, contactmogelijkheden en lokale informatie meestal een goede start.",
      websiteNextQuestion: "Heb je al een website, of begin je vanaf nul?",
      websiteStartingZeroAnswer: "Vanaf nul beginnen is meestal de makkelijkste route. Je kunt starten met de basis en later verbeteren.",
      websiteReplaceOldAnswer: "Een oude website vervangen is vaak een goed moment om de inhoud eenvoudiger en duidelijker te maken.",
      websiteNotSureAnswer: "Dat is prima. Een eenvoudige bedrijfswebsite is meestal de beste eerste stap.",
      shopIntro: "Een webshop kan goed werken als je producten, prijzen, afbeeldingen en betaal-/contactgegevens klaar hebt.",
      shopQuestion: "Begin je met een paar producten of met een grotere catalogus?",
      shopFewProductsAnswer: "Een kleinere productopzet is meestal de makkelijkste manier om te starten. Je kunt later uitbreiden.",
      shopLargerCatalogAnswer: "Een grotere catalogus vraagt meestal meer structuur voor categorieen, productdetails en navigatie.",
      shopNotSureAnswer: "Geen probleem. Kleiner beginnen is meestal veiliger als je nog aan het kiezen bent.",
      adsIntro: "Advertenties kunnen een nieuwe website sneller bezoekers geven. De kosten hebben meestal twee delen: setup/servicekosten en advertentiebudget.",
      adsQuestion: "Natuurlijk. Ben je geïnteresseerd in Facebook & Instagram Ads, Google Ads, LinkedIn Ads, of weet je het nog niet?",
      pricingQuestion: "Dat hangt af van wat je nodig hebt. Vraag je naar een website, een webshop, advertenties of support?",
      pricingWebsiteAnswer: "De prijs van een website hangt af van het type site en hoeveel inhoud je nodig hebt.",
      pricingOnlineShopAnswer: "De prijs van een webshop hangt af van het aantal producten, de structuur en hoeveel setup nodig is.",
      pricingAdsAnswer: "Advertentieprijzen bestaan meestal uit setup/servicekosten plus advertentiebudget.",
      pricingSupportAnswer: "Supportprijzen hangen af van het soort hulp of wijzigingen dat je nodig hebt.",
      supportQuestion: "Gaat dit over een bestaand Get Online Fast-project?",
      supportExistingAnswer: "Voor een bestaand project is support de juiste volgende stap.",
      supportNewAnswer: "Geen probleem. Stel je nieuwe vraag en ik wijs je de juiste kant op.",
      supportAnswer: "Zeker. Als je al een project hebt of hulp nodig hebt met wijzigingen, is support de beste start.",
      contactPromptAnswer: "Je kunt Get Online Fast bereiken via de contactpagina. Ik kan die voor je openen.",
      contactAnswer: "Natuurlijk. Je kunt Get Online Fast direct bereiken via telefoon, e-mail of de contactpagina.",
      adviceAnswer: "Geen probleem. Begin eenvoudig. Ik kan je naar websites, webshops, advertenties of support sturen.",
      pageOnlineShop: "Ja. Voor een webshop is klein beginnen meestal het beste. Je kunt starten met een kleine productcatalogus en later uitbreiden.",
      pageWebsites: "Ja. Een eenvoudige bedrijfswebsite is meestal de beste eerste stap. Begin met je diensten, locatie en contactgegevens.",
      pageAds: "Een kleine lokale advertentiecampagne kan al genoeg zijn om te starten. De beste optie hangt af van je bedrijf en servicegebied.",
      pagePricing: "De prijs hangt af van of je een website, webshop, advertenties of support nodig hebt.",
      pageContact: "Als het urgent is, is de contactpagina de snelste volgende stap.",
      pageFaq: "In de FAQ staan veelgestelde vragen over setup, prijzen en support.",
      websiteBusinessPrompt: "Wat voor soort bedrijf is het?",
      sendLabel: "Verstuur",
      buttons: {
        website: "Website",
        onlineShop: "Webshop",
        ads: "Ads",
        support: "Support",
        notSure: "Nog niet zeker",
        pricing: "Prijzen",
        faq: "FAQ",
        contact: "Contact",
        metaAds: "Facebook & Instagram",
        googleAds: "Google Ads",
        linkedinAds: "LinkedIn Ads",
        fewProducts: "Paar producten",
        largerCatalog: "Grotere catalogus",
        notSureYet: "Nog niet zeker",
        openOnlineShopPage: "Open webshop-pagina",
        openAdsPage: "Open ads-pagina",
        openPricingPage: "Open prijzenpagina",
        openContactPage: "Open contactpagina",
        contactSupport: "Contact support",
        askAnotherQuestion: "Stel een andere vraag",
        startingFromZero: "Vanaf nul beginnen",
        replaceOldWebsite: "Oude website vervangen",
        existingProjectYes: "Ja, bestaand project",
        newQuestionNo: "Nee, nieuwe vraag",
      },
      pageNames: {
        websites: "Websites",
        onlineShop: "Webshop",
        ads: "Ads",
        pricing: "Prijzen",
        faq: "FAQ",
        contact: "Contact",
        support: "Support",
        metaAds: "Facebook & Instagram Ads",
        googleAds: "Google Ads",
        linkedinAds: "LinkedIn Ads",
      },
    },
  }[language] || {
    greeting: "Hello, welcome to Get Online Fast. How can I help you today?",
  };
  const assistantOpenTriggers = Array.from(document.querySelectorAll("[data-open-site-assistant]"));

  const emptyState = () => ({
    isOpen: false,
    selectedTopic: "",
    conversationStage: "",
    pageContext: "",
    messages: [],
    pendingNavigation: null,
  });

  const normalize = (value) =>
    (value || "")
      .toLowerCase()
      .replace(/[?!.,/\\]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();

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
        selectedTopic: state.selectedTopic || "",
        conversationStage: state.conversationStage || "",
        pageContext: state.pageContext || "general",
        messages: Array.isArray(state.messages) ? state.messages.slice(-24) : [],
        pendingNavigation: state.pendingNavigation || null,
      }),
    );
  };

  const topicButtons = (keys) =>
    keys.map((key) => ({
      kind: "reply",
      value: copy.buttons[key],
      label: copy.buttons[key],
      topic: key,
    }));

  const replyButton = (labelKey, topic = "", stage = "") => ({
    kind: "reply",
    value: copy.buttons[labelKey],
    label: copy.buttons[labelKey],
    topic,
    stage,
  });

  const pageButton = (key, urlKey = key) => ({
    kind: "link",
    label: copy.buttons[key],
    pageName: copy.pageNames[urlKey],
    topic: urlKey,
    url: urls[urlKey],
  });

  const openPageButton = (labelKey, urlKey) => ({
    kind: "link",
    label: copy.buttons[labelKey],
    pageName: copy.pageNames[urlKey],
    topic: urlKey,
    url: urls[urlKey],
  });

  const appendStoredMessage = (message) => {
    state.messages.push(message);
    saveState();
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
          if (action.value) {
            button.dataset.actionValue = action.value;
          }
          if (action.topic) {
            button.dataset.actionTopic = action.topic;
          }
          if (action.stage) {
            button.dataset.actionStage = action.stage;
          }
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
    appendStoredMessage({ role, text, actions });
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

  const containsAny = (text, terms) => terms.some((term) => text.includes(term));

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

  const isGreetingOnly = (message) => {
    const normalized = normalize(message);
    if (!normalized) {
      return false;
    }

    return [
      "hi",
      "hello",
      "hey",
      "hoi",
      "hallo",
      "good morning",
      "good afternoon",
      "good evening",
    ].includes(normalized);
  };

  const detectIntent = (normalizedQuestion) => {
    if (!normalizedQuestion) {
      return "empty";
    }
    if (containsAny(normalizedQuestion, restrictedTerms)) {
      return "restricted";
    }
    if (containsAny(normalizedQuestion, ["website", "business website", "site maken", "website maken", "website nodig", "new site", "replace old website", "old website", "nieuwe site"])) {
      return "website";
    }
    if (containsAny(normalizedQuestion, ["online shop", "webshop", "ecommerce", "product", "catalog", "producten", "shop", "sell products", "producten verkopen"])) {
      return "online_shop";
    }
    if (containsAny(normalizedQuestion, ["facebook", "instagram", "google ads", "linkedin", "ads", "advert", "advertising", "meta ads", "promote my business", "promoot mijn bedrijf"])) {
      return "ads";
    }
    if (containsAny(normalizedQuestion, ["price", "pricing", "cost", "plans", "prijzen", "prijs", "kosten"])) {
      return "pricing";
    }
    if (containsAny(normalizedQuestion, ["support", "help", "dashboard", "existing project", "bestaand project", "wijziging", "login", "change my website"])) {
      return "support";
    }
    if (containsAny(normalizedQuestion, ["contact", "phone", "email", "whatsapp", "telefoon", "mail"])) {
      return "contact";
    }
    if (containsAny(normalizedQuestion, ["not sure", "advice", "what do i need", "niet zeker", "advies", "wat heb ik nodig"])) {
      return "advice";
    }
    if (containsAny(normalizedQuestion, ["hi", "hello", "hey", "hoi", "hallo"])) {
      return "greeting";
    }
    return "fallback";
  };

  const resolveContextAnswer = (normalizedQuestion) => {
    const context = state.pageContext || "general";
    if (context === "online_shop" && containsAny(normalizedQuestion, ["few products", "small catalog", "paar producten", "kleine catalogus"])) {
      return { text: copy.pageOnlineShop, actions: [pageButton("onlineShop", "onlineShop"), pageButton("pricing", "pricing")] };
    }
    if (context === "websites" && containsAny(normalizedQuestion, ["start simple", "small website", "simple website", "eenvoudige website"])) {
      return { text: copy.pageWebsites, actions: [pageButton("website", "websites"), pageButton("pricing", "pricing")] };
    }
    if (["ads", "meta_ads", "google_ads", "linkedin_ads"].includes(context) && containsAny(normalizedQuestion, ["budget", "local", "radius", "small campaign", "budget", "campagne"])) {
      return { text: copy.pageAds, actions: [pageButton("ads", "ads"), pageButton("contact", "contact")] };
    }
    if (context === "pricing" && containsAny(normalizedQuestion, ["how much", "price", "prijs", "kosten"])) {
      return { text: copy.pagePricing, actions: topicButtons(["website", "onlineShop", "ads", "support"]) };
    }
    if (context === "contact" && containsAny(normalizedQuestion, ["urgent", "call", "phone", "spoed", "bellen"])) {
      return { text: copy.pageContact, actions: [pageButton("contact", "contact")] };
    }
    if (context === "faq" && containsAny(normalizedQuestion, ["question", "faq", "vragen"])) {
      return { text: copy.pageFaq, actions: [pageButton("faq", "faq"), pageButton("contact", "contact")] };
    }
    return null;
  };

  const websiteNextActions = () => [
    replyButton("startingFromZero", "website", "website_existing_status"),
    replyButton("replaceOldWebsite", "website", "website_existing_status"),
    replyButton("notSure", "website", "website_existing_status"),
  ];

  const pricingActions = () => [
    replyButton("website", "website"),
    replyButton("onlineShop", "onlineShop"),
    replyButton("ads", "ads"),
    replyButton("support", "support"),
    openPageButton("openPricingPage", "pricing"),
  ];

  const fallbackActions = () => [
    replyButton("website", "website"),
    replyButton("onlineShop", "onlineShop"),
    replyButton("ads", "ads"),
    replyButton("pricing", "pricing"),
    replyButton("support", "support"),
  ];

  const resolveStagedReply = (normalizedQuestion) => {
    if (state.conversationStage === "website_business_type") {
      state.conversationStage = "website_existing_status";
      return {
        text: `${copy.websiteRecommendation} ${copy.websiteNextQuestion}`,
        actions: websiteNextActions(),
      };
    }

    if (state.conversationStage === "website_existing_status") {
      state.conversationStage = "";
      if (containsAny(normalizedQuestion, ["starting from zero", "from zero", "vanaf nul"])) {
        return { text: copy.websiteStartingZeroAnswer, actions: [pageButton("website", "websites"), pageButton("pricing", "pricing")] };
      }
      if (containsAny(normalizedQuestion, ["replace old website", "old website", "vervangen", "oude website"])) {
        return { text: copy.websiteReplaceOldAnswer, actions: [pageButton("website", "websites"), pageButton("contact", "contact")] };
      }
      return { text: copy.websiteNotSureAnswer, actions: [pageButton("website", "websites"), pageButton("pricing", "pricing")] };
    }

    if (state.conversationStage === "support_existing_check") {
      state.conversationStage = "";
      if (containsAny(normalizedQuestion, ["yes", "ja", "existing project", "bestaand project"])) {
        return { text: copy.supportExistingAnswer, actions: [pageButton("support", "support"), pageButton("contact", "contact")] };
      }
      return { text: copy.supportNewAnswer, actions: fallbackActions() };
    }

    return null;
  };

  const resolveKnownPricing = () => {
    if (state.selectedTopic === "website" || state.pageContext === "websites") {
      return { text: copy.pricingWebsiteAnswer, actions: [openPageButton("openPricingPage", "pricing")] };
    }
    if (state.selectedTopic === "onlineShop" || state.pageContext === "online_shop") {
      return { text: copy.pricingOnlineShopAnswer, actions: [openPageButton("openPricingPage", "pricing")] };
    }
    if (state.selectedTopic === "ads" || ["ads", "meta_ads", "google_ads", "linkedin_ads"].includes(state.pageContext)) {
      return { text: copy.pricingAdsAnswer, actions: [openPageButton("openPricingPage", "pricing")] };
    }
    if (state.selectedTopic === "support" || state.pageContext === "support") {
      return { text: copy.pricingSupportAnswer, actions: [openPageButton("openPricingPage", "pricing")] };
    }
    return null;
  };

  const resolveSelectedTopicReply = (normalizedQuestion) => {
    if (state.selectedTopic === "onlineShop") {
      if (containsAny(normalizedQuestion, ["few products", "paar producten"])) {
        return { text: copy.shopFewProductsAnswer, actions: [openPageButton("openOnlineShopPage", "onlineShop"), openPageButton("openPricingPage", "pricing")] };
      }
      if (containsAny(normalizedQuestion, ["larger catalog", "grotere catalogus"])) {
        return { text: copy.shopLargerCatalogAnswer, actions: [openPageButton("openOnlineShopPage", "onlineShop"), openPageButton("openPricingPage", "pricing")] };
      }
      if (containsAny(normalizedQuestion, ["not sure yet", "nog niet zeker"])) {
        return { text: copy.shopNotSureAnswer, actions: [openPageButton("openOnlineShopPage", "onlineShop"), openPageButton("openPricingPage", "pricing")] };
      }
    }

    if (state.selectedTopic === "ads" && containsAny(normalizedQuestion, ["not sure", "nog niet zeker"])) {
      return {
        text: copy.adsNotSureAnswer,
        actions: [pageButton("metaAds", "metaAds"), pageButton("googleAds", "googleAds"), pageButton("linkedinAds", "linkedinAds"), openPageButton("openAdsPage", "ads")],
      };
    }

    if (containsAny(normalizedQuestion, ["ask another question", "stel een andere vraag"])) {
      state.selectedTopic = "";
      return { text: copy.fallback, actions: fallbackActions() };
    }

    return null;
  };

  const buildAssistantReply = (question) => {
    if (isEmojiOnly(question)) {
      state.selectedTopic = "";
      state.conversationStage = "";
      return { text: copy.emojiGreeting, actions: [] };
    }

    if (isGreetingOnly(question)) {
      state.selectedTopic = "";
      state.conversationStage = "";
      return { text: copy.shortGreeting, actions: [] };
    }

    const normalizedQuestion = normalize(question);
    const contextReply = resolveContextAnswer(normalizedQuestion);
    if (contextReply) {
      return contextReply;
    }

    const selectedTopicReply = resolveSelectedTopicReply(normalizedQuestion);
    if (selectedTopicReply) {
      return selectedTopicReply;
    }

    const stagedReply = resolveStagedReply(normalizedQuestion);
    if (stagedReply && !detectIntent(normalizedQuestion).match(/website|online_shop|ads|pricing|support|contact|restricted/)) {
      return stagedReply;
    }

    switch (detectIntent(normalizedQuestion)) {
      case "restricted":
        state.selectedTopic = "";
        state.conversationStage = "";
        return { text: copy.restricted, actions: fallbackActions() };
      case "website":
        state.selectedTopic = "website";
        state.conversationStage = "website_business_type";
        return { text: copy.websiteQuestion, actions: [] };
      case "online_shop":
        state.selectedTopic = "onlineShop";
        state.conversationStage = "";
        return {
          text: `${copy.shopIntro} ${copy.shopQuestion}`,
          actions: [
            replyButton("fewProducts", "onlineShop"),
            replyButton("largerCatalog", "onlineShop"),
            replyButton("notSureYet", "onlineShop"),
            openPageButton("openOnlineShopPage", "onlineShop"),
          ],
        };
      case "ads":
        state.selectedTopic = "ads";
        state.conversationStage = "";
        return {
          text: `${copy.adsIntro} ${language === "nl" ? "Aan welk platform denk je?" : copy.adsQuestion}`,
          actions: [
            pageButton("metaAds", "metaAds"),
            pageButton("googleAds", "googleAds"),
            pageButton("linkedinAds", "linkedinAds"),
            replyButton("notSure", "ads"),
            openPageButton("openAdsPage", "ads"),
          ],
        };
      case "pricing":
        state.conversationStage = "";
        {
          const knownPricing = resolveKnownPricing();
          state.selectedTopic = "pricing";
          return knownPricing || { text: copy.pricingQuestion, actions: pricingActions() };
        }
      case "support":
        state.selectedTopic = "support";
        state.conversationStage = "support_existing_check";
        return {
          text: copy.supportQuestion,
          actions: [
            replyButton("existingProjectYes", "support", "support_existing_check"),
            replyButton("newQuestionNo", "support", "support_existing_check"),
            openPageButton("contactSupport", "contact"),
          ],
        };
      case "contact":
        state.selectedTopic = "contact";
        state.conversationStage = "";
        return {
          text: copy.contactPromptAnswer || copy.contactAnswer,
          actions: [openPageButton("openContactPage", "contact"), replyButton("askAnotherQuestion")],
        };
      case "advice":
        state.selectedTopic = "";
        state.conversationStage = "";
        return { text: copy.adviceAnswer, actions: fallbackActions() };
      case "greeting":
        state.selectedTopic = "";
        state.conversationStage = "";
        return { text: copy.shortGreeting, actions: [] };
      default:
        state.selectedTopic = "";
        state.conversationStage = "";
        return { text: copy.fallback, actions: fallbackActions() };
    }
  };

  const submitAssistantQuestion = (question) => {
    const trimmedQuestion = (question || "").trim();
    if (!trimmedQuestion) {
      return;
    }
    addMessage("user", trimmedQuestion);
    if (input) {
      input.value = "";
    }
    const reply = buildAssistantReply(trimmedQuestion);
    addMessage("assistant", reply.text, reply.actions || []);
  };

  const navigateFromAssistant = (url, pageName, topic = "") => {
    state.pendingNavigation = { url, pageName };
    state.selectedTopic = topic || state.selectedTopic || "";
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

  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!input) {
      return;
    }
    setOpen(true);
    submitAssistantQuestion(input.value);
  });

  messages?.addEventListener("click", (event) => {
    const button = event.target.closest(".site-assistant-action");
    if (!button) {
      return;
    }

    const actionKind = button.dataset.actionKind;
    const actionValue = button.dataset.actionValue || "";
    const actionTopic = button.dataset.actionTopic || "";
    const actionStage = button.dataset.actionStage || "";
    const actionUrl = button.dataset.actionUrl || "";
    const actionPageName = button.dataset.actionPageName || "";

    if (actionKind === "reply") {
      if (actionTopic) {
        state.selectedTopic = actionTopic;
      }
      state.conversationStage = actionStage;
      submitAssistantQuestion(actionValue);
      return;
    }

    if (actionKind === "link" && actionUrl) {
      navigateFromAssistant(actionUrl, actionPageName || button.textContent || "", actionTopic);
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
