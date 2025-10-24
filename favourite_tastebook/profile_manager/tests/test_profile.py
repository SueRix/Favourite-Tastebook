import os
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from profile_manager.models import Profile

from PIL import Image
import io

def make_png_bytes(size=(2, 2), color=(255, 0, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

TEMP_MEDIA_ROOT = tempfile.mkdtemp()



@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ProfileViewsTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user1 = User.objects.create_user(username="alice", password="pass123", email="alice@example.com")
        self.user2 = User.objects.create_user(username="bob", password="pass123", email="bob@example.com")

    def test_profile_detail_public(self):
        url = reverse("profile_detail", kwargs={"username": self.user1.username})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["profile"].user.username, "alice")

    def test_edit_requires_login_redirects_for_anonymous(self):
        url = reverse("profile_edit", kwargs={"username": self.user1.username})
        resp = self.client.get(url, follow=False)
        self.assertEqual(resp.status_code, 302)  # LoginRequiredMixin redirect

    def test_edit_owner_get_ok(self):
        self.client.force_login(self.user1)
        url = reverse("profile_edit", kwargs={"username": self.user1.username})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("user_form", resp.context)
        self.assertIn("profile_form", resp.context)

    def test_edit_non_owner_404(self):
        self.client.force_login(self.user2)
        url = reverse("profile_edit", kwargs={"username": self.user1.username})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_update_profile_success_stays_on_edit(self):
        self.client.force_login(self.user1)
        url = reverse("profile_edit", kwargs={"username": self.user1.username})
        data = {
            "first_name": "Alice",
            "last_name": "Wonder",
            "email": "alice_new@example.com",
            "display_name": "Ali",
            "country": "Ukraine",
            "bio": "I like cooking",
            "birth_date": "2005-06-01",
            "gender": "FEMALE",
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context.get("saved"))

        self.user1.refresh_from_db()
        self.assertEqual(self.user1.first_name, "Alice")
        self.assertEqual(self.user1.email, "alice_new@example.com")
        profile = self.user1.profile
        self.assertEqual(profile.display_name, "Ali")
        self.assertEqual(profile.country, "Ukraine")
        self.assertEqual(str(profile.birth_date), "2005-06-01")
        self.assertEqual(profile.gender, Profile.Gender.FEMALE)

    def test_update_profile_conflicting_email_returns_400(self):
        self.client.force_login(self.user1)
        url = reverse("profile_edit", kwargs={"username": self.user1.username})
        data = {
            "first_name": "A",
            "last_name": "B",
            "email": "bob@example.com",
            "display_name": "Ali",
            "country": "UA",
            "bio": "x",
            "birth_date": "2005-06-01",
            "gender": "F",
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("errors", resp.context)
        self.assertIn("email", resp.context["errors"]["user"])

    def test_remove_avatar_via_flag(self):
        self.client.force_login(self.user1)
        p = self.user1.profile
        initial_bytes = make_png_bytes()
        initial_file = SimpleUploadedFile("a.png", initial_bytes, content_type="image/png")
        url = reverse("profile_edit", kwargs={"username": self.user1.username})
        data_first = {
            "first_name": "A",
            "last_name": "B",
            "email": "alice@example.com",
            "display_name": "Ali",
            "country": "UA",
            "bio": "x",
            "birth_date": "2005-06-01",
            "gender": "MALE",
        }
        resp1 = self.client.post(url, {**data_first, "avatar": initial_file})
        self.assertEqual(resp1.status_code, 200)
        p.refresh_from_db()
        self.assertTrue(bool(p.avatar))
        old_path = p.avatar.path
        self.assertTrue(os.path.exists(old_path))

        data_remove = {
            **data_first,
            "remove_avatar": True,
        }
        resp2 = self.client.post(url, data_remove)
        self.assertEqual(resp2.status_code, 200)
        p.refresh_from_db()
        self.assertFalse(bool(p.avatar))
        self.assertFalse(os.path.exists(old_path))

    def test_change_avatar_deletes_old_file(self):
        self.client.force_login(self.user1)
        url = reverse("profile_edit", kwargs={"username": self.user1.username})

        data = {
            "first_name": "A",
            "last_name": "B",
            "email": "alice@example.com",
            "display_name": "Ali",
            "country": "UA",
            "bio": "x",
            "birth_date": "2005-06-01",
            "gender": "FEMALE",
        }

        file_a = SimpleUploadedFile("avatar.png", make_png_bytes(), content_type="image/png")
        resp_a = self.client.post(url, {**data, "avatar": file_a})
        self.assertEqual(resp_a.status_code, 200)
        prof = self.user1.profile
        prof.refresh_from_db()
        path_a = prof.avatar.path
        self.assertTrue(os.path.exists(path_a))

        file_b = SimpleUploadedFile("avatar.png", make_png_bytes(), content_type="image/png")
        resp_b = self.client.post(url, {**data, "avatar": file_b})
        self.assertEqual(resp_b.status_code, 200)
        prof.refresh_from_db()
        path_b = prof.avatar.path
        self.assertTrue(os.path.exists(path_b))
        self.assertFalse(os.path.exists(path_a))
