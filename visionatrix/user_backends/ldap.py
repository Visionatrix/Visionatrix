import asyncio
import base64
import contextlib
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from starlette.requests import HTTPConnection
from starlette.types import Scope

from .. import database
from ..etc import get_offset_naive_time
from ..pydantic_models import UserInfo

LOGGER = logging.getLogger("visionatrix")

# for testing with LDAP container with data like in Nextcloud (https://github.com/juliusknorr/nextcloud-docker-dev)
# it should be run with these params
# LDAP_DOMAIN: planetexpress.com
# LDAP_BASE_DN: dc=planetexpress,dc=com
# LDAP_ADMIN_PASSWORD: "adminpass"
#
# and set these environment variables for Visionatrix:
# VIX_AUTH=1
# LDAP_ADMIN_GROUP_DNS=cn=admin_staff,ou=groups,dc=planetexpress,dc=com
# LDAP_BIND_DN=cn=admin,dc=planetexpress,dc=com
# LDAP_BIND_PASSWORD=adminpass
#
#
# note: to test direct binding you create file named "99-access.ldif" with such content:
#
# dn: olcDatabase={1}mdb,cn=config
# changetype: modify
# add: olcAccess
# olcAccess: {2}to dn.subtree="ou=groups,dc=planetexpress,dc=com"
#   by users read
#   by dn.exact="cn=admin,dc=planetexpress,dc=com" write
#   by * none
# -
# add: olcAccess
# olcAccess: {3}to dn.subtree="ou=people,dc=planetexpress,dc=com"
#   by self read
#   by users read
#   by * none

LDAP_CACHE_TTL_SEC = int(os.getenv("LDAP_CACHE_TTL_SEC", "3600"))  # by default 1h.
LDAP_SERVER_URI = os.getenv("LDAP_SERVER_URI", "ldap://localhost:389")
LDAP_USER_DN_TEMPLATE = os.getenv("LDAP_USER_DN_TEMPLATE", "cn={username},ou=people,dc=planetexpress,dc=com")
LDAP_BASE_DN = os.getenv("LDAP_BASE_DN", "ou=people,dc=planetexpress,dc=com")

LDAP_GROUP_BASE_DN = os.getenv(
    "LDAP_GROUP_BASE_DN",
    f"ou=groups,{','.join(LDAP_BASE_DN.split(',', 1)[1:])}",
)
"""default ou=groups,<everything after first comma of LDAP_BASE_DN>"""

LDAP_SEARCH_FILTER = os.getenv("LDAP_SEARCH_FILTER", "(cn={username})")
LDAP_BIND_DN = os.getenv("LDAP_BIND_DN")
LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD")
LDAP_AD_DOMAIN = os.getenv("LDAP_AD_DOMAIN")
LDAP_ADMIN_GROUP_DNS = os.getenv("LDAP_ADMIN_GROUP_DNS", "").lower()
"""Group DNs considered admin, e.g. `cn=admin_staff,ou=groups,dc=planetexpress,dc=com`"""

LDAP_GROUP_RECURSION_LIMIT = int(os.getenv("LDAP_GROUP_RECURSION_LIMIT", "5"))


async def get_user_info_http(_scope: Scope, conn: HTTPConnection) -> UserInfo | None:
    auth_header = conn.headers.get("Authorization")
    return await _parse_and_verify(auth_header) if auth_header else None


async def get_user_info_ws(_scope: Scope, headers: dict[str, str], _cookies: dict[str, str]) -> UserInfo | None:
    auth_header = headers.get("authorization")
    return await _parse_and_verify(auth_header) if auth_header else None


async def _parse_and_verify(authorization: str) -> UserInfo | None:
    try:
        scheme, encoded = authorization.split()
        if scheme.lower() != "basic":
            return None
        decoded = base64.b64decode(encoded).decode("ascii")
        username, _, password = decoded.partition(":")
        ldap_attrs = await _ldap_authenticate(username, password)
        if ldap_attrs is None:
            return None
        full_name, email, is_admin = ldap_attrs
        user_obj = await _ensure_user_in_db(username, full_name, email, password, is_admin)
        return UserInfo.model_validate(user_obj) if user_obj else None
    except (ValueError, UnicodeDecodeError):
        return None


async def _ldap_authenticate(username: str, password: str) -> tuple[str, str, bool] | None:
    """Return (full_name, email, is_admin) on success or None on failure."""

    from ldap3 import ALL, NTLM, Connection, Server

    def _sync() -> tuple[str, str, bool] | None:
        server = Server(LDAP_SERVER_URI, get_info=ALL)

        try:
            if LDAP_BIND_DN and LDAP_BIND_PASSWORD:
                # service account is configured, use it for the initial search
                with Connection(
                    server, user=LDAP_BIND_DN, password=LDAP_BIND_PASSWORD, auto_bind=True
                ) as ldap_connection:
                    entry = _find_user_entry(ldap_connection, username)
                    if not entry:
                        LOGGER.warning("LDAP authentication failed, can not perform search for '%s'.", username)
                        return None
                    user_dn, full_name, email = entry

                    # verify the password: second bind as *the user*
                    with Connection(server, user=user_dn, password=password, auto_bind=True):
                        pass  # if bind succeeded then password is correct

                    is_admin = _is_user_admin(ldap_connection, user_dn)
                    return full_name, email, is_admin

            # direct bind as the user (simple bind or NTLM)
            auth_mech = NTLM if LDAP_AD_DOMAIN else None
            user_principal = (
                f"{LDAP_AD_DOMAIN}\\{username}" if LDAP_AD_DOMAIN else LDAP_USER_DN_TEMPLATE.format(username=username)
            )
            with Connection(
                server, user=user_principal, password=password, authentication=auth_mech, auto_bind=True
            ) as ldap_connection:
                entry = _find_user_entry(ldap_connection, username)
                if not entry:
                    LOGGER.warning("LDAP authentication failed, can not perform search for '%s'.", username)
                    return None
                user_dn, full_name, email = entry
                is_admin = _is_user_admin(ldap_connection, user_dn)
                return full_name, email, is_admin

        except Exception as exc:
            LOGGER.warning("LDAP authentication failed for '%s': %s", username, exc)
            return None

    return await asyncio.to_thread(_sync)


def _find_user_entry(ldap_connection, username: str) -> tuple[str, str, str] | None:
    """Return (dn, full_name, email)."""
    from ldap3 import SUBTREE

    ldap_connection.search(
        LDAP_BASE_DN,
        LDAP_SEARCH_FILTER.format(username=username),
        SUBTREE,
        attributes=["cn", "mail", "distinguishedName"],
    )
    if not ldap_connection.entries:
        return None
    entry = ldap_connection.entries[0]
    dn = entry.entry_dn
    full_name = str(entry.cn or username)
    email = str(entry.mail or "")
    return dn, full_name, email


def _is_user_admin(ldap_connection, user_dn: str) -> bool:
    """Recursively walk groupOfNames/groupOfUniqueNames membership to see if user ends up in LDAP_ADMIN_GROUP_DNS."""

    if not LDAP_ADMIN_GROUP_DNS:
        return False  # no admin groups configured

    visited: set[str] = set()
    queue: list[str] = [user_dn]
    depth = 0

    while queue and depth < LDAP_GROUP_RECURSION_LIMIT:
        depth += 1
        # search for groups whose *member* attribute contains any DN in `queue`
        filter_or = "".join(f"(member={dn})" for dn in queue)
        search_filter = f"(|{filter_or})"
        queue = []

        ldap_connection.search(
            LDAP_GROUP_BASE_DN,
            search_filter,
            search_scope="SUBTREE",
            attributes=["member"],
        )

        for grp in ldap_connection.entries:
            grp_dn = grp.entry_dn.lower()
            if grp_dn in visited:
                continue
            visited.add(grp_dn)

            if grp_dn == LDAP_ADMIN_GROUP_DNS:
                return True
            queue.append(grp_dn)  # enqueue this group itself; someone could be a member of *another* group
    return False


async def _ensure_user_in_db(username: str, full_name: str, email: str, password: str, is_admin: bool):
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=LDAP_CACHE_TTL_SEC)
    with contextlib.suppress(Exception):
        await database.create_user(
            username=username,
            full_name=full_name,
            email=email,
            password=password,
            is_admin=is_admin,
            disabled=False,
            record_expires_at=expires_at,
        )
    async with database.SESSION() as session:
        result = await session.execute(select(database.UserInfo).filter_by(user_id=username))
        user = result.scalar_one_or_none()

        if user is None:
            LOGGER.warning("User '%s' not found after creation.", username)
            return None

        record_expires_at = get_offset_naive_time(user.record_expires_at)
        if (
            record_expires_at is None
            or record_expires_at < datetime.now(timezone.utc)
            or user.full_name != full_name
            or user.email != email
            or user.is_admin != is_admin
        ):
            user.full_name = full_name
            user.email = email
            user.is_admin = is_admin
            user.record_expires_at = expires_at
            await session.commit()
    return user
