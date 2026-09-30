from django.test import TestCase
from django.urls import reverse

from .models import User


class UserTimTests(TestCase):
    def setUp(self):
        self.komersil = User.objects.create_user(
            username="komersil1", password="x12345", role=User.Role.KOMERSIL
        )
        self.operasi = User.objects.create_user(
            username="operasi1", password="x12345", role=User.Role.OPERASI
        )
        self.aoch = User.objects.create_user(
            username="aoch1", password="x12345", role=User.Role.AOCH
        )
        self.pemohon = User.objects.create_user(
            username="pemohon1", password="x12345", role=User.Role.PEMOHON
        )
        self.url = reverse("accounts:user_tim_buat")
        self.list_url = reverse("accounts:user_tim")

    def test_komersil_membuat_user_komersil(self):
        self.client.force_login(self.komersil)
        resp = self.client.post(
            self.url,
            {
                "username": "komersil2",
                "first_name": "Kawan",
                "last_name": "Komersil",
                "jabatan": "Staf Komersil",
                "phone": "0811",
                "password": "rahasia123",
            },
        )
        self.assertEqual(resp.status_code, 302)
        baru = User.objects.get(username="komersil2")
        self.assertEqual(baru.role, User.Role.KOMERSIL)
        self.assertTrue(baru.check_password("rahasia123"))
        self.assertEqual(baru.password_awal, "rahasia123")
        self.assertTrue(baru.is_active)

    def test_operasi_dan_aoch_bisa_membuat_user(self):
        for pembuat, username in (
            (self.operasi, "operasi2"),
            (self.aoch, "aoch2"),
        ):
            self.client.force_login(pembuat)
            resp = self.client.post(
                self.url,
                {"username": username, "first_name": "Teman",
                 "password": "rahasia123"},
            )
            self.assertEqual(resp.status_code, 302, username)
            self.assertEqual(User.objects.get(username=username).role, pembuat.role)
            self.client.logout()

    def test_pemohon_tidak_boleh_membuat_user(self):
        self.client.force_login(self.pemohon)
        resp = self.client.post(
            self.url,
            {"username": "jahat", "first_name": "X", "password": "rahasia123"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/dashboard/")
        self.assertFalse(User.objects.filter(username="jahat").exists())

    def test_tombol_lihat_menampilkan_username_dan_password(self):
        User.objects.create_user(
            username="komersil2", password="rahasia123", role=User.Role.KOMERSIL
        )
        u = User.objects.get(username="komersil2")
        User.objects.filter(pk=u.pk).update(password_awal="rahasia123")
        self.client.force_login(self.komersil)
        resp = self.client.get(self.list_url)
        self.assertContains(resp, "komersil2")
        self.assertContains(resp, "rahasia123")
        self.assertContains(resp, "Lihat")

    def test_password_awal_dihapus_setelah_login_pertama(self):
        User.objects.create_user(
            username="komersil2", password="rahasia123", role=User.Role.KOMERSIL
        )
        User.objects.filter(username="komersil2").update(password_awal="rahasia123")
        self.client.logout()
        self.client.post(
            reverse("accounts:login"),
            {"username": "komersil2", "password": "rahasia123"},
        )
        self.assertEqual(
            User.objects.get(username="komersil2").password_awal, ""
        )
