import os
import json
import hmac
import hashlib
import logging

import boto3

from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.resource("s3")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
GITHUB_SECRET = os.getenv("GITHUB_SECRET")


def s3_key_name(event: dict) -> str:
    r""" Returns an S3 key name to save file to

    >>> s3_key_name({}) is None
    True

    >>> s3_key_name({"headers":{}}) is None
    True

    >>> test_dict = {
    ...     "pathParameters": {"orgname": "11"},
    ...     "headers": {
    ...         "X-GitHub-Event": "22",
    ...         "X-GitHub-Delivery": "33",
    ...     }
    ... }
    >>> s3_key_name(test_dict) == '11/{0:%Y}/{0:%m}/{0:%d}/22/33'.format(
    ...     datetime.utcnow()
    ... )
    True
    """

    if event and "headers" in event:
        headers = event["headers"]
        now = datetime.utcnow()
        try:
            return "{org}/{now:%Y}/{now:%m}/{now:%d}/{event_type}/{event_id}".format(
                org=event["pathParameters"]["orgname"],
                now=now,
                event_type=headers["X-GitHub-Event"],
                event_id=headers["X-GitHub-Delivery"],
            )
        except KeyError as e:
            logger.warning(f"KeyError: {e}")

    return None


def validate_signature(github_secret: str, body: bytes, headers: dict) -> bool:
    r"""
    Validates whether the incoming HTTP request has the right headers and the
    "X-Hub-Signature-256" or "X-Hub-Signature" signature is a match.

    >>> validate_signature("123", "", {})
    False

    >>> validate_signature("123", b"123", {})
    False

    >>> validate_signature(None, None, {"X-Hub-Signature": "123"})
    False

    >>> validate_signature("123", b"123", {
    ...     "X-Hub-Signature": "sha1=a3c024f01cccb3b63457d848b0d2f89c1f744a3d"
    ... })
    True

    >>> validate_signature("123", b"123", {
    ...     "X-Hub-Signature": "sha1=badhash01cccb3b63457d848b0d2f89c1f744a3d"
    ... })
    False

    >>> validate_signature("123", b"123", {
    ...     "X-Hub-Signature-256": "sha256=3cafe40f92be6ac77d2792b4b267c2da11e3f3087b93bb19c6c5133786984b44"
    ... })
    True

    >>> validate_signature("123", b"123", {
    ...     "X-Hub-Signature-256": "sha256=badhashf92be6ac77d2792b4b267c2da11e3f3087b93bb19c6c5133786984b44"
    ... })
    False

    >>> validate_signature('{"abc":"123"}', b"123", {
    ...     "X-Hub-Signature-256": "sha256=3cafe40f92be6ac77d2792b4b267c2da11e3f3087b93bb19c6c5133786984b44",
    ...     "X-GitHub-Hook-Installation-Target-ID": "abc"
    ... })
    True

    >>> validate_signature('{"abc":"123", "def":"456"}', b"123", {
    ...     "X-Hub-Signature-256": "sha256=3cafe40f92be6ac77d2792b4b267c2da11e3f3087b93bb19c6c5133786984b44",
    ...     "X-GitHub-Hook-Installation-Target-ID": "def"
    ... })
    False

    >>> validate_signature('{"abc":"123", "def":"456"}', b"123", {
    ...     "X-Hub-Signature-256": "sha256=3cafe40f92be6ac77d2792b4b267c2da11e3f3087b93bb19c6c5133786984b44",
    ...     "X-GitHub-Hook-Installation-Target-ID": "ghi"
    ... })
    False
    """

    res = False

    if not body or not headers or not github_secret:
        return res

    signature = None

    _gs = None
    if "{" in github_secret and "X-GitHub-Hook-Installation-Target-ID" in headers:

        json_ghsec = json.loads(github_secret)
        gh_targ_id = headers["X-GitHub-Hook-Installation-Target-ID"]

        if gh_targ_id in json_ghsec:
            _gs = json_ghsec[gh_targ_id].encode("utf8")
            logger.info(f"Got key from {gh_targ_id}")
        else:
            logger.warning(f"Couldn't find key for {gh_targ_id}")

    else:
        _gs = github_secret.encode("utf8")

    if _gs and "X-Hub-Signature-256" in headers:
        signature = headers["X-Hub-Signature-256"]
        try:
            github_hmac = hmac.new(_gs, msg=body, digestmod=hashlib.sha256)
            hex_digest = "sha256={}".format(github_hmac.hexdigest())
            res = len(hex_digest) == len(signature) and hmac.compare_digest(
                hex_digest, signature
            )
            logger.info("Used sha256 successfully")
        except Exception as e:
            logger.error(e)

    if signature is None and "X-Hub-Signature" in headers:
        signature = headers["X-Hub-Signature"]

        github_hmac = hmac.new(_gs, msg=body, digestmod=hashlib.sha1)
        hex_digest = "sha1={}".format(github_hmac.hexdigest())

        res = len(hex_digest) == len(signature) and hmac.compare_digest(
            hex_digest, signature
        )
        logger.info("Used sha1 successfully")

    return res


def lambda_handler(event, context):
    body = event["body"]

    headers = event["headers"]

    try:
        print(json.dumps(headers))
    except Exception as e:
        logger.error(e)

    if validate_signature(GITHUB_SECRET, body.encode("utf8"), headers):
        logger.info("Successfully validated MAC")

        try:
            bodyObj = json.loads(body)
            bodyObj["timestamp"] = int(datetime.now().timestamp())

            # remove excessive urls
            for main in ["repository", "organization", "sender"]:
                keys_to_remove = []
                if main in bodyObj:
                    for key in bodyObj[main]:
                        if key.endswith("_url"):
                            keys_to_remove.append(key)
                for key in keys_to_remove:
                    bodyObj[main].pop(key)

            bodyStr = json.dumps(bodyObj)
        except:
            logger.error("JSON body parsing failure.")
        finally:
            logger.info("Successfully updated the JSON.")
            body = bodyStr

        s3.Object(BUCKET_NAME, s3_key_name(event)).put(Body=body)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "OK"}),
        }
    else:
        logger.warning("Missing signature headers or invalid signature MAC")

    return {
        "statusCode": 403,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "Forbidden"}),
    }


if __name__ == "__main__":
    """ Run doctest """
    import doctest

    doctest.testmod()
