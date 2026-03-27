"""Internationalization — English and Arabic translations."""

import arabic_reshaper
from bidi.algorithm import get_display


import re
import functools

_ARABIC_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')


@functools.lru_cache(maxsize=512)
def _shape_arabic(text: str) -> str:
    """Reshape Arabic text so Tkinter renders connected RTL glyphs."""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def shape_if_arabic(text: str) -> str:
    """Shape text only if it contains Arabic characters. Use for API content."""
    if _ARABIC_RE.search(text):
        return _shape_arabic(text)
    return text


STRINGS = {
    "en": {
        # App
        "app_title": "SeenShow Downloader",

        # Login
        "login_title": "SeenShow Downloader",
        "login_subtitle": "Sign in to your SeenShow account",
        "email": "Email",
        "password": "Password",
        "remember": "Remember credentials",
        "sign_in": "Sign In",
        "signing_in": "Signing in...",
        "enter_credentials": "Please enter email and password.",
        "connecting": "Connecting...",
        "conn_error": "Connection error: {0}",

        # Auth status
        "auth_csrf": "Getting CSRF token...",
        "auth_keycloak": "Connecting to Keycloak...",
        "auth_login_page": "Loading login page...",
        "auth_signing_in": "Signing in...",
        "auth_completing": "Completing authentication...",
        "auth_success": "Signed in successfully.",

        # Download
        "url_label": "URL:",
        "url_placeholder": "Paste seenshow.com URL...",
        "fetch": "Fetch",
        "loading": "Loading...",
        "episode_not_found": "Episode not found.",
        "select_all": "Select All",
        "deselect_all": "Deselect All",
        "download_selected": "Download Selected",
        "cancel": "Cancel",
        "cancelling": "Cancelling...",
        "all_done": "All downloads complete.",
        "done": "Done",
        "error": "Error",
        "cancelled": "Cancelled",
        "queued": "Queued",
        "starting": "Starting ({0}/{1})...",
        "placeholder_text": "Paste a SeenShow URL above and click Fetch\nto see available episodes.",

        # Download phases
        "fetching_info": "Fetching episode info...",
        "getting_drm": "Getting DRM token...",
        "getting_keys": "Getting decryption keys...",
        "downloading_video": "Downloading video",
        "downloading_audio": "Downloading audio",
        "decrypting_video": "Decrypting video...",
        "decrypting_audio": "Decrypting audio...",
        "muxing": "Muxing final file...",
        "left": "left",
        "eta_h": "{0}h {1}m left",
        "eta_m": "{0}m {1}s left",
        "eta_s": "{0}s left",

        # Settings
        "settings": "Settings",
        "back": "Back",
        "output_dir": "Output Directory",
        "browse": "Browse",
        "account": "Account",
        "not_signed_in": "Not signed in",
        "sign_out": "Sign Out",
        "save_settings": "Save Settings",
        "settings_saved": "Settings saved.",
        "check_updates": "Check for Updates",
        "checking": "Checking...",
        "update_available": "v{0} available!",
        "up_to_date": "Up to date.",
        "language": "Language",
    },

    "ar": {
        # App
        "app_title": "محمّل سين",

        # Login
        "login_title": "محمّل سين",
        "login_subtitle": "سجّل الدخول إلى حسابك في سين",
        "email": "البريد الإلكتروني",
        "password": "كلمة المرور",
        "remember": "تذكر بيانات الدخول",
        "sign_in": "تسجيل الدخول",
        "signing_in": "جارٍ تسجيل الدخول...",
        "enter_credentials": "يرجى إدخال البريد الإلكتروني وكلمة المرور.",
        "connecting": "جارٍ الاتصال...",
        "conn_error": "خطأ في الاتصال: {0}",

        # Auth status
        "auth_csrf": "جارٍ الحصول على رمز الأمان...",
        "auth_keycloak": "جارٍ الاتصال بالخادم...",
        "auth_login_page": "جارٍ تحميل صفحة الدخول...",
        "auth_signing_in": "جارٍ تسجيل الدخول...",
        "auth_completing": "جارٍ إتمام المصادقة...",
        "auth_success": "تم تسجيل الدخول بنجاح.",

        # Download
        "url_label": "الرابط:",
        "url_placeholder": "الصق رابط seenshow.com هنا...",
        "fetch": "جلب",
        "loading": "جارٍ التحميل...",
        "episode_not_found": "الحلقة غير موجودة.",
        "select_all": "تحديد الكل",
        "deselect_all": "إلغاء التحديد",
        "download_selected": "تحميل المحدد",
        "cancel": "إلغاء",
        "cancelling": "جارٍ الإلغاء...",
        "all_done": "اكتملت جميع التحميلات.",
        "done": "تم",
        "error": "خطأ",
        "cancelled": "ملغى",
        "queued": "في الانتظار",
        "starting": "جارٍ البدء ({0}/{1})...",
        "placeholder_text": "الصق رابط سين أعلاه واضغط جلب\nلعرض الحلقات المتاحة.",

        # Download phases
        "fetching_info": "جارٍ جلب معلومات الحلقة...",
        "getting_drm": "جارٍ الحصول على رمز DRM...",
        "getting_keys": "جارٍ الحصول على مفاتيح فك التشفير...",
        "downloading_video": "جارٍ تحميل الفيديو",
        "downloading_audio": "جارٍ تحميل الصوت",
        "decrypting_video": "جارٍ فك تشفير الفيديو...",
        "decrypting_audio": "جارٍ فك تشفير الصوت...",
        "muxing": "جارٍ دمج الملف النهائي...",
        "left": "متبقي",
        "eta_h": "{0} ساعة {1} دقيقة متبقية",
        "eta_m": "{0} دقيقة {1} ثانية متبقية",
        "eta_s": "{0} ثانية متبقية",

        # Settings
        "settings": "الإعدادات",
        "back": "رجوع",
        "output_dir": "مجلد التحميل",
        "browse": "تصفح",
        "account": "الحساب",
        "not_signed_in": "غير مسجّل الدخول",
        "sign_out": "تسجيل الخروج",
        "save_settings": "حفظ الإعدادات",
        "settings_saved": "تم حفظ الإعدادات.",
        "check_updates": "التحقق من التحديثات",
        "checking": "جارٍ التحقق...",
        "update_available": "الإصدار {0} متاح!",
        "up_to_date": "محدّث.",
        "language": "اللغة",
    },
}


class I18n:
    """Translation helper."""

    def __init__(self, lang: str = "en"):
        self._lang = lang

    @property
    def lang(self) -> str:
        return self._lang

    @lang.setter
    def lang(self, value: str):
        self._lang = value

    @property
    def is_rtl(self) -> bool:
        return self._lang == "ar"

    def t(self, key: str, *args) -> str:
        text = STRINGS.get(self._lang, STRINGS["en"]).get(key, key)
        if args:
            text = text.format(*args)
        if self._lang == "ar":
            text = _shape_arabic(text)
        return text

    # Layout helpers for RTL/LTR
    @property
    def start(self) -> str:
        return "right" if self.is_rtl else "left"

    @property
    def end(self) -> str:
        return "left" if self.is_rtl else "right"

    @property
    def anchor_start(self) -> str:
        return "e" if self.is_rtl else "w"

    @property
    def anchor_end(self) -> str:
        return "w" if self.is_rtl else "e"

    @property
    def justify(self) -> str:
        return "right" if self.is_rtl else "left"
