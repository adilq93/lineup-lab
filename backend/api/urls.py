from django.urls import path
from api import views

urlpatterns = [
    path('teams/', views.teams_list, name='teams-list'),
    path('teams/<int:team_id>/trios/', views.team_trios, name='team-trios'),
    path('trios/<str:trio_key>/', views.trio_detail, name='trio-detail'),
    path('meta/freshness/', views.meta_freshness, name='meta-freshness'),
]
