import sys

def exception_hook(exc_type, exc_value, tb):
    print(f"{exc_type.__name__}, Message: {exc_value}", file=sys.stderr)
    local_vars = {}
    while tb:
        filename = tb.tb_frame.f_code.co_filename
        name = tb.tb_frame.f_code.co_name
        line_no = tb.tb_lineno
        print(f"  {filename}:{line_no}, in {name}", file=sys.stderr)

        local_vars = tb.tb_frame.f_locals
        tb = tb.tb_next

sys.excepthook = exception_hook
