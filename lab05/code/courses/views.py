"""
courses/views.py - Lab 05: Optimasi Database Django
====================================================
Berisi 3 pasangan endpoint baseline vs optimized:

1. course_list_baseline / course_list_optimized
   → Masalah: N+1 saat akses course.teacher
   → Solusi: select_related('teacher')

2. course_members_baseline / course_members_optimized
   → Masalah: N+1 saat akses members, contents, comments
   → Solusi: prefetch_related + annotate

3. course_dashboard_baseline / course_dashboard_optimized
   → Masalah: hitung statistik dalam loop Python
   → Solusi: aggregate() + annotate() dalam 1 query
"""

from django.http import JsonResponse
from django.db.models import Count, Avg, Max, Min, Sum

from .models import Course, CourseMember, CourseContent, Comment


# =============================================================================
# ENDPOINT 1: Daftar Course + Teacher
# =============================================================================

def course_list_baseline(request):
    """
    BASELINE - N+1 Problem.
    Untuk setiap course, Django akan menjalankan query TERPISAH
    untuk mengambil data teacher. Jika ada 100 course = 101 queries!

    Query pattern:
        SELECT * FROM courses_course;                    -- 1 query
        SELECT * FROM auth_user WHERE id = 1;           -- query ke-2
        SELECT * FROM auth_user WHERE id = 2;           -- query ke-3
        ... (1 query per course)
    """
    courses = Course.objects.all()  # Hanya ambil courses, teacher BELUM di-load
    data = []
    for c in courses:
        data.append({
            'id': c.id,
            'course': c.name,
            'price': c.price,
            # c.teacher memicu query baru ke tabel auth_user! --> N+1 Problem
            'teacher': c.teacher.username,
            'teacher_email': c.teacher.email,
        })
    return JsonResponse({
        'endpoint': 'course_list_baseline',
        'note': 'N+1 Problem: 1 query courses + N query teacher (1 per course)',
        'count': len(data),
        'data': data,
    })


def course_list_optimized(request):
    """
    OPTIMIZED - select_related untuk ForeignKey.
    Django menggunakan SQL JOIN sehingga teacher diambil BERSAMAAN
    dengan course dalam 1 query.

    Query pattern:
        SELECT course.*, auth_user.*
        FROM courses_course
        INNER JOIN auth_user ON courses_course.teacher_id = auth_user.id;
        -- Hanya 1 query untuk semua data!
    """
    courses = Course.objects.select_related('teacher').all()
    data = []
    for c in courses:
        data.append({
            'id': c.id,
            'course': c.name,
            'price': c.price,
            # Tidak ada extra query - teacher sudah ada di cache Django ORM
            'teacher': c.teacher.username,
            'teacher_email': c.teacher.email,
        })
    return JsonResponse({
        'endpoint': 'course_list_optimized',
        'note': 'Optimized: select_related JOIN -> hanya 1 query untuk semua courses + teachers',
        'count': len(data),
        'data': data,
    })


# =============================================================================
# ENDPOINT 2: Daftar Course + Members + Konten + Jumlah Komentar
# =============================================================================

def course_members_baseline(request):
    """
    BASELINE - Multiple N+1 Problems.
    Tiga level nested loop yang masing-masing memicu query baru.

    Untuk 10 courses dengan 5 members dan 3 contents masing-masing:
        1 (courses) + 10 (members per course) + 50 (contents per member)
        = 61+ queries!
    """
    courses = Course.objects.all()
    data = []
    for c in courses:
        # N+1: 1 query per course untuk ambil members
        members = CourseMember.objects.filter(course_id=c)
        member_list = [
            {'user': m.user_id.username, 'role': m.roles}  # N+1: 1 query per member untuk username
            for m in members
        ]

        # N+1: 1 query per course untuk ambil contents
        contents = CourseContent.objects.filter(course_id=c)
        content_list = []
        for ct in contents:
            # N+1: 1 query per content untuk hitung comments
            comment_count = Comment.objects.filter(content_id=ct).count()
            content_list.append({
                'name': ct.name,
                'comment_count': comment_count,
            })

        data.append({
            'course': c.name,
            'teacher': c.teacher.username,  # N+1 lagi!
            'member_count': len(member_list),
            'members': member_list,
            'contents': content_list,
        })

    return JsonResponse({
        'endpoint': 'course_members_baseline',
        'note': 'N+1 berlapis: query courses + N query members + N query contents + N query comments',
        'count': len(data),
        'data': data,
    })


def course_members_optimized(request):
    """
    OPTIMIZED - Kombinasi select_related + prefetch_related + annotate.

    Query pattern (hanya 3-4 queries total):
        1. SELECT course + teacher (JOIN)
        2. SELECT semua members + user (prefetch)
        3. SELECT semua contents + annotated comment_count (prefetch + annotate)
    """
    from django.db.models import Prefetch

    # Prefetch contents dengan jumlah komentar terannotasi
    contents_with_comments = CourseContent.objects.annotate(
        comment_count=Count('comment')
    )

    # Prefetch members dengan data user
    members_prefetch = CourseMember.objects.select_related('user_id')

    courses = (
        Course.objects
        .select_related('teacher')           # JOIN untuk ForeignKey teacher
        .prefetch_related(
            Prefetch('coursemember_set', queryset=members_prefetch),
            Prefetch('coursecontent_set', queryset=contents_with_comments),
        )
        .all()
    )

    data = []
    for c in courses:
        member_list = [
            {'user': m.user_id.username, 'role': m.roles}
            for m in c.coursemember_set.all()  # Dari cache, tidak ada query baru
        ]
        content_list = [
            {'name': ct.name, 'comment_count': ct.comment_count}
            for ct in c.coursecontent_set.all()  # Dari cache + annotated
        ]
        data.append({
            'course': c.name,
            'teacher': c.teacher.username,       # Dari JOIN cache
            'member_count': len(member_list),
            'members': member_list,
            'contents': content_list,
        })

    return JsonResponse({
        'endpoint': 'course_members_optimized',
        'note': 'Optimized: select_related + prefetch_related + annotate -> 3-4 queries total',
        'count': len(data),
        'data': data,
    })


# =============================================================================
# ENDPOINT 3: Statistik Course untuk Dashboard Dosen
# =============================================================================

def course_dashboard_baseline(request):
    """
    BASELINE - Hitung statistik dalam loop Python (sangat tidak efisien).

    Untuk setiap course, menjalankan query terpisah:
        - count members
        - count contents
        - count comments
        - total comments per course

    Jika ada 50 courses = 1 + (50 × 4) = 201 queries!
    """
    courses = Course.objects.all()
    data = []

    # Statistik global dihitung manual (tidak efisien)
    total_courses = 0
    total_members = 0
    all_prices = []

    for c in courses:
        total_courses += 1

        # Setiap .count() memicu 1 query baru ke database!
        member_count = CourseMember.objects.filter(course_id=c).count()
        content_count = CourseContent.objects.filter(course_id=c).count()

        # Hitung komentar: subquery untuk setiap course
        comment_count = Comment.objects.filter(
            content_id__course_id=c
        ).count()

        total_members += member_count
        all_prices.append(c.price)

        data.append({
            'course': c.name,
            'teacher': c.teacher.username,  # N+1 lagi
            'price': c.price,
            'member_count': member_count,
            'content_count': content_count,
            'comment_count': comment_count,
        })

    # Hitung statistik harga di Python (bukan di database)
    avg_price = sum(all_prices) / len(all_prices) if all_prices else 0
    max_price = max(all_prices) if all_prices else 0
    min_price = min(all_prices) if all_prices else 0

    return JsonResponse({
        'endpoint': 'course_dashboard_baseline',
        'note': 'N+1 parah: 1 query courses + 4 query per course untuk statistik',
        'global_stats': {
            'total_courses': total_courses,
            'total_members': total_members,
            'avg_price': avg_price,
            'max_price': max_price,
            'min_price': min_price,
        },
        'courses': data,
    })


def course_dashboard_optimized(request):
    """
    OPTIMIZED - Semua statistik dihitung di level database dengan aggregate + annotate.

    Query pattern (hanya 2 queries):
        1. SELECT courses + annotated stats (member_count, content_count, comment_count)
           dengan JOIN dan GROUP BY
        2. SELECT aggregate global stats (total, avg, max, min price)
    """
    # Query 1: Statistik global dalam 1 query menggunakan aggregate()
    global_stats = Course.objects.aggregate(
        total_courses=Count('id'),
        avg_price=Avg('price'),
        max_price=Max('price'),
        min_price=Min('price'),
        total_price_sum=Sum('price'),
    )

    # Query 2: Per-course stats dengan annotate() - semuanya dalam 1 query
    courses = (
        Course.objects
        .select_related('teacher')
        .annotate(
            member_count=Count('coursemember', distinct=True),
            content_count=Count('coursecontent', distinct=True),
            comment_count=Count('coursecontent__comment', distinct=True),
        )
        .order_by('-member_count')
        .all()
    )

    data = [
        {
            'course': c.name,
            'teacher': c.teacher.username,   # Dari JOIN, tidak ada extra query
            'price': c.price,
            'member_count': c.member_count,   # Dari annotate, tidak ada extra query
            'content_count': c.content_count, # Dari annotate, tidak ada extra query
            'comment_count': c.comment_count, # Dari annotate, tidak ada extra query
        }
        for c in courses
    ]

    return JsonResponse({
        'endpoint': 'course_dashboard_optimized',
        'note': 'Optimized: aggregate() + annotate() -> hanya 2 queries untuk semua statistik',
        'global_stats': {
            'total_courses': global_stats['total_courses'],
            'total_members': sum(d['member_count'] for d in data),
            'avg_price': float(global_stats['avg_price'] or 0),
            'max_price': global_stats['max_price'] or 0,
            'min_price': global_stats['min_price'] or 0,
        },
        'courses': data,
    })


# =============================================================================
# BONUS: Bulk Operations Demo
# =============================================================================

def bulk_create_demo(request):
    """
    Demo bulk_create vs save() dalam loop.
    Endpoint ini membuat 100 dummy CourseContent sekaligus.
    """
    from django.contrib.auth.models import User

    course = Course.objects.first()
    if not course:
        return JsonResponse({'error': 'Tidak ada course. Buat course terlebih dahulu.'}, status=400)

    # Bulk create: 1 INSERT query untuk 100 record
    contents = [
        CourseContent(
            name=f'Bulk Content {i}',
            description=f'Konten ke-{i} dibuat via bulk_create',
            course_id=course,
        )
        for i in range(1, 101)
    ]
    CourseContent.objects.bulk_create(contents, batch_size=50)

    return JsonResponse({
        'endpoint': 'bulk_create_demo',
        'note': 'bulk_create: 100 record diinsert dalam 2 queries (batch_size=50)',
        'created': 100,
        'course': course.name,
    })


def bulk_update_demo(request):
    """
    Demo bulk update menggunakan .update() vs save() dalam loop.
    Naikkan harga semua course sebesar 10%.
    """
    from django.db.models import F

    count = Course.objects.count()

    # update() = 1 SQL UPDATE untuk semua record sekaligus
    Course.objects.all().update(price=F('price') * 110 / 100)

    return JsonResponse({
        'endpoint': 'bulk_update_demo',
        'note': f'bulk update: harga {count} course dinaikkan 10% dalam 1 query',
        'updated_count': count,
    })
