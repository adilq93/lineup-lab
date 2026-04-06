from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0004_pbpevent_sub_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pbpevent',
            name='sub_type',
            field=models.CharField(max_length=50, null=True),
        ),
    ]
