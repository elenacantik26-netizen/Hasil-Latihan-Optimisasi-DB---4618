# Lab 05 - Optimasi Database Django

**Mata Kuliah:** Pemrograman Sisi Server  
**Universitas Dian Nuswantoro**

## Struktur File yang Diubah

| File | Perubahan |
|------|-----------|
| `code/requirements.txt` | Tambah `django-silk==5.1.0` |
| `code/lms/settings.py` | `silk` di INSTALLED_APPS + SilkyMiddleware (sudah ada) |
| `code/lms/urls.py` | Route `/silk/` (sudah ada) |
| `code/courses/views.py` | **Dibuat baru** - 6 endpoint baseline/optimized + bulk demo |
| `code/courses/urls.py` | **Diisi** - semua route lab |
| `code/courses/models.py` | Tambah `Meta.indexes` di semua model |
| `code/courses/management/commands/seed_data.py` | **Dibuat baru** - generate 20 courses, 100 students |

## Setup & Menjalankan

```bash
# 1. Jalankan Docker
docker-compose up -d

# 2. Migrate database
docker-compose exec app python manage.py migrate

# 3. Seed data dummy (20 courses, 30 members/course, 4 contents, 5 comments)
docker-compose exec app python manage.py seed_data

# 4. Akses aplikasi
# - App:   http://localhost:8000/
# - Silk:  http://localhost:8000/silk/
# - Admin: http://localhost:8000/admin/
```

## Endpoint Lab

| Endpoint | URL |
|----------|-----|
| Course + Teacher (Baseline) | `GET /lab/course-list/baseline/` |
| Course + Teacher (Optimized) | `GET /lab/course-list/optimized/` |
| Course + Members (Baseline) | `GET /lab/course-members/baseline/` |
| Course + Members (Optimized) | `GET /lab/course-members/optimized/` |
| Dashboard Statistik (Baseline) | `GET /lab/course-dashboard/baseline/` |
| Dashboard Statistik (Optimized) | `GET /lab/course-dashboard/optimized/` |
| Bulk Create Demo | `GET /lab/bulk-create/` |
| Bulk Update Demo | `GET /lab/bulk-update/` |

## Hasil Perbandingan Silk

### Kasus 1: Course + Teacher (20 courses)

| Metrik | Baseline | Optimized | Improvement |
|--------|----------|-----------|-------------|
| Query Count | 21 | 1 | **95% lebih sedikit** |
| Duplicate Query | 20 | 0 | Eliminated |
| Teknik | - | `select_related('teacher')` | JOIN |

**Analisis N+1:**
- Baseline: 1 query ambil courses + 20 query ambil teacher (1 per course) = **21 queries**
- Untuk N=1000 courses → 1001 queries (linear growth!)
- Optimized: 1 JOIN query → hasil sama tanpa extra queries

### Kasus 2: Course + Members + Contents + Comments (20 courses)

| Metrik | Baseline | Optimized | Improvement |
|--------|----------|-----------|-------------|
| Query Count | 100+ | 3-4 | **~97% lebih sedikit** |
| Teknik | - | `prefetch_related` + `annotate` | Prefetch + GROUP BY |

**Analisis:**
- Baseline: 1 + N(members) + N(contents) + N(comments) queries = berlapis-lapis N+1
- Optimized: 1 (courses+teacher JOIN) + 1 (prefetch members) + 1 (prefetch contents+count) = 3 queries

### Kasus 3: Dashboard Statistik (20 courses)

| Metrik | Baseline | Optimized | Improvement |
|--------|----------|-----------|-------------|
| Query Count | 81+ | 2 | **~98% lebih sedikit** |
| Statistik Global | Dihitung di Python | `aggregate()` di DB | 1 query |
| Per-course Stats | 4 query per course | `annotate()` | 1 query |
| Teknik | - | `aggregate()` + `annotate()` | SQL GROUP BY |

## Teknik Optimasi yang Digunakan

### 1. `select_related()` - untuk ForeignKey
```python
# Sebelum (N+1):
courses = Course.objects.all()
for c in courses:
    print(c.teacher.username)  # query per course!

# Sesudah (1 query JOIN):
courses = Course.objects.select_related('teacher').all()
```

### 2. `prefetch_related()` - untuk reverse FK / Many-to-Many
```python
courses = Course.objects.prefetch_related(
    'coursemember_set',
    'coursecontent_set',
)
```

### 3. `annotate()` - hitung statistik per object
```python
courses = Course.objects.annotate(
    member_count=Count('coursemember', distinct=True),
    comment_count=Count('coursecontent__comment', distinct=True),
)
```

### 4. `aggregate()` - statistik global
```python
stats = Course.objects.aggregate(
    total=Count('id'),
    avg_price=Avg('price'),
    max_price=Max('price'),
)
```

### 5. `bulk_create()` & `.update()` - operasi massal
```python
# Insert 100 record = 1-2 queries (bukan 100 queries!)
CourseContent.objects.bulk_create(contents, batch_size=50)

# Update semua = 1 query
Course.objects.all().update(price=F('price') * 1.1)
```

### 6. Database Index - percepat lookup
```python
class Meta:
    indexes = [
        models.Index(fields=['teacher'], name='idx_course_teacher'),
        models.Index(fields=['price'], name='idx_course_price'),
        models.Index(fields=['teacher', 'price'], name='idx_course_teacher_price'),
    ]
```

**Justifikasi index:**
- `teacher`: sering difilter "course milik dosen X"
- `price`: sering diurutkan/difilter berdasarkan harga
- `teacher + price`: composite index untuk query filter dosen + range harga
