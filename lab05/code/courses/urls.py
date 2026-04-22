"""
courses/urls.py - Lab 05: Optimasi Database
============================================
Route untuk semua endpoint lab baseline vs optimized.
"""

from django.urls import path
from . import views

urlpatterns = [
    # ------------------------------------------------------------------
    # Endpoint 1: Daftar Course + Teacher
    # ------------------------------------------------------------------
    path('lab/course-list/baseline/', views.course_list_baseline,
         name='course-list-baseline'),
    path('lab/course-list/optimized/', views.course_list_optimized,
         name='course-list-optimized'),

    # ------------------------------------------------------------------
    # Endpoint 2: Daftar Course + Members + Konten + Jumlah Komentar
    # ------------------------------------------------------------------
    path('lab/course-members/baseline/', views.course_members_baseline,
         name='course-members-baseline'),
    path('lab/course-members/optimized/', views.course_members_optimized,
         name='course-members-optimized'),

    # ------------------------------------------------------------------
    # Endpoint 3: Statistik Course untuk Dashboard Dosen
    # ------------------------------------------------------------------
    path('lab/course-dashboard/baseline/', views.course_dashboard_baseline,
         name='course-dashboard-baseline'),
    path('lab/course-dashboard/optimized/', views.course_dashboard_optimized,
         name='course-dashboard-optimized'),

    # ------------------------------------------------------------------
    # Bonus: Bulk Operations Demo
    # ------------------------------------------------------------------
    path('lab/bulk-create/', views.bulk_create_demo, name='bulk-create'),
    path('lab/bulk-update/', views.bulk_update_demo, name='bulk-update'),
]
