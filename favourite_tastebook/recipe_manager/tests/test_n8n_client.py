from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase, override_settings

from recipe_manager.domain.exceptions import (
    VectorBackendResponseError,
    VectorBackendUnavailableError,
)
from recipe_manager.infrastructure.vector_search.n8n_client import N8nPineconeClient

POST_TARGET = "recipe_manager.infrastructure.vector_search.n8n_client.requests.post"


def _fake_response(status_code=200, payload=None, text=""):
    """Build a fake requests.Response. payload=None makes .json() raise (malformed body)."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    if payload is None:
        resp.json.side_effect = ValueError("No JSON object could be decoded")
    else:
        resp.json.return_value = payload
    return resp


@override_settings(
    N8N_PINECONE_WEBHOOK_URL="http://n8n:5678/webhook/recipe-vector-search",
    N8N_WEBHOOK_AUTH_TOKEN="test-token",
    N8N_WEBHOOK_TIMEOUT=5,
    VECTOR_SEARCH_TOP_K=20,
)
class N8nPineconeClientTests(TestCase):
    """Covers the response-parsing layer where the id/recipe_id mismatch lives."""

    @patch(POST_TARGET)
    def test_parses_valid_payload_into_ordered_tuples(self, mock_post):
        mock_post.return_value = _fake_response(
            payload={"matches": [{"id": 3, "score": 0.9}, {"id": 1, "score": 0.8}]}
        )
        result = N8nPineconeClient().query("soup", top_k=5)
        self.assertEqual(result, [(3, 0.9), (1, 0.8)])

    @patch(POST_TARGET)
    def test_sends_expected_payload_and_auth_header(self, mock_post):
        mock_post.return_value = _fake_response(payload={"matches": []})
        N8nPineconeClient().query("soup", top_k=7)
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"], {"query": "soup", "top_k": 7})
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-token")

    @patch(POST_TARGET)
    def test_wrong_field_name_recipe_id_is_rejected(self, mock_post):
        # GUARD for mismatch #1: n8n must emit "id", not "recipe_id".
        # If the n8n Code node regresses to recipe_id, this test fails loudly.
        mock_post.return_value = _fake_response(
            payload={"matches": [{"recipe_id": 1, "score": 0.7}]}
        )
        with self.assertRaises(VectorBackendResponseError):
            N8nPineconeClient().query("soup", top_k=5)

    @patch(POST_TARGET)
    def test_missing_matches_key_raises_response_error(self, mock_post):
        mock_post.return_value = _fake_response(payload={"unexpected": []})
        with self.assertRaises(VectorBackendResponseError):
            N8nPineconeClient().query("soup", top_k=5)

    @patch(POST_TARGET)
    def test_non_200_raises_response_error(self, mock_post):
        mock_post.return_value = _fake_response(status_code=500, text="boom")
        with self.assertRaises(VectorBackendResponseError):
            N8nPineconeClient().query("soup", top_k=5)

    @patch(POST_TARGET)
    def test_malformed_json_raises_response_error(self, mock_post):
        mock_post.return_value = _fake_response(status_code=200, payload=None)
        with self.assertRaises(VectorBackendResponseError):
            N8nPineconeClient().query("soup", top_k=5)

    @patch(POST_TARGET)
    def test_network_error_raises_unavailable(self, mock_post):
        mock_post.side_effect = requests.RequestException("no route to host")
        with self.assertRaises(VectorBackendUnavailableError):
            N8nPineconeClient().query("soup", top_k=5)

    @patch(POST_TARGET)
    def test_missing_score_defaults_to_zero(self, mock_post):
        mock_post.return_value = _fake_response(payload={"matches": [{"id": 1}]})
        result = N8nPineconeClient().query("soup", top_k=5)
        self.assertEqual(result, [(1, 0.0)])

    @override_settings(N8N_PINECONE_WEBHOOK_URL="")
    @patch(POST_TARGET)
    def test_missing_webhook_url_fails_fast_without_network(self, mock_post):
        with self.assertRaises(VectorBackendUnavailableError):
            N8nPineconeClient().query("soup", top_k=5)
        mock_post.assert_not_called()