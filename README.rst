paytrace
========

A Python 3 client library for the `PayTrace Payment Gateway <https://paytrace.com/>`_ public `API <https://paytrace.com/api.html>`_.

The PayTrace API is documented in a single PDF file available here: https://paytrace.com/manuals/PayTraceAPIUserGuideXML.pdf (dated July, 2011).

API usage example
-----------------

% python3 -i paytrace.py 

    To explore the API, run 'python3 -i paytrace.py', then call the _test()
    function. By default, credentials for the PayTrace demo account are in
    effect.

    >>> set_credentials('demo123', 'demo123')
    >>> # now you call _test()...
    
>>> _test()

                    === API usage example ===

    >>> # 1. Set credentials for the PayTrace demo account.
    >>> set_credentials('demo123', 'demo123')
    

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
    >>> response = send_api_request(authorization)
    >>> response
    {'AVSRESPONSE': 'No Match', 'APPCODE': 'TAS113', 'APPMSG': '  NO  MATCH      - Approved and completed', 'CSCRESPONSE': 'Match', 'TRANSACTIONID': '26303013', 'RESPONSE': '101. Your transaction was successfully approved.'}
    
    >>> # 3. Grab the transaction ID from the response.
    >>> transactionid = response['TRANSACTIONID']
    
    >>> # 4. Sending Void request to cancel authorization...
    >>> void = Void(
            tranxid=transactionid
        )
    >>> response = send_api_request(void)
    >>> response
    {'TRANSACTIONID': '26303013', 'RESPONSE': '109. Your transaction was successfully voided.'}

                  === end API usage example ===

    
Type <enter> to continue...


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
    
>>> 

