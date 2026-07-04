from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_starter', '0006_sitehandoff_staff_ai_brief_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='websiterequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('new', 'New'),
                    ('reviewed', 'Reviewed'),
                    ('contacted', 'Contacted'),
                    ('converted', 'Converted'),
                    ('cancelled', 'Cancelled'),
                ],
                default='new',
                max_length=20,
            ),
        ),
    ]
