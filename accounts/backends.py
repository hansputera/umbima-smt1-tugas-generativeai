import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

DUMMY_PASSWORD_HASH = None


def _dummy_verify(password: str) -> None:
    """Equalize timing when the email is unknown (parity with Node login)."""
    global DUMMY_PASSWORD_HASH
    if DUMMY_PASSWORD_HASH is None:
        from django.contrib.auth.hashers import make_password

        DUMMY_PASSWORD_HASH = make_password(secrets.token_hex(16))
    from django.contrib.auth.hashers import check_password

    check_password(password, DUMMY_PASSWORD_HASH)


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get("email")
        if not email or password is None:
            return None
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email__iexact=email)
        except UserModel.DoesNotExist:
            _dummy_verify(password)
            return None
        if user.check_password(password):
            # Inactive users are returned too: the login view decides between
            # "wrong credentials" and "account inactive" (Node parity).
            return user
        return None
