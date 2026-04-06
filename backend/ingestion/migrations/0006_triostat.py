from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0005_pbpevent_sub_type_longer'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrioStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trio_key', models.CharField(max_length=40)),
                ('team_id', models.IntegerField()),
                ('filter_name', models.CharField(max_length=20)),
                ('player1_id', models.IntegerField()),
                ('player2_id', models.IntegerField()),
                ('player3_id', models.IntegerField()),
                ('possessions', models.IntegerField()),
                ('ortg', models.DecimalField(decimal_places=1, max_digits=6, null=True)),
                ('drtg', models.DecimalField(decimal_places=1, max_digits=6, null=True)),
                ('net', models.DecimalField(decimal_places=1, max_digits=6, null=True)),
                ('pts', models.IntegerField(default=0)),
                ('fga', models.IntegerField(default=0)),
                ('fgm', models.IntegerField(default=0)),
                ('fg_pct', models.DecimalField(decimal_places=1, max_digits=5, null=True)),
                ('fg3m', models.IntegerField(default=0)),
                ('fta', models.IntegerField(default=0)),
                ('oreb', models.IntegerField(default=0)),
                ('tov', models.IntegerField(default=0)),
                ('computed_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'trio_stats',
                'unique_together': {('trio_key', 'team_id', 'filter_name')},
            },
        ),
        migrations.AddIndex(
            model_name='triostat',
            index=models.Index(fields=['team_id', 'filter_name'], name='trio_stats_team_id_filter_idx'),
        ),
    ]
