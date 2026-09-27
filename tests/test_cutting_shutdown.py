import signal
import pytest
from cutting import Shutdown, StopRequested


def test_repeated_ctrl_c_defers_exception_and_restores_handler(capsys):
    previous = signal.getsignal(signal.SIGINT)
    shutdown = Shutdown()
    with shutdown.installed():
        for _ in range(3):
            signal.raise_signal(signal.SIGINT)
        assert shutdown.requested
        with pytest.raises(StopRequested):
            shutdown.check()
    assert signal.getsignal(signal.SIGINT) == previous
    assert capsys.readouterr().out.count('Kończenie') == 1
