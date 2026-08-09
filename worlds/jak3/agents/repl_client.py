"""Small asynchronous client for OpenGOAL's nREPL completion barrier."""

import asyncio
from contextlib import suppress
import hashlib
import logging
import re
import struct


logger = logging.getLogger("Client")


def _form_summary(form: str) -> str:
    match = re.match(r"\s*\(([^\s()]+)", form)
    operation = match.group(1) if match else "unknown"
    digest = hashlib.sha256(form.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"operation={operation} bytes={len(form.encode('utf-8'))} sha256={digest}"


class OpenGoalRepl:
    def __init__(self, host: str = "127.0.0.1", port: int = 8181) -> None:
        self.host = host
        self.port = port
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self.writer is not None and not self.writer.is_closing()

    async def connect(self) -> None:
        if self.connected:
            logger.debug(
                "nREPL connection already open at %s:%d.", self.host, self.port
            )
            return
        logger.debug(
            "Opening OpenGOAL nREPL connection to %s:%d.", self.host, self.port
        )
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        try:
            welcome_data = await asyncio.wait_for(self.reader.read(1024), timeout=10.0)
        except asyncio.TimeoutError as exc:
            await self.close()
            raise ConnectionError(
                "Timed out waiting for the OpenGOAL nREPL greeting"
            ) from exc
        if not welcome_data:
            await self.close()
            raise ConnectionError("OpenGOAL nREPL closed before sending its greeting")
        welcome = welcome_data.decode(errors="replace")
        if "nREPL" not in welcome:
            await self.close()
            raise ConnectionError(f"Unexpected OpenGOAL nREPL greeting: {welcome!r}")
        logger.info("Connected to the Jak 3 OpenGOAL nREPL socket.")
        logger.debug(
            "nREPL greeting bytes=%d text=%r.", len(welcome_data), welcome[:500]
        )

    async def attach(self) -> None:
        response = await self.send_form("(lt)", timeout=30.0)
        if "nREPL" not in response:
            raise ConnectionError(
                "OpenGOAL did not attach to the game. Start Jak 3 in debug mode: "
                + response.strip()
            )
        logger.info("OpenGOAL attached to the Jak 3 game target.")

    async def send_form(self, form: str, timeout: float = 10.0) -> str:
        if not self.connected or self.reader is None or self.writer is None:
            raise ConnectionError("OpenGOAL nREPL is not connected")
        encoded = form.encode("utf-8")
        eval_packet = struct.pack("<II", len(encoded), 10) + encoded
        ping_packet = struct.pack("<II", 0, 0)
        async with self.lock:
            started = asyncio.get_running_loop().time()
            summary = _form_summary(form)
            logger.debug("nREPL SEND timeout=%gs %s", timeout, summary)
            # OpenGOAL processes requests serially. The PING greeting therefore
            # acts as a completion barrier for the preceding evaluation.
            try:
                self.writer.write(eval_packet + ping_packet)
                await self.writer.drain()
                response = await asyncio.wait_for(
                    self.reader.read(4096), timeout=timeout
                )
            except asyncio.TimeoutError as exc:
                raise ConnectionError(
                    f"OpenGOAL did not acknowledge this command within {timeout:g} seconds ({summary})"
                ) from exc
            except (ConnectionError, OSError) as exc:
                raise ConnectionError(
                    f"OpenGOAL communication failed while sending {summary}: {exc}"
                ) from exc
            if not response:
                raise ConnectionError(
                    f"OpenGOAL closed the nREPL connection while sending {summary}"
                )
            decoded = response.decode(errors="replace")
            if "nREPL" not in decoded:
                raise ConnectionError(
                    f"Unexpected OpenGOAL completion-barrier response for {summary}"
                )
            logger.debug(
                "nREPL ACK elapsed=%.3fs bytes=%d %s",
                asyncio.get_running_loop().time() - started,
                len(response),
                summary,
            )
            return decoded

    async def send_form_unacknowledged(self, form: str, timeout: float = 0.25) -> None:
        """Queue a bounded diagnostic form without adding a response barrier."""

        if not self.connected or self.writer is None:
            raise ConnectionError("OpenGOAL nREPL is not connected")
        encoded = form.encode("utf-8")
        eval_packet = struct.pack("<II", len(encoded), 10) + encoded
        async with self.lock:
            summary = _form_summary(form)
            logger.debug("nREPL SEND-NO-BARRIER timeout=%gs %s", timeout, summary)
            try:
                self.writer.write(eval_packet)
                await asyncio.wait_for(self.writer.drain(), timeout=timeout)
            except asyncio.TimeoutError as exc:
                raise ConnectionError(
                    "OpenGOAL did not accept a diagnostic acknowledgement within "
                    f"{timeout:g} seconds ({summary})"
                ) from exc
            except (ConnectionError, OSError) as exc:
                raise ConnectionError(
                    f"OpenGOAL communication failed while queueing {summary}: {exc}"
                ) from exc

    async def close(self) -> None:
        if self.writer:
            logger.debug("Closing OpenGOAL nREPL connection.")
            self.writer.close()
            # A compiler/game crash can reset the Windows socket while
            # wait_closed is draining it. Cleanup must not mask the original
            # startup failure or terminate the client's retry task.
            with suppress(ConnectionError, OSError):
                await self.writer.wait_closed()
        self.reader = None
        self.writer = None
