import logging
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from .models import DriverProfile
from .otp_service import generate_otp, verify_otp, get_remaining_seconds
from .permissions import IsAdminUser, IsDriver
from .serializers import (
    SendOtpSerializer,
    VerifyOtpSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    DriverProfileSerializer,
    DriverLocationUpdateSerializer,
    CreateDriverSerializer,
)
from .sms_service import send_otp_sms

User = get_user_model()
logger = logging.getLogger(__name__)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class SendOtpView(APIView):
    """
    Telefon raqamga OTP yuboradi.
    Agar foydalanuvchi mavjud bo'lsa — login, yo'q bo'lsa — register jarayoni.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Telefon Raqamga OTP kod yuborish",
        description="Telefon Raqamga OTP kod yuborish",
        request=SendOtpSerializer,
        responses={
            200: OpenApiResponse(description="Ma'lumotlar saqlandi, bot OTP yuboradi"),
            400: OpenApiResponse(description="Validatsiya xatosi"),
        },
        examples=[
            OpenApiExample(
                "Misol",
                value={
                    "phone_number": "+998901234567",
                    "first_name": "Vali",
                    "last_name": "Valiyev",
                    "organization_name": "ABC Company",
                    "position": "HR Manager",
                },
                request_only=True,
            )
        ]
    )
    def post(self, request):
        serializer = SendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]

        code = generate_otp(phone)
        if code is None:
            remaining = get_remaining_seconds(phone)
            return Response(
                {"detail": f"Iltimos {remaining} soniya kuting va qayta urinib ko'ring."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        sms_sent = send_otp_sms(phone, code)
        if not sms_sent:
            return Response(
                {"detail": "SMS yuborishda xatolik yuz berdi. Iltimos keyinroq urinib ko'ring."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        user_exists = User.objects.filter(phone=phone).exists()
        return Response({
            "detail": "Kod yuborildi.",
            "is_registered": user_exists,
        })


class VerifyOtpLoginView(APIView):
    """
    Mavjud foydalanuvchi uchun OTP ni tekshiradi va token qaytaradi.
    """

    permission_classes = [AllowAny]

    @extend_schema(request=VerifyOtpSerializer, tags=["Auth"])
    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]

        if not verify_otp(phone, code):
            return Response(
                {"detail": "Kod noto'g'ri yoki muddati o'tgan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response(
                {"detail": "Foydalanuvchi topilmadi. Avval ro'yxatdan o'ting."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])

        return Response(get_tokens_for_user(user))


class RegisterView(APIView):
    """
    Yangi foydalanuvchi (client) ro'yxatdan o'tkazadi.
    OTP oldin tasdiqlangan bo'lishi kerak — verify_otp True qaytargan bo'lsa.
    """

    permission_classes = [AllowAny]

    @extend_schema(request=RegisterSerializer, tags=["Auth"])
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        full_name = serializer.validated_data["full_name"]

        # OTP tekshiruvi shu yerda ham bo'lishi kerak
        code = request.data.get("code", "")
        if not verify_otp(phone, code):
            return Response(
                {"detail": "Kod noto'g'ri yoki muddati o'tgan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(
            phone=phone,
            full_name=full_name,
            role="client",
            is_active=True,
        )

        logger.info(f"New client registered: {phone}")
        return Response(get_tokens_for_user(user), status=status.HTTP_201_CREATED)


class MeView(APIView):
    """
    Tizimga kirgan foydalanuvchining o'z ma'lumotlari.
    GET — ko'rish, PATCH — tahrirlash.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Profile"])
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(request=UserProfileSerializer, tags=["Profile"])
    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DriverLocationView(APIView):
    """
    Haydovchi o'z joylashuvini yangilaydi.
    Frontend har 10 sekundda bu endpointga murojaat qiladi.
    """

    permission_classes = [IsDriver]

    @extend_schema(request=DriverLocationUpdateSerializer, tags=["Driver"])
    def patch(self, request):
        serializer = DriverLocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = request.user.driver_profile
        profile.current_lat = serializer.validated_data["lat"]
        profile.current_lon = serializer.validated_data["lon"]

        if "is_available" in serializer.validated_data:
            profile.is_available = serializer.validated_data["is_available"]

        profile.save(update_fields=["current_lat", "current_lon", "is_available"])
        return Response({"detail": "Joylashuv yangilandi."})


class DriverProfileView(APIView):
    """
    Haydovchi o'z profilini ko'radi.
    """

    permission_classes = [IsDriver]

    @extend_schema(tags=["Driver"])
    def get(self, request):
        serializer = DriverProfileSerializer(request.user.driver_profile)
        return Response(serializer.data)


class AdminCreateDriverView(APIView):
    """
    Admin yangi haydovchi qo'shadi.
    Haydovchiga alohida login linki beriladi — saytda rol tanlash yo'q.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(request=CreateDriverSerializer, tags=["Admin"])
    def post(self, request):
        serializer = CreateDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        driver_profile = serializer.save()
        return Response(
            DriverProfileSerializer(driver_profile).data,
            status=status.HTTP_201_CREATED,
        )


class AdminDriverListView(APIView):
    """
    Admin barcha haydovchilarni ko'radi.
    """

    permission_classes = [IsAdminUser]

    @extend_schema(tags=["Admin"])
    def get(self, request):
        profiles = DriverProfile.objects.select_related("user").all()
        serializer = DriverProfileSerializer(profiles, many=True)
        return Response(serializer.data)
