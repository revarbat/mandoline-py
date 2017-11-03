def float_fmt(val):
    """
    Returns a short, clean floating point string representation.
    Unnecessary trailing zeroes and decimal points are trimmed off.
    """
    s = "{0:.6f}".format(val).rstrip('0').rstrip('.')
    return s if s != '-0' else '0'


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
