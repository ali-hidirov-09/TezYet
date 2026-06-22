# TezYet
Local taxi ordering system built with Django REST Framework


# TezYet — Taxi Buyurtma Platformasi

Sayram tumani uchun mahalliy taxi buyurtma tizimi. Mijozlar va haydovchilarni real vaqtda bog'laydi, narxni avtomatik hisoblaydi.
Ushbu loyiha mijoz va haydovchilarni bog‘laydigan backend API bo‘lib, Django REST Framework yordamida yaratilgan.

## Tech Stack

- **Backend:** Python 3.11, Django 5.2, Django REST Framework
- **Database:** PostgreSQL (production), SQLite (development)
- **Cache / OTP:** Redis
- **Auth:** JWT (djangorestframework-simplejwt)
- **SMS:** Infobip (KZ va UZB raqamlari)
- **Maps:** Google Maps Distance Matrix API
- **Deploy:** Docker, Docker Compose
- **Docs:** Swagger (drf-spectacular)

## Loyiha tuzilmasi

```
TezYet/
├── apps/
│   ├── users/        # Autentifikatsiya, OTP, profil
│   ├── orders/       # Buyurtma yaratish va boshqarish
│   └── reviews/      # Reyting va sharhlar
├── TezYetTaxi/       # Django sozlamalari
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Ishga tushirish

**Talablar:** Docker va Docker Compose o'rnatilgan bo'lsin.

```bash
git clone https://github.com/ali-hidirov-09/TezYet.git
cd TezYet

cp .env.example .env
# .env faylini o'z ma'lumotlaringiz bilan to'ldiring

docker-compose up --build
```

Server `http://localhost:8000` da ishga tushadi.

Migratsiyalar birinchi marta qo'lda:

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

## Muhit o'zgaruvchilari

`.env.example` faylini ko'chirng va quyidagilarni to'ldiring:

```env
SECRET_KEY=
DEBUG=True

REDIS_URL=redis://redis:6379/0

INFOBIP_API_KEY=
INFOBIP_BASE_URL=

GOOGLE_MAPS_API_KEY=
```

## API

Swagger hujjati: `http://localhost:8000/api/docs/`

Asosiy endpointlar:

```
POST   /api/auth/register/          Ro'yxatdan o'tish (OTP yuborish)
POST   /api/auth/verify-otp/        OTP tasdiqlash
POST   /api/auth/login/             Kirish
POST   /api/auth/token/refresh/     Tokenni yangilash

POST   /api/orders/                 Buyurtma yaratish
GET    /api/orders/{id}/            Buyurtma holati
POST   /api/orders/{id}/accept/     Haydovchi qabul qilish
POST   /api/orders/{id}/complete/   Safarni tugatish
POST   /api/orders/{id}/cancel/     Bekor qilish

GET    /api/drivers/nearby/         Yaqin haydovchilar
PATCH  /api/drivers/location/       Joylashuvni yangilash
PATCH  /api/drivers/availability/   Online/Offline

POST   /api/reviews/                Baho berish
```

## Foydalanuvchi rollari

| Rol      | Kirish                          | Tavsif                 |
|----------|---------------------------------|------------------------|
| `client` | `/login`                        | Taxi buyurtma qiluvchi |
| `driver` | Admin tomonidan link yuboriladi | Haydovchi              |
| `admin`  | `/admin`                        | Tizim boshqaruvchisi   |

## Narx hisoblash

```
Narx = 300 tenge + (masofa_km × 1 100 tenge)
```

Masofa Google Maps Distance Matrix API orqali hisoblanadi.

## OTP jarayoni

```
Foydalanuvchi telefon kiritadi
        ↓
Infobip orqali SMS yuboriladi (6 raqamli kod)
        ↓
Foydalanuvchi kodni kiritadi
        ↓
Kod to'g'ri va muddati o'tmagan (2 daqiqa) bo'lsa — JWT token qaytadi
```

## Litsenziya

MIT


## Deployment

Project AWS yoki boshqa serverga deploy qilinadi

## Author

Ali Hidirov
Backend Developer
