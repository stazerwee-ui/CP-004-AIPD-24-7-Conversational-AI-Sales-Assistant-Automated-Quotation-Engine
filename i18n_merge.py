#!/usr/bin/env python3
"""
i18n_merge.py — merge the extracted stub into I18N_TRANSLATIONS in app.js.

TWO THINGS THIS HANDLES THAT A NAIVE MERGE WOULD GET WRONG
----------------------------------------------------------
1. HTML ENTITIES. The extractor reads raw HTML source, so values arrive as
   "Create Account &amp; Begin". setLanguage() assigns with textContent, which
   does NOT decode entities -- the user would literally see "&amp;". Every
   value is decoded before it goes into the dictionary.

2. LEGAL TEXT IS NOT MACHINE TRANSLATED. The seven PDPA consent sections are
   inserted with the English string as the value in all four languages, and
   listed for native legal review. A subtly wrong rendering of "withdrawal of
   consent" in a PDPA notice is a compliance problem, not a copy problem.
"""

import html
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app.js")
STUB = os.path.join(HERE, "i18n_stub.json")

# Keys whose wording must come from a qualified human. Inserted as English in
# all four languages so nothing breaks, and reported for review.
NEEDS_LEGAL_REVIEW = {
    "s1_1_what_we_collect",
    "s1_account_details_name_username_email_or",
    "s1_2_why_we_collect_this_information",
    "s1_to_prepare_transparent_quotations_with_guaranteed",
    "s1_3_conversational_assistant_amp_ai_safety",
    "s1_messages_are_processed_by_an_assistant",
    "s1_4_data_retention_amp_deletion",
    "s1_records_are_retained_only_for_as",
    "s1_5_who_sees_your_information",
    "s1_restricted_strictly_to_authorized_solace_director",
    "s1_6_your_rights_under_the_pdpa",
    "s1_you_have_the_right_to_request",
    "s1_7_contact",
    "s1_data_protection_officer_privacy_solace_sg",
}

# Deliberately not translated: version strings, standard scheme names, and a
# duplicate of an existing key.
SKIP = {
    "btn_close_terms_v1_0_middot_14_aug_2026",   # version + date
    "s6_pdpa_singapore_v1_0",                     # standard scheme name
    "s1_solace_dignity_care_middot_singapore",    # duplicate of hero_eyebrow
}

# UI labels. Safe to translate, but still machine output -- flagged in the
# report for a native speaker to sanity-check.
TRANSLATIONS = {
    "misc_director_notified": {
        "zh": "已通知殡仪总监", "ms": "Pengarah Dimaklumkan", "ta": "இயக்குநருக்குத் தெரிவிக்கப்பட்டது"},
    "s1_aria_select_language": {
        "zh": "选择语言", "ms": "Pilih Bahasa", "ta": "மொழியைத் தேர்ந்தெடுக்கவும்"},
    "s6_aria_select_language": {
        "zh": "选择语言", "ms": "Pilih Bahasa", "ta": "மொழியைத் தேர்ந்தெடுக்கவும்"},
    "s1_aria_show_password": {
        "zh": "显示密码", "ms": "Tunjukkan kata laluan", "ta": "கடவுச்சொல்லைக் காட்டு"},
    "s1_create_account_amp_begin": {
        "zh": "创建账户并开始", "ms": "Buka Akaun & Mulakan", "ta": "கணக்கை உருவாக்கித் தொடங்குங்கள்"},
    "s3_exit_to_ai": {
        "zh": "✕ 返回 AI 助理", "ms": "✕ Kembali ke AI", "ta": "✕ AI உதவியாளருக்குத் திரும்பு"},
    "s3_aria_conversation_with_hannah": {
        "zh": "与 Hannah 的对话", "ms": "Perbualan dengan Hannah", "ta": "Hannah உடனான உரையாடல்"},
    "s3_aria_more_actions": {
        "zh": "更多操作", "ms": "Tindakan lain", "ta": "மேலும் செயல்கள்"},
    "s3_aria_type_your_message_to_the_assistant": {
        "zh": "向助理输入讯息", "ms": "Taip mesej kepada pembantu", "ta": "உதவியாளருக்குச் செய்தியை உள்ளிடவும்"},
    "s3_aria_speak_your_message": {
        "zh": "语音输入讯息", "ms": "Sebut mesej anda", "ta": "உங்கள் செய்தியைப் பேசுங்கள்"},
    "s3_aria_send_message": {
        "zh": "发送讯息", "ms": "Hantar mesej", "ta": "செய்தியை அனுப்பு"},
    "s5_database_compliance_signature": {
        "zh": "数据库合规签署：", "ms": "Tandatangan Pematuhan Pangkalan Data:",
        "ta": "தரவுத்தள இணக்கக் கையொப்பம்:"},
    "s5_pending": {
        "zh": "待处理", "ms": "Menunggu", "ta": "நிலுவையில்"},
    "s6_none": {
        "zh": "无", "ms": "Tiada", "ta": "இல்லை"},
    "s6_not_linked": {
        "zh": "未绑定", "ms": "Tidak dipautkan", "ta": "இணைக்கப்படவில்லை"},
    "terms_terms_amp_privacy_notice": {
        "zh": "条款与隐私声明", "ms": "Terma & Notis Privasi", "ta": "விதிமுறைகள் & தனியுரிமை அறிவிப்பு"},
    "terms_singapore_pdpa_compliance": {
        "zh": "新加坡个人资料保护法合规", "ms": "Pematuhan PDPA Singapura",
        "ta": "சிங்கப்பூர் PDPA இணக்கம்"},
    "btn_close_terms_aria_close_terms": {
        "zh": "关闭条款", "ms": "Tutup Terma", "ta": "விதிமுறைகளை மூடு"},
    "btn_close_consultant_aria_close_modal": {
        "zh": "关闭窗口", "ms": "Tutup tetingkap", "ta": "சாளரத்தை மூடு"},
    "btn_close_consultant_personal_care_assistance": {
        "zh": "个人关怀协助", "ms": "Bantuan Penjagaan Peribadi", "ta": "தனிப்பட்ட பராமரிப்பு உதவி"},
    "btn_close_consultant_optional": {
        "zh": "（选填）", "ms": "(Pilihan)", "ta": "(விருப்பத்தேர்வு)"},
    "btn_close_consultant_optional_2": {
        "zh": "（选填）", "ms": "(Pilihan)", "ta": "(விருப்பத்தேர்வு)"},
    "btn_close_consultant_reason_for_request": {
        "zh": "申请事由", "ms": "Sebab Permohonan", "ta": "கோரிக்கைக்கான காரணம்"},
    "btn_close_consultant_ai_conversation_handoff": {
        "zh": "AI 对话转接", "ms": "Serahan Perbualan AI", "ta": "AI உரையாடல் ஒப்படைப்பு"},
    # Example names in placeholders are localised to a name a speaker of that
    # language would recognise. Singapore is multi-ethnic, so a single example
    # name would look out of place in three of the four dictionaries.
    "btn_close_consultant_ph_e_g_kelvin_tan": {
        "zh": "例如：陈伟明", "ms": "cth. Ahmad bin Ali", "ta": "எ.கா. ராஜேஷ் குமார்"},
    "btn_close_consultant_ph_e_g_kelvin_example_sg": {
        "zh": "例如：kelvin@example.sg", "ms": "cth. kelvin@example.sg",
        "ta": "எ.கா. kelvin@example.sg"},
    "btn_close_consultant_ph_e_g_inquiring_about_buddhist": {
        "zh": "例如：想了解佛教三日治丧统筹…",
        "ms": "cth. Bertanya tentang penyelarasan Buddha 3 hari...",
        "ta": "எ.கா. புத்த மத 3 நாள் ஏற்பாடு குறித்து விசாரிக்க..."},
}


def main():
    with io.open(STUB, encoding="utf-8") as fh:
        stub = json.load(fh)

    with io.open(APP, encoding="utf-8", newline="") as fh:
        src = fh.read()

    added, legal, skipped = [], [], []
    lines = {"en": [], "zh": [], "ms": [], "ta": []}

    for key, raw_en in stub["en"].items():
        if key in SKIP:
            skipped.append(key)
            continue
        # Decode entities: textContent renders them literally otherwise.
        en_val = html.unescape(raw_en)

        if key in NEEDS_LEGAL_REVIEW:
            legal.append(key)
            vals = {lang: en_val for lang in ("en", "zh", "ms", "ta")}
        elif key in TRANSLATIONS:
            added.append(key)
            vals = {"en": en_val}
            vals.update(TRANSLATIONS[key])
        else:
            skipped.append(key)
            continue

        for lang in lines:
            esc = vals[lang].replace("\\", "\\\\").replace('"', '\\"')
            lines[lang].append('    {}: "{}",'.format(key, esc))

    # Insert after each language's hero_eyebrow, which is unique per dictionary.
    anchors = {
        "en": '    hero_eyebrow: "Solace Dignity Care · Singapore",',
        "zh": '    hero_eyebrow: "Solace Dignity Care · 新加坡",',
        "ms": '    hero_eyebrow: "Solace Dignity Care · Singapura",',
        "ta": '    hero_eyebrow: "Solace Dignity Care · சிங்கப்பூர்",',
    }
    for lang, anchor in anchors.items():
        if src.count(anchor) != 1:
            raise SystemExit("anchor not unique for {}: {}".format(lang, src.count(anchor)))
        block = anchor + "\r\n" + "\r\n".join(lines[lang])
        src = src.replace(anchor, block)

    with io.open(APP, "w", encoding="utf-8", newline="") as fh:
        fh.write(src)

    print("Merged into I18N_TRANSLATIONS:")
    print("  translated (machine, needs sanity check): {}".format(len(added)))
    print("  English placeholder, NEEDS LEGAL REVIEW: {}".format(len(legal)))
    print("  skipped (versions/duplicates/scheme names): {}".format(len(skipped)))
    print("\nNEEDS NATIVE LEGAL REVIEW:")
    for k in legal:
        print("  " + k)
    print("\nSkipped:")
    for k in skipped:
        print("  " + k)


if __name__ == "__main__":
    main()
