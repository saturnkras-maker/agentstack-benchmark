from __future__ import annotations

import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from urllib import error, request

from agentstack_benchmark.security import SecurityConfig
from agentstack_benchmark.server import make_server


class SecurityPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-security-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def _start_server(self, security_config: SecurityConfig):
        server = make_server(
            "127.0.0.1",
            0,
            self.tmpdir / "runs",
            security_config=security_config,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.shutdown)
        return server

    def _get_json(self, server, path: str, headers: dict[str, str] | None = None) -> dict:
        req = request.Request(f"http://127.0.0.1:{server.server_port}{path}", headers=headers or {})
        with request.urlopen(req, timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "application/json")
            return json.loads(response.read().decode("utf-8"))

    def _get_error_json(
        self,
        server,
        path: str,
        expected_status: int,
        headers: dict[str, str] | None = None,
    ) -> tuple[dict, error.HTTPError]:
        req = request.Request(f"http://127.0.0.1:{server.server_port}{path}", headers=headers or {})
        try:
            request.urlopen(req, timeout=5)
        except error.HTTPError as exc:
            self.assertEqual(exc.code, expected_status)
            self.assertEqual(exc.headers.get_content_type(), "application/json")
            return json.loads(exc.read().decode("utf-8")), exc
        self.fail(f"Expected HTTP {expected_status} for {path}")

    def test_security_metadata_never_exposes_bearer_token(self) -> None:
        config = SecurityConfig.from_token(
            "synthetic-token-value",
            rate_limit_requests=7,
            rate_limit_window_seconds=60,
        )

        public_metadata = config.to_public_dict()
        encoded = json.dumps(public_metadata, ensure_ascii=False)

        self.assertEqual(public_metadata["auth"]["mode"], "bearer")
        self.assertTrue(public_metadata["auth"]["enabled"])
        self.assertEqual(public_metadata["rateLimit"]["requests"], 7)
        self.assertEqual(public_metadata["rateLimit"]["windowSeconds"], 60)
        self.assertNotIn("synthetic-token-value", encoded)

    def test_configured_bearer_auth_protects_preview_surfaces(self) -> None:
        config = SecurityConfig.from_token(
            "synthetic-token-value",
            rate_limit_requests=10,
            rate_limit_window_seconds=60,
        )
        server = self._start_server(config)

        health = self._get_json(server, "/api/v1/healthz")
        self.assertTrue(health["security"]["auth"]["enabled"])
        self.assertNotIn("synthetic-token-value", json.dumps(health, ensure_ascii=False))

        missing_body, missing_exc = self._get_error_json(server, "/api/v1/tracks", 401)
        self.assertEqual(missing_body["error"]["code"], "AUTH_REQUIRED")
        self.assertEqual(missing_exc.headers["WWW-Authenticate"], "Bearer")

        wrong_body, _ = self._get_error_json(
            server,
            "/api/v1/tracks",
            403,
            headers={"Authorization": "Bearer wrong-synthetic-token"},
        )
        self.assertEqual(wrong_body["error"]["code"], "AUTH_INVALID")

        body = self._get_json(
            server,
            "/api/v1/tracks",
            headers={"Authorization": "Bearer synthetic-token-value"},
        )
        self.assertEqual(body["trackCapabilities"]["defaultTrack"], "local-public")

    def test_rate_limit_returns_429_with_retry_after(self) -> None:
        config = SecurityConfig.from_token(
            None,
            rate_limit_requests=2,
            rate_limit_window_seconds=60,
        )
        server = self._start_server(config)

        self._get_json(server, "/api/v1/tracks")
        self._get_json(server, "/api/v1/tracks")
        body, exc = self._get_error_json(server, "/api/v1/tracks", 429)

        self.assertEqual(body["error"]["code"], "RATE_LIMITED")
        self.assertEqual(exc.headers["Retry-After"], "60")


if __name__ == "__main__":
    unittest.main()
