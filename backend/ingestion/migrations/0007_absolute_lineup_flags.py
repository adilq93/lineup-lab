from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0006_triostat'),
    ]

    operations = [
        migrations.AddField(model_name='pbpevent', name='home_is_big', field=models.BooleanField(null=True)),
        migrations.AddField(model_name='pbpevent', name='away_is_big', field=models.BooleanField(null=True)),
        migrations.AddField(model_name='pbpevent', name='home_is_shooter', field=models.BooleanField(null=True)),
        migrations.AddField(model_name='pbpevent', name='away_is_shooter', field=models.BooleanField(null=True)),
        migrations.AddField(model_name='pbpevent', name='home_is_smallball', field=models.BooleanField(null=True)),
        migrations.AddField(model_name='pbpevent', name='away_is_smallball', field=models.BooleanField(null=True)),
    ]
