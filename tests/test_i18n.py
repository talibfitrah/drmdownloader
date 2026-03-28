"""Tests for i18n — translation, shaping, RTL helpers."""

from src.ui.i18n import I18n, shape_if_arabic, STRINGS


class TestI18n:
    def test_english_default(self):
        i = I18n("en")
        assert i.t("sign_in") == "Sign In"
        assert not i.is_rtl

    def test_arabic_translation(self):
        i = I18n("ar")
        result = i.t("sign_in")
        assert result != "sign_in"  # Should be translated
        assert result != "Sign In"  # Should not be English
        assert i.is_rtl

    def test_missing_key_returns_key(self):
        i = I18n("en")
        assert i.t("nonexistent_key") == "nonexistent_key"

    def test_format_args(self):
        i = I18n("en")
        result = i.t("starting", 2, 5)
        assert "2" in result
        assert "5" in result

    def test_rtl_layout_helpers(self):
        i = I18n("ar")
        assert i.start == "right"
        assert i.end == "left"
        assert i.anchor_start == "e"
        assert i.anchor_end == "w"
        assert i.justify == "right"

    def test_ltr_layout_helpers(self):
        i = I18n("en")
        assert i.start == "left"
        assert i.end == "right"
        assert i.anchor_start == "w"
        assert i.anchor_end == "e"
        assert i.justify == "left"

    def test_lang_setter(self):
        i = I18n("en")
        assert not i.is_rtl
        i.lang = "ar"
        assert i.is_rtl

    def test_all_en_keys_have_ar_counterpart(self):
        en_keys = set(STRINGS["en"].keys())
        ar_keys = set(STRINGS["ar"].keys())
        missing = en_keys - ar_keys
        assert not missing, f"Arabic missing keys: {missing}"


class TestShapeIfArabic:
    def test_english_unchanged(self):
        assert shape_if_arabic("Hello World") == "Hello World"

    def test_arabic_shaped(self):
        original = "الحلقة"
        result = shape_if_arabic(original)
        assert result != ""
        # Shaped text should differ from raw input (connected forms)
        assert result != original, "shape_if_arabic should modify Arabic text"
        # Verify at least one codepoint differs
        assert any(
            ord(a) != ord(b) for a, b in zip(result, original)
        ), "shaped result should contain different codepoints"

    def test_empty_string(self):
        assert shape_if_arabic("") == ""

    def test_mixed_content(self):
        result = shape_if_arabic("Episode الحلقة 5")
        assert "5" in result
