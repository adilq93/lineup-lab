from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE INDEX pbp_events_home_lineup_gin
                    ON pbp_events USING gin (home_lineup);
                CREATE INDEX pbp_events_away_lineup_gin
                    ON pbp_events USING gin (away_lineup);
                CREATE INDEX pbp_events_bool_flags
                    ON pbp_events (
                        opp_is_big_lineup,
                        opp_is_shooter_lineup,
                        opp_is_smallball,
                        is_clutch,
                        is_fast_game,
                        is_slow_game
                    );
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS pbp_events_home_lineup_gin;
                DROP INDEX IF EXISTS pbp_events_away_lineup_gin;
                DROP INDEX IF EXISTS pbp_events_bool_flags;
            """,
        ),
    ]
