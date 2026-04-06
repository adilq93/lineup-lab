from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0002_pbpevents_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='pbp_fetched',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='game',
            name='lineups_computed',
            field=models.BooleanField(default=False),
        ),
    ]
