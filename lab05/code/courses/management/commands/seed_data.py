"""
Management command untuk generate data dummy Lab 05.
Jalankan: python manage.py seed_data

Membuat:
- 5 teacher users
- 20 courses
- 50-100 course members per course
- 3-5 contents per course
- 5-10 comments per content
"""

import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from courses.models import Course, CourseMember, CourseContent, Comment


COURSE_NAMES = [
    "Pemrograman Python Dasar", "Web Development dengan Django",
    "Machine Learning Fundamentals", "Database Design & SQL",
    "React JS untuk Pemula", "Data Science dengan Pandas",
    "Algoritma & Struktur Data", "DevOps & Docker",
    "REST API Development", "Mobile App Flutter",
    "Keamanan Aplikasi Web", "Cloud Computing AWS",
    "Pemrograman Java OOP", "UI/UX Design Principles",
    "Network Programming", "Kecerdasan Buatan",
    "Sistem Operasi Linux", "Analisis Big Data",
    "Pengembangan Game Unity", "Blockchain Development",
]


class Command(BaseCommand):
    help = 'Seed database dengan data dummy untuk Lab 05'

    def add_arguments(self, parser):
        parser.add_argument('--courses', type=int, default=20, help='Jumlah course')
        parser.add_argument('--members', type=int, default=30, help='Member per course')
        parser.add_argument('--contents', type=int, default=4, help='Content per course')
        parser.add_argument('--comments', type=int, default=5, help='Comment per content')

    def handle(self, *args, **options):
        self.stdout.write('=== Seeding data untuk Lab 05 ===\n')

        # --- Teachers ---
        teachers = []
        for i in range(1, 6):
            user, created = User.objects.get_or_create(
                username=f'teacher{i}',
                defaults={
                    'email': f'teacher{i}@lms.id',
                    'first_name': f'Dosen',
                    'last_name': f'{i}',
                }
            )
            if created:
                user.set_password('pass123')
                user.save()
            teachers.append(user)
        self.stdout.write(f'[+] {len(teachers)} teachers siap\n')

        # --- Students ---
        students = []
        for i in range(1, 101):
            user, created = User.objects.get_or_create(
                username=f'student{i}',
                defaults={'email': f'student{i}@lms.id', 'first_name': f'Mahasiswa {i}'}
            )
            if created:
                user.set_password('pass123')
                user.save()
            students.append(user)
        self.stdout.write(f'[+] {len(students)} students siap\n')

        # --- Courses ---
        n_courses = options['courses']
        courses = []
        for i in range(n_courses):
            name = COURSE_NAMES[i % len(COURSE_NAMES)]
            if i >= len(COURSE_NAMES):
                name = f'{name} (Batch {i // len(COURSE_NAMES) + 1})'
            course, created = Course.objects.get_or_create(
                name=name,
                defaults={
                    'description': f'Deskripsi lengkap untuk {name}',
                    'price': random.choice([0, 50000, 99000, 150000, 299000, 499000]),
                    'teacher': random.choice(teachers),
                }
            )
            courses.append(course)
        self.stdout.write(f'[+] {len(courses)} courses siap\n')

        # --- Members ---
        n_members = options['members']
        member_count = 0
        for course in courses:
            sample_students = random.sample(students, min(n_members, len(students)))
            for student in sample_students:
                _, created = CourseMember.objects.get_or_create(
                    course_id=course,
                    user_id=student,
                    defaults={'roles': random.choice(['std', 'ast'])}
                )
                if created:
                    member_count += 1
        self.stdout.write(f'[+] {member_count} course members dibuat\n')

        # --- Contents & Comments ---
        n_contents = options['contents']
        n_comments = options['comments']
        content_count = 0
        comment_count = 0

        for course in courses:
            members = list(CourseMember.objects.filter(course_id=course))
            for j in range(1, n_contents + 1):
                content, created = CourseContent.objects.get_or_create(
                    name=f'Materi {j} - {course.name}',
                    course_id=course,
                    defaults={'description': f'Deskripsi materi {j}'}
                )
                if created:
                    content_count += 1

                # Add comments
                if members:
                    for _ in range(n_comments):
                        commenter = random.choice(members)
                        Comment.objects.create(
                            content_id=content,
                            member_id=commenter,
                            comment=f'Komentar pada {content.name} oleh {commenter}'
                        )
                        comment_count += 1

        self.stdout.write(f'[+] {content_count} contents, {comment_count} comments dibuat\n')
        self.stdout.write(self.style.SUCCESS('\n=== Seeding selesai! ===\n'))
        self.stdout.write(f'Total: {Course.objects.count()} courses, '
                          f'{CourseMember.objects.count()} members, '
                          f'{CourseContent.objects.count()} contents, '
                          f'{Comment.objects.count()} comments\n')
