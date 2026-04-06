from rest_framework import serializers

from ingestion.models import Player


class PlayerSerializer(serializers.Serializer):
    player_id = serializers.IntegerField()
    name = serializers.CharField()
    headshot_url = serializers.CharField()


class BaselineStatsSerializer(serializers.Serializer):
    ortg = serializers.FloatField(allow_null=True)
    drtg = serializers.FloatField(allow_null=True)
    net = serializers.FloatField(allow_null=True)
    possessions = serializers.IntegerField()


class FilteredStatsSerializer(serializers.Serializer):
    ortg = serializers.FloatField(allow_null=True)
    drtg = serializers.FloatField(allow_null=True)
    net = serializers.FloatField(allow_null=True)
    possessions = serializers.IntegerField()
    low_confidence = serializers.BooleanField()


class DeltaSerializer(serializers.Serializer):
    ortg = serializers.FloatField(allow_null=True)
    drtg = serializers.FloatField(allow_null=True)
    net = serializers.FloatField(allow_null=True)


class TrioListItemSerializer(serializers.Serializer):
    trio_key = serializers.CharField()
    players = PlayerSerializer(many=True)
    baseline = BaselineStatsSerializer()


class CounterRecommendationSerializer(serializers.Serializer):
    archetype = serializers.CharField()
    filter = serializers.CharField()
    delta = serializers.FloatField()
    filtered_net = serializers.FloatField(allow_null=True)
    possessions = serializers.IntegerField()


class FilterResultSerializer(serializers.Serializer):
    stats = FilteredStatsSerializer(allow_null=True)
    delta = DeltaSerializer(allow_null=True)


class TrioDetailSerializer(serializers.Serializer):
    trio_key = serializers.CharField()
    players = PlayerSerializer(many=True)
    baseline = BaselineStatsSerializer()
    filtered = FilteredStatsSerializer(allow_null=True)
    delta = DeltaSerializer(allow_null=True)
    all_filters = serializers.DictField(child=FilterResultSerializer())
    active_filters = serializers.ListField(child=serializers.CharField())
    counter = CounterRecommendationSerializer(allow_null=True)


class TeamSerializer(serializers.Serializer):
    team_id = serializers.IntegerField()
    name = serializers.CharField()
    abbreviation = serializers.CharField()


class FreshnessSerializer(serializers.Serializer):
    last_game_date = serializers.DateField(allow_null=True)
    ingested_at = serializers.DateTimeField(allow_null=True)
