from hashlib import sha1
from logging import getLogger
from urllib.parse import urlencode
from uuid import UUID

from defusedxml.ElementTree import fromstring
from requests.api import get as http_get
from requests.utils import dict_from_cookiejar

# from .settings import MAX_URL_LENGTH, REQUEST_TIMEOUT

logger = getLogger("apps.bbb")

REQUEST_TIMEOUT = 15
MAX_URL_LENGTH = 2000


class MaximumURLLengthExceededError(RuntimeError):
    pass


class RequestFailedError(RuntimeError):
    pass


class SuspiciousXMLResponseError(RuntimeError):
    pass


class BBBAPIResponse(object):
    def __init__(self, url):
        logger.debug("[bbb] Start request on %s" % url)
        self.response = http_get(url, timeout=REQUEST_TIMEOUT)
        logger.debug("[bbb] Got response: %s" % self.response.status_code)
        self.response.raise_for_status()

    def get_cookies(self):
        return dict_from_cookiejar(self.response.cookies)

    def parse(self):
        content = self.response.content.decode("utf-8")
        logger.debug("[bbb] Response content:")
        logger.debug(content)

        xml = fromstring(content)

        try:
            if xml.find("returncode").text == "SUCCESS":
                return xml

            try:
                raise RequestFailedError(
                    "The server did not return SUCCESS: %s" % xml.find("message").text
                )
            except AttributeError:
                raise RequestFailedError(
                    "The server did not return SUCCESS for some unknown reason."
                )

        except AttributeError:
            raise RequestFailedError(
                "No return code supplied; damn, that response is all f*** up."
            )


def _to_bbb_api_value(value):
    if isinstance(value, str):
        pass
    elif isinstance(value, bool):
        # Booleans are instances of ints, so they should be handled before them
        value = "true" if value else "false"
    elif isinstance(value, int):
        assert not value < 0, "Only non-negative integers are supported."
        value = str(value)
    elif isinstance(value, UUID):
        value = value.hex
    else:
        raise ValueError(
            "Incompatible value %s. Compatible values are strings, non-negative integers and booleans."
            % type(value)
        )

    return value.encode("utf-8")


def get_call_url(call, instance, **kwargs):
    if instance is None:
        raise Exception
    args = tuple((key, _to_bbb_api_value(val)) for key, val in kwargs.items())
    query = urlencode(args)
    prepared = "{call}{query}{secret}".format(
        call=call, query=query, secret=instance.secret
    )
    checksum = sha1(str(prepared).encode("utf-8")).hexdigest()
    url = "{api}{call}?{query}".format(
        api=instance.api_url,
        call=call,
        query=urlencode(args + (("checksum", checksum),)),
    )

    if not len(url) > MAX_URL_LENGTH:
        return url
    else:
        raise MaximumURLLengthExceededError


def execute_api_call(call, instance, **kwargs):
    return BBBAPIResponse(get_call_url(call, instance, **kwargs))
