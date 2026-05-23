from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from src.shared.http_retry import async_fetch_with_retry


def _make_response(status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code=status_code, request=httpx.Request("GET", "http://test"))


def _make_status_error(status_code: int) -> httpx.HTTPStatusError:
    response = _make_response(status_code)
    return httpx.HTTPStatusError(
        message=f"{status_code}",
        request=response.request,
        response=response,
    )


class TestSuccessfulRequestNoRetry:
    @pytest.mark.asyncio
    async def test_returns_response_immediately(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(return_value=_make_response(200))

        result = await async_fetch_with_retry(client, "GET", "/test")

        assert result.status_code == 200
        assert client.request.call_count == 1


class TestRetryOnNetworkError:
    @pytest.mark.asyncio
    async def test_retries_on_request_error_then_succeeds(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(
            side_effect=[
                httpx.RequestError(
                    "connection failed", request=httpx.Request("GET", "http://test")
                ),
                _make_response(200),
            ]
        )

        with patch("src.shared.http_retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await async_fetch_with_retry(client, "GET", "/test")

        assert result.status_code == 200
        assert client.request.call_count == 2
        mock_sleep.assert_called_once()


class TestRetryOn503ThenSuccess:
    @pytest.mark.asyncio
    async def test_retries_on_503_then_succeeds(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(
            side_effect=[
                _make_response(503),
                _make_response(200),
            ]
        )

        call_count = 0

        async def mock_request(*args: object, **kwargs: object) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                resp = _make_response(503)
                resp.raise_for_status = lambda: (_ for _ in ()).throw(_make_status_error(503))  # type: ignore[method-assign]
                return resp
            return _make_response(200)

        client.request = AsyncMock(side_effect=mock_request)

        with patch("src.shared.http_retry.asyncio.sleep", new_callable=AsyncMock):
            result = await async_fetch_with_retry(client, "GET", "/test")

        assert result.status_code == 200


class TestNoRetryOn4xx:
    @pytest.mark.asyncio
    async def test_raises_immediately_on_400(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)

        async def mock_request(*args: object, **kwargs: object) -> httpx.Response:
            resp = _make_response(400)
            resp.raise_for_status = lambda: (_ for _ in ()).throw(_make_status_error(400))  # type: ignore[method-assign]
            return resp

        client.request = AsyncMock(side_effect=mock_request)

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await async_fetch_with_retry(client, "GET", "/test")

        assert exc_info.value.response.status_code == 400
        assert client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_raises_immediately_on_404(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)

        async def mock_request(*args: object, **kwargs: object) -> httpx.Response:
            resp = _make_response(404)
            resp.raise_for_status = lambda: (_ for _ in ()).throw(_make_status_error(404))  # type: ignore[method-assign]
            return resp

        client.request = AsyncMock(side_effect=mock_request)

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await async_fetch_with_retry(client, "GET", "/test")

        assert exc_info.value.response.status_code == 404


class TestRetryOn429:
    @pytest.mark.asyncio
    async def test_retries_on_rate_limit_then_succeeds(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        call_count = 0

        async def mock_request(*args: object, **kwargs: object) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                resp = _make_response(429)
                resp.raise_for_status = lambda: (_ for _ in ()).throw(_make_status_error(429))  # type: ignore[method-assign]
                return resp
            return _make_response(200)

        client.request = AsyncMock(side_effect=mock_request)

        with patch("src.shared.http_retry.asyncio.sleep", new_callable=AsyncMock):
            result = await async_fetch_with_retry(client, "GET", "/test")

        assert result.status_code == 200
        assert client.request.call_count == 2


class TestAllRetriesExhausted:
    @pytest.mark.asyncio
    async def test_raises_last_exception_after_exhausting_retries(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)

        async def mock_request(*args: object, **kwargs: object) -> httpx.Response:
            resp = _make_response(503)
            resp.raise_for_status = lambda: (_ for _ in ()).throw(_make_status_error(503))  # type: ignore[method-assign]
            return resp

        client.request = AsyncMock(side_effect=mock_request)

        with (
            patch("src.shared.http_retry.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(httpx.HTTPStatusError) as exc_info,
        ):
            await async_fetch_with_retry(client, "GET", "/test", max_retries=2)

        assert exc_info.value.response.status_code == 503
        assert client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_raises_last_request_error_after_exhausting_retries(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        network_error = httpx.RequestError("timeout", request=httpx.Request("GET", "http://test"))
        client.request = AsyncMock(side_effect=network_error)

        with (
            patch("src.shared.http_retry.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(httpx.RequestError),
        ):
            await async_fetch_with_retry(client, "GET", "/test", max_retries=2)

        assert client.request.call_count == 3


class TestUsesSettingsDefaults:
    @pytest.mark.asyncio
    async def test_uses_settings_when_no_override(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        network_error = httpx.RequestError("fail", request=httpx.Request("GET", "http://test"))
        client.request = AsyncMock(side_effect=network_error)

        with (
            patch("src.shared.http_retry.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(httpx.RequestError),
        ):
            await async_fetch_with_retry(client, "GET", "/test")

        # Default max_retries is 3, so 4 total attempts
        assert client.request.call_count == 4


class TestRetryOn502And504:
    @pytest.mark.asyncio
    async def test_retries_on_502(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        call_count = 0

        async def mock_request(*args: object, **kwargs: object) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                resp = _make_response(502)
                resp.raise_for_status = lambda: (_ for _ in ()).throw(_make_status_error(502))  # type: ignore[method-assign]
                return resp
            return _make_response(200)

        client.request = AsyncMock(side_effect=mock_request)

        with patch("src.shared.http_retry.asyncio.sleep", new_callable=AsyncMock):
            result = await async_fetch_with_retry(client, "GET", "/test")

        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_retries_on_504(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        call_count = 0

        async def mock_request(*args: object, **kwargs: object) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                resp = _make_response(504)
                resp.raise_for_status = lambda: (_ for _ in ()).throw(_make_status_error(504))  # type: ignore[method-assign]
                return resp
            return _make_response(200)

        client.request = AsyncMock(side_effect=mock_request)

        with patch("src.shared.http_retry.asyncio.sleep", new_callable=AsyncMock):
            result = await async_fetch_with_retry(client, "GET", "/test")

        assert result.status_code == 200
