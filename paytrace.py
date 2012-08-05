"""
Python 3 client library for the PayTrace Payment Gateway public API.

The PayTrace API is documented in a single PDF file available here:

  https://paytrace.com/manuals/PayTraceAPIUserGuideXML.pdf (dated July, 2011)

Section references in doc strings below refer to this document.

"""

import sys
from datetime import datetime
from textwrap import TextWrapper
from urllib.parse import urlencode, quote_plus

import requests

#__all__ = ['parse_response', 'send_api_request']


POST_URL = 'https://paytrace.com/api/default.pay'


def parse_response(s):
    """
    Parse a PayTrace response string into a dictionary.

    See section 5.1.

    """
    if not s.endswith('|'):
        raise Exception('Unexpected response: %r' % s[:100])

    try:
        api_response_dict = dict(s.split('~') for s in s[:-1].split('|'))
    except:
        raise Exception('Malformed response: %r' % s)

    return api_response_dict


def send_api_request(api_request, post_url=POST_URL):
    """
    Send a PayTrace API request and get a response.

      api_request -- a subclass of PayTraceRequest

    See section 3.2.

    Variable naming gets a little confusing here because both requests
    and PayTrace have a notion of "requests" and "responses". For clarity,
    you'll see

        requests.post     (an HTTP request)
        requests.response (an HTTP response object)
        api_request       (a subclass of PayTraceResponse)
        api_response_dict (a PayTrace response string parsed into a dictionary)

    TEMPORARY:

    Here are the responses.response object's attributes and methods:
        response.config
        response.content --> bytes
        response.cookies
        response.encoding
        response.error
        response.headers
        response.history
        response.iter_content(
        response.iter_lines(
        response.json
        response.ok
        response.raise_for_status(
        response.raw     --> requests.packages.urllib3.response.HTTPResponse
        response.reason
        response.request
        response.status_code
        response.text    --> Unicode
        response.url

    """
    utc_timestamp = '%s+00:00' % datetime.utcnow()
    try:
        response = requests.post(
            post_url,
            data=str(api_request),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=60,
        )
    except KeyboardInterrupt:
        raise
    except:
        exc_class, exc_instance = sys.exc_info()[:2]
        raise Exception(
            'Error sending HTTP POST.',
            {'exc_instance': exc_instance,
             'api_request': repr(api_request),
             'api_request_raw': str(api_request),
             'utc_timestamp': utc_timestamp}
        )

    try:
        api_response_dict = parse_response(response.text)
    except KeyboardInterrupt:
        raise
    except:
        exc_class, exc_instance = sys.exc_info()[:2]
        raise Exception(
            'Error parsing HTTP response.',
            {'exc_instance': exc_instance,
             'api_request': repr(api_request),
             'api_request_raw': str(api_request),
             'api_response': response.text[:100],
             'utc_timestamp': utc_timestamp}
        )

    return api_response_dict


def uppercase_keys(d):
    """Change a dictionary in-place so that all keys are uppercase."""
    for key in d:
        KEY = key.upper()
        if key != KEY:
            d[KEY] = d[key]
            del d[key]


def set_credentials(username, password):
    """
    To use the PayTrace API, you need to supply the user name and password for
    a valid PayTrace account. For example, to use the PayTrace demo account,
    run set_credentials('demo123', 'demo123').

    """
    PayTraceRequest.UN = username
    PayTraceRequest.PSWD = password


def set_test_mode():
    """
    All transaction types (TranxType) of the ProcessTranx method can be
    processed as test transactions by adding a TEST attribute. Transactions
    processed with a TEST value of "Y" will be processed as test transactions
    with standardized test responses. Test transactions will not place a hold
    on the customer's credit card.

    """
    PayTraceRequest._test_mode = True


#
# Metaclass that customizes each class's repr.
#

class MetaRepr(type):
    """
    Provide a customized repr for classes defining their metaclass as this
    class. To use, your class should implement a classmethod called
    __classrepr__ that returns the repr you are after.

    Just as the __repr__ method on a class generates the repr for instances
    of that class, the __repr__ method on the class's type (its metaclass)
    generates the repr for the class itself.

    See http://www.aleax.it/Python/osc05_bla_dp.pdf, "A tiny custom metaclass"
    (p. 21).

    """
    def __repr__(cls):
        if hasattr(cls, '__classrepr__'):
            return cls.__classrepr__()
        else:
            return repr(cls)


#
# Data definition classes
#

class PayTraceRequest(metaclass=MetaRepr):
    """
    PayTrace request abstract base class.

    Provide constant data fields for subclasses and ensure required and
    optional fields are correctly supplied by subclasses.

    """
    UN = None
    PSWD = None
    TERMS = 'Y'

    _required = NotImplemented
    _optional = NotImplemented
    _discretionary_data_allowed = NotImplemented
    _test_mode = False

    def __init__(self, **kwargs):
        """
        Convert kwargs to uppercased instance attributes, assert all required
        fields are supplied, and verify that optional fields are acceptable.

        """
        assert self.UN and self.PSWD, (
            'You first need to define UN and PSWD by running '
            "set_credentials('username', 'password')"
        )

        # Normalize kwargs to uppercase.
        uppercase_keys(kwargs)

        # Add kwargs as uppercased instance attributes.
        for key, value in kwargs.items():
            setattr(self, key, str(value))

        # TEST is a special case allowed for all ProcessTranx transactions.
        if self.METHOD == 'ProcessTranx' and PayTraceRequest._test_mode:
            # If test mode has been enabled by running set_test_mode(),
            # inject TEST here. All ProcessTranx requests will be submitted
            # as test transactions.
            self.TEST = 'Y'

        fields = set(self._fields)
        required = set(self._required)
        optional = set(self._optional)

        name = self.__class__.__name__

        # Overlapping required and optional fields check.
        assert not required & optional, (
            '{name}._required and {name}._optional must not overlap'
            .format(**locals())
        )
        # If conditional fields are defined, add at least one set to required.
        self._required = self._required[:]
        if hasattr(self, '_conditional'):
            for field, field_list in self._conditional.items():
                if field in kwargs:
                    self._required += field_list
                    required.update(field_list)
                    break
            else:
                field_sets = '\n'.join(
                    '  {0}'.format(field_list)
                    for field_list in self._conditional.values()
                )
                raise AssertionError(
                    'One of the following sets of fields is required:\n'
                    '{field_sets}'
                    .format(field_sets=field_sets)
                )
        # Missing fields check.
        missing = ', '.join(required - fields)
        if missing:
            raise KeyError(
                '{name} has missing fields: {missing}'.format(**locals())
            )
        # Extra fields check.
        extra = ', '.join(sorted(fields - required - optional))
        if extra:
            if self._discretionary_data_allowed is True:
                # Extra fields found but discretionary data is allowed.
                sys.stderr.write(
                    'Note: Extra fields found (ok if discretionary data): %s\n'
                    % extra
                )
            else:
                raise KeyError(
                    '{name} defines extra fields: {extra}'.format(**locals())
                )

    @classmethod
    def __classrepr__(cls):
        """
        Note: ipython3 doesn't seem to render class reprs correctly -- may be
        a bug in the beta version I used. Looks fine in python3 and ipython2.

        """
        def field_items(field_list):
            return list((attr, getattr(cls, attr, '')) for attr in field_list)

        def format_fields(field_list):
            s = ', '.join(
                '{field}={value!r}'.format(field=field.lower(), value=value)
                for field, value in field_items(field_list)
                if not value  # show only fields without default values
            )
            return s + ',' if s else '# <none>'

        textwrapper = TextWrapper(
            initial_indent=' ' * 4,
            subsequent_indent=' ' * 4,
        )
        l = []
        l.append('\n{cls.__name__}('.format(cls=cls))
        l.append('    # Required fields')
        l.append(textwrapper.fill(format_fields(cls._required)))
        if getattr(cls, '_conditional', None):
            for label, fields in cls._conditional.items():
                l.append('\n    # Required if using ' + label)
                l.append(textwrapper.fill(format_fields(fields)))
        if cls._discretionary_data_allowed is True:
            l.append(
                '\n    '
                '# Customer-defined discretionary data may also be included.'
            )
        l.append('\n    # Optional fields')
        l.append(textwrapper.fill(format_fields(cls._optional)))
        l.append(')\n')
        return '\n'.join(l)

    @property
    def _fields(self):
        return [s for s in dir(self) if not s.startswith('_')]

    def __str__(self):
        """
        Serialize into a PayTrace request string. For example,

        PARMLIST=METHOD%7EProcessTranx%7CPSWD%7Edemo123%7CTERMS%7EY%7CTRANXID
        %7E1539%7CTRANXTYPE%7EVoid%7CUN%7Edemo123%7C

        See section 3.2.

        """
        items = ((key, getattr(self, key)) for key in self._fields)
        params = '|'.join('~'.join(item) for item in items) + '|'
        request_string = urlencode(dict(PARMLIST=params))
        return request_string

    def __repr__(self):
        """
        Output an interpretable repr. For example,

        VoidRequest(**{'TRANXID': '1539', 'TRANXTYPE': 'Void',
          'UN': 'demo123', 'PSWD': 'demo123', 'TERMS': 'Y',
          'METHOD': 'ProcessTranx'})

        """
        d = dict((key, getattr(self, key)) for key in self._fields)
        return '{self.__class__.__name__}(**{d})'.format(self=self, d=d)


#
# Classes for processing transactions.
#

class Sale(PayTraceRequest):
    """
    Processing a sale through the PayTrace API may be accomplished by
    providing a new customer's swiped credit card information, a new customer's
    key entered credit card information, or the customer ID of an existing
    customer.

    {field_details}

    See section 4.1.1.

    """

    METHOD = 'ProcessTranx'
    TRANXTYPE = 'Sale'

    _required = [
        'UN', 'PSWD', 'TERMS', 'METHOD', 'TRANXTYPE', 'AMOUNT',
    ]
    _conditional = {
        'SWIPE': ['SWIPE'],
        'CC': ['CC', 'EXPMNTH', 'EXPYR'],
        'CUSTID': ['CUSTID']
    }
    _optional = [
        'BNAME', 'BADDRESS', 'BADDRESS2', 'BCITY', 'BSTATE', 'BZIP',
        'BCOUNTRY', 'SNAME', 'SADDRESS', 'SADDRESS2', 'SCITY', 'SCOUNTY',
        'SSTATE', 'SZIP', 'SCOUNTRY', 'EMAIL', 'CSC', 'INVOICE', 'DESCRIPTION',
        'TAX', 'CUSTREF', 'RETURNCLR', 'CUSTOMDBA', 'ENABLEPARTIALAUTH',
        'TEST'
    ]
    _discretionary_data_allowed = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Additional encoding of value is required when SWIPE is used;
        # see 3.3.1 SWIPE data definition for details.
        if 'SWIPE' in kwargs:
            kwargs['SWIPE'] = quote_plus(kwargs['SWIPE'].replace('|', '***'))


class Authorization(Sale):
    """
    Processing an authorization through the PayTrace API will request
    authorization for specified amount. However, the approved funds
    will not be charged or funded until the transaction is captured
    and settled.

    The required fields for processing an Authorization Request are the same
    as processing a Sale Request.

    See section 4.1.2.

    """

    TRANXTYPE = 'Authorization'


class Refund(PayTraceRequest):
    """
    Processing a refund through the PayTrace API may be accomplished by
    providing a new customer's swiped credit card information, providing a new
    customer's key entered credit card information, providing the customer ID
    of an existing customer, or providing the transaction ID of the original
    transaction that should be refunded.

    See section 4.1.3.

    """

    METHOD = 'ProcessTranx'
    TRANXTYPE = 'Refund'

    _required = [
        'UN', 'PSWD', 'TERMS', 'METHOD', 'TRANXTYPE'
    ]
    _conditional = {
        'SWIPE': ['AMOUNT', 'SWIPE'],
        'CC': ['AMOUNT', 'CC', 'EXPMNTH', 'EXPYR'],
        'CUSTID': ['AMOUNT', 'CUSTID'],
        'TRANXID': ['TRANXID']
    }
    _optional = [
        'BNAME', 'BADDRESS', 'BADDRESS2', 'BCITY', 'BSTATE', 'BZIP',
        'BCOUNTRY', 'SNAME', 'SADDRESS', 'SADDRESS2', 'SCITY', 'SCOUNTY',
        'SSTATE', 'SZIP', 'SCOUNTRY', 'EMAIL', 'CSC', 'INVOICE', 'DESCRIPTION',
        'TAX', 'CUSTREF', 'AMOUNT', 'TEST'
    ]
    _discretionary_data_allowed = True


class Void(PayTraceRequest):
    """
    Processing a void through the PayTrace API may only be accomplished by
    providing the transaction ID of the unsettled transaction that should
    be voided.

    See section 4.1.4.

    """

    METHOD = 'ProcessTranx'
    TRANXTYPE = 'Void'

    _required = [
        'UN', 'PSWD', 'TERMS', 'METHOD', 'TRANXTYPE', 'TRANXID'
    ]
    _optional = ['TEST']


class ForcedSale(PayTraceRequest):
    """
    Processing a forced sale through the PayTrace API may be accomplished by
    providing a new customer's swiped credit card information, providing a new
    customer's key entered credit card information, or providing the customer
    ID of an existing customer.  A forced sale is a sale where the approval
    code for the purchase amount has been obtained outside of the PayTrace
    Payment Gateway or has been voided from the settlement record.

    ForcedSale has the same fields as SaleRequest with the addition of
    APPROVAL.

    See section 4.1.5.

    """

    METHOD = 'ProcessTranx'
    TRANXTYPE = 'Force'

    _required = [
        'UN', 'PSWD', 'TERMS', 'METHOD', 'TRANXTYPE', 'AMOUNT', 'APPROVAL'
    ]
    _conditional = {
        'SWIPE': ['SWIPE'],
        'CC': ['CC', 'EXPMNTH', 'EXPYR'],
        'CUSTID': ['CUSTID']
    }
    _optional = [
        'UN', 'PSWD', 'TERMS', 'METHOD', 'TRANXTYPE', 'AMOUNT', 'SWIPE',
        'APPROVAL', 'TEST'
    ]


class Capture(PayTraceRequest):
    """
    Capturing a transaction updates an approved authorization to a pending
    settlement status that will initiate a transfer of funds. Processing a
    capture through the PayTrace API may only be accomplished by providing
    the transaction ID of the unsettled transaction that should be settled.

    See section 4.1.6.

    """

    METHOD = 'ProcessTranx'
    TRANXTYPE = 'Capture'

    _required = [
        'UN', 'PSWD', 'TERMS', 'METHOD', 'TRANXTYPE', 'TRANXID'
    ]
    _optional = ['TEST']


class CashAdvance(PayTraceRequest):
    """
    Processing a Cash Advance transaction is similar to processing a Sale;
    however, Cash Advances are special transactions that result in cash
    disbursements to the card holder.  Consequently, additional information is
    required to process Cash Advances. Cash Advances should always be swiped
    unless your card reader is not able to reader the card's magnetic stripe.
    Additionally, your PayTrace account must be specially configured to process
    this type of transaction.

    Please note that Cash Advances may also be processed as forced
    transactions by setting the TranxType to FORCE and including a valid
    APPROVAL value, all other fields remain the same.  Forced Cash Advance
    transactions should be also be swiped unless your card reader is not able
    to read the card's magnetic stripe.

    See section 4.1.7.

    """

    METHOD = 'ProcessTranx'
    TRANXTYPE = 'Sale'

    _required = [
        'UN', 'PSWD', 'TERMS', 'METHOD', 'TRANXTYPE', 'AMOUNT', 'SWIPE',
        'CASHADVANCE', 'PHOTOID', 'IDEXP', 'LAST4', 'BNAME', 'BADDRESS',
        'BADDRESS2', 'BCITY', 'BSTATE', 'BZIP'
    ]
    _optional = [
        'UN', 'PSWD', 'TERMS', 'METHOD', 'TRANXTYPE', 'AMOUNT', 'CC',
        'EXPMNTH', 'EXPYR', 'CASHADVANCE', 'PHOTOID', 'IDEXP', 'LAST4',
        'BNAME', 'BADDRESS', 'BADDRESS2', 'BCITY', 'BSTATE', 'BZIP', 'TEST'
    ]


class StoreAndForward(Sale):
    """
    Processing a store & forward through the PayTrace API will request that
    the transaction is stored for future authorization for specified amount.
    Please note that the authorization of the store & forward may be scheduled
    by provided a StrFwdDate value or manually via the Virtual Terminal.

    Note that swiped account numbers and *CSC* values are not stored.

    See section 4.1.8.

    """

    METHOD = 'ProcessTranx'
    TRANXTYPE = 'Str/FWD'


#
# Classes for managing customer profiles.
#

class CreateCustomer(PayTraceRequest):
    """
    Create a customer profile.

    """

    METHOD = 'CreateCustomer'

    _required = [
        'UN', 'PSWD', 'TERMS', 'METHOD', 'CUSTID', 'BNAME', 'CC', 'EXPMNTH',
        'EXPYR'
    ]
    _optional = [
        'BADDRESS', 'BADDRESS2', 'BCITY', 'BSTATE', 'BZIP', 'BCOUNTRY',
        'SNAME', 'SADDRESS', 'SADDRESS2', 'SCITY', 'SCOUNTY', 'SSTATE', 'SZIP',
        'SCOUNTRY', 'EMAIL', 'PHONE', 'FAX', 'CUSTPSWD', 'DDA', 'TR'
    ]
    _discretionary_data_allowed = True


class UpdateCustomer(PayTraceRequest):
    """
    Update an existing customer profile.

    """

    METHOD = 'UpdateCustomer'

    _required = [
        'UN', 'PSWD', 'TERMS', 'METHOD', 'CUSTID'
    ]
    _optional = [
        'BADDRESS', 'BADDRESS2', 'BCITY', 'BSTATE', 'BZIP', 'BCOUNTRY',
        'SNAME', 'SADDRESS', 'SADDRESS2', 'SCITY', 'SCOUNTY', 'SSTATE', 'SZIP',
        'SCOUNTRY', 'EMAIL', 'PHONE', 'FAX', 'CC', 'EXPMNTH', 'EXPYR',
        'CUSTPSWD', 'DDA', 'TR', 'NEWCUSTID'
    ]
    _discretionary_data_allowed = True


class DeleteCustomer(PayTraceRequest):
    """
    Delete an existing customer profile.

    """

    METHOD = 'DeleteCustomer'

    _required = [
        'UN', 'PSWD', 'TERMS', 'METHOD', 'CUSTID'
    ]
    _optional = []


#
# Emailing recepits
#

class EmailReceipt(PayTraceRequest):
    """
    Email a transaction or check receipt.

    """

    METHOD = 'EmailReceipt'

    _required = ['UN', 'PSWD', 'TERMS', 'METHOD', 'EMAIL']
    _conditional = {
        'TRANXID': ['TRANXID'],
        'CHECKID': ['CHECKID']
    }
    _optional = ['TRANXTYPE', 'CUSTID', 'USER', 'RETURNBIN', 'SEARCHTEXT']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        tranxtype = kwargs.get('TRANXTYPE')
        if tranxtype:
            assert tranxtype in ['SETTLED', 'PENDING', 'DECLINED']


#
# Exporting transaction information
#

class ExportTransaction(PayTraceRequest):
    """
    Export transaction information.

    See 4.4.

    Response from PayTrace support that explains how to use ExportTransaction
    to deal with "Service Unavailable" API responses.

    "Web servers typically restart when large volumes of transactions
    processing from our gateway, or when we release product updates into our
    production environment. One work around that you can try that does not
    involve manually logging into the site would be to perform an export
    transaction request to our gateway if you happen to receive this response.
    This essentially would be a "query" to our gateway that would check to
    see if the transaction had really processed if you receive a
    "service unavailable" response. This call to our API is outlined here --
    http://help.paytrace.com/api-export-transaction-information.
    You can use the "searchtext" parameter in your request to narrow down which
    transaction you are looking for to see if it truly had been processed. If
    it was processed, it will return the details of your transaction to parse
    through and store -- and then you can move on to your next transaction. If
    the transaction has not processed, no results will be returned letting you
    know if the transaction truly did not process."

    """

    METHOD = 'ExportTranx'

    _required = ['UN', 'PSWD', 'TERMS', 'METHOD']
    _conditional = {
        'TRANXID': ['TRANXID'],
        'SDATE': ['SDATE', 'EDATE']
    }
    _optional = ['TRANXTYPE', 'CUSTID', 'USER', 'RETURNBIN', 'SEARCHTEXT']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Validate TRANXTYPE value.
        allowed_tranxtypes = [
            'Sale', 'Authorization', 'Str/Fwd', 'Refund', 'Void', 'Capture',
            'Force', 'SETTLED', 'PENDING', 'DECLINED'
        ]
        tranxtype = kwargs.get('TRANXTYPE')
        assert tranxtype is None or tranxtype in allowed_tranxtypes, (
            'Invalid TRANXTYPE value: %r (allowed values: %s)'
            % (tranxtype, allowed_tranxtypes)
        )


class ExportBatch(PayTraceRequest):
    """
    Export batch information.

    See 4.12.

    """

    METHOD = 'ExportBatch'

    _required = ['UN', 'PSWD', 'TERMS', 'METHOD']
    _optional = ['SDATE', 'BATCHNUMBER']


# TODO: Implement 4.5, 4.6, 4.7, 4.8, 4.9, 4.11, 4.13, 4.14.

class SettleTranxRequest(PayTraceRequest):
    """
    4.10 Settling Transactions Through the PayTrace API

    Transactions processed through merchant accounts that are set up on the
    TSYS/Vital network or other terminal-based networks may initiate the
    settlement of batches through the PayTrace API.

    See section 4.10.

    """

    METHOD = 'SETTLETRANX'

    _required = [
        'UN', 'PSWD', 'TERMS', 'METHOD'
    ]
    _optional = []


def _test():
    """
    Send Authorization and Void requests to the PayTrace demo account using
    the demo credit card shown in the PayTrace API docs.

    """
    import time

    print("""
                    === API usage example ===

    >>> # 1. Set credentials for the PayTrace demo account.
    >>> set_credentials('demo123', 'demo123')
    """)
    time.sleep(2)

    print("""
    >>> # 2. Sending Authorization request to PayTrace demo account...
    >>> authorization = Authorization(
    ...     amount='1.00',
    ...     cc='4012881888818888',
    ...     expmnth='01',
    ...     expyr='15',
    ...     csc='999',
    ...     baddress='123 Main St.',
    ...     bzip='53719',
    ...     invoice='8888',
    ... )
    >>> response = send_api_request(authorization)""")
    authorization = Authorization(
        amount='1.00',
        cc='4012881888818888',
        expmnth='01',
        expyr='15',
        csc='999',
        baddress='123 Main St.',
        bzip='53719',
        invoice='8888',
    )
    response = send_api_request(authorization)

    print("""\
    >>> response
    {response}
    """.format(**locals()))

    print("""\
    >>> # 3. Grab the transaction ID from the response.
    >>> transactionid = response['TRANSACTIONID']
    """)

    time.sleep(2)
    print("""\
    >>> # 4. Sending Void request to cancel authorization...
    >>> void = Void(
            tranxid=transactionid
        )
    >>> response = send_api_request(void)""")
    transactionid = response['TRANSACTIONID']
    void = Void(tranxid=transactionid)
    response = send_api_request(void)
    print("""\
    >>> response
    {response}

                  === end API usage example ===

    """.format(**locals()))

    input('Type <enter> to continue...')
    print("""

    # NOTE: To explore more of the API, run dir() to see what's in the current
    # namespace. To see the required and optional fields for a particular
    # request class, print it's repr. For example,

    >>> Sale  # Note: if using ipython, you'll need to use repr(Sale) instead
    Sale(
        # Required fields
        amount='',

        # Required if using CC
        cc='', expmnth='', expyr='',

        # Required if using SWIPE
        swipe='',

        # Required if using CUSTID
        custid='',

        # Customer-defined discretionary data may also be included.

        # Optional fields
        bname='', baddress='', baddress2='', bcity='', bstate='', bzip='',
        bcountry='', sname='', saddress='', saddress2='', scity='',
        scounty='', sstate='', szip='', scountry='', email='', csc='',
        invoice='', description='', tax='', custref='', returnclr='',
        customdba='', enablepartialauth='', test='',
    )
    """.format(**locals()))

if __name__ == '__main__':
    print("""
    To explore the API, run 'python3 -i paytrace.py', then call the _test()
    function. By default, credentials for the PayTrace demo account are in
    effect.

    >>> set_credentials('demo123', 'demo123')
    >>> # now you call _test()...
    """)
    set_credentials('demo123', 'demo123')

