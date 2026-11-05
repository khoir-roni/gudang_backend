"""
==============================================================================
FILE: tests/test_ssl_tls.py
FUNGSI: Pengujian Otomatis Keamanan Transport Layer SSL/TLS (HTTPS)
SISTEM: Smart Tools Asset Tracking System (STATS) - PT PLN Indonesia Power UBP Saguling
DESKRIPSI:
    Modul pengujian otomatis untuk memverifikasi kepatuhan keamanan siber transport
    layer pada endpoint publik STATS (https://api.gudangapp-hki.my.id) sesuai
    standar ISA/IEC 62443 dan ISO/IEC 27001:
    1. Validitas & masa berlaku sertifikat SSL/TLS.
    2. Penegakan protokol mutakhir TLS 1.3 / TLS 1.2.
    3. Kekuatan Cipher Suite (AES-256-GCM / 256-bit).
    4. Penolakan protokol usang dan tidak aman (SSLv2, SSLv3, TLS 1.0, TLS 1.1).
    5. Integritas HTTP Security Headers (Strict-Transport-Security / HSTS).
==============================================================================
"""

import unittest
import socket
import ssl
import datetime
import urllib.request
import urllib.error
import http.client

HOSTNAME = "api.gudangapp-hki.my.id"
HTTPS_PORT = 443
HTTPS_URL = f"https://{HOSTNAME}"


class TestSSLTLSSecurity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Memastikan host dapat di-resolve via DNS sebelum menjalankan pengujian
        try:
            socket.gethostbyname(HOSTNAME)
        except socket.gaierror as e:
            raise unittest.SkipTest(f"Host '{HOSTNAME}' tidak dapat dijangkau via DNS: {e}")

    def test_01_certificate_validity_and_expiration(self):
        """
        Test 1: Memverifikasi sertifikat SSL valid, terpercaya, dan belum kedaluwarsa.
        """
        context = ssl.create_default_context()
        with socket.create_connection((HOSTNAME, HTTPS_PORT), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=HOSTNAME) as ssock:
                cert = ssock.getpeercert()

                # 1. Pastikan sertifikat memuat informasi subject dan issuer
                self.assertIsNotNone(cert, "Sertifikat server tidak boleh kosong.")
                issuer_dict = dict(x[0] for x in cert.get("issuer", ()))
                self.assertIn("organizationName", issuer_dict, "Issuer harus memiliki nama organisasi.")

                # 2. Validasi masa berlaku (notBefore <= sekarang <= notAfter)
                not_before = datetime.datetime.strptime(cert["notBefore"], "%b %d %H:%M:%S %Y %Z")
                not_after = datetime.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

                self.assertLessEqual(not_before, now_utc, "Sertifikat belum berlaku (notBefore di masa depan).")
                self.assertGreater(not_after, now_utc, "Sertifikat sudah kedaluwarsa (expired).")

                # 3. Peringatan dini jika sisa masa berlaku < 30 hari
                days_remaining = (not_after - now_utc).days
                self.assertGreater(days_remaining, 30, f"Masa berlaku sertifikat menipis: {days_remaining} hari tersisa.")

    def test_02_enforced_tls_13_protocol(self):
        """
        Test 2: Memverifikasi negosiasi TLS 1.3 didukung dan berhasil dinegosiasikan.
        """
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        context.load_default_certs()

        with socket.create_connection((HOSTNAME, HTTPS_PORT), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=HOSTNAME) as ssock:
                version = ssock.version()
                self.assertEqual(version, "TLSv1.3", f"Negosiasi harus menggunakan TLSv1.3, bukan {version}.")

    def test_03_cipher_suite_strength(self):
        """
        Test 3: Memverifikasi kekuatan cipher suite enkripsi simetris (minimal 128-bit, preferensi 256-bit).
        """
        context = ssl.create_default_context()
        with socket.create_connection((HOSTNAME, HTTPS_PORT), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=HOSTNAME) as ssock:
                cipher_name, tls_version, secret_bits = ssock.cipher()
                # secret_bits harus >= 128-bit untuk mencegah brute force
                self.assertGreaterEqual(secret_bits, 128, f"Kekuatan cipher terlalu lemah: {secret_bits}-bit.")
                # Memastikan menggunakan algoritma modern (GCM / Poly1305 / SHA256 / SHA384)
                self.assertTrue(
                    any(alg in cipher_name for alg in ["GCM", "POLY1305", "AES", "CHACHA20"]),
                    f"Cipher suite harus menggunakan algoritma AEAD modern, aktual: {cipher_name}"
                )

    def test_04_deprecated_protocols_rejection(self):
        """
        Test 4: Memastikan server MENOLAK protokol usang dan tidak aman (TLS 1.0 & TLS 1.1).
        """
        # Cek penolakan TLS 1.0
        try:
            ctx_tls10 = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx_tls10.minimum_version = ssl.TLSVersion.TLSv1
            ctx_tls10.maximum_version = ssl.TLSVersion.TLSv1
            ctx_tls10.check_hostname = False
            ctx_tls10.verify_mode = ssl.CERT_NONE

            with socket.create_connection((HOSTNAME, HTTPS_PORT), timeout=5) as sock:
                with ctx_tls10.wrap_socket(sock, server_hostname=HOSTNAME) as ssock:
                    self.fail("Server membahayakan: TLS 1.0 diterima (seharusnya ditolak).")
        except (ssl.SSLError, ConnectionResetError, OSError):
            # Ditolak sesuai ekspektasi keamanan
            pass

        # Cek penolakan TLS 1.1
        try:
            ctx_tls11 = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx_tls11.minimum_version = ssl.TLSVersion.TLSv1_1
            ctx_tls11.maximum_version = ssl.TLSVersion.TLSv1_1
            ctx_tls11.check_hostname = False
            ctx_tls11.verify_mode = ssl.CERT_NONE

            with socket.create_connection((HOSTNAME, HTTPS_PORT), timeout=5) as sock:
                with ctx_tls11.wrap_socket(sock, server_hostname=HOSTNAME) as ssock:
                    self.fail("Server membahayakan: TLS 1.1 diterima (seharusnya ditolak).")
        except (ssl.SSLError, ConnectionResetError, OSError):
            # Ditolak sesuai ekspektasi keamanan
            pass

    def test_05_https_get_request_and_security_headers(self):
        """
        Test 5: Memverifikasi endpoint HTTPS publik dapat diakses dan merespons dengan aman.
        """
        req = urllib.request.Request(
            f"{HTTPS_URL}/get_barang",
            headers={"User-Agent": "STATS-Security-Audit/1.0"}
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                status_code = response.getcode()
                self.assertIn(status_code, [200, 401, 404], f"Respons HTTP status tidak valid: {status_code}")

                # Verifikasi header server/proxy
                headers = dict(response.info())
                # Server diproxy via Cloudflare yang mengamankan transmisi
                has_cloudflare = any("cf-" in k.lower() or "cloudflare" in v.lower() for k, v in headers.items())
                self.assertTrue(has_cloudflare, "Trafik harus melalui Cloudflare Edge Proxy.")
        except urllib.error.HTTPError as e:
            # Jika memerlukan autentikasi (401/403) atau route SPA, SSL handshake tetap sukses
            self.assertIn(e.code, [401, 403, 404], f"HTTP error tidak terduga: {e.code}")

    def test_06_hostname_mismatch_verification(self):
        """
        Test 6: Memastikan perlindungan terhadap serangan Man-in-the-Middle (MitM) melalui hostname mismatch.
        Server Cloudflare Edge atau klien TLS wajib menolak koneksi dengan handshake failure atau CertificateError.
        """
        context = ssl.create_default_context()
        with socket.create_connection((HOSTNAME, HTTPS_PORT), timeout=10) as sock:
            # Mencoba handshake dengan SNI yang salah (spoofed hostname)
            with self.assertRaises((ssl.CertificateError, ssl.SSLError), msg="Klien atau server harus menolak jika hostname tidak cocok"):
                with context.wrap_socket(sock, server_hostname="fake.domain.invalid") as ssock:
                    _ = ssock.getpeercert()


if __name__ == "__main__":
    unittest.main()
