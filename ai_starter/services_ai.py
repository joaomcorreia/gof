import json
import logging
import re
from copy import deepcopy

from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(__name__)


def is_ai_enabled():
    return bool(getattr(settings, 'GOF_AI_ENABLED', False) and getattr(settings, 'OPENAI_API_KEY', '').strip())


def clean_assistant_output(text):
    if text is None:
        return ''

    cleaned = str(text).strip()
    fence_match = re.match(r"^```[a-zA-Z0-9_-]*\s*\n(?P<body>[\s\S]*?)\n```$", cleaned)
    if fence_match:
        cleaned = fence_match.group('body').strip()

    return cleaned


def _string_value(value):
    if value is None:
        return ''
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _collect_content_summary(content_rows):
    section_counts = {}
    missing_rows = []

    for row in content_rows:
        section_key = _string_value(row.get('section_key')) or 'unknown'
        section_counts[section_key] = section_counts.get(section_key, 0) + 1
        if not _string_value(row.get('value')):
            missing_rows.append(f"{section_key}.{_string_value(row.get('field_key')) or 'value'}")

    section_summary = ', '.join(
        f'{section} ({count})' for section, count in sorted(section_counts.items())
    ) or 'No content rows found.'

    return section_summary, missing_rows


def build_fallback_handoff_brief(handoff):
    payload = handoff.handoff_payload or {}
    business = payload.get('business') or {}
    design = payload.get('design') or {}
    content_rows = payload.get('content') or []
    request_data = payload.get('website_request') or {}
    wordpress_target = payload.get('wordpress_target') or {}

    section_summary, missing_rows = _collect_content_summary(content_rows)

    follow_up_questions = []
    if not _string_value(request_data.get('contact_email')):
        follow_up_questions.append('- Confirm the main customer contact email.')
    if not _string_value(request_data.get('contact_phone')):
        follow_up_questions.append('- Confirm the preferred phone or WhatsApp contact.')
    if not _string_value(request_data.get('current_domain')):
        follow_up_questions.append('- Ask whether an existing domain should be connected or a new domain is needed.')
    if not _string_value(request_data.get('preferred_colors')):
        follow_up_questions.append('- Ask for preferred brand colors or example sites.')
    if not _string_value(request_data.get('main_services')):
        follow_up_questions.append('- Confirm the main services that must appear first in WordPress.')
    if not follow_up_questions:
        follow_up_questions.append('- Confirm the first priority page or service to prepare in WordPress.')

    weak_information = []
    if missing_rows:
        weak_information.append(f"- Empty or weak content rows detected: {', '.join(missing_rows[:8])}")
    if not request_data:
        weak_information.append('- No linked WebsiteRequest was attached to this handoff.')
    if not _string_value(request_data.get('business_description')):
        weak_information.append('- Business description is missing or thin.')
    if not _string_value(request_data.get('style_notes')):
        weak_information.append('- Style notes are missing.')
    if not _string_value(request_data.get('opening_hours')):
        weak_information.append('- Opening hours are missing.')
    if not weak_information:
        weak_information.append('- No major payload gaps detected from the Django handoff data.')

    setup_notes = [
        f"- Start from WordPress template/editor setup for `{_string_value(design.get('template_slug')) or 'default starter'}`.",
        f"- Apply Django color palette hint: `{_string_value(design.get('color_palette')) or 'not set'}`.",
        '- Import or manually copy the generated section content into the appropriate WordPress builder fields.',
        '- Review media, branding, menus, contact details, and service structure manually before customer handoff.',
    ]
    if not any(_string_value(wordpress_target.get(key)) for key in ('site_url', 'admin_url', 'user_reference')):
        setup_notes.append('- WordPress target details are still empty, so this remains a manual staff handoff.')

    business_summary = [
        'Business summary',
        f"- Business name: {_string_value(business.get('business_name')) or _string_value(handoff.site.business_name) or 'Unknown'}",
        f"- Service type: {_string_value(business.get('service_type')) or _string_value(handoff.site.service_type) or 'Unknown'}",
        f"- City: {_string_value(business.get('city')) or _string_value(handoff.site.city) or 'Unknown'}",
        f"- Source public ID: {_string_value((payload.get('source') or {}).get('public_id')) or str(handoff.site.public_id)}",
        f"- Handoff status: {handoff.get_status_display()}",
    ]

    content_summary = [
        'Content summary',
        f'- Total content rows: {len(content_rows)}',
        f'- Sections represented: {section_summary}',
        f"- Website request linked: {'Yes' if request_data else 'No'}",
    ]

    return '\n'.join(
        business_summary
        + ['']
        + content_summary
        + ['']
        + ['Missing or weak information']
        + weak_information
        + ['']
        + ['Suggested WordPress setup notes']
        + setup_notes
        + ['']
        + ['Recommended next staff actions']
        + [
            '- Prepare or confirm the target WordPress customer/site record manually.',
            '- Use the handoff payload and this brief as the staff checklist before opening JCW Tools.',
            '- Record any WordPress URL/user reference back on the SiteHandoff once known.',
        ]
        + ['']
        + ['Customer follow-up questions']
        + follow_up_questions
        + ['']
        + ['Note: AI is not configured in Django yet. This is a local fallback brief based on the handoff payload only.']
    )


def _build_openai_prompt(handoff):
    payload = handoff.handoff_payload or {}
    metadata = {
        'handoff_id': handoff.pk,
        'handoff_status': handoff.status,
        'target_system': handoff.target_system,
        'site_id': handoff.site_id,
        'site_public_id': str(handoff.site.public_id),
        'website_request_id': handoff.website_request_id,
    }

    instructions = (
        'You are writing an internal staff handoff brief for a Django to WordPress workflow. '
        'This brief is for staff only. Do not mention changing WordPress automatically. '
        'Do not invent credentials, URLs, uploaded file contents, or completed setup steps. '
        'Use only the provided metadata and handoff payload. '
        'Return concise markdown with exactly these headings: '
        'Business summary, Content summary, Missing or weak information, '
        'Suggested WordPress setup notes, Recommended next staff actions, Customer follow-up questions.'
    )

    return (
        f'{instructions}\n\n'
        f'Metadata:\n{json.dumps(metadata, ensure_ascii=False, indent=2)}\n\n'
        f'Handoff payload:\n{json.dumps(payload, ensure_ascii=False, indent=2)}'
    )


def generate_handoff_brief(handoff):
    if not is_ai_enabled():
        return clean_assistant_output(build_fallback_handoff_brief(handoff))

    try:
        from openai import OpenAI
    except ImportError:
        return clean_assistant_output(build_fallback_handoff_brief(handoff))

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.responses.create(
        model=settings.GOF_AI_MODEL,
        input=_build_openai_prompt(handoff),
        temperature=0.2,
        max_output_tokens=900,
    )

    output_text = getattr(response, 'output_text', '') or ''
    if output_text.strip():
        return clean_assistant_output(output_text)

    response_dict = response.model_dump() if hasattr(response, 'model_dump') else {}
    for item in response_dict.get('output', []) if isinstance(response_dict, dict) else []:
        for content in item.get('content', []) if isinstance(item, dict) else []:
            text = content.get('text') if isinstance(content, dict) else ''
            if isinstance(text, str) and text.strip():
                return clean_assistant_output(text)

    raise ValueError(f'OpenAI returned an empty handoff brief at {timezone.now().isoformat()}.')


def _reply_tone_label(reply_tone):
    tone_map = {
        'friendly_professional': 'friendly and professional',
        'short_direct': 'short and direct',
        'warm_sales': 'warm and sales-aware',
        'support_helpful': 'supportive and helpful',
    }
    return tone_map.get(reply_tone, tone_map['friendly_professional'])


def _reply_language_code(reply_language):
    language_map = {
        'Portuguese': 'pt',
        'English': 'en',
        'Dutch': 'nl',
        'French': 'fr',
    }
    return language_map.get(reply_language, 'pt')


def infer_recommended_website_setup(customer_message, handoff=None):
    message = (customer_message or '').lower()
    payload = handoff.handoff_payload if handoff and isinstance(handoff.handoff_payload, dict) else {}
    business = payload.get('business') or {}
    request_data = payload.get('website_request') or {}
    service_type = _string_value(business.get('service_type')).lower()
    business_description = _string_value(request_data.get('business_description')).lower()
    combined = ' '.join(part for part in [message, service_type, business_description] if part)

    setup = {
        'recommended_setup_label': 'Local service website',
        'recommended_pages_or_sections': [
            'Homepage',
            'Services',
            'About',
            'Contact',
            'WhatsApp / Call CTA',
            'Google-ready local SEO basics',
        ],
        'recommended_features': [
            'Contact form',
            'Phone and WhatsApp CTA',
            'Location or service area',
        ],
        'optional_addons': [
            'Professional domain email',
            'Gallery or reviews section',
        ],
        'reasoning': 'Safe default for a small business that likely needs a clear Google-ready website before more advanced features.',
        'essential_questions': [
            'Business name',
            'Main services or products',
            'Existing domain yes/no',
            'Preferred contact method',
        ],
    }

    def has_any(*keywords):
        return any(keyword in combined for keyword in keywords)

    def has_ai_intent():
        ai_patterns = [
            r'\bai\b',
            r'\bassistant\b',
            r'customer-service',
            r'customer service',
            r'chatbot',
            r'reply automation',
            r'automation',
            r'assistente ai',
            r'assistente de respostas',
        ]
        return any(re.search(pattern, combined) for pattern in ai_patterns)

    if has_any('garage', 'mechanic', 'workshop', 'oficina', 'auto repair'):
        setup.update(
            {
                'recommended_setup_label': 'Local service website for garage / mechanic business',
                'recommended_pages_or_sections': ['Homepage', 'Services', 'Quote request', 'Contact', 'Service area', 'Google-ready local SEO'],
                'recommended_features': ['Quote/contact form', 'WhatsApp and call CTA', 'Service area coverage', 'Trust/reviews section'],
                'optional_addons': ['Project gallery', 'Business email/domain help'],
                'reasoning': 'Garage and mechanic businesses usually need service visibility, fast contact, and local search readiness more than a complex custom build.',
                'essential_questions': ['Business name', 'Main repair/services offered', 'Existing domain yes/no', 'Preferred contact method'],
            }
        )
    elif has_any('restaurant', 'restaurante', 'café', 'cafe', 'bar'):
        setup.update(
            {
                'recommended_setup_label': 'Restaurant or cafe business website',
                'recommended_pages_or_sections': ['Homepage', 'Menu or highlights', 'Opening hours', 'Location', 'Contact / reservations CTA'],
                'recommended_features': ['Opening hours', 'Map/location', 'WhatsApp or reservations CTA', 'Photo highlights'],
                'optional_addons': ['Menu PDF', 'Google Business setup help'],
                'reasoning': 'Restaurants and cafes need clear menu, hours, contact, and location information first.',
                'essential_questions': ['Business name', 'Main menu or offer highlights', 'Preferred booking/contact method', 'Existing domain yes/no'],
            }
        )
    elif has_any('print shop', 'printing', 'gráfica', 'grafica', 'print'):
        setup.update(
            {
                'recommended_setup_label': 'Printing business website with quote request flow',
                'recommended_pages_or_sections': ['Homepage', 'Services/products', 'Quote request', 'Contact', 'File delivery guidance'],
                'recommended_features': ['Quote request form', 'WhatsApp/contact CTA', 'Service categories', 'Upload later workflow note'],
                'optional_addons': ['File upload step later', 'Business email/domain help'],
                'reasoning': 'Printing businesses usually need service visibility and quote capture first, with file upload added later if needed.',
                'essential_questions': ['Business name', 'Main printing services/products', 'Preferred quote contact method', 'Whether file upload is needed later'],
            }
        )
    elif has_any('construction', 'building', 'renovation', 'builder', 'contractor', 'construção', 'renovação'):
        setup.update(
            {
                'recommended_setup_label': 'Construction or renovation service website',
                'recommended_pages_or_sections': ['Homepage', 'Services', 'Projects/gallery', 'Service area', 'Quote form', 'Contact'],
                'recommended_features': ['Quote request form', 'Projects/gallery', 'Service area coverage', 'WhatsApp/call CTA'],
                'optional_addons': ['Reviews section', 'Business email/domain help'],
                'reasoning': 'Construction businesses usually need trust-building, project examples, and fast local quote contact.',
                'essential_questions': ['Business name', 'Main services offered', 'Service area', 'Preferred contact method'],
            }
        )
    elif has_any('taxi', 'transport', 'airport transfer', 'private rides', 'transporte'):
        setup.update(
            {
                'recommended_setup_label': 'Taxi or transport service website',
                'recommended_pages_or_sections': ['Homepage', 'Service area', 'Airport/private rides', 'Quote/request form', 'Contact'],
                'recommended_features': ['WhatsApp/call CTA', 'Quote/request form', 'Service area coverage', 'Google-ready local SEO'],
                'optional_addons': ['Pricing guide later', 'Business email/domain help'],
                'reasoning': 'Taxi and transport businesses need clear service area, ride types, and immediate contact/request actions.',
                'essential_questions': ['Business name', 'Main ride types or routes', 'Service area', 'Preferred contact method'],
            }
        )
    elif has_any('beauty', 'spa', 'salon', 'nails', 'hair', 'barber'):
        setup.update(
            {
                'recommended_setup_label': 'Beauty, spa, or salon website',
                'recommended_pages_or_sections': ['Homepage', 'Services', 'Prices/from-prices', 'Gallery', 'Contact / appointment CTA'],
                'recommended_features': ['Gallery', 'Appointment/contact CTA', 'Service list', 'Location information'],
                'optional_addons': ['Instagram integration', 'Business email/domain help'],
                'reasoning': 'Beauty and salon businesses usually need services, pricing guidance, visual trust, and easy appointment contact.',
                'essential_questions': ['Business name', 'Main services', 'Preferred appointment/contact method', 'Existing domain yes/no'],
            }
        )
    elif has_ai_intent():
        setup.update(
            {
                'recommended_setup_label': 'AI Reply Assistant early-access add-on',
                'recommended_pages_or_sections': ['Internal reply drafting flow', 'Business knowledge summary', 'Manual review step', 'Contact/help intake'],
                'recommended_features': ['Draft replies only', 'Manual review before sending', 'Business-specific knowledge later', 'Copy/paste first workflow'],
                'optional_addons': ['Website or service landing page', 'Business email/domain help', 'Future automation review later'],
                'reasoning': 'The message suggests interest in AI-assisted customer replies. The safest V1 is an early-access assistant that drafts replies for staff review instead of automatic sending.',
                'essential_questions': ['Business name', 'What type of customer messages are most common', 'Preferred reply language', 'Whether replies must always be reviewed before sending'],
            }
        )
    elif has_any('shop', 'store', 'loja', 'drogist', 'boutique', 'products', 'productos'):
        future_sales_hint = has_any('later', 'mais tarde', 'later on', 'future')
        wants_payments = has_any('online payments', 'payments', 'sell online', 'ecommerce', 'e-commerce', 'checkout')
        if not future_sales_hint and has_any('vender', 'sell'):
            wants_payments = True
        setup.update(
            {
                'recommended_setup_label': 'Product catalog or simple business website',
                'recommended_pages_or_sections': ['Homepage', 'Products or categories', 'About', 'Contact', 'Location'],
                'recommended_features': ['Product showcase', 'Contact CTA', 'Category highlights', 'WhatsApp/call CTA'],
                'optional_addons': [
                    'eCommerce later' if not wants_payments else 'Online payment setup only after product/process confirmation',
                    'Business email/domain help',
                ],
                'reasoning': 'Small shops often need a simple product showcase or catalog first, with eCommerce added only when online payment flow is clearly required.',
                'essential_questions': ['Business name', 'Main product categories', 'Whether online payments are needed now or later', 'Preferred contact method'],
            }
        )
        if wants_payments:
            setup['recommended_setup_label'] = 'Small online store or catalog with future eCommerce confirmation'
            setup['recommended_features'] = ['Product showcase', 'Category pages', 'Contact CTA', 'Payment requirement review']

    return setup


def _extract_missing_reply_bits(customer_message, handoff):
    missing = []
    payload = handoff.handoff_payload if handoff and isinstance(handoff.handoff_payload, dict) else {}
    request_data = payload.get('website_request') or {}
    message = (customer_message or '').lower()
    recommendation = infer_recommended_website_setup(customer_message, handoff)

    if not request_data.get('contact_phone') and 'phone' not in message and 'telefone' not in message:
        missing.append('Preferred phone or WhatsApp contact')
    if not request_data.get('current_domain') and 'domain' not in message and 'dominio' not in message:
        missing.append('Existing domain or whether domain help is needed')
    if not request_data.get('main_services'):
        missing.append('Main service or page priority')
    if not request_data.get('preferred_colors') and 'color' not in message and 'cor' not in message:
        missing.append('Preferred colors or style direction')
    if any('payment' in addon.lower() or 'ecommerce' in addon.lower() for addon in recommendation.get('optional_addons', [])) and not any(term in message for term in ['payment', 'payments', 'pagamento', 'ecommerce', 'sell online', 'vender']):
        missing.append('Whether online payments are needed now or later')

    return missing


def _build_fallback_reply(customer_message, handoff, reply_language='Portuguese', reply_tone='friendly_professional'):
    payload = handoff.handoff_payload if handoff and isinstance(handoff.handoff_payload, dict) else {}
    business = payload.get('business') or {}
    request_data = payload.get('website_request') or {}
    business_name = _string_value(business.get('business_name')) or 'our team'
    contact_name = _string_value(request_data.get('contact_name'))
    recommendation = infer_recommended_website_setup(customer_message, handoff)
    missing = _extract_missing_reply_bits(customer_message, handoff)

    recommended_label = recommendation.get('recommended_setup_label', 'Local service website')
    recommended_pages = ', '.join(recommendation.get('recommended_pages_or_sections', []))
    optional_addons = ', '.join(recommendation.get('optional_addons', []))
    reasoning = recommendation.get('reasoning', '')
    language = _reply_language_code(reply_language)
    tone_label = _reply_tone_label(reply_tone)

    if language == 'en':
        opening_line = (
            f"Thank you for your message. Based on what you described, the most suitable starting point will probably be a {recommended_label.lower()} with {recommended_pages.lower()}."
        )
        if 'ai reply assistant' in recommended_label.lower():
            opening_line = (
                'Thank you for your message. Based on what you described, the best starting point will probably be an early-access AI reply assistant that drafts replies for staff review before anything is sent.'
            )
        reply = (
            f"Suggested reply\n\n"
            f"Hi{f' {contact_name}' if contact_name else ''},\n\n"
            f"{opening_line}\n\n"
            f"We have reviewed your request and {business_name} will confirm the next details after a staff review.\n\n"
            f"Best regards,\n{business_name}\n\n"
            f"Missing information to ask\n"
            + ('\n'.join(f"- {item}" for item in missing) if missing else "- No major basics are missing from the current context.")
            + "\n\nInternal notes for staff\n"
            f"- Requested reply language: {reply_language}\n"
            f"- Requested tone: {tone_label}\n"
            f"- Recommended setup: {recommended_label}\n"
            f"- Suggested pages/sections: {recommended_pages}\n"
            f"- Optional add-ons: {optional_addons or '--'}\n"
            f"- Why this recommendation was made: {reasoning}\n"
            f"- Fallback draft used because Django AI is not configured.\n"
            f"- Review before sending.\n"
            f"- Do not confirm price, deadline, or availability until the team checks the linked handoff/request."
        )
        return reply

    if language == 'nl':
        opening_line = (
            f"Bedankt voor je bericht. Op basis van je vraag lijkt een {recommended_label.lower()} met {recommended_pages.lower()} waarschijnlijk het beste startpunt."
        )
        if 'ai reply assistant' in recommended_label.lower():
            opening_line = (
                'Bedankt voor je bericht. Op basis van je vraag lijkt een vroege AI-reply-assistent die eerst alleen conceptantwoorden maakt voor handmatige controle het beste startpunt.'
            )
        reply = (
            f"Suggested reply\n\n"
            f"Hallo{f' {contact_name}' if contact_name else ''},\n\n"
            f"{opening_line}\n\n"
            f"We hebben je aanvraag ontvangen en {business_name} bevestigt de details na een interne controle.\n\n"
            f"Met vriendelijke groet,\n{business_name}\n\n"
            f"Missing information to ask\n"
            + ('\n'.join(f"- {item}" for item in missing) if missing else "- Geen grote basisgegevens ontbreken in de huidige context.")
            + "\n\nInternal notes for staff\n"
            f"- Gewenste antwoordtaal: {reply_language}\n"
            f"- Gewenste toon: {tone_label}\n"
            f"- Recommended setup: {recommended_label}\n"
            f"- Suggested pages/sections: {recommended_pages}\n"
            f"- Optional add-ons: {optional_addons or '--'}\n"
            f"- Why this recommendation was made: {reasoning}\n"
            f"- Fallback-antwoord gebruikt omdat Django AI niet is ingesteld.\n"
            f"- Review before sending.\n"
            f"- Bevestig geen prijs, planning of beschikbaarheid zonder teamcontrole."
        )
        return reply

    if language == 'fr':
        opening_line = (
            f"D'après votre demande, le point de départ le plus adapté sera probablement un {recommended_label.lower()} avec {recommended_pages.lower()}."
        )
        if 'ai reply assistant' in recommended_label.lower():
            opening_line = (
                "D'après votre demande, le point de départ le plus adapté sera probablement un assistant IA en accès anticipé qui prépare des brouillons de réponse avec validation manuelle avant envoi."
            )
        reply = (
            f"Suggested reply\n\n"
            f"Bonjour{f' {contact_name}' if contact_name else ''},\n\n"
            f"Merci pour votre message. {opening_line}\n\n"
            f"{business_name} confirmera les détails après une vérification interne.\n\n"
            f"Cordialement,\n{business_name}\n\n"
            f"Missing information to ask\n"
            + ('\n'.join(f"- {item}" for item in missing) if missing else "- Aucun élément de base important ne manque dans le contexte actuel.")
            + "\n\nInternal notes for staff\n"
            f"- Langue demandée: {reply_language}\n"
            f"- Ton demandé: {tone_label}\n"
            f"- Recommended setup: {recommended_label}\n"
            f"- Suggested pages/sections: {recommended_pages}\n"
            f"- Optional add-ons: {optional_addons or '--'}\n"
            f"- Why this recommendation was made: {reasoning}\n"
            f"- Brouillon local utilisé car l'IA Django n'est pas configurée.\n"
            f"- Review before sending.\n"
            f"- Ne pas confirmer le prix, le délai ou la disponibilité sans vérification interne."
        )
        return reply

    opening_line = (
        f"Pelo tipo de pedido, o ponto de partida mais indicado será provavelmente um {recommended_label.lower()} com {recommended_pages.lower()}."
    )
    if 'ai reply assistant' in recommended_label.lower():
        opening_line = (
            'Pelo tipo de pedido, o ponto de partida mais indicado será provavelmente um assistente AI em early access para criar rascunhos de resposta com revisão manual antes de qualquer envio.'
        )
    reply = (
        f"Suggested reply\n\n"
        f"Olá{f' {contact_name}' if contact_name else ''},\n\n"
        f"Obrigado pela sua mensagem. {opening_line}\n\n"
        f"A equipa de {business_name} vai confirmar os próximos detalhes após uma revisão interna.\n\n"
        f"Com os melhores cumprimentos,\n{business_name}\n\n"
        f"Missing information to ask\n"
        + ('\n'.join(f"- {item}" for item in missing) if missing else "- Nao faltam dados basicos importantes no contexto atual.")
        + "\n\nInternal notes for staff\n"
        f"- Idioma pedido: {reply_language}\n"
        f"- Tom pedido: {tone_label}\n"
        f"- Recommended setup: {recommended_label}\n"
        f"- Suggested pages/sections: {recommended_pages}\n"
        f"- Optional add-ons: {optional_addons or '--'}\n"
        f"- Why this recommendation was made: {reasoning}\n"
        f"- Rascunho local usado porque a AI do Django ainda nao esta configurada.\n"
        f"- Review before sending.\n"
        f"- Nao confirmar preco final, prazo ou disponibilidade sem revisao da equipa."
    )
    return reply


def _build_customer_reply_prompt(customer_message, handoff=None, reply_language='Portuguese', reply_tone='friendly_professional'):
    payload = handoff.handoff_payload if handoff and isinstance(handoff.handoff_payload, dict) else {}
    recommendation = infer_recommended_website_setup(customer_message, handoff)
    metadata = {
        'reply_language': reply_language,
        'reply_tone': _reply_tone_label(reply_tone),
        'handoff_id': handoff.pk if handoff else None,
        'site_public_id': str(handoff.site.public_id) if handoff else None,
    }
    instructions = (
        'Draft an internal staff-reviewed customer reply. '
        'This is not sent automatically. Do not claim the message was sent. '
        'Do not promise final prices, deadlines, guarantees, or availability unless explicitly present in the provided context. '
        'Do not ask the customer to choose from too many website types. Propose the likely setup first. '
        'Ask only the minimum necessary follow-up questions. '
        'If something is uncertain, say the team will confirm details. '
        'Always remind staff in Internal notes that the reply should be reviewed before sending. '
        'Return markdown with exactly these headings: Suggested reply, Missing information to ask, Internal notes for staff.'
    )
    return (
        f'{instructions}\n\n'
        f'Metadata:\n{json.dumps(metadata, ensure_ascii=False, indent=2)}\n\n'
        f'Customer message:\n{customer_message}\n\n'
        f'Inferred recommendation:\n{json.dumps(recommendation, ensure_ascii=False, indent=2)}\n\n'
        f'Safe handoff context:\n{json.dumps(payload, ensure_ascii=False, indent=2)}'
    )


def draft_customer_reply(
    customer_message,
    handoff=None,
    reply_language='Portuguese',
    reply_tone='friendly_professional',
):
    if not is_ai_enabled():
        return clean_assistant_output(_build_fallback_reply(customer_message, handoff, reply_language, reply_tone))

    try:
        from openai import OpenAI
    except ImportError:
        return clean_assistant_output(_build_fallback_reply(customer_message, handoff, reply_language, reply_tone))

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.responses.create(
        model=settings.GOF_AI_MODEL,
        input=_build_customer_reply_prompt(
            customer_message,
            handoff=handoff,
            reply_language=reply_language,
            reply_tone=reply_tone,
        ),
        temperature=0.2,
        max_output_tokens=900,
    )

    output_text = getattr(response, 'output_text', '') or ''
    if output_text.strip():
        return clean_assistant_output(output_text)

    response_dict = response.model_dump() if hasattr(response, 'model_dump') else {}
    for item in response_dict.get('output', []) if isinstance(response_dict, dict) else []:
        for content in item.get('content', []) if isinstance(item, dict) else []:
            text = content.get('text') if isinstance(content, dict) else ''
            if isinstance(text, str) and text.strip():
                return clean_assistant_output(text)

    raise ValueError(f'OpenAI returned an empty customer reply draft at {timezone.now().isoformat()}.')


def polish_starter_suggestions_with_ai(base_suggestions, business_context):
    """Optionally polish starter copy using one low-cost OpenAI call.

    This function must never break starter generation. If anything fails,
    it returns the original deterministic suggestions unchanged.
    """
    if not isinstance(base_suggestions, dict):
        return base_suggestions

    if not is_ai_enabled():
        return base_suggestions

    try:
        from openai import OpenAI
    except ImportError:
        return base_suggestions

    working = deepcopy(base_suggestions)
    hero = working.get('hero', {}) if isinstance(working.get('hero'), dict) else {}
    about = working.get('about', {}) if isinstance(working.get('about'), dict) else {}
    services = working.get('services', {}) if isinstance(working.get('services'), dict) else {}

    intro_heading = ''
    intro_paragraph = ''
    if about:
        intro_heading = str(about.get('title', '')).strip()
        intro_paragraph = str(about.get('description', '')).strip()
    else:
        intro_heading = str(services.get('title', '')).strip()
        intro_paragraph = str(services.get('intro', '')).strip()

    service_descriptions = []
    service_source_keys = []
    for key in ('item_1_text', 'item_2_text', 'item_3_text'):
        value = str(services.get(key, '')).strip()
        if value:
            service_descriptions.append(value)
            service_source_keys.append(key)
    if not service_descriptions:
        for key in ('item_1', 'item_2', 'item_3'):
            value = str(services.get(key, '')).strip()
            if value:
                service_descriptions.append(value)
                service_source_keys.append(key)

    source_payload = {
        'hero_title': str(hero.get('title', '')).strip(),
        'hero_text': str(hero.get('description', '')).strip(),
        'intro_heading': intro_heading,
        'intro_paragraph': intro_paragraph,
        'service_descriptions': service_descriptions[:3],
    }

    context_payload = {
        'business_name': str((business_context or {}).get('business_name', '')).strip(),
        'business_type': str((business_context or {}).get('business_type', '')).strip(),
        'city': str((business_context or {}).get('city', '')).strip(),
        'selected_services': [
            str(item).strip()
            for item in ((business_context or {}).get('selected_services') or [])
            if str(item).strip()
        ][:3],
    }

    prompt = (
        'Polish only short marketing copy for a starter website. '\
        'Keep meaning grounded in the provided business context. '\
        'Do not invent offers, prices, guarantees, certifications, or legal claims. '\
        'Do not write generic phrases like "professional services", "clear services", '\
        '"quality solutions", "local visibility", or "simple contact path". '\
        'Every field must clearly match the selected business type and selected services. '\
        'Use the provided business name, business type, city, and selected services. '\
        'Keep the business name unchanged and keep the city name unchanged. '\
        'Write all customer-facing copy in English unless a site language is explicitly provided. '\
        'Return compact JSON only with keys: hero_title, hero_text, intro_heading, intro_paragraph, service_descriptions. '\
        'service_descriptions must be an array with up to 3 short strings. '\
        'No markdown, no code fences, no extra keys.\n\n'
        f'Business context:\n{json.dumps(context_payload, ensure_ascii=False)}\n\n'
        f'Current copy:\n{json.dumps(source_payload, ensure_ascii=False)}'
    )

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.responses.create(
            model=settings.GOF_AI_MODEL,
            input=prompt,
            temperature=0.1,
            max_output_tokens=350,
        )
    except Exception as exc:
        logger.warning('Starter AI polish call failed: %s', exc)
        return base_suggestions

    raw_output = getattr(response, 'output_text', '') or ''
    if not raw_output.strip():
        response_dict = response.model_dump() if hasattr(response, 'model_dump') else {}
        for item in response_dict.get('output', []) if isinstance(response_dict, dict) else []:
            for content in item.get('content', []) if isinstance(item, dict) else []:
                text = content.get('text') if isinstance(content, dict) else ''
                if isinstance(text, str) and text.strip():
                    raw_output = text
                    break
            if raw_output.strip():
                break

    if not raw_output.strip():
        logger.warning('Starter AI polish returned empty output.')
        return base_suggestions

    try:
        parsed = json.loads(clean_assistant_output(raw_output))
    except Exception as exc:
        logger.warning('Starter AI polish returned invalid JSON: %s', exc)
        return base_suggestions

    required_keys = {
        'hero_title',
        'hero_text',
        'intro_heading',
        'intro_paragraph',
        'service_descriptions',
    }
    if not isinstance(parsed, dict) or not required_keys.issubset(parsed.keys()):
        logger.warning('Starter AI polish JSON missing required keys.')
        return base_suggestions

    if not isinstance(parsed.get('service_descriptions'), list):
        logger.warning('Starter AI polish service_descriptions has invalid type.')
        return base_suggestions

    polished_services = [
        str(item).strip()
        for item in parsed.get('service_descriptions', [])
        if isinstance(item, str) and str(item).strip()
    ][:3]

    hero_title = str(parsed.get('hero_title', '')).strip()
    hero_text = str(parsed.get('hero_text', '')).strip()
    intro_heading_value = str(parsed.get('intro_heading', '')).strip()
    intro_paragraph_value = str(parsed.get('intro_paragraph', '')).strip()

    if hero and hero_title:
        hero['title'] = hero_title
    if hero and hero_text:
        hero['description'] = hero_text

    if about:
        if intro_heading_value and 'title' in about:
            about['title'] = intro_heading_value
        if intro_paragraph_value and 'description' in about:
            about['description'] = intro_paragraph_value
    elif services:
        if intro_heading_value and 'title' in services:
            services['title'] = intro_heading_value
        if intro_paragraph_value and 'intro' in services:
            services['intro'] = intro_paragraph_value

    for idx, key in enumerate(service_source_keys[:3]):
        if idx < len(polished_services) and key in services:
            services[key] = polished_services[idx]

    return working
