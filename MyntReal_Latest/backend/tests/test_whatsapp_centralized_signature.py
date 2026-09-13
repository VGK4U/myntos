import unittest
from app.services.whatsapp_auto_service import (
    get_channel_business_contacts,
    get_whatsapp_business_contacts,
    get_ivy_business_contacts,
    build_whatsapp_customer_signature,
    build_channel_customer_signature,
    format_staff_whatsapp_message,
    strip_staff_whatsapp_signature,
)


class TestWhatsAppCentralizedSignature(unittest.TestCase):

    def test_01_centralized_contacts(self):
        contacts = get_whatsapp_business_contacts()
        self.assertEqual(contacts["primary"], "+91 85858 52738")
        self.assertEqual(contacts["secondary"], "+91 8897797667")
        self.assertEqual(contacts["combined_formatted"], "+91 85858 52738 | +91 8897797667")
        self.assertEqual(contacts["canonical_display"], "📞 +91 85858 52738 | +91 8897797667")
        self.assertEqual(contacts["company"], "Mynt Real")

    def test_02_customer_signature_builder_default(self):
        sig = build_whatsapp_customer_signature()
        expected = (
            "Regards,\n"
            "Mynt Real\n"
            "+91 85858 52738 | +91 8897797667"
        )
        self.assertEqual(sig, expected)

    def test_03_customer_signature_builder_with_extension(self):
        sig = build_whatsapp_customer_signature("Madhava Rao", extension="11")
        expected = (
            "Regards,\n"
            "Madhava Rao\n"
            "+91 85858 52738 | +91 8897797667\n"
            "Ext: 11"
        )
        self.assertEqual(sig, expected)

    def test_04_format_staff_message_default_dual_number(self):
        msg = "Dear customer, your solar proposal has been generated."
        formatted = format_staff_whatsapp_message(msg, "Pujita", extension="1")
        expected = (
            "Dear customer, your solar proposal has been generated.\n\n"
            "Regards,\n"
            "Pujita\n"
            "+91 85858 52738 | +91 8897797667\n"
            "Ext: 1"
        )
        self.assertEqual(formatted, expected)

    def test_05_format_staff_message_explicit_override_backward_compat(self):
        msg = "Namaskaram!"
        formatted = format_staff_whatsapp_message(
            msg, "Pujita", contact_number="8585852738", extension="1"
        )
        expected = (
            "Namaskaram!\n\n"
            "Regards,\n"
            "Pujita\n"
            "8585852738\n"
            "Ext: 1"
        )
        self.assertEqual(formatted, expected)

    def test_06_strip_signature_idempotency(self):
        orig = "Hello, welcome to Mynt Real!"
        fmt1 = format_staff_whatsapp_message(orig, "Staff Member", extension=None)
        self.assertIn("+91 85858 52738 | +91 8897797667", fmt1)

        fmt2 = format_staff_whatsapp_message(fmt1, "Staff Member", extension=None)
        self.assertEqual(fmt1, fmt2)

        fmt3 = format_staff_whatsapp_message(fmt1, "Nandana", extension="15")
        self.assertNotIn("Staff Member", fmt3)
        self.assertIn("Nandana", fmt3)
        self.assertIn("Ext: 15", fmt3)

    def test_07_strip_legacy_and_new_signatures(self):
        legacy_signed = "Test message\n\nRegards,\nPujita\n8585852738\nExt: 1"
        self.assertEqual(strip_staff_whatsapp_signature(legacy_signed), "Test message")

        new_signed = "Test message\n\nRegards,\nPujita\n+91 85858 52738 | +91 8897797667\nExt: 1"
        self.assertEqual(strip_staff_whatsapp_signature(new_signed), "Test message")

        ivy_signed = "Test message\n\nRegards,\nPujita\n+91 85858 52738 | +91 80317 28899\nExt: 1"
        self.assertEqual(strip_staff_whatsapp_signature(ivy_signed), "Test message")

        co_signed = "Test message\n\nRegards,\nMynt Real\n+91 85858 52738 | +91 8897797667"
        self.assertEqual(strip_staff_whatsapp_signature(co_signed), "Test message")

    def test_08_channel_ivy_contacts(self):
        contacts = get_ivy_business_contacts()
        self.assertEqual(contacts["channel"], "ivy")
        self.assertEqual(contacts["primary"], "+91 85858 52738")
        self.assertEqual(contacts["secondary"], "+91 80317 28899")
        self.assertEqual(contacts["combined_formatted"], "+91 85858 52738 | +91 80317 28899")
        self.assertEqual(contacts["canonical_display"], "📞 +91 85858 52738 | +91 80317 28899")

    def test_09_channel_signatures_separation_and_negative_checks(self):
        wa_sig = build_channel_customer_signature("whatsapp", include_icon=True)
        ivy_sig = build_channel_customer_signature("ivy", include_icon=True)

        self.assertIn("📞 +91 85858 52738 | +91 8897797667", wa_sig)
        self.assertIn("📞 +91 85858 52738 | +91 80317 28899", ivy_sig)

        # STRICT NEGATIVE CHECKS:
        # WhatsApp MUST NEVER contain 80317 28899
        self.assertNotIn("80317", wa_sig)
        # Ivy MUST NEVER contain 88977 97667
        self.assertNotIn("88977", ivy_sig)

    def test_10_format_staff_message_channel_aware(self):
        msg = "Appointment confirmed."
        wa_msg = format_staff_whatsapp_message(msg, "Agent", channel="whatsapp")
        ivy_msg = format_staff_whatsapp_message(msg, "Agent", channel="ivy")

        self.assertIn("+91 85858 52738 | +91 8897797667", wa_msg)
        self.assertNotIn("80317", wa_msg)

        self.assertIn("+91 85858 52738 | +91 80317 28899", ivy_msg)
        self.assertNotIn("88977", ivy_msg)


if __name__ == "__main__":
    unittest.main()
