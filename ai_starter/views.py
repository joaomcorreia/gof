from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .forms import StarterOnboardingForm
from .models import Site, Template
from .services import (
    available_palette_options,
    available_template_options,
    build_editor_sections,
    build_render_sections,
    build_suggestions,
    ensure_language_content,
    ensure_default_templates,
    save_site_content,
    site_slug,
)


@require_http_methods(['GET', 'POST'])
def start_onboarding(request):
    ensure_default_templates()
    if request.method == 'POST':
        form = StarterOnboardingForm(request.POST)
        if form.is_valid():
            site = Site.objects.create(
                user=request.user if request.user.is_authenticated else None,
                template_slug='local_service',
                business_name=form.cleaned_data['business_name'],
                service_type=form.cleaned_data['service_type'],
                city=form.cleaned_data['city'],
            )
            save_site_content(
                site,
                request.LANGUAGE_CODE,
                build_suggestions(
                    business_name=site.business_name,
                    service_type=site.service_type,
                    city=site.city,
                    template_slug=site.template_slug,
                ),
            )
            return redirect('ai_starter:preview', public_id=site.public_id)

        return render(
            request,
            'ai_starter/start.html',
            {
                'form': form,
            },
            status=400,
        )

    return render(
        request,
        'ai_starter/start.html',
        {
            'form': StarterOnboardingForm(),
        },
    )


@require_http_methods(['GET', 'POST'])
def preview(request, public_id):
    ensure_default_templates()
    site = get_object_or_404(Site, public_id=public_id)
    language = request.LANGUAGE_CODE
    ensure_language_content(site, language)

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        if action == 'apply_template':
            selected_template = request.POST.get('template_slug', '').strip()
            if Template.objects.filter(slug=selected_template).exists():
                site.template_slug = selected_template
                site.save(update_fields=['template_slug', 'updated_at'])
                site.contents.all().delete()
                save_site_content(
                    site,
                    language,
                    build_suggestions(
                        business_name=site.business_name,
                        service_type=site.service_type,
                        city=site.city,
                        template_slug=site.template_slug,
                    ),
                )
        elif action == 'apply_palette':
            selected_palette = request.POST.get('color_palette', '').strip()
            valid_palettes = {choice for choice, _label in Site.ColorPalette.choices}
            if selected_palette in valid_palettes:
                site.color_palette = selected_palette
                site.save(update_fields=['color_palette', 'updated_at'])
        elif action == 'regenerate':
            save_site_content(
                site,
                language,
                build_suggestions(
                    business_name=site.business_name,
                    service_type=site.service_type,
                    city=site.city,
                    template_slug=site.template_slug,
                ),
            )
        else:
            for content in site.contents.filter(language=language):
                posted_value = request.POST.get(f'content__{content.id}')
                if posted_value is not None:
                    content.value = posted_value
                    content.save(update_fields=['value', 'updated_at'])
        return redirect('ai_starter:preview', public_id=site.public_id)

    return render(
        request,
        'ai_starter/preview.html',
        {
            'site': site,
            'site_slug': site_slug(site),
            'editor_sections': build_editor_sections(site, language),
            'template_options': available_template_options(),
            'palette_options': available_palette_options(),
        },
    )


@xframe_options_sameorigin
def preview_frame(request, public_id):
    ensure_default_templates()
    site = get_object_or_404(Site, public_id=public_id)
    language = request.LANGUAGE_CODE
    ensure_language_content(site, language)
    return render(
        request,
        'ai_starter/frame.html',
        {
            'site': site,
            'site_slug': site_slug(site),
            'render_sections': build_render_sections(site, language),
        },
    )
