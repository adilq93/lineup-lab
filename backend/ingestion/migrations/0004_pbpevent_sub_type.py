from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0003_game_pipeline_flags'),
    ]

    operations = [
        migrations.AddField(
            model_name='pbpevent',
            name='sub_type',
            field=models.CharField(max_length=10, null=True),
        ),
    ]
