"""
Some useful API utilities.
"""


def split_list(args, fld_nm):
    if isinstance(args.get(fld_nm), str):
        args[fld_nm] = args[fld_nm].split(',')
    return args.get(fld_nm)


def get_req_headers(request):
    return dict(request.headers)
