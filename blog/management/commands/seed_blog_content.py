from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import BlogCategory, BlogPost


LEGACY_CATEGORY_DESCRIPTIONS = {
    'Website Basics and practical setup guidance.',
    'Visibility, traffic, and customer growth ideas.',
    'Hosting, speed, and performance basics.',
    'Practical product and workflow guides.',
    'Guides intended for logged-in users.',
}

LEGACY_POST_BODIES = {
    'A short comparison of the two hosting approaches and when each one makes sense for a small business website.',
    'A simple overview of what happens first, what you need to provide, and how quickly a website can move from preview to launch.',
    'Regular posts help businesses stay visible, create repeat awareness, and give people more reasons to contact you.',
    'A website gives your business a base, but it still needs visibility work such as search structure, content, and promotion.',
    'This placeholder guide explains the next practical steps after sign-up, including setup, review, and launch preparation.',
    'A short guide to finding your main controls, reviewing your website, and understanding the most useful actions first.',
    'A simple explanation of how to request updates or edit the parts of your website that need to stay current.',
    'This guide explains how to update phone numbers, email addresses, and business details when something changes.',
    'A practical overview of how to ask for changes, what to include, and how support requests are usually handled.',
    'A short explanation of how structure, visibility, contact options, and follow-up support work together over time.',
}


CATEGORY_DATA = [
    {
        'title': 'Website Basics',
        'slug': 'website-basics',
        'description': 'Foundational website topics for small business owners who want a clear, useful online presence.',
        'is_public': True,
        'order': 1,
    },
    {
        'title': 'Growth & Marketing',
        'slug': 'growth-marketing',
        'description': 'Simple visibility, promotion, and customer-growth ideas that help a website bring more business.',
        'is_public': True,
        'order': 2,
    },
    {
        'title': 'Hosting & Performance',
        'slug': 'hosting-performance',
        'description': 'Straightforward guidance about hosting, speed, reliability, and the technical basics that affect your website.',
        'is_public': True,
        'order': 3,
    },
    {
        'title': 'Get Online Fast Guides',
        'slug': 'get-online-fast-guides',
        'description': 'Practical explanations of how Get Online Fast works, from first preview to launch and follow-up support.',
        'is_public': True,
        'order': 4,
    },
    {
        'title': 'Customer Guides',
        'slug': 'customer-guides',
        'description': 'Logged-in customer help articles for managing content, requesting support, and understanding what happens next.',
        'is_public': False,
        'order': 5,
    },
]


POST_DATA = [
    {
        'title': 'Shared Hosting vs VPS Hosting',
        'slug': 'shared-hosting-vs-vps-hosting',
        'category': 'Hosting & Performance',
        'visibility': BlogPost.Visibility.PUBLIC,
        'order': 1,
        'featured_image': '/static/core/img/blog/shared-hosting-vs-vps.jpeg',
        'excerpt': 'A simple explanation of the difference between shared hosting and VPS hosting, and when a small business should upgrade.',
        'body': (
            '## Shared hosting keeps costs low\n\n'
            'Shared hosting means many websites use the same server resources. That can be perfectly fine for a very small website with light traffic, a few pages, and simple contact needs.\n\n'
            '## VPS gives more stability\n\n'
            'A VPS gives your website more stable resources and better control. It is usually a better fit when speed, reliability, email setup, security, or business growth starts to matter more.\n\n'
            '## When shared hosting is still enough\n\n'
            'If your website is basic, does not get many visitors yet, and mainly acts as a simple online business card, shared hosting may still do the job.\n\n'
            '## When it is time to upgrade\n\n'
            'If your business depends on website enquiries, business email, better loading speed, or a more reliable setup, VPS hosting is often the safer choice.\n\n'
            '## Need help?\n\n'
            'You do not need to make this choice alone. Get Online Fast can help you choose a hosting setup that fits your business without turning it into a technical project.'
        ),
    },
    {
        'title': 'How Fast Can You Launch a Website with Get Online Fast?',
        'slug': 'how-fast-can-you-launch-a-website-with-get-online-fast',
        'category': 'Get Online Fast Guides',
        'visibility': BlogPost.Visibility.PUBLIC,
        'order': 2,
        'excerpt': 'What happens after signup, what we need from you, and how quickly your website can move from preview to launch.',
        'body': (
            '## It starts with your preview or signup\n\n'
            'The first step is starting a preview or confirming that you want to move forward. That gives us the basic direction for your website.\n\n'
            '## We need your business details\n\n'
            'A fast launch depends on how quickly you provide the basics: your business name, services, city, contact details, and any key information you want visitors to see.\n\n'
            '## We set up the structure and content\n\n'
            'Once we have the right details, the website structure and first content can be prepared. This includes your service flow, contact path, and any launch essentials.\n\n'
            '## You review and request corrections\n\n'
            'Before launch, you can review the setup and ask for corrections. This stage is important because small adjustments can make the website clearer and more useful.\n\n'
            '## Launch happens on a domain or subdomain\n\n'
            'Your website can go live on a project subdomain or on your own domain. If a domain connection is needed, domain propagation may still take some time after the final launch step.\n\n'
            '## Next step\n\n'
            'The fastest launches happen when business details are ready early. If you want to move quickly, prepare your contact information, services, and any important corrections as soon as possible.'
        ),
    },
    {
        'title': 'Why Posting on Facebook Consistently Helps You Get Customers',
        'slug': 'why-posting-on-facebook-consistently-helps-you-get-customers',
        'category': 'Growth & Marketing',
        'visibility': BlogPost.Visibility.PUBLIC,
        'order': 3,
        'excerpt': 'Regular posts keep your business visible, create repeat awareness, and give people more reasons to contact you.',
        'body': (
            '## A website alone is not enough\n\n'
            'A website gives your business a place to send people, but that does not automatically create attention. People still need reminders that your business exists.\n\n'
            '## Facebook keeps your business visible\n\n'
            'Regular posts help you appear in front of local people again and again. That repeat visibility matters because many customers do not contact a business the first time they see it.\n\n'
            '## Repetition builds trust\n\n'
            'When people keep seeing your name, services, and examples of work, your business feels more familiar. Familiarity often makes it easier for someone to call, message, or ask for a quote.\n\n'
            '## Posts can send traffic back to your website\n\n'
            'Facebook is useful for awareness, but your website is still the place where people can read more, understand your services, and contact you properly.\n\n'
            '## What works well\n\n'
            'Offers, before-and-after photos, short tips, reminders, and practical service updates often work better than trying to post something complicated every time.\n\n'
            '## Need help?\n\n'
            'If you want consistency without handling every post yourself, Get Online Fast can help with monthly posting support that keeps your business active online.'
        ),
    },
    {
        'title': 'Why a Website Alone Does Not Bring Visitors',
        'slug': 'why-a-website-alone-does-not-bring-visitors',
        'category': 'Growth & Marketing',
        'visibility': BlogPost.Visibility.PUBLIC,
        'order': 4,
        'excerpt': 'A website gives your business a base, but it still needs visibility through search, social media, content, and promotion.',
        'body': (
            '## Your website is the foundation\n\n'
            'A website gives your business a professional base. It explains your services, shows how to contact you, and helps people take the next step.\n\n'
            '## Visitors come from somewhere else first\n\n'
            'Most visitors arrive through Google, Facebook, referrals, ads, links from other websites, or repeat exposure over time. The website helps convert attention into contact, but it does not create all the attention by itself.\n\n'
            '## Search visibility takes time\n\n'
            'SEO can help, but it usually builds gradually. Small businesses often need patience, better service pages, and steady improvements before search traffic becomes consistent.\n\n'
            '## Social posts and ads can speed things up\n\n'
            'Facebook posts, local promotion, and Google Ads can help more people discover your business sooner while search visibility is still growing.\n\n'
            '## Structure helps conversion\n\n'
            'Once people arrive, clear service pages and simple contact forms help turn that visit into a call, message, or quote request.\n\n'
            '## Next step\n\n'
            'Think of your website as the place where interest becomes action. If you want more visitors, add visibility work around it instead of expecting the website to do everything alone.'
        ),
    },
    {
        'title': 'What Happens After You Sign Up?',
        'slug': 'what-happens-after-you-sign-up',
        'category': 'Get Online Fast Guides',
        'visibility': BlogPost.Visibility.PUBLIC,
        'order': 5,
        'excerpt': 'A simple step-by-step explanation of what happens after you request or start your website.',
        'body': (
            '## First comes confirmation\n\n'
            'After you sign up or confirm that you want to move forward, the next step is making sure we have the right contact information and the correct business direction.\n\n'
            '## Then we collect your business details\n\n'
            'This includes the services you want to highlight, the city or areas you serve, and the key contact details customers should see.\n\n'
            '## You receive a first preview\n\n'
            'A preview helps you understand the structure before the website goes fully live. At this stage, it is normal to request small changes.\n\n'
            '## Review and corrections\n\n'
            'You can send updates, corrections, and clarifications so the website reflects your business more accurately.\n\n'
            '## Domain, email, and contact setup\n\n'
            'If your plan includes domain or email support, those setup steps can happen before or alongside launch. Contact forms should also be tested so enquiries reach the right place.\n\n'
            '## Launch and support\n\n'
            'Once everything is ready, the website can go live. After that, future updates and support depend on the plan you chose.\n\n'
            '## Need help?\n\n'
            'If you are unsure what to send first, start with your business name, services, and contact details. That usually makes the next steps much easier.'
        ),
    },
    {
        'title': 'Website vs Facebook Page: Why Your Business Should Have Both',
        'slug': 'website-vs-facebook-page-why-your-business-should-have-both',
        'category': 'Website Basics',
        'visibility': BlogPost.Visibility.PUBLIC,
        'order': 6,
        'excerpt': 'A Facebook page helps people discover your business, while a website gives them a stronger place to learn more and contact you properly.',
        'body': (
            '## They do different jobs\n\n'
            'A Facebook page helps people notice your business. A website helps them understand what you offer and take action with more confidence.\n\n'
            '## Social media is useful for visibility\n\n'
            'Facebook is good for reminders, updates, offers, and staying visible in front of local people.\n\n'
            '## Your website gives you more control\n\n'
            'A website lets you structure services clearly, show proper contact details, and create a more professional impression than a social profile alone.\n\n'
            '## Together they work better\n\n'
            'Facebook can send attention to your website, and your website can help convert that attention into enquiries.\n\n'
            '## Next step\n\n'
            'If you already have a Facebook page, the website should support it, not replace it. The best result usually comes from using both together.'
        ),
    },
    {
        'title': 'What Pages Does a Small Business Website Need?',
        'slug': 'what-pages-does-a-small-business-website-need',
        'category': 'Website Basics',
        'visibility': BlogPost.Visibility.PUBLIC,
        'order': 7,
        'excerpt': 'Most small business websites do not need dozens of pages, but they do need the right pages in the right order.',
        'body': (
            '## Start with the essentials\n\n'
            'Most small businesses need a homepage, service pages, a contact page, and a clear way for people to reach them.\n\n'
            '## Service pages matter more than people expect\n\n'
            'If visitors cannot quickly understand what you do, they are less likely to contact you. Clear service pages help both people and search engines.\n\n'
            '## About and trust pages help too\n\n'
            'An about page, testimonials, or practical trust signals can help a business feel more established.\n\n'
            '## Do not add pages just to look bigger\n\n'
            'A shorter, clearer website often works better than a large site with weak content.\n\n'
            '## Need help?\n\n'
            'If you are not sure what pages you need, start with the pages that explain services and make contact simple. Extra pages can always be added later.'
        ),
    },
    {
        'title': 'Why Website Speed Matters for Small Businesses',
        'slug': 'why-website-speed-matters-for-small-businesses',
        'category': 'Hosting & Performance',
        'visibility': BlogPost.Visibility.PUBLIC,
        'order': 8,
        'excerpt': 'A faster website feels more professional, keeps visitors engaged longer, and can make it easier for customers to contact you.',
        'body': (
            '## Speed affects first impressions\n\n'
            'If a website feels slow, visitors may leave before reading your services or contact details.\n\n'
            '## Faster websites feel more trustworthy\n\n'
            'A quick-loading site often feels more modern and better maintained, especially on phones where patience is limited.\n\n'
            '## Speed also affects growth\n\n'
            'Better hosting, lighter pages, and cleaner setup can help with search visibility and conversion because visitors stay on the site longer.\n\n'
            '## Small businesses do not need perfection\n\n'
            'You do not need a highly technical setup to improve speed. A practical, stable website is usually enough to create a better user experience.\n\n'
            '## Next step\n\n'
            'If your website feels slow, focus first on hosting quality, page weight, and clean structure. Those basics usually matter more than complex tricks.'
        ),
    },
    {
        'title': 'How Customers Contact You Through Your Website',
        'slug': 'how-customers-contact-you-through-your-website',
        'category': 'Website Basics',
        'visibility': BlogPost.Visibility.PUBLIC,
        'order': 9,
        'excerpt': 'A website should make it easy for customers to call, send a message, or request a quote without confusion.',
        'body': (
            '## The contact path should be obvious\n\n'
            'Visitors should not have to search for a phone number, form, or next step. If contact is hidden, many people will leave instead of trying harder.\n\n'
            '## Different people prefer different methods\n\n'
            'Some customers want to call. Others prefer a contact form, WhatsApp, or email. A clear website gives a few practical options without making the page messy.\n\n'
            '## Good service pages support contact\n\n'
            'When service pages are clear, people arrive at the contact step with more confidence. That usually means better-quality enquiries.\n\n'
            '## Follow-up still matters\n\n'
            'The website helps people reach you, but quick follow-up is what turns interest into real customers.\n\n'
            '## Need help?\n\n'
            'If you want more enquiries, review whether your website makes the contact step clear, fast, and visible on mobile as well as desktop.'
        ),
    },
    {
        'title': 'How Get Online Fast Helps You Start Getting Customers',
        'slug': 'how-get-online-fast-helps-you-start-getting-customers',
        'category': 'Get Online Fast Guides',
        'visibility': BlogPost.Visibility.PUBLIC,
        'order': 10,
        'excerpt': 'Get Online Fast helps combine website structure, contact tools, and practical visibility support so a business can start building momentum.',
        'body': (
            '## It starts with a clear website base\n\n'
            'The first goal is giving your business a website that explains services properly and makes contact easy.\n\n'
            '## Visibility support matters too\n\n'
            'A website works better when it is supported by local visibility, stronger service pages, social posting, or other promotion when needed.\n\n'
            '## Contact tools help turn attention into enquiries\n\n'
            'Forms, calls, WhatsApp, and strong calls to action all make it easier for visitors to become real leads.\n\n'
            '## Growth can happen step by step\n\n'
            'You do not need to launch everything at once. Many businesses start with the basics and add more visibility support later.\n\n'
            '## Next step\n\n'
            'If you want to start getting customers more consistently, the best first move is often a clear website plus one practical visibility channel that keeps your business in front of people.'
        ),
    },
    {
        'title': 'How to Use Your Website Dashboard',
        'slug': 'how-to-use-your-website-dashboard',
        'category': 'Customer Guides',
        'visibility': BlogPost.Visibility.USERS_ONLY,
        'order': 11,
        'excerpt': 'A simple guide to understanding the main areas of your dashboard and what to do first.',
        'body': (
            '## Start with the overview\n\n'
            'Your dashboard should help you understand the most important parts of your website first: what is live, what needs updating, and where to request changes.\n\n'
            '## Check the basics regularly\n\n'
            'Look at your contact details, visible service content, and any guides or support notes that help you manage the website more confidently.\n\n'
            '## Use it as a working tool\n\n'
            'The dashboard is not just there for technical settings. It should help you keep your website accurate, usable, and ready for new customers.\n\n'
            '## Need help?\n\n'
            'If something in the dashboard feels unclear, make note of it and ask for support. A clear dashboard saves time only when you know where to look.'
        ),
    },
    {
        'title': 'How to Edit Your Website Content',
        'slug': 'how-to-edit-your-website-content',
        'category': 'Customer Guides',
        'visibility': BlogPost.Visibility.USERS_ONLY,
        'order': 12,
        'excerpt': 'A practical guide to keeping your website content current as your business changes.',
        'body': (
            '## Keep the important parts current\n\n'
            'The most important updates are usually your services, prices if shown, opening details, and contact information.\n\n'
            '## Small updates matter\n\n'
            'Even short edits can improve clarity. If a visitor understands your service faster, they are more likely to contact you.\n\n'
            '## Prepare changes clearly\n\n'
            'It helps to send updates in a simple format: what should change, where it appears, and what the new wording should be.\n\n'
            '## Next step\n\n'
            'Make a habit of reviewing your website content every so often, especially when your services, offers, or contact details change.'
        ),
    },
    {
        'title': 'How to Change Your Contact Details',
        'slug': 'how-to-change-your-contact-details',
        'category': 'Customer Guides',
        'visibility': BlogPost.Visibility.USERS_ONLY,
        'order': 13,
        'excerpt': 'How to update the phone number, email, address, or other contact information that visitors rely on.',
        'body': (
            '## Accurate contact details are essential\n\n'
            'If your contact details are wrong or outdated, even a good website can lose customers.\n\n'
            '## Check all visible contact points\n\n'
            'Review the contact page, footer, forms, email addresses, and any other areas where customers are expected to reach you.\n\n'
            '## Update quickly when something changes\n\n'
            'Phone numbers, business addresses, and service areas should be kept current as soon as they change.\n\n'
            '## Need help?\n\n'
            'If you are unsure where your contact details appear across the website, ask for support so everything stays consistent.'
        ),
    },
    {
        'title': 'How to Request Changes or Support',
        'slug': 'how-to-request-changes-or-support',
        'category': 'Customer Guides',
        'visibility': BlogPost.Visibility.USERS_ONLY,
        'order': 14,
        'excerpt': 'A simple guide to asking for changes clearly so updates can be handled faster and with less back and forth.',
        'body': (
            '## Start with the exact change\n\n'
            'When you request support, explain what should change, where it appears, and what the correct result should be.\n\n'
            '## Keep the request practical\n\n'
            'A short, clear message is usually better than a long message with mixed topics. If you have several changes, list them separately.\n\n'
            '## Include missing details early\n\n'
            'If the update involves contact details, new text, or an image, send those at the start. That reduces delays.\n\n'
            '## Next step\n\n'
            'Good support requests save time for everyone. If you are not sure how to phrase a request, start with the page name and the exact section that needs attention.'
        ),
    },
    {
        'title': 'How Your Website Helps You Get New Customers',
        'slug': 'how-your-website-helps-you-get-new-customers',
        'category': 'Customer Guides',
        'visibility': BlogPost.Visibility.USERS_ONLY,
        'order': 15,
        'excerpt': 'A practical explanation of how your website supports visibility, trust, and customer enquiries over time.',
        'body': (
            '## Your website supports the decision process\n\n'
            'Many customers want to check a business online before they contact it. A clear website helps them feel more certain.\n\n'
            '## Structure helps people understand the offer\n\n'
            'When services, locations, and contact options are easy to understand, visitors can move from interest to action more quickly.\n\n'
            '## Visibility and trust work together\n\n'
            'Your website becomes more useful when people can find it through search, social posts, referrals, or promotion.\n\n'
            '## Need help?\n\n'
            'If you want better results, look at both sides: how people find the website and how the website helps them contact you once they arrive.'
        ),
    },
]


class Command(BaseCommand):
    help = 'Seed useful starter blog categories and posts without overwriting genuinely edited content.'

    def handle(self, *args, **options):
        category_map = {}
        created_categories = []
        updated_categories = []
        created_posts = []
        updated_posts = []

        for category_data in CATEGORY_DATA:
            category, was_created, was_updated = self._upsert_category(category_data)
            category_map[category_data['title']] = category
            if was_created:
                created_categories.append(category.title)
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.title}'))
            elif was_updated:
                updated_categories.append(category.title)
                self.stdout.write(self.style.WARNING(f'Updated category: {category.title}'))

        for post_data in POST_DATA:
            post, was_created, was_updated = self._upsert_post(post_data, category_map)
            if was_created:
                created_posts.append(post.title)
                self.stdout.write(self.style.SUCCESS(f'Created post: {post.title}'))
            elif was_updated:
                updated_posts.append(post.title)
                self.stdout.write(self.style.WARNING(f'Updated post: {post.title}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Seed summary'))
        self.stdout.write(f'Categories created: {len(created_categories)}')
        self.stdout.write(f'Categories updated: {len(updated_categories)}')
        self.stdout.write(f'Posts created: {len(created_posts)}')
        self.stdout.write(f'Posts updated: {len(updated_posts)}')

    def _upsert_category(self, category_data):
        category, created = BlogCategory.objects.get_or_create(
            slug=category_data['slug'],
            language='en',
            defaults={
                'title': category_data['title'],
                'description': category_data['description'],
                'is_public': category_data['is_public'],
                'order': category_data['order'],
            },
        )
        if created:
            return category, True, False

        updated = False
        if category.title != category_data['title']:
            category.title = category_data['title']
            updated = True
        if not category.description or category.description in LEGACY_CATEGORY_DESCRIPTIONS:
            if category.description != category_data['description']:
                category.description = category_data['description']
                updated = True
        if category.is_public != category_data['is_public']:
            category.is_public = category_data['is_public']
            updated = True
        if category.order != category_data['order']:
            category.order = category_data['order']
            updated = True

        if updated:
            category.save()
        return category, False, updated

    def _upsert_post(self, post_data, category_map):
        category = category_map[post_data['category']]
        defaults = {
            'title': post_data['title'],
            'category': category,
            'featured_image': post_data.get('featured_image', ''),
            'excerpt': post_data['excerpt'],
            'body': self._clean_body(post_data['body']),
            'visibility': post_data['visibility'],
            'language': 'en',
            'meta_title': post_data['title'],
            'meta_description': post_data['excerpt'],
            'order': post_data['order'],
            'published_at': timezone.now(),
        }
        post, created = BlogPost.objects.get_or_create(
            slug=post_data['slug'],
            language='en',
            defaults=defaults,
        )
        if created:
            return post, True, False

        if not self._should_update_post(post):
            return post, False, False

        updated = False
        for field, value in defaults.items():
            current = getattr(post, field)
            if field == 'published_at':
                if current is None:
                    setattr(post, field, value)
                    updated = True
                continue
            if current != value:
                setattr(post, field, value)
                updated = True

        if updated:
            post.save()
        return post, False, updated

    def _should_update_post(self, post):
        if not post.body or not post.excerpt:
            return True
        if post.body in LEGACY_POST_BODIES:
            return True
        if post.body == post.excerpt and post.excerpt in LEGACY_POST_BODIES:
            return True
        if post.meta_description in LEGACY_POST_BODIES:
            return True
        return False

    def _clean_body(self, body):
        return body.replace('## ', '')
