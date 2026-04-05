# users app

Bu app foydalanuvchilar, haydovchilar va autentifikatsiyani boshqaradi.

---

## Fayl tuzilmasi

```
apps/users/
├── migrations/          # DB migratsiyalar
├── __init__.py
├── admin.py             # Django admin paneli sozlamalari
├── apps.py
├── models.py            # User, DriverProfile modellari
├── otp_service.py       # Redis orqali OTP logikasi
├── sms_service.py       # Infobip SMS yuborish
├── serializers.py       # Input/output validatsiya
├── permissions.py       # IsDriver, IsClient, IsAdminUser
├── views.py             # API endpoint handlerlari
├── urls.py              # URL marshrutlari
└── tests.py             # Unit testlar
```

---

## Rollar

| Rol      | Kirish yo'li                         | Kim yaratadi       |
|----------|--------------------------------------|--------------------|
| `client` | `/api/users/auth/register/`          | O'zi ro'yxatdan    |
| `driver` | `/api/users/auth/verify-otp/`        | Admin yaratadi     |
| `admin`  | Django admin `/admin/` + superuser   | `createsuperuser`  |

---

## Auth jarayoni

### Yangi mijoz uchun:
```
POST /api/users/auth/send-otp/    → SMS yuboriladi
POST /api/users/auth/register/    → OTP + ism → JWT token
```

### Mavjud foydalanuvchi uchun:
```
POST /api/users/auth/send-otp/    → SMS yuboriladi
POST /api/users/auth/verify-otp/  → OTP → JWT token
```

### Token yangilash:
```
POST /api/users/auth/token/refresh/  → { refresh } → yangi access token
```

---

## Endpoints

| Method | URL                              | Kim                | Tavsif                        |
|--------|----------------------------------|--------------------|-------------------------------|
| POST   | `/auth/send-otp/`                | Hamma              | OTP yuborish                  |
| POST   | `/auth/verify-otp/`              | Mavjud user        | OTP tekshirib login           |
| POST   | `/auth/register/`                | Yangi user         | OTP + ism bilan ro'yxat       |
| POST   | `/auth/token/refresh/`           | Autentifikatsiya   | Token yangilash                |
| GET    | `/me/`                           | Autentifikatsiya   | O'z profilini ko'rish         |
| PATCH  | `/me/`                           | Autentifikatsiya   | Ismini o'zgartirish           |
| GET    | `/driver/profile/`               | Driver             | O'z haydovchi profilini ko'rish |
| PATCH  | `/driver/location/`              | Driver             | Koordinatni yangilash         |
| GET    | `/admin/drivers/`                | Admin              | Barcha haydovchilar           |
| POST   | `/admin/drivers/create/`         | Admin              | Yangi haydovchi qo'shish      |

---

## OTP logikasi (`otp_service.py`)

- Kod Redis da saqlanadi — database ga yuk tushmaydi
- Muddati: **2 daqiqa** (120 sekund)
- Cooldown: **1 daqiqa** — bir raqamga tez-tez yuborish oldini oladi
- Bir kod faqat **bir marta** ishlatiladi, tekshirilgandan keyin o'chadi

---

## Settings da kerakli o'zgaruvchilar

`.env` fayliga qo'shing:

```env
INFOBIP_API_KEY=your_api_key_here
INFOBIP_BASE_URL=xxxxx.api.infobip.com
INFOBIP_SENDER=TezYet
SMS_SKIP_IN_DEV=True    # Development da SMS yubormaslik uchun
```

`settings.py` ga qo'shing:

```python
INFOBIP_API_KEY = os.getenv("INFOBIP_API_KEY")
INFOBIP_BASE_URL = os.getenv("INFOBIP_BASE_URL")
INFOBIP_SENDER = os.getenv("INFOBIP_SENDER", "TezYet")
SMS_SKIP_IN_DEV = os.getenv("SMS_SKIP_IN_DEV", "False") == "True"
```

---

## Testlarni ishga tushirish

```bash
docker-compose exec web python manage.py test apps.users
```

---

## Admin orqali superuser yaratish

```bash
docker-compose exec web python manage.py createsuperuser
```

Phone: `+77000000000`, so'ng parol kiriting.
