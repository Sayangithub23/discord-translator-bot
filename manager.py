"""
manager.py — Provider health tracker, quota manager, and rotation logic.
"""

import time
import logging
import threading
from dataclasses import dataclass
from typing import Optional, Protocol, Any
from enum import Enum

from providers import TranslationError, QuotaExceededError

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    UP = "up"
    DOWN = "down"
    QUOTA_EXCEEDED = "quota_exceeded"


# ── Protocol so Pylance knows what a provider looks like ─────────────────────
class TranslationProvider(Protocol):
    NAME: str
    def translate(self, text: str, source_lang: str, target_lang: str) -> str: ...


@dataclass
class ProviderState:
    provider: TranslationProvider            # typed properly now
    status: ProviderStatus = ProviderStatus.UP
    quota_used: int = 0
    quota_limit: int = 0                     # 0 = unlimited
    avg_latency_ms: float = 0.0
    total_requests: int = 0
    total_failures: int = 0
    last_failure_time: float = 0.0
    recovery_after_seconds: int = 300
    consecutive_failures: int = 0
    failure_threshold: int = 3

    @property
    def name(self) -> str:
        return self.provider.NAME

    @property
    def quota_remaining(self) -> float:      # float to allow inf
        if self.quota_limit == 0:
            return float("inf")
        return max(0, self.quota_limit - self.quota_used)

    @property
    def is_available(self) -> bool:
        if self.status == ProviderStatus.QUOTA_EXCEEDED:
            return False
        if self.status == ProviderStatus.DOWN:
            if time.time() - self.last_failure_time > self.recovery_after_seconds:
                logger.info(f"[{self.name}] Recovery window passed — marking UP for retry")
                self.status = ProviderStatus.UP
                self.consecutive_failures = 0
                return True
            return False
        return True

    def record_success(self, latency_ms: float) -> None:
        self.total_requests += 1
        self.consecutive_failures = 0
        self.status = ProviderStatus.UP
        if self.avg_latency_ms == 0:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = 0.8 * self.avg_latency_ms + 0.2 * latency_ms

    def record_failure(self, is_quota: bool = False) -> None:
        self.total_requests += 1
        self.total_failures += 1
        self.last_failure_time = time.time()

        if is_quota:
            self.status = ProviderStatus.QUOTA_EXCEEDED
            logger.warning(f"[{self.name}] Quota exceeded — removing from rotation")
        else:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.failure_threshold:
                self.status = ProviderStatus.DOWN
                logger.warning(
                    f"[{self.name}] {self.consecutive_failures} consecutive failures — marking DOWN"
                )

    def record_chars(self, char_count: int) -> None:
        self.quota_used += char_count


class TranslationManager:
    def __init__(self, providers: list[tuple[TranslationProvider, int]], mode: str = "quota_aware"):
        self.states: list[ProviderState] = []
        self._lock = threading.Lock()
        self.mode = mode
        self._round_robin_index = 0

        for provider, quota_limit in providers:
            state = ProviderState(provider=provider, quota_limit=quota_limit)
            self.states.append(state)
            logger.info(
                f"Registered provider [{provider.NAME}] | "
                f"quota={'unlimited' if quota_limit == 0 else quota_limit}"
            )

    def _select_provider(self) -> Optional[ProviderState]:
        available = [s for s in self.states if s.is_available]
        if not available:
            return None

        if self.mode == "round_robin":
            idx = self._round_robin_index % len(available)
            self._round_robin_index += 1
            return available[idx]

        elif self.mode == "fastest":
            untested = [s for s in available if s.avg_latency_ms == 0]
            if untested:
                return untested[0]
            return min(available, key=lambda s: s.avg_latency_ms)

        else:  # quota_aware
            with_quota = [s for s in available if s.quota_remaining > 0]
            if not with_quota:
                with_quota = available

            untested = [s for s in with_quota if s.avg_latency_ms == 0]
            if untested:
                return untested[0]
            return min(with_quota, key=lambda s: s.avg_latency_ms)

    def translate(self, text: str, source_lang: str, target_lang: str) -> tuple[str, str]:
        tried: list[ProviderState] = []

        with self._lock:
            for attempt in range(len(self.states)):
                state = self._select_provider()

                if state is None or state in tried:
                    break
                tried.append(state)

                logger.debug(f"Trying [{state.name}] (attempt {attempt + 1})")
                start = time.time()

                try:
                    result = state.provider.translate(text, source_lang, target_lang)
                    latency = (time.time() - start) * 1000
                    state.record_success(latency)
                    state.record_chars(len(text))
                    logger.info(f"✅ [{state.name}] {len(text)} chars in {latency:.0f}ms")
                    return result, state.name

                except QuotaExceededError as e:
                    logger.warning(f"⚠️  [{state.name}] quota exceeded: {e}")
                    state.record_failure(is_quota=True)

                except TranslationError as e:
                    logger.warning(f"❌ [{state.name}] failed: {e}")
                    state.record_failure()

                except Exception as e:
                    logger.warning(f"❌ [{state.name}] unexpected error: {e}")
                    state.record_failure()

        raise TranslationError(
            f"All providers failed. Tried: {[s.name for s in tried]}"
        )

    def reset_monthly_quotas(self) -> None:
        with self._lock:
            for state in self.states:
                if state.status == ProviderStatus.QUOTA_EXCEEDED:
                    state.status = ProviderStatus.UP
                state.quota_used = 0
                state.consecutive_failures = 0
            logger.info("Monthly quotas reset for all providers")

    def status_report(self) -> list[dict[str, Any]]:
        report = []
        for s in self.states:
            report.append({
                "name": s.name,
                "status": s.status.value,
                "quota_used": s.quota_used,
                "quota_limit": s.quota_limit if s.quota_limit > 0 else "unlimited",
                "quota_remaining": s.quota_remaining if s.quota_limit > 0 else "unlimited",
                "avg_latency_ms": round(s.avg_latency_ms, 1),
                "total_requests": s.total_requests,
                "total_failures": s.total_failures,
                "success_rate": (
                    f"{((s.total_requests - s.total_failures) / s.total_requests * 100):.1f}%"
                    if s.total_requests > 0 else "n/a"
                ),
            })
        return report