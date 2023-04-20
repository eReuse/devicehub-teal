from flask.testing import FlaskCliRunner


class TealCliRunner(FlaskCliRunner):
    """The same as FlaskCliRunner but with invoke's
    'catch_exceptions' as False.
    """

    def invoke(self, *args, cli=None, **kwargs):
        kwargs.setdefault('catch_exceptions', False)
        r = super().invoke(cli, args, **kwargs)
        assert r.exit_code == 0, 'CLI code {}: {}'.format(r.exit_code, r.output)
        return r
