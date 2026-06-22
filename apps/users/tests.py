from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import DriverProfile
from apps.users.otp_service import generate_otp, verify_otp, get_remaining_seconds

User = get_user_model()


class OtpServiceTests(TestCase):

    def setUp(self):
        cache.clear()

    def test_generate_otp_returns_6_digit_code(self):
        code = generate_otp("+77001234567")
        self.assertIsNotNone(code)
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_generate_otp_cooldown_returns_none(self):
        generate_otp("+77001234567")
        second = generate_otp("+77001234567")
        self.assertIsNone(second)

    def test_verify_otp_correct_code(self):
        code = generate_otp("+77001234567")
        result = verify_otp("+77001234567", code)
        self.assertTrue(result)

    def test_verify_otp_wrong_code(self):
        generate_otp("+77001234567")
        result = verify_otp("+77001234567", "000000")
        self.assertFalse(result)

    def test_verify_otp_can_only_be_used_once(self):
        code = generate_otp("+77001234567")
        verify_otp("+77001234567", code)
        result = verify_otp("+77001234567", code)
        self.assertFalse(result)

    def test_remaining_seconds_after_cooldown(self):
        generate_otp("+77001234567")
        remaining = get_remaining_seconds("+77001234567")
        self.assertGreater(remaining, 0)
        self.assertLessEqual(remaining, 60)


class SendOtpViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        cache.clear()

    @patch("apps.users.views.send_otp_sms", return_value=True)
    @patch("apps.users.views.generate_otp", return_value="123456")
    def test_send_otp_new_user(self, mock_otp, mock_sms):
        response = self.client.post("/api/users/auth/send-otp/", {"phone": "+77001234567"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_registered"])

    @patch("apps.users.views.send_otp_sms", return_value=True)
    @patch("apps.users.views.generate_otp", return_value="123456")
    def test_send_otp_existing_user(self, mock_otp, mock_sms):
        User.objects.create_user(phone="+77001234567", full_name="Test User")
        response = self.client.post("/api/users/auth/send-otp/", {"phone": "+77001234567"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_registered"])

    @patch("apps.users.views.generate_otp", return_value=None)
    def test_send_otp_cooldown(self, mock_otp):
        response = self.client.post("/api/users/auth/send-otp/", {"phone": "+77001234567"})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_send_otp_invalid_phone(self):
        response = self.client.post("/api/users/auth/send-otp/", {"phone": "998901234567"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.users.views.send_otp_sms", return_value=False)
    @patch("apps.users.views.generate_otp", return_value="123456")
    def test_send_otp_sms_failure(self, mock_otp, mock_sms):
        response = self.client.post("/api/users/auth/send-otp/", {"phone": "+77001234567"})
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)


class RegisterViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        cache.clear()

    @patch("apps.users.views.verify_otp", return_value=True)
    def test_register_success(self, mock_verify):
        response = self.client.post("/api/users/auth/register/", {
            "phone": "+77001234567",
            "full_name": "Ali Karimov",
            "code": "123456",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    @patch("apps.users.views.verify_otp", return_value=False)
    def test_register_wrong_otp(self, mock_verify):
        response = self.client.post("/api/users/auth/register/", {
            "phone": "+77001234567",
            "full_name": "Ali Karimov",
            "code": "000000",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.users.views.verify_otp", return_value=True)
    def test_register_duplicate_phone(self, mock_verify):
        User.objects.create_user(phone="+77001234567", full_name="Ali")
        response = self.client.post("/api/users/auth/register/", {
            "phone": "+77001234567",
            "full_name": "Ali Karimov",
            "code": "123456",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class VerifyOtpLoginViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        cache.clear()
        self.user = User.objects.create_user(
            phone="+77001234567",
            full_name="Test User",
            is_active=True,
        )

    @patch("apps.users.views.verify_otp", return_value=True)
    def test_login_success(self, mock_verify):
        response = self.client.post("/api/users/auth/verify-otp/", {
            "phone": "+77001234567",
            "code": "123456",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    @patch("apps.users.views.verify_otp", return_value=False)
    def test_login_wrong_code(self, mock_verify):
        response = self.client.post("/api/users/auth/verify-otp/", {
            "phone": "+77001234567",
            "code": "000000",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.users.views.verify_otp", return_value=True)
    def test_login_user_not_found(self, mock_verify):
        response = self.client.post("/api/users/auth/verify-otp/", {
            "phone": "+77009999999",
            "code": "123456",
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MeViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone="+77001234567",
            full_name="Test User",
            is_active=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_get_profile(self):
        response = self.client.get("/api/users/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["phone"], "+77001234567")

    def test_update_full_name(self):
        response = self.client.patch("/api/users/me/", {"full_name": "Yangi Ism"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Yangi Ism")

    def test_unauthenticated_access(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/users/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminDriverTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            phone="+77000000001",
            full_name="Admin",
            role="admin",
            is_active=True,
            is_staff=True,
        )
        self.client.force_authenticate(user=self.admin)

    def test_create_driver(self):
        response = self.client.post("/api/users/admin/drivers/create/", {
            "phone": "+77001112233",
            "full_name": "Haydovchi Ism",
            "car_model": "Cobalt",
            "car_number": "01A123BC",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(phone="+77001112233", role="driver").exists())

    def test_create_driver_duplicate_car_number(self):
        User.objects.create_user(phone="+77001112234", full_name="D1", role="driver", is_active=True)
        driver_user = User.objects.get(phone="+77001112234")
        DriverProfile.objects.create(user=driver_user, car_model="Nexia", car_number="01A999ZZ")

        response = self.client.post("/api/users/admin/drivers/create/", {
            "phone": "+77001112235",
            "full_name": "D2",
            "car_model": "Cobalt",
            "car_number": "01A999ZZ",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_drivers(self):
        response = self.client.get("/api/users/admin/drivers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_admin_cannot_create_driver(self):
        client_user = User.objects.create_user(
            phone="+77001112240", full_name="Client", role="client", is_active=True
        )
        self.client.force_authenticate(user=client_user)
        response = self.client.post("/api/users/admin/drivers/create/", {
            "phone": "+77001112250",
            "full_name": "New Driver",
            "car_model": "Cobalt",
            "car_number": "01B111AA",
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
