from typing import List, Tuple

import requests
from django.conf import settings

from recipe_manager.domain.exceptions import (
    VectorBackendUnavailableError,
    VectorBackendResponseError,
)


class N8nPineconeClient:
    """
    What: Thin HTTP client that calls the self-hosted n8n webhook which, in turn,
          embeds the query and runs the Pinecone similarity search.
    Where: Used by VectorSelectionStrategy to obtain candidate recipe ids.
    Why: Keeps ALL transport concerns (URL, auth header, timeout, payload shape,
         error translation) in one place, so the strategy stays pure domain logic.

    Contract with the n8n workflow:
        Request  (POST, JSON):  {"query": "<keyword>", "top_k": <int>}
        Response (JSON):        {"matches": [{"id": <int>, "score": <float>}, ...]}
    """

    def __init__(self, webhook_url: str = None, auth_token: str = None, timeout: float = None):
        self.webhook_url = webhook_url or settings.N8N_PINECONE_WEBHOOK_URL
        self.auth_token = auth_token if auth_token is not None else settings.N8N_WEBHOOK_AUTH_TOKEN
        self.timeout = timeout or settings.N8N_WEBHOOK_TIMEOUT

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        # n8n "Header Auth" credential — sent only when configured.
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def query(self, keyword: str, top_k: int) -> List[Tuple[int, float]]:
        """
        Returns an ORDERED list of (recipe_id, score) tuples, best match first.
        Ordering is authoritative — it is Pinecone's similarity ranking and must be
        preserved by the caller when hydrating rows from Postgres.
        """
        if not self.webhook_url:
            raise VectorBackendUnavailableError("N8N_PINECONE_WEBHOOK_URL is not configured.")

        payload = {"query": keyword, "top_k": top_k}

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise VectorBackendUnavailableError(f"n8n webhook request failed: {exc}") from exc

        if response.status_code != 200:
            raise VectorBackendResponseError(
                f"n8n webhook returned HTTP {response.status_code}: {response.text[:200]}"
            )

        try:
            data = response.json()
            matches = data["matches"]
            return [(int(m["id"]), float(m.get("score", 0.0))) for m in matches]
        except (ValueError, KeyError, TypeError) as exc:
            raise VectorBackendResponseError(f"Malformed n8n webhook payload: {exc}") from exc