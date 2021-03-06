"""
Calculate digital signatures for messages sent to/from credit providers,
using a shared secret key.

The signature is calculated as follows:

    1) Encode all parameters of the request (except the signature) in a string.
    2) Encode each key/value pair as a string of the form "{key}:{value}".
    3) Concatenate key/value pairs in ascending alphabetical order by key.
    4) Calculate the HMAC-SHA256 digest of the encoded request parameters, using a 32-character shared secret key.
    5) Encode the digest in hexadecimal.

It is the responsibility of the credit provider to check the signature of messages
we send them, and it is our responsibility to check the signature of messages
we receive from the credit provider.

"""

import hashlib
import hmac

from django.conf import settings


def get_shared_secret_key(provider_id):
    """
    Retrieve the shared secret key for a particular credit provider.
    """
    return getattr(settings, "CREDIT_PROVIDER_SECRET_KEYS", {}).get(provider_id)


def signature(params, shared_secret):
    """
    Calculate the digital signature for parameters using a shared secret.

    Arguments:
        params (dict): Parameters to sign.  Ignores the "signature" key if present.

    Returns:
        str: The 32-character signature.

    """
    encoded_params = "".join([
        "{key}:{value}".format(key=key, value=params[key])
        for key in sorted(params.keys())
        if key != "signature"
    ])
    hasher = hmac.new(shared_secret, encoded_params, hashlib.sha256)
    return hasher.hexdigest()
