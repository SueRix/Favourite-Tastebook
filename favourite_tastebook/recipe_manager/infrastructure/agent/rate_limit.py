import time

from django.conf import settings
from django.core.cache import cache

from recipe_manager.domain.exceptions import AgentChatRateLimitedError

KEY_PREFIX = "agent-chat"
DAY_SECONDS = 24 * 60 * 60


class AgentChatRateLimiter:
    """
    What: Counts a user's chat messages per minute and per day.
    Where: Called by AgentChatUseCase before anything is sent to n8n.
    Why: This is the only hard limit on what the chat can cost. The system
         prompt bounds the topic and can be talked around; a counter cannot.
         It also protects the model quota itself — one answer is three or four
         calls to the model, so a handful of enthusiastic users would exhaust a
         free tier long before anything looked like abuse.

    Two windows on purpose: the per-minute one stops a burst, the per-day one
    stops a slow drip that would never trip it.
    """

    @staticmethod
    def _bucket_keys(user_id) -> tuple:
        now = int(time.time())
        return (
            f"{KEY_PREFIX}:{user_id}:m:{now // 60}",
            f"{KEY_PREFIX}:{user_id}:d:{now // DAY_SECONDS}",
            60 - (now % 60),
        )

    @classmethod
    def check(cls, user_id) -> None:
        """Registers one message, or raises AgentChatRateLimitedError."""
        minute_key, day_key, seconds_left = cls._bucket_keys(user_id)

        # Fixed windows rather than a rolling log: a rolling window would need a
        # timestamp list per user, and the extra precision buys nothing here.
        minute_count = cls._hit(minute_key, 60)
        if minute_count > settings.AGENT_CHAT_RATE_PER_MINUTE:
            raise AgentChatRateLimitedError(retry_after=seconds_left)

        day_count = cls._hit(day_key, DAY_SECONDS)
        if day_count > settings.AGENT_CHAT_RATE_PER_DAY:
            raise AgentChatRateLimitedError(
                retry_after=DAY_SECONDS - (int(time.time()) % DAY_SECONDS),
                message="You have reached today's limit of assistant messages.",
            )

    @staticmethod
    def _hit(key: str, ttl: int) -> int:
        # add() only writes when the key is absent, so it starts the window
        # exactly once; incr() then never resets the expiry, which is what keeps
        # the window fixed instead of sliding forward with every message.
        cache.add(key, 0, ttl)
        try:
            return cache.incr(key)
        except ValueError:
            # The key expired between add() and incr() — a new window began.
            cache.set(key, 1, ttl)
            return 1
