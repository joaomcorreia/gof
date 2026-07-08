import hashlib
import logging
from collections.abc import Mapping

from django.conf import settings
from django.core.cache import cache


logger = logging.getLogger(__name__)

PUBLIC_ASSISTANT_RATE_LIMIT_RESPONSES = {
    'en': 'Too many messages for now. You can use the start form or contact support.',
    'nl': 'Te veel berichten voor nu. Gebruik het startformulier of neem contact op met support.',
    'fr': 'Trop de messages pour le moment. Vous pouvez utiliser le formulaire de démarrage ou contacter le support.',
    'pt': 'Mensagens a mais por agora. Pode usar o formulário inicial ou contactar o suporte.',
}

PUBLIC_ASSISTANT_SYSTEM_PROMPT = """You are the public Get Online Fast website assistant.

Answer only about Get Online Fast and related visitor questions:
- website setup
- starter pages
- business websites for self-employed people and small businesses
- WordPress websites finished by humans
- previews and testing before activation
- pricing and plans only when grounded in provided context
- domains, hosting, business email, Google visibility, support, and next steps
- general promotion topics such as Facebook/Instagram content or Google Ads

Identity and interpretation rules:
- The visitor is currently on the Get Online Fast website.
- "this site" usually means the Get Online Fast website itself.
- "Get Online Fast", "this page", "this website", or launch/open questions usually refer to the Get Online Fast website/service.
- "my site", "my website", "our website", "my business site", or business-specific wording usually refer to the visitor's future website project.
- If a question uses only "site" and the meaning is unclear, answer briefly and ask one short clarifying question.
- For questions about whether "this site" is open, launched, or usable, answer about Get Online Fast itself, not about the visitor's future website build.

Constraints:
- Keep replies short, practical, and customer-safe.
- Do not behave like a general chatbot.
- If a visitor asks an unrelated question, politely say you only help with Get Online Fast topics and redirect them back to website setup, pricing, previews, domains, Google visibility, or support.
- Do not invent a public launch date for Get Online Fast if none is provided in context.
- Do not invent guarantees, rankings, certifications, reviews, prices, payment status, or activation status.
- Do not claim a website is already paid, activated, or live unless explicitly provided.
- Do not provide legal, financial, or medical advice.
- Do not ask for sensitive personal data.
- Guide visitors toward choosing a plan, contacting support, or the right next step.
- If the visitor only says hello, greet them briefly and offer help with pricing, previews, domains, Google visibility, or getting started.
- If the question is unclear, ask one short clarifying question or provide the safest next step.
"""


def public_assistant_status():
    configured_model = (
        getattr(settings, 'GOF_PUBLIC_AI_ASSISTANT_MODEL', '')
        or getattr(settings, 'GOF_AI_MODEL', '')
        or ''
    ).strip()
    has_openai_key = bool(getattr(settings, 'OPENAI_API_KEY', '').strip())
    ai_enabled = bool(getattr(settings, 'GOF_AI_ENABLED', False))
    public_ai_enabled = bool(getattr(settings, 'GOF_PUBLIC_AI_ASSISTANT_ENABLED', False))
    return {
        'available': bool(ai_enabled and public_ai_enabled and has_openai_key),
        'ai_enabled': ai_enabled,
        'public_ai_enabled': public_ai_enabled,
        'has_openai_key': has_openai_key,
        'model_used': configured_model,
    }


def normalize_public_assistant_input(message):
    limit = max(1, int(getattr(settings, 'GOF_PUBLIC_AI_ASSISTANT_MAX_INPUT_CHARS', 500)))
    normalized = ' '.join(str(message or '').strip().split())
    if not normalized:
        return {'valid': False, 'message': '', 'reason': 'empty'}
    if len(normalized) > limit:
        return {'valid': False, 'message': normalized[:limit], 'reason': 'too_long'}
    return {'valid': True, 'message': normalized, 'reason': ''}


def _client_ip(request):
    forwarded = str(request.META.get('HTTP_X_FORWARDED_FOR', '') or '').strip()
    if forwarded:
        return forwarded.split(',')[0].strip()
    return str(request.META.get('REMOTE_ADDR', '') or '').strip() or 'unknown'


def _ip_cache_key(request, window):
    raw = _client_ip(request)
    salt = getattr(settings, 'SECRET_KEY', 'public-assistant')
    digest = hashlib.sha256(f'{salt}:{raw}'.encode('utf-8')).hexdigest()[:24]
    return f'gof_public_assistant:{window}:{digest}'


def rate_limit_public_assistant(request):
    if request is None:
        return {'allowed': True, 'reason': ''}

    hour_limit = max(1, int(getattr(settings, 'GOF_PUBLIC_AI_ASSISTANT_MAX_MESSAGES_PER_IP_PER_HOUR', 5)))
    day_limit = max(1, int(getattr(settings, 'GOF_PUBLIC_AI_ASSISTANT_MAX_MESSAGES_PER_IP_PER_DAY', 20)))

    hour_key = _ip_cache_key(request, 'hour')
    day_key = _ip_cache_key(request, 'day')
    hour_count = cache.get(hour_key, 0)
    day_count = cache.get(day_key, 0)

    if hour_count >= hour_limit:
        return {'allowed': False, 'reason': 'hour'}
    if day_count >= day_limit:
        return {'allowed': False, 'reason': 'day'}

    try:
        hour_count = cache.incr(hour_key)
    except ValueError:
        cache.set(hour_key, 1, timeout=60 * 60)
        hour_count = 1
    else:
        cache.touch(hour_key, timeout=60 * 60)

    try:
        day_count = cache.incr(day_key)
    except ValueError:
        cache.set(day_key, 1, timeout=60 * 60 * 24)
        day_count = 1
    else:
        cache.touch(day_key, timeout=60 * 60 * 24)

    return {'allowed': True, 'reason': '', 'hour_count': hour_count, 'day_count': day_count}


def _language_copy(language):
    return language if language in {'en', 'nl', 'fr', 'pt'} else 'en'


def _site_status_context(language):
    site_status = getattr(settings, 'GOF_SITE_STATUS', 'pre_launch')
    launch_date = getattr(settings, 'GOF_PUBLIC_LAUNCH_DATE', None)
    if language == 'nl':
        if launch_date:
            launch_line = f'- Publieke launchdatum getoond in configuratie: {launch_date}\n'
        else:
            launch_line = '- Er wordt momenteel geen vaste publieke launchdatum getoond in de configuratie.\n'
        return (
            'Site-statuscontext:\n'
            f'- Get Online Fast status: {site_status}\n'
            f'{launch_line}'
            '- Als iemand vraagt wanneer "deze site" opent of lanceert, bedoelen ze meestal Get Online Fast zelf.\n'
            '- Veilige antwoordstijl voor launch/open-vragen zonder datum: '
            'Get Online Fast wordt voorbereid voor launch. Je kunt deze pagina nu al gebruiken om de dienst te bekijken '
            'en, als het startformulier beschikbaar is, je bedrijfsgegevens te sturen voor een private website preview. '
            'Er staat hier nog geen vaste publieke launchdatum.\n'
        )
    if language == 'fr':
        if launch_date:
            launch_line = f'- Date de lancement public affichée dans la configuration : {launch_date}\n'
        else:
            launch_line = '- Aucune date de lancement public fixe n’est affichée dans la configuration pour le moment.\n'
        return (
            'Contexte du statut du site :\n'
            f'- Statut de Get Online Fast : {site_status}\n'
            f'{launch_line}'
            '- Si quelqu’un demande quand "ce site" ouvre ou se lance, il parle généralement de Get Online Fast lui-même.\n'
            '- Réponse sûre pour les questions sur l’ouverture/le lancement sans date : '
            'Get Online Fast est en cours de préparation pour le lancement. Vous pouvez déjà utiliser cette page pour découvrir le service '
            'et, si le formulaire de démarrage est disponible, envoyer les détails de votre entreprise pour l’étape suivante. '
            'Aucune date de lancement public fixe n’est affichée ici.\n'
        )
    if language == 'pt':
        if launch_date:
            launch_line = f'- Data de lançamento público mostrada na configuração: {launch_date}\n'
        else:
            launch_line = '- Neste momento não existe uma data pública de lançamento fixa mostrada na configuração.\n'
        return (
            'Contexto do estado do site:\n'
            f'- Estado do Get Online Fast: {site_status}\n'
            f'{launch_line}'
            '- Se alguém perguntar quando "este site" abre ou é lançado, normalmente está a falar do próprio Get Online Fast.\n'
            '- Resposta segura para perguntas sobre abertura/lançamento sem data: '
            'O Get Online Fast está a ser preparado para o lançamento. Já pode usar esta página para conhecer o serviço '
            'e, se o formulário inicial estiver disponível, enviar os dados da sua empresa para o próximo passo. '
            'Ainda não existe aqui uma data pública de lançamento fixa.\n'
        )
    if launch_date:
        launch_line = f'- Public launch date shown in configuration: {launch_date}\n'
    else:
        launch_line = '- No fixed public launch date is shown in configuration right now.\n'
    return (
        'Site status context:\n'
        f'- Get Online Fast status: {site_status}\n'
        f'{launch_line}'
        '- If someone asks when "this site" opens or launches, they usually mean Get Online Fast itself.\n'
        '- Safe answer style for launch/open questions without a date: '
        'Get Online Fast is being prepared for launch. You can already use this page to learn about the service and, '
        'if the start form is available, send your business details for a private website preview. There is no public '
        'launch date shown here yet.\n'
    )


def _page_context_block(language, context):
    current_path = str((context or {}).get('current_path') or '').strip() or '/'
    current_page = str((context or {}).get('current_page') or '').strip()
    if language == 'nl':
        page_line = f'- Huidige paginacontext: {current_page}\n' if current_page else ''
        return (
            'Huidige bezoekcontext:\n'
            f'- Huidig pad: {current_path}\n'
            f'{page_line}'
            '- Gebruik deze context om antwoorden beter af te stemmen op de pagina die de bezoeker nu bekijkt.\n'
        )
    if language == 'fr':
        page_line = f'- Contexte de la page actuelle : {current_page}\n' if current_page else ''
        return (
            'Contexte de visite actuel :\n'
            f'- Chemin actuel : {current_path}\n'
            f'{page_line}'
            '- Utilisez ce contexte pour adapter la réponse à la page que le visiteur consulte en ce moment.\n'
        )
    if language == 'pt':
        page_line = f'- Contexto da página atual: {current_page}\n' if current_page else ''
        return (
            'Contexto atual do visitante:\n'
            f'- Caminho atual: {current_path}\n'
            f'{page_line}'
            '- Use este contexto para adaptar a resposta à página que o visitante está a ver neste momento.\n'
        )
    page_line = f'- Current page context: {current_page}\n' if current_page else ''
    return (
        'Current visitor context:\n'
        f'- Current path: {current_path}\n'
        f'{page_line}'
        '- Use this context to tailor answers to the page the visitor is viewing right now.\n'
    )


def _prompt_context(language, links, context):
    if language == 'nl':
        return (
            'Bedrijfscontext:\n'
            '- Get Online Fast bouwt snelle websites voor zzp\'ers en kleine bedrijven.\n'
            '- Productkaart: Starter Page = snelle gegenereerde startpagina; One-Time Website = volledige bedrijfswebsite; Monthly Website = website met hosting, support en doorlopende zorg; catalogus = producten tonen zonder volledige checkout; online shop = shop met checkout en betaalopties; promotie = launch posts en advertenties; business email = professioneel e-mailadres op domein; support = praktische hulp bij updates en verbeteringen.\n'
            '- De bezoeker bekijkt nu de Get Online Fast website.\n'
            '- "deze site" betekent normaal de Get Online Fast website.\n'
            '- "mijn site" of "onze website" betekent normaal het toekomstige websiteproject van de bezoeker.\n'
            '- Websites worden menselijk afgewerkt op WordPress.\n'
            '- Preview/testing gebeurt voor activatie of handoff wanneer van toepassing.\n'
            '- Publieke preview-creatie is momenteel niet algemeen beschikbaar.\n'
            '- Verwijs bij betalen of voorwaarden naar de juiste GOF pagina\'s.\n'
            '- Contact: {contact}\n'
            '- Support: {support}\n'
            '- Pakketten: {plans}\n'
            '- Betaling en annulering: {payment}\n'
            '- Catalogus en webshop: {catalog}\n'
            '- Promotie: {promotion}\n'
            '{page_context}'
            '{site_status}'
        ).format(
            contact=links.get('contact_url', ''),
            support=links.get('support_url', ''),
            plans=links.get('plans_url', ''),
            payment=links.get('payment_url', ''),
            catalog=links.get('catalog_url', ''),
            promotion=links.get('promotion_url', ''),
            page_context=_page_context_block(language, context),
            site_status=_site_status_context(language),
        )
    if language == 'fr':
        return (
            'Contexte commercial :\n'
            '- Get Online Fast crée des sites rapides pour les indépendants et les petites entreprises.\n'
            '- Carte produit : Starter Page = page de départ rapide générée ; site en paiement unique = site professionnel complet ; site mensuel = site avec hébergement, support et suivi ; catalogue = montrer des produits sans checkout complet ; boutique en ligne = boutique avec checkout et paiement ; promotion = posts de lancement et publicités ; e-mail professionnel = e-mail sur domaine ; support = aide pratique pour les mises à jour et améliorations.\n'
            '- Le visiteur consulte actuellement le site Get Online Fast.\n'
            '- "ce site" désigne généralement le site Get Online Fast lui-même.\n'
            '- "mon site", "notre site" ou "notre website" désignent généralement le futur projet du visiteur.\n'
            '- Les sites sont finalisés humainement sur WordPress.\n'
            '- L’aperçu et les tests ont lieu avant l’activation ou la remise quand cela s’applique.\n'
            '- La création publique d’aperçu n’est pas largement disponible pour le moment.\n'
            '- Utilisez les liens GOF fournis pour le paiement, les plans, le support et le contact.\n'
            '- Contact : {contact}\n'
            '- Support : {support}\n'
            '- Plans : {plans}\n'
            '- Paiement et annulation : {payment}\n'
            '- Catalogues et boutique en ligne : {catalog}\n'
            '- Promotion : {promotion}\n'
            '{page_context}'
            '{site_status}'
        ).format(
            contact=links.get('contact_url', ''),
            support=links.get('support_url', ''),
            plans=links.get('plans_url', ''),
            payment=links.get('payment_url', ''),
            catalog=links.get('catalog_url', ''),
            promotion=links.get('promotion_url', ''),
            page_context=_page_context_block(language, context),
            site_status=_site_status_context(language),
        )
    if language == 'pt':
        return (
            'Contexto do negócio:\n'
            '- O Get Online Fast cria websites rápidos para trabalhadores independentes e pequenas empresas.\n'
            '- Mapa de produtos: Starter Page = página inicial gerada para arranque rápido; One-Time Website = website empresarial completo; Monthly Website = website com alojamento, suporte e acompanhamento; catálogo = mostrar produtos sem checkout completo; loja online = loja com checkout e opções de pagamento; promoção = posts de lançamento e anúncios; business email = email profissional com domínio; suporte = ajuda prática com atualizações e melhorias.\n'
            '- O visitante está neste momento no website Get Online Fast.\n'
            '- "este site" normalmente significa o próprio website Get Online Fast.\n'
            '- "o meu site", "o meu website" ou "o nosso site" normalmente significam o futuro projeto do visitante.\n'
            '- Os websites são finalizados por pessoas em WordPress.\n'
            '- A pré-visualização e os testes acontecem antes da ativação ou da entrega quando isso se aplica.\n'
            '- A criação pública de pré-visualizações não está geralmente disponível neste momento.\n'
            '- Use os links GOF fornecidos para pagamento, planos, suporte e contacto.\n'
            '- Contacto: {contact}\n'
            '- Suporte: {support}\n'
            '- Planos: {plans}\n'
            '- Pagamento e cancelamento: {payment}\n'
            '- Catálogos e loja online: {catalog}\n'
            '- Promoção: {promotion}\n'
            '{page_context}'
            '{site_status}'
        ).format(
            contact=links.get('contact_url', ''),
            support=links.get('support_url', ''),
            plans=links.get('plans_url', ''),
            payment=links.get('payment_url', ''),
            catalog=links.get('catalog_url', ''),
            promotion=links.get('promotion_url', ''),
            page_context=_page_context_block(language, context),
            site_status=_site_status_context(language),
        )
    return (
        'Business context:\n'
        '- Get Online Fast builds fast websites for self-employed people and small businesses.\n'
        '- Product map: Starter Page = quick generated page; One-Time Website = full business website; Monthly Website = website with hosting, support, and ongoing care; product catalog = show products without full checkout; online shop = checkout and payment options when needed; promotion = launch posts and ads; business email = professional domain email setup; support = practical help with updates and improvements.\n'
        '- The visitor is currently on the Get Online Fast website.\n'
        '- "this site" usually means the Get Online Fast website itself.\n'
        '- "my site", "my website", or "our website" usually mean the visitor\'s future website project.\n'
        '- Websites are human-finished WordPress websites.\n'
        '- Preview/testing happens before activation or handoff where relevant.\n'
        '- Public preview creation is not generally available right now.\n'
        '- Use the provided GOF links for payment, plans, support, and contact.\n'
        '- Contact: {contact}\n'
        '- Support: {support}\n'
        '- Plans: {plans}\n'
        '- Payment and cancellation: {payment}\n'
        '- Catalogs and online shops: {catalog}\n'
        '- Promotion: {promotion}\n'
        '{page_context}'
        '{site_status}'
    ).format(
        contact=links.get('contact_url', ''),
        support=links.get('support_url', ''),
        plans=links.get('plans_url', ''),
        payment=links.get('payment_url', ''),
        catalog=links.get('catalog_url', ''),
        promotion=links.get('promotion_url', ''),
        page_context=_page_context_block(language, context),
        site_status=_site_status_context(language),
    )


def generate_public_assistant_answer_with_ai(message, language, links, context):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError('openai package unavailable') from exc

    language_name = {
        'nl': 'Dutch',
        'fr': 'French',
        'pt': 'Portuguese',
    }.get(language, 'English')
    prompt = (
        f'{PUBLIC_ASSISTANT_SYSTEM_PROMPT}\n\n'
        f'{_prompt_context(language, links, context)}\n'
        f'Reply language: {language_name}\n'
        f'Visitor message: {message}\n\n'
        'Return only the answer text. Keep it under 120 words when possible.'
    )

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.responses.create(
        model=getattr(settings, 'GOF_PUBLIC_AI_ASSISTANT_MODEL', settings.GOF_AI_MODEL),
        input=prompt,
        temperature=0.2,
        max_output_tokens=int(getattr(settings, 'GOF_PUBLIC_AI_ASSISTANT_MAX_OUTPUT_TOKENS', 250)),
    )

    answer = getattr(response, 'output_text', '') or ''
    if not answer.strip() and hasattr(response, 'model_dump'):
        response_dict = response.model_dump()
        for item in response_dict.get('output', []) if isinstance(response_dict, dict) else []:
            for content in item.get('content', []) if isinstance(item, dict) else []:
                text = content.get('text') if isinstance(content, dict) else ''
                if isinstance(text, str) and text.strip():
                    answer = text
                    break
            if answer.strip():
                break

    answer = ' '.join(str(answer or '').strip().split())
    if not answer:
        raise RuntimeError('public assistant returned empty answer')
    return answer


def _sanitized_openai_error(exc):
    error_text = ' '.join(str(exc or '').strip().split())
    if not error_text:
        return exc.__class__.__name__
    return f'{exc.__class__.__name__}: {error_text}'


def build_public_assistant_response(*, request, question, language, fallback_response, links, context=None):
    fallback = fallback_response if isinstance(fallback_response, Mapping) else {}
    fallback_intent = str(fallback.get('intent') or 'fallback')
    fallback_answer = str(fallback.get('answer') or '').strip()
    fallback_links = fallback.get('suggested_links') if isinstance(fallback.get('suggested_links'), list) else []
    language_code = _language_copy(language)
    status = public_assistant_status()
    diagnostics = {
        'received_message': str(question or ''),
        'route_function': 'core.views.assistant_help',
        'ai_enabled': status['ai_enabled'],
        'public_ai_enabled': status['public_ai_enabled'],
        'has_openai_key': status['has_openai_key'],
        'rate_limited': False,
        'input_valid': False,
        'selected_path_before_answer': '',
        'reason_selected_path': '',
        'did_attempt_openai': False,
        'openai_error': '',
        'final_mode': '',
    }

    def payload(*, answer, intent, suggested_links, mode, fallback_reason):
        diagnostics['final_mode'] = mode
        return {
            'intent': intent,
            'answer': answer,
            'suggested_links': suggested_links,
            'mode': mode,
            'fallback_reason': fallback_reason,
            'ai_enabled': status['ai_enabled'],
            'public_ai_enabled': status['public_ai_enabled'],
            'has_openai_key': status['has_openai_key'],
            'model_used': status['model_used'],
            'diagnostics': diagnostics,
        }

    normalized = normalize_public_assistant_input(question)
    diagnostics['input_valid'] = bool(normalized['valid'])
    if not normalized['valid']:
        diagnostics['selected_path_before_answer'] = 'fallback'
        diagnostics['reason_selected_path'] = f'input_{normalized["reason"]}'
        return payload(
            answer=fallback_answer,
            intent=fallback_intent,
            suggested_links=fallback_links,
            mode='fallback',
            fallback_reason=normalized['reason'],
        )

    if not status['ai_enabled']:
        diagnostics['selected_path_before_answer'] = 'disabled'
        diagnostics['reason_selected_path'] = 'gof_ai_disabled'
        return payload(
            answer=fallback_answer,
            intent=fallback_intent,
            suggested_links=fallback_links,
            mode='disabled',
            fallback_reason='gof_ai_disabled',
        )
    if not status['public_ai_enabled']:
        diagnostics['selected_path_before_answer'] = 'disabled'
        diagnostics['reason_selected_path'] = 'public_ai_disabled'
        return payload(
            answer=fallback_answer,
            intent=fallback_intent,
            suggested_links=fallback_links,
            mode='disabled',
            fallback_reason='public_ai_disabled',
        )
    if not status['has_openai_key']:
        diagnostics['selected_path_before_answer'] = 'disabled'
        diagnostics['reason_selected_path'] = 'missing_openai_key'
        return payload(
            answer=fallback_answer,
            intent=fallback_intent,
            suggested_links=fallback_links,
            mode='disabled',
            fallback_reason='missing_openai_key',
        )

    limited = rate_limit_public_assistant(request)
    diagnostics['rate_limited'] = not limited['allowed']
    if not limited['allowed']:
        diagnostics['selected_path_before_answer'] = 'fallback'
        diagnostics['reason_selected_path'] = f'rate_limit_{limited["reason"]}'
        return payload(
            answer=PUBLIC_ASSISTANT_RATE_LIMIT_RESPONSES[language_code],
            intent='rate_limited',
            suggested_links=[
                {'label': 'Support' if language_code == 'en' else 'Support', 'url': links.get('support_url', '')},
                {'label': 'Contact', 'url': links.get('contact_url', '')},
            ],
            mode='fallback',
            fallback_reason=f'rate_limit_{limited["reason"]}',
        )

    diagnostics['selected_path_before_answer'] = 'openai'
    diagnostics['reason_selected_path'] = 'ai_enabled_and_allowed'
    diagnostics['did_attempt_openai'] = True
    try:
        answer = generate_public_assistant_answer_with_ai(normalized['message'], language_code, links, context or {})
    except Exception as exc:
        logger.warning('Public assistant AI fallback triggered: %s', exc)
        diagnostics['openai_error'] = _sanitized_openai_error(exc)
        diagnostics['selected_path_before_answer'] = 'openai_error_fallback'
        diagnostics['reason_selected_path'] = 'openai_error'
        return payload(
            answer=fallback_answer,
            intent=fallback_intent,
            suggested_links=fallback_links,
            mode='error',
            fallback_reason='openai_error',
        )

    diagnostics['reason_selected_path'] = 'openai_answer_returned'
    return payload(
        answer=answer,
        intent=fallback_intent if fallback_intent != 'fallback' else 'ai_answer',
        suggested_links=fallback_links,
        mode='ai',
        fallback_reason='',
    )
