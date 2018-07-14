from ereuse_devicehub.devicehub import Devicehub


def test_dummy(_app: Devicehub):
    """Tests the dummy cli command."""
    runner = _app.test_cli_runner()
    runner.invoke(args=['dummy', '--yes'], catch_exceptions=False)
