import json

from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.translation import gettext_lazy as _

from .models import Site, SiteContent, SiteHandoff, StarterOnboardingSubmission, Template, WebsiteRequest, WebsiteRequestFile


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'updated_at')
    search_fields = ('slug', 'name')


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = (
        'business_name',
        'service_type',
        'city',
        'template_slug',
        'latest_wordpress_handoff_status',
        'latest_wordpress_handoff_link',
        'created_at',
    )
    search_fields = ('business_name', 'service_type', 'city', 'template_slug')
    actions = ('prepare_wordpress_handoff',)
    readonly_fields = (
        'latest_wordpress_handoff_status',
        'latest_wordpress_handoff_link',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        (None, {
            'fields': ('business_name', 'service_type', 'city', 'template_slug', 'color_palette', 'user')
        }),
        (_('WordPress handoff'), {
            'fields': ('latest_wordpress_handoff_status', 'latest_wordpress_handoff_link')
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at')
        }),
    )

    @admin.action(description=_('Prepare WordPress handoff'))
    def prepare_wordpress_handoff(self, request, queryset):
        prepared_count = 0

        for site in queryset:
            handoff, created = SiteHandoff.objects.get_or_create(
                site=site,
                target_system='wordpress_jcw',
                defaults={
                    'status': SiteHandoff.Status.PREPARED,
                    'prepared_by': request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
                },
            )

            if not created:
                handoff.status = SiteHandoff.Status.PREPARED
                if getattr(request, 'user', None) and request.user.is_authenticated:
                    handoff.prepared_by = request.user
                handoff.save(update_fields=['status', 'prepared_by', 'updated_at'])

            handoff.refresh_payload()
            prepared_count += 1

        self.message_user(
            request,
            _('Prepared %(count)s WordPress handoff(s).') % {'count': prepared_count},
        )

    def _latest_wordpress_handoff(self, obj):
        return obj.handoffs.filter(target_system='wordpress_jcw').order_by('-updated_at', '-created_at').first()

    @admin.display(description=_('WP handoff status'))
    def latest_wordpress_handoff_status(self, obj):
        handoff = self._latest_wordpress_handoff(obj)
        if handoff is None:
            return _('No handoff')
        return handoff.get_status_display()

    @admin.display(description=_('WP handoff'))
    def latest_wordpress_handoff_link(self, obj):
        handoff = self._latest_wordpress_handoff(obj)
        if handoff is None:
            return '--'
        url = reverse('admin:ai_starter_sitehandoff_change', args=[handoff.pk])
        return format_html('<a href="{}">{}</a>', url, _('Open latest handoff'))


@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    list_display = ('site', 'section_key', 'field_key', 'language', 'updated_at')
    list_filter = ('language', 'section_key')
    search_fields = ('site__business_name', 'section_key', 'field_key', 'value')


@admin.register(StarterOnboardingSubmission)
class StarterOnboardingSubmissionAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'business_type', 'city', 'created_at')
    search_fields = ('business_name', 'business_type', 'city')


class WebsiteRequestFileInline(admin.TabularInline):
    model = WebsiteRequestFile
    extra = 0
    readonly_fields = ('original_name', 'file', 'created_at')


class WebsiteRequestBusinessTypeFilter(admin.SimpleListFilter):
    title = _('business type')
    parameter_name = 'business_type'

    def lookups(self, request, model_admin):
        values = (
            WebsiteRequest.objects.exclude(business_type='')
            .order_by('business_type')
            .values_list('business_type', flat=True)
            .distinct()
        )
        return [(value, value) for value in values[:50]]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        return queryset.filter(business_type=value)


@admin.register(WebsiteRequest)
class WebsiteRequestAdmin(admin.ModelAdmin):
    list_display = (
        'business_name',
        'business_type',
        'service_area',
        'contact_name',
        'contact_email',
        'main_language',
        'source_code',
        'status',
        'created_at',
    )
    list_filter = ('status', 'source_code', 'main_language', WebsiteRequestBusinessTypeFilter, 'created_at')
    search_fields = (
        'business_name',
        'business_type',
        'service_area',
        'business_address',
        'contact_name',
        'contact_email',
        'contact_phone',
        'contact_whatsapp',
        'current_domain',
    )
    readonly_fields = (
        'public_id',
        'storage_key',
        'created_at',
        'normal_price',
        'offer_price',
        'source_code',
        'starter_request_admin_summary',
    )
    inlines = [WebsiteRequestFileInline]
    actions = (
        'mark_as_reviewed',
        'mark_as_contacted',
        'mark_as_cancelled',
    )
    fieldsets = (
        (_('Starter request summary'), {
            'fields': ('starter_request_admin_summary',),
        }),
        (_('Business'), {
            'fields': (
                'business_name',
                'business_type',
                'business_address',
                'service_area',
                'main_services',
                'business_description',
                'main_language',
                'extra_languages',
            ),
        }),
        (_('Contact'), {
            'fields': (
                'contact_name',
                'contact_email',
                'contact_phone',
                'contact_whatsapp',
                'opening_hours',
                'social_links',
            ),
        }),
        (_('Website request details'), {
            'fields': (
                'existing_website_url',
                'current_domain',
                'needs_domain_help',
                'preferred_colors',
                'style_notes',
                'special_requests',
            ),
        }),
        (_('Tracking'), {
            'fields': (
                'status',
                'source_code',
                'normal_price',
                'offer_price',
                'public_id',
                'storage_key',
                'created_at',
            ),
        }),
    )

    @admin.display(description=_('Starter request summary'))
    def starter_request_admin_summary(self, obj):
        summary_items = [
            ('Business', obj.business_name or '--'),
            ('Type', obj.business_type or '--'),
            ('Area', obj.service_area or obj.business_address or '--'),
            ('Language', obj.main_language or '--'),
            ('Contact', obj.contact_name or obj.contact_email or '--'),
            ('Email', obj.contact_email or '--'),
        ]
        note_lines = [line.strip() for line in (obj.special_requests or '').splitlines() if line.strip()]
        service_lines = [line.strip() for line in (obj.main_services or '').splitlines() if line.strip()]
        style_lines = [line.strip() for line in (obj.style_notes or '').splitlines() if line.strip()]

        chunks = ['<div class="help">']
        for label, value in summary_items:
            chunks.append(f'<p><strong>{escape(label)}:</strong> {escape(value)}</p>')
        if service_lines:
            chunks.append(f"<p><strong>{escape(_('Services'))}:</strong> {escape(', '.join(service_lines[:6]))}</p>")
        if style_lines:
            chunks.append(f"<p><strong>{escape(_('Style'))}:</strong> {escape(' | '.join(style_lines[:4]))}</p>")
        if note_lines:
            chunks.append(f"<p><strong>{escape(_('Notes'))}:</strong> {escape(' | '.join(note_lines[:4]))}</p>")
        chunks.append('</div>')
        return format_html(''.join(chunks))

    @admin.action(description=_('Mark selected starter requests as Reviewed'))
    def mark_as_reviewed(self, request, queryset):
        updated = queryset.update(status=WebsiteRequest.Status.REVIEWED)
        self.message_user(
            request,
            _('Marked %(count)s website request(s) as Reviewed.') % {'count': updated},
            level=messages.SUCCESS,
        )

    @admin.action(description=_('Mark selected starter requests as Contacted'))
    def mark_as_contacted(self, request, queryset):
        updated = queryset.update(status=WebsiteRequest.Status.CONTACTED)
        self.message_user(
            request,
            _('Marked %(count)s website request(s) as Contacted.') % {'count': updated},
            level=messages.SUCCESS,
        )

    @admin.action(description=_('Mark selected starter requests as Cancelled'))
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status=WebsiteRequest.Status.CANCELLED)
        self.message_user(
            request,
            _('Marked %(count)s website request(s) as Cancelled.') % {'count': updated},
            level=messages.SUCCESS,
        )


@admin.register(SiteHandoff)
class SiteHandoffAdmin(admin.ModelAdmin):
    list_display = (
        'site',
        'status',
        'target_system',
        'wordpress_site_url',
        'wordpress_user_reference',
        'staff_ai_brief_generated_at',
        'created_at',
        'updated_at',
    )
    list_filter = ('status', 'target_system', 'created_at')
    search_fields = (
        'site__business_name',
        'site__service_type',
        'site__city',
        'website_request__business_name',
        'website_request__contact_name',
        'website_request__contact_email',
        'wordpress_user_reference',
        'notes',
    )
    actions = ('generate_staff_ai_handoff_brief',)
    readonly_fields = (
        'payload_summary',
        'request_contact_summary',
        'pretty_payload',
        'handoff_payload',
        'staff_ai_brief',
        'staff_ai_brief_generated_at',
        'staff_ai_brief_error',
        'created_at',
        'updated_at',
        'completed_at',
    )
    fieldsets = (
        (_('Source'), {
            'fields': (
                'site',
                'website_request',
                'payload_summary',
                'request_contact_summary',
            )
        }),
        (_('Status'), {
            'fields': (
                'status',
                'target_system',
                'prepared_by',
            )
        }),
        (_('WordPress target'), {
            'fields': (
                'wordpress_site_url',
                'wordpress_admin_url',
                'wordpress_user_reference',
            )
        }),
        (_('Notes and dates'), {
            'fields': (
                'notes',
                'created_at',
                'updated_at',
                'completed_at',
            )
        }),
        (_('Staff AI brief'), {
            'fields': (
                'staff_ai_brief_generated_at',
                'staff_ai_brief_error',
                'staff_ai_brief',
            )
        }),
        (_('Payload inspection'), {
            'fields': (
                'pretty_payload',
                'handoff_payload',
            )
        }),
    )

    @admin.action(description=_('Generate staff AI handoff brief'))
    def generate_staff_ai_handoff_brief(self, request, queryset):
        generated_count = 0
        failed_count = 0

        for handoff in queryset:
            try:
                handoff.generate_staff_ai_brief()
            except Exception as exc:
                failed_count += 1
                self.message_user(
                    request,
                    _('Could not generate staff AI brief for %(site)s: %(error)s') % {
                        'site': handoff.site.business_name,
                        'error': str(exc),
                    },
                    level=messages.ERROR,
                )
                continue

            generated_count += 1

        if generated_count:
            self.message_user(
                request,
                _('Generated %(count)s staff AI handoff brief(s).') % {'count': generated_count},
            )
        if failed_count and not generated_count:
            self.message_user(
                request,
                _('No staff AI handoff briefs were generated.'),
                level=messages.WARNING,
            )

    @admin.display(description=_('Payload summary'))
    def payload_summary(self, obj):
        payload = obj.handoff_payload or {}
        source = payload.get('source') or {}
        business = payload.get('business') or {}
        design = payload.get('design') or {}
        website_request = payload.get('website_request') or {}
        wordpress_target = payload.get('wordpress_target') or {}
        content_rows = payload.get('content') or []

        contact_bits = []
        if website_request.get('contact_email'):
            contact_bits.append(f"Email: {website_request['contact_email']}")
        if website_request.get('contact_phone'):
            contact_bits.append(f"Phone: {website_request['contact_phone']}")

        target_values = [
            wordpress_target.get('site_url'),
            wordpress_target.get('admin_url'),
            wordpress_target.get('user_reference'),
        ]
        target_note = _('Manual/empty target') if not any(target_values) else _('Target details present')

        lines = [
            f"Schema: {payload.get('schema_version', '--')}",
            f"Source public ID: {source.get('public_id', '--')}",
            f"Business: {business.get('business_name', '--')}",
            f"Service type: {business.get('service_type', '--')}",
            f"City: {business.get('city', '--')}",
            f"Template: {design.get('template_slug', '--')}",
            f"Color palette: {design.get('color_palette', '--')}",
            f"Content rows: {len(content_rows)}",
        ]
        if contact_bits:
            lines.append(' | '.join(contact_bits))
        lines.append(str(target_note))

        return format_html(
            '<pre style="white-space:pre-wrap;margin:0;">{}</pre>',
            escape('\n'.join(lines)),
        )

    @admin.display(description=_('Request / contact summary'))
    def request_contact_summary(self, obj):
        website_request = obj.website_request
        payload_request = (obj.handoff_payload or {}).get('website_request') or {}

        if website_request is None and not payload_request:
            return _('No request linked')

        def pick(name):
            value = getattr(website_request, name, None) if website_request is not None else None
            if value in (None, ''):
                value = payload_request.get(name, '')
            return str(value).strip() if value not in (None, '') else ''

        lines = [
            f"Contact: {pick('contact_name') or '--'}",
            f"Email: {pick('contact_email') or '--'}",
            f"Phone / WhatsApp: {pick('contact_phone') or pick('contact_whatsapp') or '--'}",
            f"Business type: {pick('business_type') or '--'}",
            f"Language: {pick('main_language') or '--'}",
            f"Domain: {pick('current_domain') or '--'}",
            f"Status / source: {' | '.join(bit for bit in [pick('status'), pick('source_code')] if bit) or '--'}",
        ]

        request_link = ''
        if website_request is not None:
            url = reverse('admin:ai_starter_websiterequest_change', args=[website_request.pk])
            request_link = str(format_html('<div style="margin-top:8px;"><a href="{}">{}</a></div>', url, _('Open linked request in admin')))

        return format_html(
            '<div><pre style="white-space:pre-wrap;margin:0;">{}</pre>{}</div>',
            escape('\n'.join(lines)),
            format_html(request_link) if request_link else '',
        )

    @admin.display(description=_('Pretty payload'))
    def pretty_payload(self, obj):
        payload = obj.handoff_payload or {}
        pretty = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
        return format_html(
            '<pre style="white-space:pre-wrap;max-width:100%;overflow:auto;margin:0;">{}</pre>',
            escape(pretty),
        )
